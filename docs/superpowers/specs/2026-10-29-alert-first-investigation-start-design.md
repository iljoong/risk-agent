# Alert-first investigation start

Status: approved by the maintainer request "update specs and implement".
Amends `2026-10-28-investigation-evidence-desk-design.md`; its fictional-data, source-gap,
immutable-priority and unconfirmed-external-status rules are unchanged.

## Problem

The evidence desk can only be started from a generic "New investigation" button. An analyst
has no list of alerts to work from, nothing links an alert to its case, and opening the same
alert twice would create duplicate cases. Reviewed investigation tools (for example the NICE
Actimize case-management brochure and the demo at `app-hub-spark-team3`) begin from an alert
queue and only generate findings after the analyst has seen the alert.

## Decision

Work starts from an **alert**. A separate **New investigation** action remains for referrals
and manual leads.

| Entry point | Behavior |
| --- | --- |
| Select an alert in the alert list | Create the one case linked to that alert, or resume it if it exists. Idempotent per owner and alert. |
| New investigation (secondary) | Unchanged creation of a standalone fictional case for a referral or manual lead. It has no alert link. |

### Alert list

- Packaged fictional alerts (`ALT-2041`, `ALT-2038`, `ALT-2036`, `ALT-2033`) with priority,
  trigger, subject, received date and a review-by reminder. Labeled fictional / demo.
- Each row shows whether a case exists and its current stage. Priority is the immutable
  original alert priority; triage never edits it.
- Only `ALT-2041` has packaged evidence. Other alerts open normally, and preparation records
  an explicit source gap ("no demonstration records packaged for this alert") instead of
  inventing evidence or implying adverse content.
- The review-by date is a reminder, not legal or regulatory advice and not a filing deadline.

### Opening an alert

1. The case opens at **Investigate** with the original alert and its starting question visible.
2. Nothing is prepared automatically. The analyst may clarify scope (existing A2UI form)
   and then explicitly prepares evidence. Until then the desk states that no evidence has
   been collected.
3. Existing stage, amendment, challenge, review and note behavior is unchanged.

### Stage sub-tasks (guidance shown with each stage)

| Stage | Primary action |
| --- | --- |
| Detect | Read-only for alert-opened cases: shows the original alert and priority, starts acknowledged, is never invalidated, and rejects amendment. Continue to Investigate. |
| Investigate | State the question and scope. |
| Gather evidence | Prepare evidence; list gaps and restricted sources. |
| Analyze | Weigh supporting, contradicting and missing evidence with references. |
| Human review | Acknowledge affected outputs; record rationale. |
| Decision | Prepare the draft note; external status stays unconfirmed. |

## Contracts

- `GET /api/alerts` returns `{alerts: [{id, case_id, subject, priority, trigger, received,
  review_by, evidence: "demo" | "none", chat_id, stage}]}` for the server-derived owner.
- `POST /api/alerts/{alert_id}/investigation` with `{model_id?, client_request_id}` returns
  `{chat_id, revision, created}`; `created` is false when an existing case was resumed.
  Unknown alert IDs return 404.
- `investigations.alert_id` (nullable) with a unique `(owner_id, alert_id)` constraint added
  by Alembic revision `0003`. Deleting the chat frees the alert for a new case.

## Out of scope

Live alert feeds, assignment or triage writes, no-case-needed dispositions, SAR filing,
and any external write remain deferred.
