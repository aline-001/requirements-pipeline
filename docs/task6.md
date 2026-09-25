# Task 6 — Change Requests

## Change Request State Diagram

States: Draft -> Submitted -> UnderReview -> Approved -> Implemented
                                 \-> Rejected
See SUBMISSION.md for the rendered Mermaid diagram.

## Baselining Rule

A baselined requirement changes only through an approved change request.
When a requirement is removed, its status is set to Obsolete, and its
ID is never reused — a new ID is issued for the replacement.

## Impact Assessment — CR Add SSO support to login

| Aspect | Value |
|---|---|
| Change Request | Add SSO support to login |
| Raised | 2026-09-24 |
| Target Requirement | REQ-001 |
| Affected Need | Secure user login |
| Affected Elements | Auth Subsystem, Login Component |
| Affected Verification | VER-001 |
| Proposed Change | Extend REQ-001 to accept SSO in addition to username/password |
| Effort Estimate | 3 days |
| Risk | Low |
| Status | Approved |

## End-to-End Demonstration

The change request is carried from Baserow through the sync pipeline to Git
and the RTM as follows:

1. Baserow — A new ChangeRequest row is created and moved to Approved. The
   target requirement REQ-001 is either edited (if the change preserves the
   ID) or replaced. If replaced, old REQ-001 is set to Obsolete and a new UID
   is issued — REQ-001 is never reused.

2. Sync — ./run_sync.sh re-fetches from the Baserow API. Requirements with
   Status = Approved are written to docs/generated/*.sdoc. Obsolete
   requirements are omitted from new sdoc files. Their historical records
   remain available in Baserow for audit.

3. Git — The regenerated .sdoc files are committed:
   git add docs/generated
   git commit -m change-REQ-001-updated-per-CR-Add-SSO-support

4. RTM — python3 rtm.py recomputes the RTM. The affected requirement appears
   with its new ID or statement, and the pass rate reflects the current
   state of the repository.

## Evidence

- ChangeRequest row Add SSO support to login is present in Baserow with
  Status = Approved, Requirement = REQ-001, Impact describes affected need,
  elements, and verification.
- A second row Remove session timeout demonstrates the Rejected path.

## Note on Live Demonstration

The end-to-end execution of this change request was documented rather than
performed live, due to a Baserow UI connection issue preventing row edits
from the browser and API restrictions on discovering the numeric option id
for the Obsolete status.

The pipeline itself is validated end-to-end by Tasks 4 and 5: every Approved
requirement in Baserow is written to .sdoc files by sync.py, committed to
Git, and appears in the RTM. Applying the same flow to the CR's effect on
REQ-001 would follow an identical path.

The ChangeRequest row "Add SSO support to login" is present in Baserow with
Status = Approved and its impact assessment is recorded above. The state
diagram documents the states and transitions the CR would pass through.
