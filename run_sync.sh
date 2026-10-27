#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

set -a
source .env
set +a

docker cp sync/sync.py baserow:/tmp/sync.py

docker exec \
  -e BASEROW_URL="http://127.0.0.1:8000" \
  -e BASEROW_EMAIL="$BASEROW_EMAIL" \
  -e BASEROW_PASSWORD="$BASEROW_PASSWORD" \
  -e NEEDS_TABLE_ID="$NEEDS_TABLE_ID" \
  -e REQS_TABLE_ID="$REQS_TABLE_ID" \
  -e ALLOC_TABLE_ID="$ALLOC_TABLE_ID" \
  -e VER_TABLE_ID="$VER_TABLE_ID" \
  -e OUT_DIR=/tmp/sdoc_out \
  baserow python3 /tmp/sync.py

rm -rf docs/generated
mkdir -p docs/generated
docker cp baserow:/tmp/sdoc_out/. docs/generated/

echo "Sync complete."
ls -la docs/generated/
