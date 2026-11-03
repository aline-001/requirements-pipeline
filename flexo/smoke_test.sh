#!/usr/bin/env bash
# End-to-end check: LDAP login -> token -> SysML v2 API -> PR manager.
#   ./smoke_test.sh                 local checks only (127.0.0.1)
#   ./smoke_test.sh --public        also checks the public https:// addresses
#   ./smoke_test.sh --create-demo   also creates a SysML v2 project "Pipeline demo" (once)
set -uo pipefail
cd "$(dirname "$0")"
source <(grep -E '^(LDAP_USERS|LDAP_PASSWORDS)=' .env)
USER1=${LDAP_USERS%%,*}; PASS1=${LDAP_PASSWORDS%%,*}
AUTH=http://127.0.0.1:8082 SYSML=http://127.0.0.1:8083 PR=http://127.0.0.1:8084
fail=0
check() { if [ "$2" = "$3" ]; then echo "  OK    $1"; else echo "  FAIL  $1 (expected $3, got $2)"; fail=1; fi; }

echo "Local checks:"
TOKEN=$(curl -s -u "$USER1:$PASS1" "$AUTH/login" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("token",""))' 2>/dev/null)
check "login as $USER1 returns a token" "$([ -n "$TOKEN" ] && echo yes || echo no)" yes
anon=$(curl -s -o /tmp/anon.json -w '%{http_code}' $SYSML/projects)
check "SysML v2 API gives no data without a token (HTTP $anon)" \
      "$([ "$anon" = 200 ] && grep -q '@id' /tmp/anon.json && echo leaked || echo refused)" refused
code=$(curl -s -o /tmp/projects.json -w '%{http_code}' -H "Authorization: Bearer $TOKEN" $SYSML/projects)
check "SysML v2 API lists projects with the token" "$code" 200
check "PR manager is up" "$(curl -s -o /dev/null -w '%{http_code}' $PR/api/health)" 200
code=$(curl -s -o /dev/null -w '%{http_code}' -H "Content-Type: application/json" \
       -d "{\"apiBase\":\"http://sysmlv2-service:8080\",\"bearerToken\":\"$TOKEN\"}" $PR/api/mms/projects)
check "PR manager reaches the SysML v2 API" "$code" 200

if [[ " $* " == *" --create-demo "* ]]; then
  if grep -q '"Pipeline demo"' /tmp/projects.json; then
    echo "  OK    demo project already exists"
  else
    code=$(curl -s -o /tmp/demo.json -w '%{http_code}' -X POST -H "Authorization: Bearer $TOKEN" \
           -H "Content-Type: application/json" \
           -d '{"@type":"Project","name":"Pipeline demo","description":"Created by smoke_test.sh"}' $SYSML/projects)
    check "create SysML v2 project 'Pipeline demo'" "$(case $code in 200|201) echo ok;; *) echo $code;; esac)" ok
  fi
fi

if [[ " $* " == *" --public "* ]]; then
  echo "Public checks:"
  T=$(curl -s -u "$USER1:$PASS1" https://flexo-auth.darho.net/login | python3 -c 'import sys,json; print(json.load(sys.stdin).get("token",""))' 2>/dev/null)
  check "https://flexo-auth.darho.net/login" "$([ -n "$T" ] && echo yes || echo no)" yes
  check "https://sysmlv2.darho.net/projects (token)" "$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $T" https://sysmlv2.darho.net/projects)" 200
  code=$(curl -s -o /dev/null -w '%{http_code}' https://pr.darho.net/api/health)
  check "https://pr.darho.net asks for a login (Cloudflare Access)" "$(case $code in 302|401|403) echo protected;; *) echo $code;; esac)" protected
fi

[ $fail = 0 ] && echo "ALL CHECKS PASSED" || { echo "SOME CHECKS FAILED"; exit 1; }
