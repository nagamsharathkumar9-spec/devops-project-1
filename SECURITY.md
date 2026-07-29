# Security Policy — EMA Backtester Platform

## Security Posture

### Container Security
- **Non-root user:** Container runs as `appuser` (uid=1001), never root
- **Pinned base image:** `python:3.14-slim@sha256:cea0e604...` — immutable, no surprise updates
- **Multi-stage build:** Build tools never exist in the runtime image
- **Minimal image:** Only 3 application files copied into container
- **Vulnerability scanning:** Trivy scans every image in CI/CD pipeline

### Kubernetes Security
- **Least-privilege RBAC:** Dedicated ServiceAccount (`ema-backtester-sa`)
  with a Role that only allows `get` on the specific `postgres-credentials` Secret
- **NetworkPolicy:** Backtester pod can only communicate with PostgreSQL (port 5432)
  and DNS (port 53). No other egress or ingress allowed.
- **Pod Disruption Budget:** Ensures availability during maintenance
- **Resource limits:** CPU and memory limits prevent resource exhaustion attacks

### Secrets Management
- **No secrets in code:** All credentials injected at runtime via Kubernetes Secrets
- **No secrets in Git:** `.gitignore` excludes `.env` files and Terraform state
- **Separation of concerns:** Non-sensitive config in ConfigMap, sensitive data in Secrets
- **CI/CD secrets:** AWS credentials stored as GitHub Secrets, never in workflow YAML

### AWS Security
- **IAM least privilege:** `sharath-admin` IAM user with AdministratorAccess
  (to be scoped down in production)
- **MFA on root account:** Root account protected with authenticator app
- **ECR scan on push:** Every pushed image automatically scanned for CVEs
- **CloudWatch audit logs:** All EKS control plane actions logged

---

## Known Vulnerabilities

Trivy scans regularly identify vulnerabilities in the `python:3.14-slim` base image
OS packages (glibc, perl, ncurses, etc.). These are tracked and addressed when
patches are available.

**Current status:** Base OS vulnerabilities present. Application code (Python,
pandas, yfinance, psycopg2) is clean with no known CVEs.

---

## Compliance Awareness

This is a learning/portfolio project. In a production fintech environment,
additional controls would be required:

### PCI DSS (if handling payment data)
- Encrypt data at rest (AWS KMS for EBS volumes)
- Encrypt data in transit (TLS everywhere)
- Maintain audit logs of all data access
- Implement data retention and deletion policies
- Regular penetration testing

### GDPR (if handling EU user data)
- No PII is stored in this system (backtest results only)
- Would require data subject access request (DSAR) process
- Data residency requirements (keep data in EU regions)

---

## Reporting Security Issues

This is a personal portfolio project. For any security concerns,
contact: nagamsharathkumar9@gmail.com