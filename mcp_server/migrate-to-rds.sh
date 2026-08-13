#!/bin/bash
# Migrates incident_postmortems data from the in-cluster PostgreSQL
# (Bitnami Helm chart, StatefulSet) to AWS RDS PostgreSQL (Multi-AZ).
#
# Run this during a maintenance window when both the old and new
# databases are reachable at the same time.
#
# USAGE:
#   1. In a separate terminal, port-forward the in-cluster Postgres:
#        kubectl port-forward svc/postgres-postgresql 5433:5432
#   2. Set the required env vars (see below), then run this script.
#
# REQUIRED ENV VARS:
#   SOURCE_DB_PASSWORD  - password for the in-cluster Postgres
#   TARGET_DB_HOST      - RDS endpoint (e.g. rds-lab-postgres.xxxx.rds.amazonaws.com)
#   TARGET_DB_PASSWORD  - password for the RDS instance

set -euo pipefail

SOURCE_HOST="localhost"
SOURCE_PORT="5433"   # matches the kubectl port-forward local port
SOURCE_USER="backtester"
SOURCE_DB="backtestdb"

TARGET_PORT="5432"
TARGET_USER="backtester"
TARGET_DB="backtestdb"

: "${SOURCE_DB_PASSWORD:?Set SOURCE_DB_PASSWORD before running}"
: "${TARGET_DB_HOST:?Set TARGET_DB_HOST before running}"
: "${TARGET_DB_PASSWORD:?Set TARGET_DB_PASSWORD before running}"

echo "Step 1: Dumping incident_postmortems from source (in-cluster Postgres)..."
PGPASSWORD="$SOURCE_DB_PASSWORD" pg_dump \
  -h "$SOURCE_HOST" -p "$SOURCE_PORT" -U "$SOURCE_USER" -d "$SOURCE_DB" \
  --table=incident_postmortems \
  --no-owner --no-privileges \
  -f postmortems_dump.sql

echo "Step 2: Restoring into target (RDS)..."
PGPASSWORD="$TARGET_DB_PASSWORD" psql \
  -h "$TARGET_DB_HOST" -p "$TARGET_PORT" -U "$TARGET_USER" -d "$TARGET_DB" \
  -f postmortems_dump.sql

echo "Step 3: Verifying row counts match..."
SOURCE_COUNT=$(PGPASSWORD="$SOURCE_DB_PASSWORD" psql -h "$SOURCE_HOST" -p "$SOURCE_PORT" -U "$SOURCE_USER" -d "$SOURCE_DB" -t -c "SELECT COUNT(*) FROM incident_postmortems;" | tr -d ' ')
TARGET_COUNT=$(PGPASSWORD="$TARGET_DB_PASSWORD" psql -h "$TARGET_DB_HOST" -p "$TARGET_PORT" -U "$TARGET_USER" -d "$TARGET_DB" -t -c "SELECT COUNT(*) FROM incident_postmortems;" | tr -d ' ')

echo "Source rows: $SOURCE_COUNT | Target rows: $TARGET_COUNT"

if [ "$SOURCE_COUNT" != "$TARGET_COUNT" ]; then
  echo "WARNING: row counts do not match. Investigate before cutting over."
  exit 1
fi

echo "Migration verified. Update DB_HOST in mcp-deployment.yaml to $TARGET_DB_HOST and redeploy."
rm postmortems_dump.sql
