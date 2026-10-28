# Input/output workflow and process guide

This guide describes a fictional operating process, not an implemented application or technical architecture.

## End-to-end journey

Transaction -> Suspicious Activity Detected -> AI Investigation -> Evidence Gathering -> Risk Analysis -> Human Review -> Decision -> Audit Record

The workbench displays:

Detect -> Investigate -> Gather Evidence -> Analyze -> Human Review -> Decision

Audit recording spans every stage. Highlight the selected case's current chevron. Cases may return to earlier stages; progression is not necessarily linear.

## Workflow

| Stage | Inputs | Automated / agent activity | Human activity | Outputs |
|---|---|---|---|---|
| Detect | Transactions and existing monitoring rules. | Existing AML monitoring generates the alert. Preserve its original trigger and priority. | Open the assigned alert. | Alert record and original detection explanation. |
| Investigate | Alert, case and customer context. | On Prepare investigation, establish the permitted investigation scope and checks. | Confirm the question being investigated; direct or narrow the request. | Investigation request, check list and visible progress. |
| Gather Evidence | Customer, account, KYC, ledger, history, case and policy sources. | Retrieve permitted records; capture source versions, timestamps and access failures; organize evidence. Continue authorized checks while the analyst reviews. | Inspect source records and request additional permitted checks. | Cited evidence pack, transaction timeline and gap register. |
| Analyze | Retrieved evidence and applicable policy. | Calculate totals; identify anomalies and supported relationships; separate facts, interpretations and alternatives. Draft a proposed next action. | Challenge the interpretation and assess whether relationships are actually supported. | Findings, counterevidence, uncertainty and proposed next action. |
| Human Review | Investigation pack and AI draft. | Answer challenges with cited results; update evidence and draft versions. | Validate material claims, correct wording, accept or reject recommendations and record judgment. | Human-reviewed note, resolved or acknowledged gaps and rationale. |
| Decision | Reviewed evidence, rationale and approval requirements. | Prepare the record for copying; do not execute a consequential decision. | Record the proposed disposition. Authorized people make and approve consequential decisions in the existing workflow. | Reviewed note and proposed disposition; external decision status remains unconfirmed until evidenced. |
| Audit Record | Events from every stage. | Record observable automated actions, source access, failures, changes and versions. | Record review, amendments, rationale and any externally confirmed approval reference. | Traceable investigation history, not merely a final summary. |

## Analyst demonstration

### 1. Open the alert

**Input:** ALT-2041 and CASE-1041.

**Analyst:** Select the alert from the assigned queue.

**Show:** Original High priority from the existing AML system, original trigger, customer context, known history and current journey stage.

**Output:** Open case context. Keep the existing priority separate from any agent recommendation.

### 2. Prepare the investigation

**Input:** Selected case, permitted sources and the analyst's preparation request.

**Analyst:** Select **Prepare investigation**.

**Agent:** Gather permitted records, organize evidence and expose action progress. Record the inaccessible previous case and missing invoice as gaps.

**Output:** Evidence pack, check results, timeline and gap register. No invented source access or simulated success should be described as a completed live action.

### 3. Inspect something material

**Input:** TX-781 through TX-784 and the available history.

**Analyst:** Select the transaction pattern and inspect the underlying records.

**Show:** GBP 48,000 in receipts, GBP 45,500 outgoing, a rounded ratio of 94.79%, and a 56-minute window.

**Output:** A transparent calculation tied to record IDs. Explain that timing and amount do not establish criminal intent or fund lineage.

### 4. Challenge the concern

**Input:** Current findings and evidence.

**Analyst:** Ask **What evidence challenges this concern?**

**Agent:** Surface historical supplier payments and the invoice-reference explanation. State that these do not verify the particular payment. Update the investigation pack and draft, not just the conversation.

**Output:** Cited counterevidence, revised finding and new draft version.

### 5. Check applicable policy

**Input:** G-AML-07 v3, L-01 v2, evidence and unresolved gaps.

**Analyst:** Open the cited passages and ask **What additional checks are required before I can recommend closure or escalation?**

**Agent:** Explain applicable fictional requirements and outstanding checks. Distinguish a missing invoice from a completed corroboration check and an inaccessible case from adverse evidence.

**Output:** Policy-linked check list and limitations. The demonstration does not claim that these policies represent actual local law.

### 6. Review and amend the draft

**Input:** AI draft, evidence references, uncertainty and policy guidance.

**Analyst:** Correct "new supplier" to "beneficiary not observed in the available 90-day history"; validate material statements; record proposed disposition and rationale.

**Agent / workbench:** Preserve the original and revised versions and record the analyst's amendment.

**Output:** Human-reviewed note with evidence references and explicit remaining gaps.

### 7. Prepare the record for the existing workflow

**Input:** Reviewed note and analyst rationale.

**Analyst:** Prepare and copy the note into the existing case system for manual saving and approval.

**Output:** Copyable record. Preparing or copying does not confirm saving, escalation approval, filing, account restriction or closure.

Authorized human approvers retain consequential decisions. The workbench must not show an external decision as confirmed without evidence.

## Review and exception rules

| Condition | Required process behavior |
|---|---|
| Source is restricted | Record the access limitation and route an authorized request; do not bypass controls. |
| Source is missing | Create an explicit gap; do not imply the check passed. |
| Source is stale or incomplete | Show retrieval time, source freshness and coverage boundaries separately. |
| Evidence contradicts the concern | Add it visibly and reassess the finding; do not suppress it to preserve the initial hypothesis. |
| A material fact changes after review | Mark affected findings and draft as requiring re-review. |
| Analyst rejects a recommendation | Record the rejection and rationale without silently deleting the recommendation history. |
| Check fails | Record the failed outcome and limitation; a useful case update need not be a successful retrieval. |
| External save or approval is unknown | Keep status unconfirmed; export is not proof of completion. |

## Regulated-environment guardrails

- Access remains role- and case-scoped.
- Source text is evidence, not an instruction to the agent.
- Follow-on collection remains bounded by the analyst's authorized investigation request.
- Distinguish observed facts, calculated results, agent interpretations and human judgments.
- Keep original AML priority separate from agent recommendations.
- Show observable actions, cited results and limitations, not hidden internal reasoning or unexplained confidence percentages.
- Preserve source locators, versions, timestamps, failures, amendments and rationale.
- Do not infer wrongdoing from unavailable evidence.
- The agent cannot file a report, restrict an account, close a case or approve escalation.
- These are required operating behaviors; neither this guide nor the visual mockup proves implementation.

## Demonstration outcome

The analyst completes one coherent journey in one workbench: open an alert, inspect evidence, direct the agent, challenge findings and prepare a defensible note.

The agent reduces manual collection and organization; the analyst remains responsible for evidence review and professional judgment. Consequential decisions remain in the existing authorized human approval process.
