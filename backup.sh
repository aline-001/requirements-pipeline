#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="$(cd "$(dirname "$0")" && pwd)/backups"
mkdir -p "$BACKUP_DIR"

DATE=$(date +%Y%m%d_%H%M%S)
OUT="$BACKUP_DIR/baserow_${DATE}.sql"

PGPASSWORD=$(cat /tmp/pgpass 2>/dev/null || docker exec baserow cat /baserow/data/.pgpass | cut -d: -f5)

docker exec -e PGPASSWORD="$PGPASSWORD" baserow pg_dump -U baserow -h localhost -d baserow > "$OUT"
echo "Backup written to $OUT"

# Keep only the last 7 backups
ls -t "$BACKUP_DIR"/baserow_*.sql | tail -n +8 | xargs -r rm
echo "Old backups pruned. Current backups:"
ls -lh "$BACKUP_DIR"
