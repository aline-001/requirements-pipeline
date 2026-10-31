# Requirements Engineering Pipeline — Submission

**Author:** Aline ASIMWE, intern, UR UNIPOD (Rwanda)
**Supervisor:** Patrick DARHO
**Deadline:** Friday 25 September 2026

## Links

| What | Link |
|---|---|
| Baserow (workspace "Requirements Engineering", database 169) | https://baserow.darho.net |
| Repository (source of truth) | https://github.com/aline-001/requirements-pipeline |
| RTM and coverage (computed from Git) | https://rtm.darho.net |
| StrictDoc documents and trace | https://rtm.darho.net/strictdoc/ |
| Form: Register a Stakeholder | ⟨FORM_REGISTER_STAKEHOLDER⟩ |
| Form: Submit a Need | ⟨FORM_SUBMIT_NEED⟩ |
| Form: Review a Need | ⟨FORM_REVIEW_NEED⟩ |
| Form: Request a Change | ⟨FORM_REQUEST_CHANGE⟩ |
| Form: Record a Verification Result | ⟨FORM_RECORD_VERIFICATION⟩ |
| View: Element Responsibility | https://baserow.darho.net/database/169/table/706/⟨VIEW_ID⟩ |
| View: Requirements by Element | https://baserow.darho.net/database/169/table/706/⟨VIEW_ID⟩ |
| View: Needs Without Approved Review | https://baserow.darho.net/database/169/table/709/⟨VIEW_ID⟩ |
| View: Unverified Requirements | https://baserow.darho.net/database/169/table/703/⟨VIEW_ID⟩ |
| View: Ready to Baseline | https://baserow.darho.net/database/169/table/703/⟨VIEW_ID⟩ |

The supervisor account (info.darho@gmail.com) is a workspace admin, so every view link opens directly after login. Form links are public share links; anyone with the link can submit, nobody can read the tables through them.

---

## Task 1 — Normalized Requirements Database

The Google Sheet retyped stakeholder names, sources and reviewers in every row. In Baserow each fact is stored once and referenced with link-row fields, so a stakeholder's name is changed in one place and every need, review and change request follows.

### Tables, fields, types and links

| # | Table (ID) | Fields (type) | Links |
|---|---|---|---|
| 1 | **Stakeholder** (683) | Name (text, primary), Role (text), Organisation (text), Contact (email/text) | ← StakeholderNeed, ← Review |
| 2 | **StakeholderNeed** (709) | Title (text, primary), Statement (long text), Priority (single select: Must/Should/Could), Rationale (long text), Source (text), Status (single select: Proposed/Approved/Rejected) | → Stakeholder; ← Review; ← Requirement |
| 3 | **Review** (704) | Review Title (text, primary), Decision (single select: Approved/Rejected/Changes requested), Comments (long text) | → Stakeholder (Reviewer); → StakeholderNeed (Need) |
| 4 | **Requirement** (703) | ID (text, primary, REQ-nnn), Statement (long text), Status (single select: Draft/Approved/Baselined/Obsolete) | → StakeholderNeed; ← Allocation; ← Verification; ← ChangeRequest |
| 5 | **SystemElement** (701) | Name (text, primary), Description (long text) | ← Allocation |
| 6 | **Allocation** (706) | id (primary) | → Requirement; → SystemElement |
| 7 | **Verification** (707) | Verification ID (text, primary), Method (single select: Test/Inspection/Analysis/Demonstration), Acceptance Criteria (long text), Result (single select: Pass/Fail/Not run) | → Requirement |
| 8 | **ChangeRequest** (708) | Title (text, primary), Description (long text), Impact (long text), Status (single select: Submitted/Approved/Rejected/Implemented) | → Requirement |

### Why each table exists

1. **Stakeholder** — the people who raise needs and review them are stored once; every other table links to them instead of retyping names.
2. **StakeholderNeed** — what a stakeholder wants, in their words, one need per row. It is the root of every trace and carries priority, rationale and where it came from.
3. **Review** — a decision is a separate fact (who decided what, when, why), and one need can have several reviewers, so it cannot be a column on the need.
4. **Requirement** — the engineering "shall" statement derived from a need. It has its own life cycle (Draft → Approved → Baselined → Obsolete) and a permanent ID.
5. **SystemElement** — the parts of the system that will carry the requirements; needed so responsibility can be assigned and queried.
6. **Allocation** — requirements and elements are many-to-many; a join table keeps each assignment as one row and makes both "who owns this requirement" and "what does this element own" simple views.
7. **Verification** — evidence that a requirement is met, with method, acceptance criteria and result; a requirement can have several verifications over time.
8. **ChangeRequest** — once a requirement is baselined it may only change through an approved request, so the request, its impact and its decision are recorded separately.

