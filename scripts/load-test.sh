#!/usr/bin/env bash
# Generates steady traffic against the API from inside the cluster so the HPA
# and the Grafana dashboard have something to show.
#   ./scripts/load-test.sh [concurrency] [seconds]
set -euo pipefail
NS=${NS:-shelfwise}
C=${1:-20}
SECS=${2:-180}
kubectl -n "$NS" delete pod shelfwise-load --ignore-not-found >/dev/null
kubectl -n "$NS" run shelfwise-load --image=busybox:1.36 --restart=Never -- sh -c "
  end=\$((\$(date +%s) + $SECS))
  for i in \$(seq 1 $C); do
    ( while [ \$(date +%s) -lt \$end ]; do
        wget -q -O /dev/null http://shelfwise-backend:8000/api/books
        wget -q -O /dev/null http://shelfwise-backend:8000/api/books/stats
        wget -q -O /dev/null 'http://shelfwise-backend:8000/api/books?q=history'
        wget -q -O /dev/null http://shelfwise-backend:8000/api/books/99999 || true
      done ) &
  done
  wait"
echo "load running for ${SECS}s with $C workers; watch with: kubectl get hpa -n $NS -w"
