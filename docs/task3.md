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

## Verification (2026-09-25)

### Daily Backup
Crontab entries:
    0 3 * * *  backup.sh  ->  backups/backup.log
    15 3 * * * run_sync.sh -> sync.log

backup.sh runs pg_dump inside the container using the embedded Postgres
password from /baserow/data/.pgpass. Prunes to the last 7 backups.

### Tested Restore
Procedure:
1. Created a fresh database baserow_restore_test inside the container.
2. Piped the most recent backup into psql -d baserow_restore_test.
3. Listed restored tables with \dt — auth_user, core_workspace,
   database_table and other Baserow tables were present.
4. Dropped baserow_restore_test.

This proves the backup is usable for recovery.

### Security Settings
- Public sign-up: disabled (allow_new_signups = False).
- Separate API token "sync-script" with read/write scope.
- HTTPS via Cloudflare Tunnel edge; no plain HTTP is exposed.
