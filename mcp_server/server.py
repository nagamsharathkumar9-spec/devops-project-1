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
import re
import requests
import psycopg2

app = FastAPI(title="EMA Backtester MCP Server", version="1.0")

# ============================================================
# Load Kubernetes config
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
# Slack webhook
# ============================================================
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

# ============================================================
# PostgreSQL connection for post-mortem storage
# ============================================================
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "postgres-postgresql.default.svc.cluster.local"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME", "backtestdb"),
    "user": os.environ.get("DB_USER", "backtester"),
    "password": os.environ.get("DB_PASSWORD", "backtester123"),
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_postmortem_db():
    """Creates the incident_postmortems table if it doesn't exist."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS incident_postmortems (
                id SERIAL PRIMARY KEY,
                alert_name TEXT,
                pod_name TEXT,
                deployment_name TEXT,
                severity TEXT,
                analysis TEXT,
                detected_at TIMESTAMP DEFAULT NOW(),
                slack_posted BOOLEAN DEFAULT FALSE
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("Post-mortem table initialized.")
    except Exception as e:
        print(f"Could not initialize post-mortem table: {e}")


init_postmortem_db()

# ============================================================
# In-memory approval token store
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
    alert_name: str = "manual_trigger"


# ============================================================
# TOOL 1 (READ): Get Pod Logs
# ============================================================
@app.post("/tools/get_pod_logs")
def get_pod_logs(req: PodLogsRequest):
    """Read-only. Returns the last N lines of logs from a specific pod."""
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
    """Read-only. Returns replica counts, conditions, and health of a deployment."""
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
# HELPER: Extract severity from Claude's structured analysis
# ============================================================
def extract_severity(analysis_text: str) -> str:
    match = re.search(r"SEVERITY:\**\s*\**\s*(Critical|Warning|Info)", analysis_text, re.IGNORECASE)
    return match.group(1).capitalize() if match else "Unknown"


# ============================================================
# HELPER: Post formatted message to Slack
# ============================================================
def post_to_slack(alert_name: str, pod_name: str, deployment_name: str, severity: str, analysis: str) -> bool:
    if not SLACK_WEBHOOK_URL:
        print("SLACK_WEBHOOK_URL not configured, skipping Slack post")
        return False

    severity_emoji = {
        "Critical": "🔴",
        "Warning": "🟡",
        "Info": "🟢",
        "Unknown": "⚪"
    }.get(severity, "⚪")

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} Incident Alert: {alert_name}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Deployment:*\n{deployment_name}"},
                    {"type": "mrkdwn", "text": f"*Pod:*\n{pod_name}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity}"},
                    {"type": "mrkdwn", "text": f"*Detected:*\n{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*AI Analysis:*\n```{analysis}```"
                }
            }
        ]
    }

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=message, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Slack post failed: {e}")
        return False


# ============================================================
# HELPER: Save post-mortem to PostgreSQL
# ============================================================
def save_postmortem(alert_name: str, pod_name: str, deployment_name: str, severity: str, analysis: str, slack_posted: bool):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO incident_postmortems
               (alert_name, pod_name, deployment_name, severity, analysis, slack_posted)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (alert_name, pod_name, deployment_name, severity, analysis, slack_posted)
        )
        conn.commit()
        cur.close()
        conn.close()
        print(f"Post-mortem saved for alert: {alert_name}")
    except Exception as e:
        print(f"Failed to save post-mortem: {e}")


# ============================================================
# AI ANALYSIS: Claude-powered incident analysis
# Now posts to Slack and saves to PostgreSQL automatically
# ============================================================
@app.post("/analyze_incident")
def analyze_incident(req: IncidentAnalysisRequest):
    """
    Gathers context, asks Claude to analyze, posts to Slack, saves to DB.
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
            messages=[{"role": "user", "content": prompt}]
        )
        analysis = message.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claude API error: {str(e)}")

    severity = extract_severity(analysis)

    slack_posted = post_to_slack(
        alert_name=req.alert_name,
        pod_name=req.pod_name,
        deployment_name=req.deployment_name,
        severity=severity,
        analysis=analysis
    )

    save_postmortem(
        alert_name=req.alert_name,
        pod_name=req.pod_name,
        deployment_name=req.deployment_name,
        severity=severity,
        analysis=analysis,
        slack_posted=slack_posted
    )

    return {
        "pod_name": req.pod_name,
        "deployment_name": req.deployment_name,
        "severity": severity,
        "analysis": analysis,
        "slack_posted": slack_posted,
        "raw_context": {
            "deployment_status": status_data,
            "log_lines_analyzed": req.lines
        }
    }


# ============================================================
# WEBHOOK: Receives alerts from Prometheus AlertManager
# ============================================================
@app.post("/webhook/alert")
def receive_alert(payload: dict):
    """AlertManager POSTs here when an alert fires."""
    alerts = payload.get("alerts", [])
    results = []

    for alert in alerts:
        labels = alert.get("labels", {})
        status = alert.get("status", "unknown")

        if status != "firing":
            continue

        alert_name = labels.get("alertname", "unknown")
        deployment_name = labels.get("deployment", "")
        pod_name = labels.get("pod", "")

        # Skip alerts that don't specify our application deployment
        if not deployment_name:
            results.append({
                "alert_name": alert_name,
                "status": "skipped",
                "reason": "no deployment label - not an application alert"
            })
            continue

        print(f"Alert received: {alert_name} | status={status} | pod={pod_name}")

        if not pod_name:
            try:
                pods = v1.list_namespaced_pod(
                    namespace=NAMESPACE,
                    label_selector=f"app={deployment_name}"
                )
                if pods.items:
                    pod_name = pods.items[0].metadata.name
            except Exception as e:
                print(f"Could not find pod for deployment {deployment_name}: {e}")

        if not pod_name:
            results.append({
                "alert_name": alert_name,
                "status": "skipped",
                "reason": "no pod found to analyze"
            })
            continue

        try:
            analysis_result = analyze_incident(
                IncidentAnalysisRequest(
                    pod_name=pod_name,
                    deployment_name=deployment_name,
                    lines=50,
                    alert_name=alert_name
                )
            )
            results.append({
                "alert_name": alert_name,
                "status": "analyzed",
                "severity": analysis_result["severity"],
                "slack_posted": analysis_result["slack_posted"]
            })
            print(f"Auto-analysis complete for alert: {alert_name}")
        except Exception as e:
            results.append({
                "alert_name": alert_name,
                "status": "error",
                "reason": str(e)
            })

    return {"processed_alerts": len(results), "results": results}


# ============================================================
# QUERY: Get historical post-mortems
# ============================================================
@app.get("/postmortems")
def get_postmortems(limit: int = 20):
    """Returns recent incident post-mortems from the database."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT id, alert_name, pod_name, deployment_name, severity,
                      analysis, detected_at, slack_posted
               FROM incident_postmortems
               ORDER BY detected_at DESC
               LIMIT %s""",
            (limit,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id": r[0],
                "alert_name": r[1],
                "pod_name": r[2],
                "deployment_name": r[3],
                "severity": r[4],
                "analysis": r[5],
                "detected_at": r[6].isoformat(),
                "slack_posted": r[7]
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ============================================================
# APPROVAL: Generate a one-time approval token
# ============================================================
@app.post("/tools/request_approval")
def request_approval(req: ApprovalRequest):
    """Generates a one-time approval token for a write operation."""
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
    """WRITE operation. Deletes the specified pod — Kubernetes recreates it."""
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
# Health check
# ============================================================
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "mcp-server",
        "claude_configured": claude_client is not None,
        "slack_configured": SLACK_WEBHOOK_URL is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)