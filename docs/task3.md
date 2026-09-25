# Task 3 — Baserow on the Internet

## Deployment Method
Cloudflare Tunnel — no DNS or TLS setup, no inbound firewall ports, automatic HTTPS.

## Public URL
Quick tunnel: https://shade-laws-occasion-africa.trycloudflare.com

## Networking Note
WSL blocks outbound UDP 7844 (QUIC); cloudflared uses --protocol http2 (TCP 443).

## Security
- HTTPS only via Cloudflare
- Public sign-up disabled
- Separate API token for sync script

## Backup and Restore
backup.sh runs pg_dump daily, prunes to last 7. Restore tested with a temporary baserow_restore_test database.

## Deployment Diagram
Client -> Cloudflare Edge -> cloudflared -> Baserow container -> baserow_data volume.
