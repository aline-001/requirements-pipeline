#!/usr/bin/env bash
# One-time preparation for the Flexo stack. Safe to run again: it never overwrites .env.
#   1. creates flexo/.env with random secrets and LDAP user passwords (shown once)
#   2. downloads Flexo PR Manager source at a pinned commit (it has no published image)
#   3. pulls all images and builds the PR manager, so problems show up before anything starts
set -euo pipefail
cd "$(dirname "$0")"

PR_MANAGER_REPO="https://github.com/Open-MBEE/flexo-pr-manager.git"
PR_MANAGER_COMMIT="cd37aef357bade3e7aa0fd97e158ec799bb78c14"
USERS="${FLEXO_USERS:-aline,patrick}"   # LDAP accounts to create; all become Flexo admins

rand() { openssl rand -hex "${1:-16}"; }

if [ -f .env ]; then
  echo ".env already exists - keeping it."
else
  IFS=',' read -ra U <<< "$USERS"
  PW=(); for _ in "${U[@]}"; do PW+=("$(rand 12)"); done
  umask 077
  cat > .env <<EOF
# Flexo secrets. Never commit this file.
FLEXO_JWT_SECRET=$(rand 32)
LDAP_ADMIN_PASSWORD=$(rand 16)
LDAP_USERS=$USERS
LDAP_PASSWORDS=$(IFS=','; echo "${PW[*]}")
FUSEKI_HEAP=1g
# space-separated web origins allowed to call the SysML v2 API from a browser (optional)
SYSMLV2_CORS_ORIGINS=
EOF
  chmod 600 .env
  echo "Created .env. Flexo logins (save them in a password manager; shown only now):"
  for i in "${!U[@]}"; do echo "   user: ${U[$i]}   password: ${PW[$i]}"; done
fi

if [ ! -d pr-manager-src/.git ]; then
  git clone -q "$PR_MANAGER_REPO" pr-manager-src
fi
git -C pr-manager-src fetch -q origin
git -C pr-manager-src checkout -q "$PR_MANAGER_COMMIT"
echo "PR manager source at $(git -C pr-manager-src rev-parse --short HEAD)"

echo "Pulling images (this can take a few minutes the first time)..."
docker compose pull --ignore-buildable
docker compose build -q pr-manager
echo "setup.sh done. Next: docker compose up -d   then   ./init.sh"
