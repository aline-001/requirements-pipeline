#!/usr/bin/env bash
# Daily backup of the Flexo stack (cron 03:30). Keeps the last 7.
# Fuseki is stopped for a few seconds so the TDB2 files are copied in a consistent state.
#   Restore:  docker compose stop quad-store
#             docker run --rm -v flexo_fuseki_data:/v -v "$PWD/backups":/b alpine \
#               sh -c 'rm -rf /v/* && tar xzf /b/<file>-fuseki.tgz -C /v'
#             docker compose start quad-store
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p backups
STAMP=$(date +%Y%m%d-%H%M%S)

docker compose stop -t 20 quad-store
for v in fuseki_data ldap_data pr_data; do
  docker run --rm -v "flexo_${v}:/v:ro" -v "$PWD/backups:/b" alpine \
    tar czf "/b/${STAMP}-${v%_data}.tgz" -C /v .
done
docker compose start quad-store

ls -1t backups/*-fuseki.tgz | tail -n +8 | while read -r f; do rm -f "${f%-fuseki.tgz}"-*.tgz; done
echo "backup $STAMP: $(ls backups/${STAMP}-* | xargs -n1 basename | tr '\n' ' ')"
