cd ~/requirements-pipeline
cat > SUBMISSION.md << 'SUBMISSION_EOF'
# Requirements Engineering Pipeline — Submission

**Student:** Aline ASIMWE
**Date:** 2026-10-27

## Links

- **Baserow instance (public HTTPS):** https://baserow.darho.net
- **Git repository:** https://github.com/aline-001/requirements-pipeline
- **RTM:** `rtm.html` in the repository root (renders in any browser)

---

## Task 1 — Normalized Requirements Database

### Tables

| # | Table | ID | Key Fields | Links |
|---|-------|-----|------------|-------|
| 1 | Stakeholder | 683 | Name, Role, Organisation, Contact | (auto reverse links) |
| 2 | SystemElement | 701 | Name, Type, Description | (auto reverse links) |
| 3 | StakeholderNeed | 709 | Title, Statement, Priority, Rationale, Status, Source | → Stakeholder |
| 4 | Requirement | 703 | Req ID, Statement, Type, Status | → StakeholderNeed |
| 5 | Review | 704 | Review Title, Decision, Comments | → Stakeholder, → StakeholderNeed |
| 6 | Allocation | 706 | Allocation, Notes | → Requirement, → SystemElement |
| 7 | Verification | 707 | Verification ID, Method, Acceptance Criteria, Result | → Requirement |
| 8 | ChangeRequest | 708 | Title, Description, Status, Impact | → Requirement |

### Justification

- **Stakeholder** — Each person or group who raises needs, stored once, referenced by ID.
- **SystemElement** — Subsystems, components, and interfaces so requirements can be allocated without retyping.
- **StakeholderNeed** — What stakeholders want, separate from technical requirements. Holds priority, rationale, status.
- **Requirement** — The precise, testable version of a need. Status determines whether it syncs to Git.
- **Review** — Approval decisions. A need is Approved when an Approved review exists and no Rejected review exists.
- **Allocation** — Bridge table linking requirements to system elements.
- **Verification** — Records how each requirement was verified. Feeds coverage and pass-rate reports.
- **ChangeRequest** — Enforces the rule that a baselined requirement changes only through an approved CR.

### Views

- **Element Responsibility** (Allocation, grouped by Requirement)
- **Requirements by Element** (Allocation, grouped by Element)
- **Needs Without Approved Review** (StakeholderNeed, filtered where Status ≠ Approved)
- **Unverified Requirements** (Requirement, filtered where Verification is empty)

### Test Data

- 3 Stakeholders (Jane Smith, Keza Kelly, David Mugisha)
- 4 SystemElements (Auth Subsystem, Login Component, Session Manager, Password Reset Service)
- 3 StakeholderNeeds (Secure user login, Session timeout, Password reset)
- 3 Requirements (REQ-001, REQ-002, REQ-003 — later REQ-004 created via CR)
- 3 Reviews, 3 Allocations, 3 Verifications, 3 ChangeRequests

---

## Task 2 — Stakeholder Intake Forms

### Form 1 — Submit a Need

**Table:** StakeholderNeed (709)
**Public URL:** https://baserow.darho.net/form/hK4S4mXw-oCgQjSXvValroTj4udT2_INWbGh7KcXygU

Configured fields (all required unless noted):
- **Title** — Short summary of the need.
- **Statement** — Describe exactly what the stakeholder requires.
- **Priority** — Must / Should / Could / Wont.
- **Rationale** — Why is this needed?
- **Source** — Where did this come from?
- **Stakeholder** — Who is raising this need?
- **Status** — hidden (auto-set to Proposed on submission).
- **Requirement, Review** — hidden (reverse links).

Submit message: *"Thank you — your need has been submitted and will be reviewed."*

### Form 2 — Review a Need

**Table:** Review (704)
**Public URL:** https://baserow.darho.net/form/qGqeK05o89p_dXVUn9OA1fj4mb5qOYgF8v1OU8e4glg

Configured fields (all required):
- **Review Title**, **Decision**, **Comments**, **Reviewer**, **Need**

Submit message: *"Thank you — your review has been recorded."*

### Approval Rule

A StakeholderNeed becomes **Approved** when at least one Review exists with Decision = Approved AND no Review exists with Decision = Rejected.

### Ready to Baseline View

A Grid view on Requirement, filtered where Status = Approved.

---

## Task 3 — Baserow on the Internet

### Deployment Method

Cloudflare Tunnel, running as a systemd service on the Contabo VPS. Public hostname `baserow.darho.net` routes through Cloudflare edge to the tunnel, which forwards to Caddy in the Baserow container on `localhost:80`.

Reason: no manual DNS or TLS setup needed, HTTPS provided by Cloudflare, no inbound firewall ports required.

### Public URL

**https://baserow.darho.net**

### Security

- HTTPS only via Cloudflare edge
- Public sign-up disabled in Baserow admin (`core_settings.allow_new_signups = false`)
- Separate Baserow account used for the sync pipeline (JWT authentication)
- UFW firewall on the VPS allows only SSH (port 22)
- fail2ban installed and running

### Backup and Restore

`backup.sh` runs `pg_dump` inside the container daily at 03:00, writes timestamped SQL to `backups/`, prunes to last 7. Restore was tested by piping a backup into a fresh `baserow_restore_test` database and confirming tables with `psql`.

### Deployment Diagram

```mermaid
flowchart LR
    Browser[Stakeholder Browser] -->|HTTPS| CF[Cloudflare Edge]
    CF -->|Tunnel protocol=http2| CFD[cloudflared systemd service<br/>on Contabo VPS]
    CFD -->|HTTP localhost:80| Baserow[Baserow Container]
    Baserow --> Vol[(baserow_data volume)]
    Sync[sync.py] -->|JWT over HTTPS| Baserow
    Sync --> Git[(Git Repository<br/>docs/generated/*.sdoc)]
    Backup[backup.sh cron 03:00] -->|pg_dump| Vol
