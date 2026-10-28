# RCI Agent demonstration manual

Evidence desk presenter guide | 28 October 2026

## 1. Demo at a glance

**Audience:** presenters, analysts, and stakeholders exploring the implemented investigation demo. Allow 15-20 minutes after setup. This manual describes the current app, not every capability in the aspirational scenario pack.

**Opening message:** "This is a fictional investigation workbench. The agent helps organize and challenge evidence; the analyst controls amendments and review. No bank, case-management system, or regulatory decision service is connected."

### What the audience will see

| Segment | Time | Demonstration |
|---|---|---|
| Open and prepare | 3 min | Create a session and collect packaged fictional evidence. |
| Inspect and challenge | 4 min | Inspect source limitations and ask the configured agent to challenge findings. |
| Amend and clarify | 4 min | Save an analyst correction and submit a bounded scope form. |
| Review and prepare | 4 min | Review six outputs and prepare a copyable case note. |
| Change and revisit | 3 min | Invalidate the review, inspect history, and reopen saved work. |

### The case in one minute

Harbour Components Ltd is a fictional industrial component wholesaler. Existing alert **ALT-2041**, shown in **CASE-1041**, has original AML priority **High**. Three receipts total **GBP 48,000**, followed by **GBP 45,500** to Meridian Supply: **94.79%** of the receipts, **56 minutes** after the first incoming payment.

The beneficiary is not observed in the available 90-day history. That is a stipulated scenario fact, not a deduction from the displayed rows or proof of a new commercial relationship. A supplier-payment explanation remains plausible. The invoice is missing and a previous case is restricted.

### Choose the presentation route

**Full route:** follow sections 2-8. Preparation uses no model inference, but sending messages and submitting the scope form call the configured model and may incur charges. Model wording, timing, and proposed updates are not guaranteed.

**No-inference route:** use preparation, source inspection, manual amendments, review, history, and reopening. Skip sending agent prompts, policy requests, and scope-form submission. Demonstrate the form by opening and cancelling it. Explicitly say that this route does not demonstrate live agent analysis.

**Core distinction:** saved amendments become context for subsequent agent turns; they do not automatically rewrite every other stage's prose or modify original source records. Affected stages are marked for re-review.

## 2. Prepare the environment

### Before the audience arrives

Use the repository root in Windows PowerShell. Follow **README.md** for first-time installation, dependency restoration, model configuration, and authentication. Do not copy credentials into prompts or demonstration material.

If upgrading, stop the app's API and worker and back up the configured data directory, `.data` by default, before startup migrations. Restore the backend and frontend locks as documented in the README. Restart both API and worker after extension or dependency changes; their configuration and data directory must match.

Use a configured model with authorized inference access for the full route. Select it before beginning. The sidebar session title is the same fictional case for each new investigation, so avoid creating unnecessary duplicate sessions during rehearsal.

### Start the three processes

**Terminal 1 - API**

```powershell
.\.venv\Scripts\python.exe -m uvicorn skill_chat.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

**Terminal 2 - durable worker**

```powershell
.\.venv\Scripts\python.exe -m skill_chat.tasks.worker
```

**Terminal 3 - frontend**

```powershell
npm --prefix .\web run dev -- --host 127.0.0.1 --port 5173
```

Open **http://127.0.0.1:5173**. Use the exact configured frontend origin. If a port is already occupied, use the README's alternate-port instructions rather than stopping an unknown process.

### Check readiness

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
```

Readiness requires a recent worker heartbeat. It does not validate cloud permissions or model quality. Rehearse one short model request separately before a full-route presentation; it may be billable.

**Presenter checklist:** use fictional data only; enlarge the browser for the audience; locate the model picker; keep the API and worker terminals available for diagnosis without projecting logs or secrets. Do not use the isolated automated-test servers as a substitute for the normal app.

## 3. Open the desk and inspect evidence

### Create the investigation

1. In the **Investigation sessions** sidebar, choose **New investigation**.
2. Confirm **CASE-1041 evidence desk**, the **Demo connector / fictional records** label, and the original **High** alert priority.
3. Point out the six stages: Detect, Investigate, Gather evidence, Analyze, Human review, and Decision.
4. Click **Prepare investigation**. Wait for the preparation task to succeed and **Refresh demo evidence** to become enabled.

