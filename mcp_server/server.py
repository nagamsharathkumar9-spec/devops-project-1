"""
MCP Server for EMA Backtester Platform
Exposes safe, scoped tools for Claude to inspect and (with approval) act on
the Kubernetes cluster running the backtester.

Guardrail principle:
- READ tools execute immediately, no approval needed
- WRITE tools require a valid approval_token, generated per-incident
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kubernetes import client, config
from anthropic import Anthropic
from datetime import datetime
import secrets
import os

app = FastAPI(title="EMA Backtester MCP Server", version="1.0")

# ============================================================
# Load Kubernetes config
# Works both in-cluster (when deployed) and locally (via kubeconfig)
# ============================================================
try:
    config.load_incluster_config()
    print("Loaded in-cluster Kubernetes config")
except config.ConfigException:
    config.load_kube_config()
    print("Loaded local kubeconfig")

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

# ============================================================
# Claude API client
# ============================================================
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
claude_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# ============================================================
# In-memory approval token store
# In production this would be Redis or a database with TTL
# ============================================================
APPROVAL_TOKENS = {}
NAMESPACE = os.environ.get("K8S_NAMESPACE", "default")


# ============================================================
# Request/Response Models
# ============================================================
class PodLogsRequest(BaseModel):
    pod_name: str
    lines: int = 100


class DeploymentStatusRequest(BaseModel):
    deployment_name: str


class RestartPodRequest(BaseModel):
    pod_name: str
    approval_token: str


class ApprovalRequest(BaseModel):
    reason: str


class IncidentAnalysisRequest(BaseModel):
    pod_name: str
    deployment_name: str
    lines: int = 50


# ============================================================
# TOOL 1 (READ): Get Pod Logs
# ============================================================
@app.post("/tools/get_pod_logs")
def get_pod_logs(req: PodLogsRequest):
    """
    Read-only. Returns the last N lines of logs from a specific pod.
    No approval required — this is a safe, non-destructive operation.
    """
    try:
        logs = v1.read_namespaced_pod_log(
            name=req.pod_name,
            namespace=NAMESPACE,
            tail_lines=req.lines,
            _preload_content=True
        )
        if isinstance(logs, str) and logs.startswith("b'") and logs.endswith("'"):
            logs = logs[2:-1].encode().decode("unicode_escape")

        return {
            "pod_name": req.pod_name,
            "namespace": NAMESPACE,
            "lines_requested": req.lines,
            "logs": logs
        }
    except client.exceptions.ApiException as e:
        raise HTTPException(status_code=404, detail=f"Pod not found or error: {e.reason}")


# ============================================================
# TOOL 2 (READ): Get Deployment Status
# ============================================================
@app.post("/tools/get_deployment_status")
def get_deployment_status(req: DeploymentStatusRequest):
    """
    Read-only. Returns replica counts, conditions, and health of a deployment.
    No approval required.
    """
    try:
        deployment = apps_v1.read_namespaced_deployment(
            name=req.deployment_name,
            namespace=NAMESPACE
        )
        conditions = [
            {
                "type": c.type,
                "status": c.status,
                "message": c.message,
                "last_transition": str(c.last_transition_time)
            }
            for c in (deployment.status.conditions or [])
        ]
        return {
            "deployment_name": req.deployment_name,
            "namespace": NAMESPACE,
            "desired_replicas": deployment.spec.replicas,
            "available_replicas": deployment.status.available_replicas or 0,
            "ready_replicas": deployment.status.ready_replicas or 0,
            "unavailable_replicas": deployment.status.unavailable_replicas or 0,
            "conditions": conditions
        }
    except client.exceptions.ApiException as e:
        raise HTTPException(status_code=404, detail=f"Deployment not found or error: {e.reason}")


# ============================================================
# AI ANALYSIS: Claude-powered incident analysis
# ============================================================
@app.post("/analyze_incident")
def analyze_incident(req: IncidentAnalysisRequest):
    """
    Gathers context (logs + deployment status) and asks Claude to produce
    a plain-English incident analysis with likely root cause and
    recommended next steps.
    """
    if not claude_client:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    try:
        logs_data = get_pod_logs(PodLogsRequest(pod_name=req.pod_name, lines=req.lines))
    except HTTPException as e:
        logs_data = {"error": str(e.detail), "logs": ""}

    try:
        status_data = get_deployment_status(DeploymentStatusRequest(deployment_name=req.deployment_name))
    except HTTPException as e:
        status_data = {"error": str(e.detail)}

    prompt = f"""You are an SRE assistant analyzing a Kubernetes incident.

DEPLOYMENT STATUS:
{status_data}

RECENT POD LOGS (last {req.lines} lines):
{logs_data.get('logs', 'No logs available')}

Provide a concise incident analysis in this exact format:
1. SEVERITY: (Critical/Warning/Info)
2. LIKELY ROOT CAUSE: (one or two sentences)
3. IMPACT: (what is affected)
4. RECOMMENDED ACTION: (specific next step)

Be direct and technical. This will be posted to a Slack channel for on-call engineers."""

    try:
        message = claude_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        analysis = message.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")

    return {
        "pod_name": req.pod_name,
        "deployment_name": req.deployment_name,
        "analysis": analysis,
        "raw_context": {
            "deployment_status": status_data,
            "log_lines_analyzed": req.lines
        }
    }


# ============================================================
# APPROVAL: Generate a one-time approval token
# ============================================================
@app.post("/tools/request_approval")
def request_approval(req: ApprovalRequest):
    """
    Generates a one-time approval token for a write operation.
    """
    token = secrets.token_urlsafe(16)
    APPROVAL_TOKENS[token] = {
        "reason": req.reason,
        "issued_at": datetime.utcnow().isoformat(),
        "used": False
    }
    return {
        "approval_token": token,
        "reason": req.reason,
        "expires_note": "Token is single-use and valid for this session only"
    }


# ============================================================
# TOOL 3 (WRITE): Restart a Pod — REQUIRES APPROVAL TOKEN
# ============================================================
@app.post("/tools/restart_pod")
def restart_pod(req: RestartPodRequest):
    """
    WRITE operation. Deletes the specified pod — Kubernetes will
    recreate it automatically if it's managed by a Deployment/ReplicaSet.
    """
    token_data = APPROVAL_TOKENS.get(req.approval_token)

    if not token_data:
        raise HTTPException(status_code=403, detail="Invalid or unknown approval token")

    if token_data["used"]:
        raise HTTPException(status_code=403, detail="Approval token already used")

    try:
        v1.delete_namespaced_pod(name=req.pod_name, namespace=NAMESPACE)
        token_data["used"] = True
        return {
            "action": "restart_pod",
            "pod_name": req.pod_name,
            "status": "deleted — kubernetes will recreate automatically",
            "approved_reason": token_data["reason"]
        }
    except client.exceptions.ApiException as e:
        raise HTTPException(status_code=404, detail=f"Pod not found or error: {e.reason}")


# ============================================================
# Health check for the MCP server itself
# ============================================================
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "mcp-server",
        "claude_configured": claude_client is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)