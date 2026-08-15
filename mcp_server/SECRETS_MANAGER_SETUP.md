# Secrets Manager + IRSA — mcp-server-sa

## Summary
Moved MCP server secrets (Anthropic API key, Slack webhook URL) from raw
Kubernetes Secrets into AWS Secrets Manager, fetched at runtime via IRSA
using the same `mcp-server-sa` ServiceAccount established in Session C.

## Why
Kubernetes Secrets are only base64-encoded, not encrypted, and anyone with
`get` access to the namespace can read them in plaintext. Secrets Manager
provides real encryption at rest, automatic rotation support, and access
auditing via CloudTrail, none of which raw K8s Secrets offer on their own.

## What was built
1. Two secrets created in Secrets Manager:
   - `mcp-server/anthropic-api-key`
   - `mcp-server/slack-webhook`
2. IAM policy (`mcp-server-secrets-read`) — scoped to `secretsmanager:GetSecretValue`
   on exactly these two secret ARNs, not `*`
3. IAM role (`mcp-server-secrets-irsa-role`) — trust policy restricted to
   `mcp-server-sa` in the `default` namespace via OIDC sub/aud conditions
   (same pattern as Session C's IRSA setup)
4. `mcp-rbac.yaml` ServiceAccount annotation updated to point at this role

## Live test results (2026-08-15)
Ran a test pod using `mcp-server-sa` and verified:

| Test | Result |
|---|---|
| Fetch `anthropic-api-key` secret | Succeeded |
| Fetch `slack-webhook` secret | Succeeded |
| Fetch a third, ungranted secret (`off-limits-test`) | **AccessDeniedException** — confirms the permission boundary is real |

## Next step (not yet done)
`server.py` currently reads secrets via K8s Secret env vars
(`ANTHROPIC_API_KEY`, `SLACK_WEBHOOK_URL`). To fully adopt this pattern,
the app would call `boto3.client('secretsmanager').get_secret_value(...)`
at startup instead. Not changed in this session to keep the scope focused
on proving the IRSA + Secrets Manager mechanism works.

## Trade-offs / notes
- EKS cluster created fresh for this session and deleted after testing.
- A new IAM role was created (`mcp-server-secrets-irsa-role`) rather than
  reusing Session C's role, since that role was deleted during that
  session's teardown.
