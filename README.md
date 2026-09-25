# Requirements Engineering Pipeline

A complete Requirements Engineering pipeline using Baserow, Docker, Cloudflare Tunnel, StrictDoc, and Git.

## Architecture

- Baserow (Docker, self-hosted) stores stakeholders, needs, requirements, reviews, verifications, and change requests.
- Web forms in Baserow let stakeholders submit needs and reviewers approve them.
- Cloudflare Tunnel exposes Baserow over HTTPS.
- A sync script pulls approved requirements from the Baserow API and writes StrictDoc .sdoc files.
- Git holds the resulting .sdoc files as the source of truth.
- An RTM script computes a Requirements Traceability Matrix and coverage report from the repository.

## Reuse on a New Project

1. Clone this repository.
2. Copy .env.example to .env and fill in BASEROW_URL, BASEROW_TOKEN, and the two table IDs.
3. Start Baserow: docker compose up -d
4. Create the tables in Baserow (see docs/task1.md for the schema).
5. Run ./run_sync.sh to pull approved requirements into docs/generated/.
6. Run python3 rtm.py to build the RTM and coverage report.
7. View rtm.html in a browser.

## Directory Layout

- docker-compose.yml   Baserow service definition
- .env                 Secrets (gitignored)
- sync/sync.py         Baserow -> .sdoc sync script
- run_sync.sh          Wrapper that runs sync.py inside the container
- backup.sh            Daily Postgres backup
- rtm.py               RTM + coverage report generator
- src/                 Source code with @relation tags
- docs/                Per-task deliverables
- docs/generated/      .sdoc files written by the sync script
- rtm.csv              Generated RTM
- rtm.html             Rendered RTM
