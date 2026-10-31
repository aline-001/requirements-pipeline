# Applying this update on the VPS (about 20 minutes)

```bash
cd ~/requirements-pipeline
git checkout -b strictdoc-fix
```

1. **Copy the new files in** (overwrite): `sync/sync.py`, `run_sync.sh`, `publish.sh`, `rtm.py`,
   `strictdoc_config.py`, `docker-compose.yml`, `README.md`, `.env.example`, `deploy/`, `docs/diagrams/`,
   `docs/SUBMISSION.template.md`, `docs/build_submission.py`, `examples/`.
   Then: `chmod +x run_sync.sh publish.sh` and `rm -rf docs/generated`.

2. **Check StrictDoc accepts the format** before using real data:
   ```bash
   strictdoc export examples/sample-output --output-dir /tmp/sample && echo FORMAT OK
   ```

3. **Fix the code markers** in `src/auth.py`: StrictDoc only reads markers inside the docstring,
   without quotes, with a scope. Replace each `@relation("REQ-002")` with a docstring line
   `@relation(REQ-002, scope=function)` (see `examples/auth.py`).

4. **Baserow:** add the option `Baselined` to Requirement → Status if it is not there. Create a database
   token (Settings → Database tokens: read all tables, update Requirement). Put it in `.env` as
   `BASEROW_TOKEN=...` and set `BASEROW_URL=http://127.0.0.1:8000`.

5. **Docker ports + secrets:** move the Brevo key into `.env` (`BREVO_SMTP_USER`, `BREVO_SMTP_KEY`,
   `FROM_EMAIL`), then `docker compose up -d`. Check `curl -sI http://185.217.126.18` from another
   machine now fails, and https://baserow.darho.net still works.
   Also close the StrictDoc ports: `sudo ufw delete allow 5111 && sudo ufw delete allow 8080`.

6. **Run the pipeline:**
   ```bash
   python3 sync/sync.py check      # must print CHECK OK
   python3 sync/sync.py export     # writes docs/sdoc/*.sdoc
   strictdoc export . --output-dir /tmp/real && echo STRICTDOC OK
   ./publish.sh                    # site/ = RTM + StrictDoc
   ```
   Commit everything, push, open the PR, merge it. Then `./run_sync.sh` (marks REQ-002/REQ-004 Baselined
   and opens the follow-up PR).

7. **Publish permanently at rtm.darho.net:**
   ```bash
   sudo cp deploy/rtm-site.service /etc/systemd/system/
   sudo systemctl daemon-reload && sudo systemctl enable --now rtm-site
   curl -s http://127.0.0.1:8090 | head -3
   ```
   Cloudflare dashboard → Zero Trust → Networks → Tunnels → baserow-tunnel → Public Hostname → Add:
   subdomain `rtm`, domain `darho.net`, service `HTTP` `localhost:8090`.
   (If the tunnel uses /etc/cloudflared/config.yml instead, see `deploy/cloudflared-ingress-example.yml`,
   then `cloudflared tunnel route dns baserow-tunnel rtm.darho.net` and `sudo systemctl restart cloudflared`.)

   Fallback only if you cannot add a hostname: `cloudflared tunnel --url http://localhost:8090 --protocol http2`
   prints a `*.trycloudflare.com` URL, but it changes every restart and stops when the command stops.

8. **Cron** (`crontab -e`):
   ```
   15 6 * * *   cd $HOME/requirements-pipeline && ./run_sync.sh >> logs/sync.log 2>&1
   */30 * * * * cd $HOME/requirements-pipeline && ./publish.sh  >> logs/publish.log 2>&1
   ```
   The sync pushes from cron, so the server needs non-interactive push access: a GitHub deploy key with
   write access, or `gh auth login`.

9. **Build the submission:** `python3 docs/build_submission.py`, then fill in the ⟨…⟩ links it lists
   (form share links, view IDs, the CR Pull Request and merge commit URLs).