### Entity-relationship diagram

{{DIAGRAM:1-erd|Entity-relationship diagram (Baserow database 169)}}

### Test data loaded

| Table | Rows |
|---|---|
| Stakeholder | Jane Smith, Keza Kelly, David Mugisha |
| SystemElement | Auth Subsystem, Login Component, Session Manager, Password Reset Service |
| StakeholderNeed | NEED-3 Secure user login, NEED-4 Session timeout, NEED-5 Password reset |
| Requirement | REQ-001 (Obsolete, replaced through CR), REQ-002 (Approved), REQ-003 (Draft), REQ-004 (Approved, created by CR "Add SSO support to login") |
| Review | 3 reviews (one per need) |
| Allocation | REQ-004 → Auth Subsystem, REQ-002 → Login Component, REQ-003 → Password Reset Service |
| Verification | VER-1 → REQ-004, VER-2 → REQ-002, VER-3 → REQ-003 |
| ChangeRequest | "Add SSO support to login" (Implemented), "Increase session timeout" (Submitted), "Remove password reset" (Rejected) |

### Views

| Question | View | Table | Configuration |
|---|---|---|---|
| Which element is responsible for a requirement? | Element Responsibility | Allocation | grouped by Requirement |
| Which requirements are allocated to an element? | Requirements by Element | Allocation | grouped by SystemElement |
| Which needs have no approved review? | Needs Without Approved Review | StakeholderNeed | filter: no linked Review with Decision = Approved |
| Which requirements have no verification? | Unverified Requirements | Requirement | filter: Verification is empty |

---

## Task 2 — Stakeholder Intake Forms

Nobody edits tables directly: stakeholders, reviewers and engineers use five Baserow form views (links at the top).

| Form | Table | Fields (all required) | Who uses it |
|---|---|---|---|
| Register a Stakeholder | Stakeholder | Name, Role, Organisation, Contact | anyone joining the project |
| Submit a Need | StakeholderNeed | Title, Statement, Priority, Rationale, Source, Stakeholder | stakeholders |
| Review a Need | Review | Review Title, Decision, Comments, Reviewer, Need | reviewers |
| Request a Change | ChangeRequest | Title, Description, Requirement, Impact | anyone, for baselined requirements |
| Record a Verification Result | Verification | Verification ID, Requirement, Method, Acceptance Criteria, Result | test engineers |

### Submit a Need — help text and required fields

| Field | Required | Help text shown on the form |
|---|---|---|
| Title | yes | A short name for the need, 3 to 8 words. Example: "Secure user login". |
| Statement | yes | Describe one need only, in your own words: who needs what, and why it matters. If you have two needs, submit the form twice. Do not describe a solution. |
| Priority | yes | Must = the system is unusable without it. Should = important but there is a workaround. Could = nice to have. |
| Rationale | yes | Why is this needed? Give the problem, rule or event behind it. |
| Source | yes | Where does it come from? Meeting, interview, regulation, incident or document, with a date or reference. |
| Stakeholder | yes | Choose yourself from the list. Not listed? Use the Register a Stakeholder form first. |
| Status | hidden | Set automatically to **Proposed**. Only the review process changes it. |

### Rule: when a need becomes Approved

A stakeholder need becomes **Approved** when it has **at least one linked Review with Decision = Approved and no linked Review with Decision = Rejected**. A Rejected review keeps the need out of the baseline until the reviewer submits a new review. The "Needs Without Approved Review" view lists the needs still waiting.

### Ready to Baseline view

View "Ready to Baseline" on the Requirement table, filter **Status = Approved**. These rows are exactly what `sync.py` exports as new baseline content; after the Pull Request is merged they move to Baselined and leave the view.

{{DIAGRAM:2-form-flow|Flow from form submission to approved and baselined requirement}}

---

## Task 3 — Baserow on the Internet

### Docker setup with persistent storage

{{FILE:docker-compose.yml|yaml}}

All data (PostgreSQL, uploaded files) lives in the named volume `baserow_data`, so the container can be recreated or upgraded without data loss. SMTP credentials are in `.env`, which is not committed.

### Chosen method: Cloudflare Tunnel (named tunnel on a Contabo VPS)

