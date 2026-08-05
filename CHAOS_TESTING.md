# Chaos Engineering Report — EMA Backtester AIOps

This report documents controlled failure injection tests performed against
the EMA Backtester platform to validate the AIOps incident response system
(Prometheus → AlertManager → MCP Server → Claude API → Slack).

Date: August 5, 2026
Environment: Local Kubernetes (Docker Desktop)

---

## Methodology

For each scenario:
1. Record start timestamp
2. Inject failure
3. Trigger incident analysis (simulating automated AlertManager webhook call)
4. Record timestamp when Slack notification is confirmed posted
5. Calculate MTTR (Mean Time To Resolution/Response)
6. Evaluate diagnosis accuracy against known root cause

---

## Scenario 1: Pod Deletion (Crash Simulation)

**Failure injected:** `kubectl delete pod` on the running backtester pod

**MTTR:** 2 minutes 10 seconds
- Kubernetes self-heal (new pod scheduled): ~34 seconds
- Analysis + Slack notification: ~1 minute 36 seconds

**Claude's diagnosis:**

SEVERITY: Info
ROOT CAUSE: No incident detected — deployment healthy, replicas available
IMPACT: No impact — service operating normally
RECOMMENDED ACTION: No action required. Noted: pod logs are empty,
consider verifying application is actively processing.


**Accuracy assessment:** Correct. Kubernetes' self-healing resolved the
issue before analysis ran, so "no incident" was the accurate conclusion.
Claude additionally flagged that logs were empty — a genuinely useful
observation, since the app only logs on HTTP requests and none had been
made yet.

---

## Scenario 2: Database Connection Failure (DNS Resolution)

**Failure injected:** `kubectl set env` to point `DB_HOST` at a
nonexistent hostname, forcing a DNS resolution failure on startup —
same failure class as a real incident encountered during Project 2.

**MTTR:** 1 minute 33 seconds

**Claude's diagnosis:**

SEVERITY: Critical
ROOT CAUSE: Application cannot start due to invalid database hostname
"broken-nonexistent-host". DNS resolution is failing because the
hostname does not exist.
IMPACT: Pods crash-looping on startup. Application non-functional.
RECOMMENDED ACTION: Update the database connection configuration
(ConfigMap/Secret) with the correct PostgreSQL hostname, then restart
the deployment.


**Accuracy assessment:** Excellent. Exact root cause identified from
pod logs, correct severity, specific and actionable remediation step.
This matches how a human SRE would diagnose the same failure class.

---

## Scenario 3: Resource Exhaustion (OOM Kill)

**Failure injected:** Patched deployment memory limit to 20Mi (far
below application requirements), causing the container to be killed
by the kernel OOM killer (`OOMKilled`, exit code 137).

**MTTR:** 1 minute 44 seconds

**Claude's diagnosis:**

SEVERITY: Warning
ROOT CAUSE: Inconsistent replica state detected — deployment reports
1 available and 1 ready replica, but also 1 unavailable, which is
mathematically impossible with desired_replicas=1. Indicates either
a rollout in progress or a status reporting anomaly.
RECOMMENDED ACTION: Check actual pod states, describe deployment,
check for CrashLooping or ImagePullBackOff.


**Accuracy assessment:** Partial. Claude correctly identified an
anomaly and recommended reasonable diagnostic commands, but did not
pinpoint OOMKilled as the specific cause. Root cause: our
`get_deployment_status` tool exposes replica counts and conditions,
but not container-level `lastState.reason` (which contains "OOMKilled").
Additionally, OOM-killed containers rarely produce useful application
logs since the kernel terminates the process before it can log
anything.

**This is a genuine, documented limitation of the current tool schema
— not a hidden failure.**

---

## Summary

| Metric | Value |
|--------|-------|
| Scenarios tested | 3 |
| Average MTTR | 1 minute 49 seconds |
| Fully accurate diagnoses | 2 of 3 (67%) |
| Partially accurate diagnoses | 1 of 3 (33%) |
| False negatives | 0 |
| System failures (webhook/API errors) | 0 |

---

## Key Findings

1. **Diagnosis accuracy correlates with data richness.** When application
   logs contain clear error messages (Scenario 2), Claude's diagnosis is
   near-perfect. When the failure is infrastructure-level with sparse
   logs (Scenario 3), diagnosis quality degrades to "correctly identifies
   something is wrong" without pinpointing the exact mechanism.

2. **MTTR is dominated by the Claude API call, not data gathering.**
   Kubernetes API calls (get logs, get status) complete in milliseconds.
   The majority of the 1.5-2 minute MTTR is the round trip to Claude API
   plus Slack webhook posting.

3. **Tool schema gaps directly impact AI diagnosis quality.** This
   validates the MCP design principle — the AI is only as good as the
   context tools provide. Improving `get_deployment_status` to include
   container `lastState.reason` and OOM-specific metrics would likely
   improve Scenario 3-class diagnosis accuracy significantly.

---

## Future Improvements (identified via this testing)

1. Add container `lastState.reason` and exit codes to `get_deployment_status`
2. Add a dedicated `get_pod_events` tool (surfaces OOMKilled, Evicted,
   ImagePullBackOff reasons directly from Kubernetes events)
3. Add memory/CPU usage metrics from `kube_pod_container_resource_usage`
   to give Claude quantitative context, not just qualitative status
4. Investigate reducing MTTR by using Claude's streaming API to post a
   preliminary Slack message immediately, then update with full analysis