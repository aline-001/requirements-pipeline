#!/usr/bin/env python3
"""
Make a Flexo MMS token (HS256 JWT), the same kind the Flexo auth service issues.

Used by init.sh for the one-time setup (an admin token valid for minutes), and by
you when a script needs a token without an LDAP login.

    python3 make_token.py                         # admin, valid 15 minutes
    python3 make_token.py --user aline --hours 24 # a named user, valid 1 day

Reads FLEXO_JWT_SECRET from flexo/.env (or the environment). Standard library only.
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path

# Must match docker-compose.yml (JWT_DOMAIN / JWT_AUDIENCE).
ISSUER = "http://flexo-mms-services"
AUDIENCE = "flexo-mms-audience"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_token(secret: str, username: str, groups: list[str], exp: int) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"aud": AUDIENCE, "iss": ISSUER, "username": username, "groups": groups, "exp": exp}
    enc = lambda o: b64url(json.dumps(o, separators=(",", ":")).encode())  # noqa: E731
    signing_input = f"{enc(header)}.{enc(payload)}"
    sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{b64url(sig)}"


def read_secret() -> str:
    if os.environ.get("FLEXO_JWT_SECRET"):
        return os.environ["FLEXO_JWT_SECRET"]
    env = Path(__file__).resolve().parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("FLEXO_JWT_SECRET="):
                return line.split("=", 1)[1].strip().strip("'\"")
    sys.exit("FLEXO_JWT_SECRET not found: run ./setup.sh first")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--user", default="admin")
    p.add_argument("--groups", default="super_admins", help="comma-separated")
    p.add_argument("--minutes", type=int, default=15)
    p.add_argument("--hours", type=int, default=0)
    a = p.parse_args()
    lifetime = a.hours * 3600 if a.hours else a.minutes * 60
    groups = [g for g in a.groups.split(",") if g]
    print(make_token(read_secret(), a.user, groups, int(time.time()) + lifetime))


if __name__ == "__main__":
    main()
