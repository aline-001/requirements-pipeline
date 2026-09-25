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

### Backup
Crontab entries confirmed:
    0 3 * * *  backup.sh  ->  backups/backup.log
    15 3 * * * run_sync.sh -> sync.log

backup.sh extracts the embedded Postgres password from the container's
/baswerow/data/.pgpass file and runs pg_dump -U baserow -h localhost -d baserow.
Most recent backup: 14 MB SQL file at backups/baserow_20260925_145107.sql.
Backups older than 7 are pruned.

### Restore Test
Test procedure:
1. Created fresh database baserow_restore_test inside the container.
2. Piped the 14 MB backup into psql -d baserow_restore_test.
3. Listed tables with \dt.
4. Dropped baserow_restore_test.

### Security Settings
- HTTPS via Cloudflare Tunnel edge (no plain HTTP exposed).
- Separate API token "sync-script" scoped to the Requirements Engineering
  workspace with read/write permissions.
- Public sign-up: [FILL IN AFTER RESOLVING]
