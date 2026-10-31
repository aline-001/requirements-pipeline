# Requirements Engineering Pipeline

Baserow (intake and review) → `sync.py` → StrictDoc `.sdoc` files in Git (baseline) → RTM and coverage computed from Git → published read-only site.

| Part | Where |
|---|---|
| Baserow (forms, review, change requests) | https://baserow.darho.net |
| Repository (source of truth) | https://github.com/aline-001/requirements-pipeline |
| RTM, coverage, StrictDoc documents | https://rtm.darho.net |

## Repository layout

```
docker-compose.yml        Baserow, persistent volume, localhost-only ports
backup.sh                 daily pg_dump (cron 03:00), keeps 7
sync/sync.py              Baserow API -> docs/sdoc/*.sdoc (+ "baseline" and "check" commands)
run_sync.sh               sync -> StrictDoc check -> branch -> Pull Request (manual or cron)
docs/sdoc/                GENERATED: needs, requirements, elements, verification (.sdoc)
src/                      code; functions carry @relation(REQ-xxx, scope=function)
strictdoc_config.py       StrictDoc 0.30 project config (docs/sdoc + src traceability)
rtm.py                    computes RTM (index.html, rtm.csv) and coverage.txt from Git
publish.sh                rebuilds site/ = RTM + StrictDoc export (cron)
deploy/rtm-site.service   serves site/ read-only on 127.0.0.1:8090
docs/diagrams/*.mmd       Mermaid sources used in SUBMISSION.md
```

Never edit `docs/sdoc/*.sdoc`, `rtm.csv` or `coverage.txt` by hand. Change Baserow (through the forms and a change request) and run the sync.

## Reusing the pipeline on a new project

You need: a Linux server with Docker, a domain on Cloudflare, a GitHub repository, Python 3.10+, and `pipx install strictdoc`.

1. **Start Baserow.** Copy `docker-compose.yml`, set `BASEROW_PUBLIC_URL` to your hostname and put SMTP settings in a `.env` file next to it (not in Git). Run `docker compose up -d`. Ports stay bound to `127.0.0.1`; nothing is exposed directly.
2. **Put it on the internet.** `cloudflared tunnel create <name>`, route `baserow.<domain>` to `http://localhost:80` (add `--protocol http2` if QUIC is blocked), install it as a service: `sudo cloudflared service install`. HTTPS is handled by Cloudflare.
3. **Lock it down.** Create the admin account, then Admin → Settings → turn off "Allow creating new accounts". Invite members by email only.
4. **Create the database.** Recreate the 8 tables from the table list in `SUBMISSION.md` (Task 1), or export this workspace (Workspace → Export) and import it into the new one, then delete the test rows. Keep the Status options exactly: needs `Proposed, Approved, Rejected`; requirements `Draft, Approved, Baselined, Obsolete`.
5. **Create the forms and views** listed in Tasks 1 and 2. Every need starts as `Proposed`.
6. **Create a database token** (Settings → Database tokens): read on all tables, update on Requirement only. Copy `.env.example` to `.env`, fill in `BASEROW_TOKEN` and the new table IDs (they are in the table URL).
7. **Prepare the repository.** Copy this repo, delete `docs/sdoc/*`, adjust field names at the top of `sync/sync.py` (`F = {...}`) if yours differ, and run `python3 sync/sync.py check`. Give the server push access (deploy key with write access, or `gh auth login`).
8. **Run it.** `./run_sync.sh` once by hand, merge the Pull Request, run it again (the merged requirements become Baselined). Then add the cron lines from the top of `run_sync.sh`, `publish.sh` and `backup.sh`.
9. **Publish.** `sudo cp deploy/rtm-site.service /etc/systemd/system/ && sudo systemctl enable --now rtm-site`, add the public hostname `rtm.<domain>` → `http://localhost:8090` to the same tunnel, run `./publish.sh`.
10. **Tag code.** In each function that implements a requirement, add `@relation(REQ-xxx, scope=function)` to its docstring.

## Everyday commands

```bash
python3 sync/sync.py check      # validate Baserow data, write nothing
./run_sync.sh                   # export + Pull Request
python3 sync/sync.py baseline   # mark merged requirements Baselined (run_sync.sh does this)
./publish.sh                    # rebuild RTM + StrictDoc site
strictdoc server . --port 5111  # local editing/preview only; do not expose publicly
```

## Rules the sync enforces

| Error | Meaning | Fix |
|---|---|---|
| `DUPLICATE ID` | two Requirement or Verification rows share an ID | give the newer row the next free ID |
| `NO NEED` | an exported requirement has no stakeholder need | link it to an approved need |
| `BROKEN LINK` | a link points to a missing row or to a need that is not Approved | fix the link or approve the need |
| `REMOVED` | an ID that is in Git disappeared from Baserow | set the requirement to Obsolete instead of deleting it |
| `ID REUSE` | an Obsolete ID was set active again | create a new requirement with a new ID |

Exit codes: `0` ok, `1` configuration or API problem, `2` data errors (nothing is written).
