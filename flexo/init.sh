#!/usr/bin/env bash
# First-time data setup for Flexo. Safe to run again: each step checks before it changes anything.
#   1. waits for Fuseki, loads mount/cluster.trig (Flexo schema + access policies) if the store is empty
#   2. waits for Flexo layer 1, creates the "sysmlv2" org the SysML v2 API stores projects in
set -euo pipefail
cd "$(dirname "$0")"

FUSEKI=http://127.0.0.1:3030/ds
LAYER1=http://127.0.0.1:8080
ORG=sysmlv2

wait_for() {  # url, name
  printf "waiting for %s " "$2"
  for _ in $(seq 1 90); do
    code=$(curl -s -o /dev/null -w "%{http_code}" "$1" || true)
    if [ "$code" != "000" ] && [ "$code" -lt 500 ]; then echo "- up"; return 0; fi
    printf "."; sleep 2
  done
  echo; echo "ERROR: $2 did not start. Look at: docker compose logs --tail 50"; exit 1
}

ask_initialized() {
  curl -s -H "Accept: application/sparql-results+json" \
    --data-urlencode 'query=ASK { GRAPH <http://layer1-service/graphs/AccessControl.Policies> { ?s ?p ?o } }' \
    "$FUSEKI/sparql" | grep -q '"boolean" *: *true'
}

wait_for "$FUSEKI/sparql?query=ASK%7B%7D" "Fuseki (quad store)"
if ask_initialized; then
  echo "Quad store already initialized."
else
  echo "Loading mount/cluster.trig into the quad store..."
  code=$(curl -s -o /tmp/flexo-load.txt -w "%{http_code}" -X POST \
         -H "Content-Type: application/trig" --data-binary @mount/cluster.trig "$FUSEKI")
  if ! ask_initialized; then   # some Fuseki setups only take quads on the /data endpoint
    code=$(curl -s -o /tmp/flexo-load.txt -w "%{http_code}" -X POST \
           -H "Content-Type: application/trig" --data-binary @mount/cluster.trig "$FUSEKI/data")
  fi
  if ! ask_initialized; then
    echo "ERROR: loading failed (HTTP $code):"; head -c 400 /tmp/flexo-load.txt; echo; exit 1
  fi
  echo "Quad store initialized."
fi

wait_for "$LAYER1/" "Flexo layer 1"
TOKEN=$(python3 make_token.py --minutes 10)
code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" "$LAYER1/orgs/$ORG")
if [ "$code" = "200" ]; then
  echo "Org '$ORG' already exists."
else
  code=$(curl -s -o /tmp/flexo-org.txt -w "%{http_code}" -X PUT \
         -H "Authorization: Bearer $TOKEN" -H "Content-Type: text/turtle" \
         --data '<> dct:title "SysML v2"@en .' "$LAYER1/orgs/$ORG")
  case "$code" in
    200|201|204) echo "Created org '$ORG'." ;;
    *) echo "ERROR: creating org failed (HTTP $code):"; head -c 400 /tmp/flexo-org.txt; echo; exit 1 ;;
  esac
fi
./grant_users.sh
echo "init.sh done. Next: ./smoke_test.sh"