**Expected result:** the transaction timeline and evidence register populate. Preparation retrieves packaged fixture records through the backend worker without model inference. It is not a live financial-system query.

### Explain navigation

Click **Analyze** to inspect its output. Clicking a stage selects the view; it does not advance the workflow. Use **Make current stage** only when deliberately changing the current workflow stage. Reviewing a note later sets Human review; preparing a note sets Decision.

### Inspect the underlying records

Open **Inspect SRC-01** from a relevant evidence item. Read the selected ledger records, fixture snapshot, version, retrieval timestamp, and coverage. Close the source before moving on.

| Record | UTC | Amount | Counterparty |
|---|---|---|---|
| TX-781 | 09:12 | +GBP 18,000 | Alder Industrial |
| TX-782 | 09:31 | +GBP 16,000 | Beacon Assembly |
| TX-783 | 09:54 | +GBP 14,000 | Cedar Parts |
| TX-784 | 10:08 | -GBP 45,500 | Meridian Supply |

In the **Analyze** output, point to the 94.79% comparison and 56-minute window. Explain that selected records do not supply balances or establish fund lineage or intent.

Inspect **SRC-04** to show the restricted prior case. Inspect **SRC-07** to show the missing invoice. **All sources (7)** provides another way to open each source.

**Expected result:** SRC-04 remains restricted and SRC-07 remains missing. Neither means an adverse finding or a completed corroboration check. Refreshing evidence changes retrieval observations; it does not make unavailable records accessible or make old fixture content newly current.

**Talk track:** "Source freshness and retrieval time are different. We can see what was supplied, what was not supplied, and why the conclusion remains limited."

## 4. Challenge and amend an interpretation

### Ask the configured agent

For the full route, click **Draft a challenge**. This only populates the composer. Read the prompt, then click **Send message**.

Wait for this new task to finish; do not mistake a preceding successful task for the new result. Inspect the response and stage output rather than promising a fixed answer.

**Suggested follow-up prompt:**

> What evidence challenges the concern? Separate observed facts, calculated comparisons, alternative explanations, and gaps. Propose a revised Analyze output with evidence references. Do not infer wrongdoing, fund lineage, or the contents of the restricted case.

**Expected behavior:** the agent receives the current saved investigation context and can propose scoped output updates. A proposal becomes canonical only after successful task completion. A response is not proof that an output was changed: inspect the stage's text and version. If no update was proposed, ask explicitly or use the manual amendment below.

### Save an analyst correction

Select **Analyze**, replace **Stage output** with the following example, and enter the reason.

> Selected records show GBP 48,000 incoming and GBP 45,500 outgoing within 56 minutes [E-01]. Timing alone does not establish intent or fund lineage. Supplier payments fit the business profile [E-03], but the invoice remains unverified [E-04, GAP-01]. Restricted case contents are not adverse evidence [GAP-02].

**Reason for stage amendment:**

> Preserve the alternative explanation and distinguish observed facts from interpretation.

Before saving, click **Detect** and return to **Analyze**. The unsaved output and reason should remain while inspecting stages. Click **Apply stage amendment** to persist them.

**Expected result:** the revision and output version increase; Analyze and downstream outputs require review; a prepared note is cleared. Earlier stage prose and the original source records are not overwritten.

### Explain persistence precisely

Saved edits enter subsequent agent context. Unsaved drafts survive stage inspection within the mounted desk, but are not a saved record and must not be relied on across reloads or session changes.

Open **Revision history** to inspect the amendment, reason, **Previous text**, and **Saved text** where available. Use **Load older revisions** when offered. This is application revision history, not proof of an external compliance audit system.

## 5. Clarify scope and check fictional policy

### Demonstrate the bounded A2UI form

1. With no active task, click **Clarify investigation scope**.
2. In **Investigation scope**, enter the example below.
3. For the full route, click **Apply scope and ask agent**.
4. Wait for **Scope clarification resolved.** and for the newly created task to succeed before continuing.

> Assess the permitted supplier-payment evidence. Keep the missing invoice and restricted prior case explicit. Do not infer a new commercial relationship from absence in the available 90-day history.

