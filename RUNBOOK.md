# Operations Runbook — EMA Backtester Platform

This runbook covers common operational tasks and incident responses
for the EMA Backtester platform.

---

## 1. Recreate EKS Cluster (Start of Session)

```bash
eksctl create cluster \
  --name ema-backtester-cluster \
  --region ap-south-1 \
  --nodegroup-name standard-workers \
  --node-type t3.small \
  --nodes 2 --nodes-min 1 --nodes-max 3 --managed

aws eks update-kubeconfig --region ap-south-1 --name ema-backtester-cluster
kubectl get nodes  # verify both nodes are Ready
```

---

## 2. Delete EKS Cluster (End of Session — Saves Cost)

```bash
eksctl delete cluster --name ema-backtester-cluster --region ap-south-1
# After deletion, check EC2 → Volumes for orphaned EBS volumes and delete them
```

---

## 3. Deploy Full Stack

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Install PostgreSQL
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install postgres bitnami/postgresql \
  --set auth.username=backtester \
  --set auth.password=backtester123 \
  --set auth.database=backtestdb

# Fix PVC storage class (required on EKS)
kubectl patch pvc data-postgres-postgresql-0 \
  -p '{"spec":{"storageClassName":"gp2"}}'

# Create database credentials secret
kubectl create secret generic postgres-credentials \
  --from-literal=password=backtester123

# Apply ArgoCD app (deploys all k8s/ manifests automatically)
kubectl apply -f k8s/argocd-app.yaml
```

---

## 4. Rollback a Deployment

```bash
# View deployment history
kubectl rollout history deployment/ema-backtester

# Rollback to previous version
kubectl rollout undo deployment/ema-backtester

# Rollback to specific revision
kubectl rollout undo deployment/ema-backtester --to-revision=2

# Verify rollback
kubectl get pods
kubectl logs deployment/ema-backtester
```

---

## 5. Rotate Database Password

```bash
# Update the secret
kubectl create secret generic postgres-credentials \
  --from-literal=password=NEW_PASSWORD \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart the backtester to pick up new credentials
kubectl rollout restart deployment/ema-backtester

# Update PostgreSQL password
kubectl exec -it postgres-postgresql-0 -- \
  psql -U postgres -c "ALTER USER backtester PASSWORD 'NEW_PASSWORD';"
```

---

## 6. Check System Health

```bash
# Pod status
kubectl get pods

# HPA status
kubectl get hpa

# ArgoCD sync status
kubectl get applications -n argocd

# Recent events (last 1 hour)
kubectl get events --sort-by='.lastTimestamp' | tail -20

# Backtester logs
kubectl logs deployment/ema-backtester --tail=50

# PostgreSQL logs
kubectl logs postgres-postgresql-0 --tail=50
```

---

## 7. RCA War Stories (Real Incidents from Development)

### Incident 1: ErrImageNeverPull on Local Kubernetes
**Symptom:** Pod stuck in `ErrImageNeverPull` status  
**Root cause:** Docker Desktop's Kubernetes uses containerd with a separate
`k8s.io` namespace — images built with `docker build` go into Docker's image
store, not containerd's store that Kubernetes uses.  
**Fix:**
```bash
docker save ema-backtester:latest -o ema-backtester.tar
docker cp ema-backtester.tar desktop-control-plane:/ema-backtester.tar
docker exec desktop-control-plane ctr -n k8s.io images import //ema-backtester.tar
```
**Prevention:** Use ECR for all Kubernetes deployments — never rely on local images.

---

### Incident 2: CrashLoopBackOff — PostgreSQL Not Ready
**Symptom:** Backtester pod crashing repeatedly with `connection refused`  
**Root cause:** Backtester started before PostgreSQL finished initializing.
Kubernetes starts all containers simultaneously with no dependency ordering.  
**Fix:** Added initContainer that polls PostgreSQL port until it accepts connections:
```yaml
initContainers:
  - name: wait-for-postgres
    image: busybox:1.36
    command: ['sh', '-c', 'until nc -z postgres-postgresql 5432; do sleep 5; done']