`cloudflared` runs as a systemd service on the VPS and keeps an outbound connection to Cloudflare; `baserow.darho.net` is routed to `http://localhost:80`. Reasons:

- **No inbound port is opened.** The firewall allows only SSH; the tunnel connects outward, so Baserow is not directly reachable from the internet.
- **HTTPS and certificates are automatic** at the Cloudflare edge for `darho.net`, with no certificate renewal to manage.
- **Fixed address** independent of the server IP; the same tunnel also serves `rtm.darho.net`.
- QUIC (UDP) is blocked on this network, so the tunnel runs with `--protocol http2`.

### Security

| Requirement | How it is met |
|---|---|
| HTTPS only | Only entry point is the Cloudflare tunnel (TLS at the edge, "Always Use HTTPS" on). Docker ports are bound to `127.0.0.1`, so Baserow cannot be reached over plain HTTP on the VPS IP. UFW allows only 22/tcp. |
| Public sign-up off | Baserow Admin → Settings → "Allow creating new accounts" is off. New members join by email invitation only (Brevo SMTP). |
| Separate API token for the sync script | `sync.py` uses a Baserow **database token** (`BASEROW_TOKEN` in `.env`) with read on all tables and update on Requirement only, not a personal login. It can be revoked without affecting any user. |
| Server hardening | SSH key login only, root login disabled, fail2ban, UFW default deny. |

### Daily backup and tested restore

- `backup.sh` runs from cron at 03:00 every day: `pg_dump` inside the container, written to `~/backups/`, keeping the last 7 dumps.
- Restore test: the latest dump was restored into a fresh database `baserow_restore_test` inside the container and the tables were listed with `psql` (all Baserow tables present, row counts matching).

{{DIAGRAM:3-deployment|Deployment diagram}}

---

## Task 4 — Sync to StrictDoc

`sync/sync.py` (Python, standard library only) reads the Baserow REST API and writes four StrictDoc 0.30 documents to `docs/sdoc/`. Only approved needs and Approved/Baselined/Obsolete requirements are written; Draft requirements stay in Baserow. The merged Pull Request is the baseline, after which the requirement is marked Baselined in Baserow.

| File | Node type | Relations |
|---|---|---|
| `needs.sdoc` | `[NEED]` | — |
| `requirements.sdoc` | `[REQUIREMENT]` | Parent → NEED |
| `elements.sdoc` | `[ELEMENT]` | Parent → REQUIREMENT, role Implements |
| `verification.sdoc` | `[VERIFICATION]` | Parent → REQUIREMENT, role Verifies |

Each document declares its own `[GRAMMAR]`, so custom fields such as PRIORITY, STAKEHOLDER, SOURCE, METHOD and RESULT are valid, and sections use the StrictDoc 0.30 `[[SECTION]]` … `[[/SECTION]]` syntax.

### Example: requirements.sdoc (generated)

{{FILE:generated/requirements.sdoc|text}}

### Errors (the sync stops and writes nothing)

| Check | Example message |
|---|---|
| Broken link | `BROKEN LINK: REQ-002 -> NEED-4 is not Approved (status "Proposed")` |
| Duplicate ID | `DUPLICATE ID: REQ-002 is used by Requirement rows 2 and 9` |
| Requirement with no need | `NO NEED: REQ-004 is not linked to any stakeholder need` |
| ID removed from Baserow | `REMOVED: REQ-002 is in Git but no longer exported. Set it to Obsolete instead of deleting it.` |
| Obsolete ID reused | `ID REUSE: REQ-001 is Obsolete in Git and may not be reused (now Approved).` |

After writing, `run_sync.sh` also runs `strictdoc export`; if StrictDoc rejects the files nothing is pushed.

### Manual and scheduled run

- Manual: `./run_sync.sh` on the VPS (or `python3 sync/sync.py check` to validate only).
- Scheduled: cron `15 6 * * *` runs `run_sync.sh` daily. Each run first marks merged requirements as Baselined, then exports, validates, pushes a `sync/<timestamp>` branch and opens a Pull Request when something changed.

{{DIAGRAM:4-sync-sequence|Sync sequence: Baserow → script → Git → Baserow}}

---

## Task 5 — Traceability, Verification and RTM

Git is the source of truth. Traceability, the RTM and the coverage report are computed by `rtm.py` and `strictdoc export` from the files in the repository on every publish run; nothing is typed by hand.

### Repository structure