**Expected behavior:** the answer is persisted and queues one ordinary durable agent continuation. The worker does not wait while the analyst types. Pending, resolved, and cancelled status survives reopening.

For the no-inference route, do not submit. Click **Cancel scope clarification** instead. Opening or cancelling the fixed form is not an agent analysis demonstration.

If the official renderer cannot display the form, an accessible **Plain form fallback** may appear. It supports the same bounded answer and submission; it is not permission to load arbitrary agent-generated HTML or screens.

### Optional policy request

Open **All sources (7)** and inspect **SRC-05** and **SRC-06**. These contain fictional **G-AML-07 v3** and **L-01 v2** passages.

Click **Draft a policy check**, inspect the prepared composer text, and send it only on the full route. Alternatively use:

> Using the supplied fictional G-AML-07 v3 and L-01 v2 passages, identify the checks and gaps that remain before a human could recommend closure or escalation. Cite the passage locators. Distinguish this demo policy from law and do not claim the invoice has been corroborated.

**Expected discussion:** supporting and contradicting evidence must be considered; investigator validation and rationale remain necessary; the missing invoice and inaccessible case remain limitations. The generated wording is model-dependent and must be checked against the source passages.

### Explain AG-UI without overclaiming

**AG-UI** delivers replayable investigation snapshots and clarification activity to the fixed React workspace. User actions are validated server-side commands; conversation text keeps its existing separate stream.

**A2UI** renders only the restricted scope form. This is not arbitrary agent-authored workflow design, a complete AG-UI text/tool lifecycle implementation, or SDK checkpoint/resume of a worker waiting for human input.

## 6. Review and prepare the case note

Complete agent turns and amendments before this segment. Each further material change may invalidate review.

### Fill the human-owned outputs

Preparation populates evidence and analysis, not a complete human judgment. Inspect every stage. Do not acknowledge generic "Awaiting investigation preparation and human assessment" text as a completed assessment.

For **Human review**, amend the output as appropriate to the demonstration:

> Analyst checked the selected transaction comparison and considered the plausible supplier explanation. The invoice is unavailable [GAP-01]; prior case contents remain restricted [GAP-02]. No conclusion about intent or fund lineage is established.

For **Decision**, record a proposed disposition, not an executed decision:

> Proposed next action: obtain invoice corroboration and request authorized access to the prior case before considering closure. No closure, escalation approval, regulatory filing, or account restriction has been executed.

Enter a meaningful **Reason for stage amendment** for each change and click **Apply stage amendment**. These examples are presenter-supplied judgments, not automatic agent findings.

### Acknowledge and review

1. Visit all six stage outputs after the final amendment.
2. Validate each output and its evidence references. Click **Acknowledge this output** only when satisfied.
3. Wait until each stage shows **Acknowledged**, not merely a disabled button while a request is running.
4. Open **Review & record**. In **Analyst rationale**, enter the example below, adjusting it to the actual outputs.
5. Click **Mark note reviewed**, then **Prepare case note**.

> I checked the selected records and alternative supplier explanation. The invoice gap and restricted prior case remain unresolved. Further authorized evidence collection is proposed; no external decision or approval is confirmed.

**Expected result:** preparation must already have succeeded; all affected outputs must be acknowledged; rationale must be nonempty. The prepared note appears with the shared finding, stage outputs, rationale, evidence-derived references and gaps, and **External saving / approval: unconfirmed**.

### Copy, do not claim external completion

Click **Copy case note**, or manually select and copy the displayed note if clipboard access is unavailable. Use a disposable demonstration document as the destination, not a real case system.

**Talk track:** "This prepares a record for the existing human workflow. Copying is not saving to another system, approving a disposition, or closing a case."

## 7. Show that changes invalidate review

### Amend a shared fact

After preparing the note, open **Shared fact across all stages**. Change **Shared beneficiary description** to:

> Meridian Supply was not observed in the available 90-day history; the age of the commercial relationship is unknown.

In **Reason for shared fact amendment**, enter:

> Avoid equating absence from available history with a new commercial relationship.

Click **Apply shared fact amendment**.

**Expected result:** the shared finding changes; all six outputs require re-review; the reviewed flag and prepared note are cleared. **Copy case note** disappears and note review is unavailable until the required acknowledgments are renewed.

