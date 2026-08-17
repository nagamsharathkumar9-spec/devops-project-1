# ALB Ingress + Cluster Autoscaler — Session E

## Summary
Installed the AWS Load Balancer Controller (via Helm, IRSA-authenticated)
and Cluster Autoscaler, then proved both with live tests: a real ALB
provisioned from a Kubernetes Ingress, and a real node scale-up triggered
by pod scheduling pressure.

Route53 + ACM (custom domain, HTTPS) were scoped out of this session —
no domain was purchased. The ALB is reachable on its AWS-generated
hostname over HTTP. Adding a real domain later is a small, additive step
(point Route53 at the existing ALB, request an ACM cert, add one
annotation) — documented as a clear next step, not re-architected.

## What was built

### AWS Load Balancer Controller
- Official IAM policy (`AWSLoadBalancerControllerIAMPolicy`) downloaded
  from the upstream `kubernetes-sigs/aws-load-balancer-controller` repo
  (pinned to v2.14.1, not `main`, for reproducibility)
- IRSA wired via `eksctl create iamserviceaccount` — a one-command
  shortcut vs. the manual role/trust-policy/ServiceAccount steps used
  in Sessions C and D
- Installed via Helm from the official `eks/` chart repo

### Cluster Autoscaler
- Custom scoped IAM policy: broad `Describe*` (read-only, safe) plus
  `SetDesiredCapacity` / `TerminateInstanceInAutoScalingGroup` /
  `UpdateAutoScalingGroup` restricted via a resource tag condition
  (`k8s.io/cluster-autoscaler/ema-backtester-cluster: owned`) — the
  autoscaler can only touch this cluster's own ASG, not any ASG in
  the account
- IRSA via the same `eksctl create iamserviceaccount` shortcut
- ASG resized from a fixed 2/2/2 (min/desired/max) to 2/2/4, giving
  the autoscaler real room to scale
- ASG tagged for auto-discovery (`k8s.io/cluster-autoscaler/enabled`,
  `k8s.io/cluster-autoscaler/ema-backtester-cluster`)

## Real bugs hit and fixed
1. **IRSA ≠ K8s RBAC.** First deploy crashed immediately:
   `nodes is forbidden: User "system:serviceaccount:kube-system:cluster-autoscaler"
   cannot list resource "nodes"`. IRSA only grants *AWS* API access —
   the autoscaler separately needs a Kubernetes ClusterRole/ClusterRoleBinding
   to read cluster resources. Two independent permission systems, both
   required.
2. **Missing `volumeattachments` permission.** Cluster Autoscaler 1.34.4
   watches a resource type not present in older reference RBAC templates.
   Patched the ClusterRole live with `kubectl patch` rather than a full
   reapply.

## Live test results (2026-08-17)

### ALB (Ingress → real AWS Application Load Balancer)
- Applied an Ingress with `alb.ingress.kubernetes.io/*` annotations
- Real ALB hostname assigned in **17 seconds**:
  `k8s-default-albdemoi-26248f1d82-792445715.ap-south-1.elb.amazonaws.com`
- Confirmed live: `curl` returned the expected response through the
  real internet-facing load balancer

### Cluster Autoscaler (forced scale-up)
- Deployed 10 pods requesting 400m CPU each (4000m total) against
  2× `t3.small` nodes — deliberately more than available capacity
- Autoscaler log: `Final scale-up plan: [{...ng-9e1125c0... 2->3 (max: 4)}]`
- New EC2 node went from not-existing to `Ready` in **~12 seconds**
  after appearing
- All 10 pods reached `Running`, 3rd node confirmed via `kubectl get nodes`
- Scale-down cooldown (`--scale-down-delay-after-add=2m`) is intentional,
  prevents flapping up/down under bursty load

## Cost optimization (discussed, not deployed live)
- **Spot Instances**: 70–90% cheaper, AWS can reclaim with ~2 min notice.
  Good fit for stateless/fault-tolerant workloads; never for stateful
  services like RDS or a Jenkins controller. Typically run as mixed
  node groups (On-Demand baseline + Spot burst), often paired with
  Karpenter for smarter Spot selection.
- **Right-sizing**: matching instance size to real usage rather than
  guessing. AWS Compute Optimizer automates this in a real account
  using actual CloudWatch metrics.

## Trade-offs / notes
- EKS cluster created fresh for this session, all AWS resources
  (ALB, EC2 nodes, IAM roles/policies) deleted after testing.
- No domain purchased this session — Route53/ACM covered conceptually.
  Revisit when the GitHub Pages / always-on EC2 enhancement work begins,
  since a domain is reusable across both.
