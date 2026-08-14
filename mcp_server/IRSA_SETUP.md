# IRSA Setup — mcp-server-sa

## Summary
Configured IAM Roles for Service Accounts (IRSA) for the MCP server's
Kubernetes ServiceAccount, replacing the default (and insecure) pattern
of relying on broad, node-level IAM permissions.

## Why
By default, any pod running on an EKS worker node inherits whatever IAM
permissions are attached to that node's IAM role. This means every pod
on a node has the same AWS access, even pods that have no legitimate
need for it. IRSA scopes IAM permissions to a specific Kubernetes
ServiceAccount instead, enforced via OIDC federation, so only pods using
that exact ServiceAccount (in a specific namespace) get those permissions.

This also resolves a warning eksctl prints by default:

recommended policies were found for "vpc-cni" addon, but since OIDC is
disabled on the cluster, eksctl cannot configure the requested permissions


## What was built
1. **OIDC provider** associated with the cluster via
   `eksctl utils associate-iam-oidc-provider`
2. **IAM policy** (`mcp-server-cloudwatch-read`) — scoped to
   `logs:GetLogEvents`, `DescribeLogStreams`, `DescribeLogGroups` on a
   single log group ARN only, not `*`
3. **IAM role** (`mcp-server-irsa-role`) — trust policy restricts
   `sts:AssumeRoleWithWebIdentity` to only the `mcp-server-sa`
   ServiceAccount in the `default` namespace, via OIDC `sub` and `aud`
   condition checks
4. **ServiceAccount annotation** — `mcp-rbac.yaml` now includes
   `eks.amazonaws.com/role-arn` pointing at the role. EKS's Pod Identity
   webhook automatically injects short-lived, auto-rotating credentials
   into any pod using this ServiceAccount — no static keys involved.

## Live test results (2026-08-14)
Ran a test pod using `mcp-server-sa` and verified:

| Test | Command | Result |
|---|---|---|
| Identity | `aws sts get-caller-identity` | Confirmed `assumed-role/mcp-server-irsa-role`, not the node role |
| Permitted action | `aws logs describe-log-streams` on the granted log group | Succeeded |
| Unpermitted action | `aws s3 ls` | **AccessDenied** — proves the scope is real, not just documented |

## Trade-offs / notes
- Granted permission was CloudWatch Logs read-only, chosen as a small,
  real, testable example since the MCP server doesn't currently call
  AWS APIs directly in `server.py`.
- EKS cluster was created fresh for this session (no OIDC enabled by
  default on `eksctl create cluster` without extra flags) and deleted
  after testing to avoid ongoing cost.