The shared wording is now available to all subsequent agent turns. It does not automatically replace each stage's text or alter immutable source content. If demonstrating agent propagation, send a short request to explain the amended shared fact and propose any needed output corrections; this is a model call.

### Inspect the record and reopen

Open **Revision history**. Show the actor, action, revision, reason, and before/after text for an amendment. Load older revisions when available.

Save any remaining draft before reloading. Reload the page and reopen **Harbour Components Ltd / CASE-1041** from the sidebar. If several sessions share that title, select the one just used. Confirm the saved amendment, evidence, and clarification status remain.

Reloading does not itself rerun evidence preparation or agent analysis. Browser disconnection does not cancel durable background work.

### Keep ordinary conversations distinct

Choose **New conversation** to show that ordinary chat, PDF review, optional skills, and saved HTML artifacts remain available. Do not introduce a removed historical RFP skill as a current product feature.

**Close the presentation:** "We have a persistent, editable evidence desk with traceable revisions. The analyst can challenge and correct the agent. Source limitations stay visible, and the app does not execute consequential financial or regulatory decisions."

### Reset for the next demonstration

Use **New investigation** for a fresh independent fictional session. Do not delete `.data` to reset the demo. Avoid **Refresh demo evidence** as a reset button: it creates a new preparation turn and can invalidate prior review.

## 8. Troubleshooting and boundaries

| Symptom | Presenter action |
|---|---|
| Task stays queued | Check worker readiness and matching API/worker configuration. Do not submit duplicates. |
| Controls are disabled | Wait for the active turn or mutation to finish. Review also needs prepared evidence, acknowledgments, and rationale. |
| Revision conflict | Keep the local draft. Compare with the saved output; use **Keep draft and use latest revision** when offered, then deliberately reapply with a reason. Do not blindly overwrite another revision. |
| Model fails or is unauthorized | Keep the failure visible. Check provider setup outside the presentation or switch to the no-inference route. Do not call a fixture response live inference. |
| Context exceeds budget | Shorten excessive saved outputs or choose a suitably configured model budget. A retry does not silently rebase stale analysis. |
| Source remains unavailable | Explain SRC-04 is restricted and SRC-07 is missing by design. Do not imply access bypass or successful invoice retrieval. |
| Note cannot be prepared | Finish preparation; amend placeholders; acknowledge every affected stage; enter rationale; mark the note reviewed. |
| Scope renderer fails | Use the plain fallback if offered. If the surface is invalid, reopen the session to reload it. |
| Copy fails | Select and copy the displayed note manually; external saving remains unconfirmed. |
| Sidebar is hidden | Use **Toggle history**, particularly on narrow screens. |

### Operating limits to state accurately

The app is local and single-user: one API process, one worker, one globally running task, and one active turn per session. Local scope is not multi-user authentication. Do not relax loopback/origin protections for an audience deployment.

**Stop** is a cooperative cancellation request; wait for its terminal outcome. **Retry** is explicit and creates a linked new task. Failed, cancelled, or stale proposals must not be presented as published output. Closing the browser is not cancellation.

This demo does not detect live anomalies, compute a validated risk score, prove regulatory compliance, or connect to live bank/case systems. Its revision history is not a complete regulated audit-control implementation. The scenario's alert queue, advanced filters, and full operating model are not all implemented.

The matched official A2UI packages retain an upstream Zod dependency advisory, **GHSA-mrhx-c7xc-m3w5**. Fixed-template validation and size/depth limits are safeguards, not a claim that the advisory is resolved. See the README for the dependency disclosure.

### Source material and maintenance

**README.md** is the operational source for installation, configuration, commands, limitations, and validation. The Markdown and PDF versions of this manual contain the same demonstration content.

- Scenario narrative and intended process: `docs\scenario\scenario.md` and `docs\scenario\process.md`.
- Implemented design: `docs\superpowers\specs\2026-10-28-investigation-evidence-desk-design.md`.
- Protocol design background: `docs\research\ag-ui-a2ui-integration.md`.
- Executable browser acceptance: `web\e2e\investigation-workflow.spec.ts`.

Recheck UI labels and behavior when the app changes. Automated fixture runs verify application behavior, not live inference quality, financial accuracy, or real-system permissions.
