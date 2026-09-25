# Task 2 — Stakeholder Intake Forms

## Forms

All records are added through Baserow Form views, not by editing tables directly. This ensures stakeholders, reviewers, and engineers supply data in a controlled way, with required fields, help text, and automatic status defaults.

### Form 1 — Submit a Need

**Table:** StakeholderNeed
**Public form URL:** (paste the URL from your Baserow Share form dialog)

**Purpose:** Stakeholders submit one need per submission, linked to their stakeholder record and a source. Every new need starts as Proposed.

**Configuration:**

| Field | Visible | Required | Help Text | Default |
|---|---|---|---|---|
| Title | Yes | Yes | Short summary of the need (one need per submission). | — |
| Statement | Yes | Yes | Describe exactly what the stakeholder requires. Be specific. | — |
| Priority | Yes | Yes | Must = non-negotiable; Should = important; Could = nice-to-have; Wont = out of scope. | — |
| Rationale | Yes | Yes | Why is this needed? What problem does it solve? | — |
| Status | No (hidden) | — | — | Proposed |
| Source | Yes | Yes | Where did this come from? Meeting, email, interview, ticket. | — |
| Stakeholder | Yes | Yes | Who is raising this need? | — |

**Rule:** Every new need starts as Proposed. This is enforced by a default value on the Status field. If the deployed Baserow version does not support defaults on hidden fields, the sync script (Task 4) treats a missing Status as Proposed.

### Form 2 — Review a Need

**Table:** Review
**Public form URL:** (paste the URL)

**Purpose:** Reviewers approve, reject, or request work on submitted needs.

| Field | Required | Help Text |
|---|---|---|
| Review Title | Yes | Short label for this review. |
| Reviewer | Yes | Your name. |
| Need | Yes | Which need are you reviewing? |
| Decision | Yes | Approved, Rejected, or Needs Work. |
| Comments | Yes | Explain your decision. |
| Reviewed At | Yes | Date of review. |

### Form 3 — Register a Stakeholder (described, not built)

**Table:** Stakeholder

| Field | Required |
|---|---|
| Name | Yes |
| Role | Yes |
| Organisation | Yes |
| Contact | Yes |

### Form 4 — Request a Change (described, not built)

**Table:** ChangeRequest

| Field | Required | Default |
|---|---|---|
| Title | Yes | — |
| Description | Yes | — |
| Status | No | Draft |
| Requirement | Yes | — |
| Impact | Yes | — |
| Raised At | Yes | Today |

### Form 5 — Record a Verification Result (described, not built)

**Table:** Verification

| Field | Required |
|---|---|
| Verification ID | Yes |
| Requirement | Yes |
| Method | Yes |
| Acceptance Criteria | Yes |
| Result | Yes |
| Verified At | Yes |

---

## Approval Rule

A StakeholderNeed becomes Approved when:

- At least one Review row exists with Decision = Approved, AND
- No Review row exists with Decision = Rejected

This rule is enforced by the Needs Without Approved Review view (Task 1), which filters for needs whose Review Decisions lookup does not contain Approved.

---

## Ready to Baseline View

A Grid view on the Requirement table, filtered where Status = Approved. This view shows requirements eligible to be synced to Git by the Task 4 script.

---

## Form Submission to Approved Requirement — Flow

```mermaid
flowchart TD
    A[Stakeholder opens Submit a Need form] --> B[Fills Title, Statement, Priority, Rationale, Source, Stakeholder]
    B --> C[Form submits]
    C --> D[StakeholderNeed created with Status = Proposed]
    D --> E[Reviewer opens Review a Need form]
    E --> F[Selects the need and enters Decision + Comments]
    F --> G{Decision?}
    G -->|Rejected| H[Need remains Proposed; Rejected review blocks approval]
    G -->|Needs Work| I[Need remains Proposed; stakeholder revises]
    G -->|Approved| J[Need satisfies approval rule]
    J --> K[Engineer creates Requirement linked to the need]
    K --> L[Requirement.Status = Approved]
    L --> M[Requirement appears in Ready to Baseline view]
    M --> N[Eligible for sync to Git in Task 4]