```
**Prevention:** Always use initContainers for apps that depend on databases.

---

### Incident 3: PVC Stuck in Pending — EBS AZ Mismatch
**Symptom:** PostgreSQL pod stuck in `Pending`, PVC not binding  
**Root cause:** EBS volumes are AZ-specific. The PVC was created without a
StorageClass, so it couldn't provision a volume. When nodes scaled, the new
node was in a different AZ from the existing EBS volume.  
**Fix:**
```bash
kubectl patch pvc data-postgres-postgresql-0 \
  -p '{"spec":{"storageClassName":"gp2"}}'
kubectl delete pod postgres-postgresql-0  # forces recreation with bound PVC
```
**Prevention:** Always specify StorageClass in PVC. For multi-AZ databases,
use EFS (multi-AZ) instead of EBS (single-AZ).

---

### Incident 4: CloudFormation Stack Stuck in DELETE_FAILED
**Symptom:** `eksctl create cluster` fails with "Stack already exists"  
**Root cause:** Previous cluster deletion failed midway, leaving a
CloudFormation stack in DELETE_FAILED state.  
**Fix:** Manually deleted the stuck stack via AWS Console → CloudFormation.  
**Prevention:** Always wait for full cluster deletion before recreating.
Use `eksctl delete cluster` and wait for `all cluster resources were deleted`.

---

### Incident 5: Git Push Rejected — 111MB File
**Symptom:** `git push` rejected: "File exceeds GitHub's 100MB limit"  
**Root cause:** `ema-backtester.tar` was accidentally committed.  
**Fix:**
```bash
git rm --cached ema-backtester.tar
echo "*.tar" >> .gitignore
git commit --amend -m "previous message"
git push --force-with-lease
```
**Prevention:** Add binary artifacts to `.gitignore` BEFORE creating them.

---

## 8. Cost Management

| Resource | Cost | Action |
|----------|------|--------|
| EKS Control Plane | ~₹600/month | Delete cluster after each session |
| EC2 t3.small (x2) | ~₹500/month | Included in cluster deletion |
| EBS Volume (8Gi) | ~₹60/month | Check EC2→Volumes after deletion |
| ECR Storage | ~₹5/month | Leave running (minimal cost) |
| CloudWatch Logs | ~₹10/month | Leave running |
| **Total active session** | **~₹8/hour** | **Always delete when done** |

---

## 9. Disaster Recovery Procedure

### RPO: 24 hours | RTO: 30 minutes

**Scenario: Complete cluster loss (region outage, accidental deletion)**

#### Step 1: Assess (5 minutes)
```bash
# Check if cluster exists
aws eks describe-cluster --name ema-backtester-cluster --region ap-south-1

# Check EBS snapshots available
aws ec2 describe-snapshots \
  --filters "Name=tag:Project,Values=ema-backtester" \
  --query 'Snapshots[*].[SnapshotId,StartTime,State]' \
  --output table
```

#### Step 2: Recreate cluster (15-20 minutes)
```bash
eksctl create cluster \
  --name ema-backtester-cluster \
  --region ap-south-1 \
  --node-type t3.small \
  --nodes 2 --managed

aws eks update-kubeconfig \
  --region ap-south-1 \
  --name ema-backtester-cluster
```

#### Step 3: Restore PostgreSQL from snapshot (5 minutes)
```bash
# Create EBS volume from latest snapshot
aws ec2 create-volume \
  --snapshot-id <latest-snapshot-id> \
  --availability-zone ap-south-1a \
  --volume-type gp2

# Deploy PostgreSQL pointing to restored volume
# (update PV manifest with new volume ID)
```

#### Step 4: Redeploy application (3-5 minutes)
```bash
# ArgoCD auto-deploys from Git when installed
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl apply -f k8s/argocd-app.yaml
```

#### Step 5: Verify recovery
```bash
kubectl get pods          # all pods Running
kubectl get hpa           # HPA active
curl http://localhost:8001/health  # returns {"status": "healthy"}
curl http://localhost:8001/results # returns historical data from restored DB
```

**Expected total recovery time: ~25-30 minutes**
**Data loss: Maximum 24 hours (last DLM snapshot)**