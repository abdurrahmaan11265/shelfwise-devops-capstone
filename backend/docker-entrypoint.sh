#!/bin/sh
# Migrate, then serve. Migrations are idempotent, so running them on every start
# is safe; RUN_MIGRATIONS=false lets Kubernetes leave it to a single job instead.
set -e
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
