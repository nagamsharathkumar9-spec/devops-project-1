# RDS Migration — incident_postmortems database

## Summary
Migrated the `incident_postmortems` table from a self-hosted PostgreSQL
StatefulSet (Bitnami Helm chart, single AZ, EBS-backed) to AWS RDS
PostgreSQL 16, Multi-AZ, `db.t3.micro`.

## Why
- Self-hosted Postgres was tied to the EKS cluster's lifecycle — deleting
  the cluster meant losing the database unless manually backed up.
- No automatic failover: a node or AZ outage meant manual recovery.
- RDS Multi-AZ decouples the database from the cluster entirely and
  provides automatic failover to a synchronous standby in a second AZ.

## Real failover test (2026-08-13)
Triggered via:

aws rds reboot-db-instance --region ap-south-1 --db-instance-identifier rds-lab-postgres --force-failover


AWS event log (authoritative, via `aws rds describe-events`):

| Time (UTC) | Event |
|---|---|
| 11:41:15 | Multi-AZ instance failover started |
| 11:41:32 | DB instance restarted |
| 11:41:49 | Multi-AZ instance failover completed |

**Total measured downtime: 34 seconds.**

A live `psql` session observed the disconnect directly:

SSL error: unexpected eof while reading
The connection to the server was lost. Attempting reset: Succeeded.

The client auto-reconnected without manual intervention — no application
code changes needed to survive the failover.

## Migration process
See `migrate-to-rds.sh`. Steps:
1. Port-forward the in-cluster Postgres service locally
2. `pg_dump` the `incident_postmortems` table
3. `psql` restore into the RDS endpoint
4. Verify row counts match between source and target
5. Update `DB_HOST` in `mcp-deployment.yaml`, redeploy

## Known trade-offs (lab setup, not production)
- RDS instance was `publicly_accessible = true`, locked to a single
  trusted IP via security group, for direct `psql` access during
  testing. Production would place RDS in private subnets only,
  reachable exclusively from within the VPC (e.g. from EKS pods).
- A minimal, NAT-free VPC was built specifically for this lab and
  destroyed after — see `terraform/rds-lab/`.

## Cost
`db.t3.micro` Multi-AZ in ap-south-1: ~$0.046/hr. Instance created
2026-08-13 09:51:34 UTC, destroyed at the end of this session via
`terraform destroy` (see git commit history for exact teardown time).
Total cost for the full lab: a few hundred rupees at most.
