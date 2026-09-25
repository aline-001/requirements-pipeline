#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="$(cd "$(dirname "$0")" && pwd)/backups"
mkdir -p "$BACKUP_DIR"

DATE=$(date +%Y%m%d_%H%M%S)
OUT="$BACKUP_DIR/baserow_${DATE}.sql"

# Extract the password from the .pgpass file (format: export DATABASE_PASSWORD=...)
PGPASSWORD=$(docker exec baserow cat /baserow/data/.pgpass | sed -n 's/^export DATABASE_PASSWORD=//p')

if [ -z "$PGPASSWORD" ]; then
    echo "ERROR: could not read DB password" >&2
    exit 1
fi

docker exec -e PGPASSWORD="$PGPASSWORD" baserow pg_dump -U baserow -h localhost -d baserow > "$OUT"
echo "Backup written to $OUT"
ls -lh "$OUT"

# Keep last 7 backups
ls -t "$BACKUP_DIR"/baserow_*.sql 2>/dev/null | tail -n +8 | xargs -r rm