```
docs/sdoc/        needs.sdoc, requirements.sdoc, elements.sdoc, verification.sdoc   (generated by sync.py)
src/auth.py       implementation, functions tagged with @relation
strictdoc_config.py
rtm.py            -> site/index.html (RTM), site/rtm.csv, site/coverage.txt
publish.sh        -> site/strictdoc/ (StrictDoc HTML export)
```

### Trace in StrictDoc: need → requirement → element → code → verification

- **Need → requirement:** `[REQUIREMENT]` nodes have `Parent: NEED-n`.
- **Requirement → element:** `[ELEMENT]` nodes have `Parent: REQ-nnn` with role *Implements*.
- **Requirement → code:** StrictDoc's source traceability (enabled in `strictdoc_config.py`) reads `@relation` markers in `src/` and shows the function next to the requirement.
- **Requirement → verification:** `[VERIFICATION]` nodes have `Parent: REQ-nnn` with role *Verifies*.

In the published StrictDoc site, open *System Requirements* and select a requirement: its parent need, the element that implements it, the tagged function and its verification are shown together; the *Traceability* and *Deep traceability* screens show the whole chain.

### Functions tagged with @relation

| Function (src/auth.py) | Marker in docstring | Requirement |
|---|---|---|
| `login()` | `@relation(REQ-001, scope=function)` | REQ-001 (Obsolete, kept for audit) |
| `enforce_session_timeout()` | `@relation(REQ-002, scope=function)` | REQ-002 |
| `login_via_sso()` | `@relation(REQ-004, scope=function)` | REQ-004 |

### Verification records

Generated from `docs/sdoc/verification.sdoc` (entered through the Record a Verification Result form). Verifications of Draft requirements stay in Baserow until the requirement is approved.

{{VERIFICATION}}

### RTM (one row per requirement)

Published at **https://rtm.darho.net** (also `rtm.csv`). Current content:

{{CSV:generated/rtm.csv}}

### Coverage report

{{FILE:generated/coverage.txt|text}}

{{DIAGRAM:5-rtm-sequence|RTM computation and publication sequence}}

---

## Task 6 — Change Requests

A baselined requirement changes only through an approved change request. A removed requirement is set to Obsolete and its ID is never reused; `sync.py` enforces both (`REMOVED` and `ID REUSE` errors).

{{DIAGRAM:6-cr-state|Change-request state diagram}}

### Impact assessment — CR "Add SSO support to login"

| Item | Assessment |
|---|---|
| Request | Replace username/password login with single sign-on through the organisation's identity provider. |
| Reason | Users already have institutional accounts; separate passwords are a security and support burden. |
| Affected need | NEED-3 Secure user login (unchanged; the need is still valid). |
| Affected requirements | REQ-001 "authenticate users with username and password" → **Obsolete** (ID kept, never reused). New **REQ-004** "authenticate users via SSO", Parent NEED-3. |
| Affected elements | Auth Subsystem (allocation moves from REQ-001 to REQ-004). Login Component interface changes (redirect to identity provider). |
| Affected code | `login()` kept but marked for REQ-001 only; new `login_via_sso()` tagged REQ-004. |
| Verification | Old password-login test retired; new VER-1 (Test) for REQ-004. |
| Other requirements | REQ-002 session timeout: unaffected (sessions are created the same way after login). |
| Risk | Identity provider outage blocks all logins; mitigated by keeping an admin break-glass account outside SSO. |
| Effort | Small: one new function, one configuration, one test. |
| Decision | Approved by the change control board, then Implemented. |

### The change request carried end to end

| Step | Where | Evidence |
|---|---|---|
| 1. Request submitted | Baserow, Request a Change form | ChangeRequest row "Add SSO support to login", Status Submitted |
| 2. Impact assessed and approved | Baserow ChangeRequest.Impact | assessment above; Status Approved |
| 3. Requirements changed | Baserow Requirement | REQ-001 → Obsolete; REQ-004 created (Approved), linked to NEED-3; allocation and VER-1 added |
| 4. Sync | `./run_sync.sh` | Pull Request ⟨PR_URL⟩ showing REQ-001 STATUS Obsolete and the new REQ-004 |
| 5. Baseline | GitHub | merge commit ⟨COMMIT_URL⟩; next sync marks REQ-004 Baselined in Baserow |
| 6. RTM recomputed | https://rtm.darho.net | REQ-001 shown struck through as Obsolete; REQ-004 traced NEED-3 → Auth Subsystem → `login_via_sso` → VER-1 Pass |
| 7. Closed | Baserow | ChangeRequest Status Implemented |

---

## README — how to reuse the pipeline on a new project

{{README}}
