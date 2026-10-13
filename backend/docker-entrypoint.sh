#!/bin/sh
# Migrate, then serve. The database may still be starting (compose, kubernetes),
# so migrations are retried for up to a minute before giving up.
set -e
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  i=0
  until alembic upgrade head; do
    i=$((i + 1))
    if [ "$i" -ge 20 ]; then echo "database never became reachable" >&2; exit 1; fi
    echo "migration attempt $i failed, retrying in 3s"; sleep 3
  done
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
