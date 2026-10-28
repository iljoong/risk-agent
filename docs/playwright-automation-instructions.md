# Playwright agent instructions: RCI Agent demo walkthrough

Derived from `demonstration-manual.md`. For an agent with Playwright browser tools. The app is a **fictional** AML investigation demo; never enter real data.

## Rules for the agent

- Locate elements by accessible role and visible name (use the **bold** labels exactly). Use a page snapshot before each action; do not rely on pixel coordinates.
- After every step, verify its **Expect** line. If it fails, stop and report the step number, expected vs. actual, and a snapshot. Do not retry destructive steps.
- Default route is **no-inference**: skip every step tagged `[MODEL]` (they call a billable model). Run them only if the user asks for the full route.
- Wait on UI state, not fixed delays: for tasks, wait until the status shows success and the named control is enabled (timeout 120 s; 300 s for `[MODEL]` steps).
- "Acknowledged" means the visible text **Acknowledged**, not merely a disabled button.
- Do not click **Refresh demo evidence** (it invalidates review). Do not delete `.data`. Do not use `?prototype=centered-chat`.
- Never send credentials or real data. Do not stop unknown processes.

## 0. Preconditions

1. API, worker and frontend run on `http://127.0.0.1:8000`, worker, and `http://127.0.0.1:5173`.
2. GET `http://127.0.0.1:8000/health/ready` returns success (needs a worker heartbeat). If not, stop and report.
3. Use a desktop viewport of at least 1280x800 (below 1000 px, history and chat become drawers).
4. If ALT-2041 already has a case (its button reads **Resume alert**), either resume it and skip step 2's "creates" expectation, or ask the user before deleting its session.

## 1. Open the app

1. Navigate to `http://127.0.0.1:5173`.
   - Expect: sidebar with **Alerts (fictional demo)** and a **New investigation** button.
2. Expect four alerts listed (ALT-2041, ALT-2038, ALT-2036, ALT-2033), each showing ID, priority, subject, trigger and either "No case yet. Review by ..." or "Case open at ...".

## 2. Open alert ALT-2041

1. Click **Open alert ALT-2041, Harbour Components Ltd** (or **Resume alert ...**).
   - Expect: heading **CASE-1041 evidence desk**; label **Demo connector / fictional records**; original priority **High**; text **Question to answer** and a statement that no evidence has been collected.
2. Expect six stages: Detect, Investigate, Gather evidence, Analyze, Human review, Decision. Current stage is **Investigate**.
3. Click **Detect**.
   - Expect: **Read-only** panel; no editable stage output / no **Apply stage amendment**.
4. Click **Continue to Investigate**.
   - Expect: Investigate stage shown.

## 3. Prepare evidence (no model)

1. Click **Prepare investigation**.
   - Wait: task succeeds and **Refresh demo evidence** becomes enabled.
2. Click the central **Evidence** tab.
   - Expect: transaction timeline with TX-781 (+GBP 18,000, Alder Industrial), TX-782 (+GBP 16,000, Beacon Assembly), TX-783 (+GBP 14,000, Cedar Parts), TX-784 (-GBP 45,500, Meridian Supply); evidence register.

## 4. Inspect sources

1. Click **Inspect SRC-01**.
   - Expect: ledger records, snapshot, version, retrieval timestamp, coverage. Click **Close source**.
2. Click **Analyze**.
   - Expect: Output tab text mentions **94.79%** and **56 minutes**.
3. Click **Evidence**, then **All sources (7)**. Open **SRC-04**.
   - Expect: restricted prior case. Close it.
4. Open **SRC-07**.
   - Expect: missing invoice. Close it.
5. Open **SRC-05** and **SRC-06**.
   - Expect: fictional **G-AML-07 v3** and **L-01 v2** passages. Close each.

## 5. Manual amendment on Analyze

1. Click **Analyze**, then the **Output** tab.
2. Replace **Stage output** with:
   `Selected records show GBP 48,000 incoming and GBP 45,500 outgoing within 56 minutes [E-01]. Timing alone does not establish intent or fund lineage. Supplier payments fit the business profile [E-03], but the invoice remains unverified [E-04, GAP-01]. Restricted case contents are not adverse evidence [GAP-02].`
3. Fill **Reason for stage amendment**: `Preserve the alternative explanation and distinguish observed facts from interpretation.`
4. Persistence check (do not save yet): click **Detect**, then **Analyze**; click **Evidence**, then **Output**.
   - Expect: output text and reason are still present.
5. Click **Apply stage amendment**.
   - Expect: revision/version increases; Analyze and downstream stages need review.
6. Open **Revision history**.
   - Expect: entry with the reason, **Previous text**, **Saved text**. Use **Load older revisions** if shown.

## 6. Scope form (no model)

1. Scroll below the active tab and click **Clarify investigation scope** (requires no active task).
   - Expect: **Investigation scope** form.
2. Click **Cancel scope clarification**.
   - Expect: form closed/cancelled status. (`[MODEL]` alternative: enter `Assess the permitted supplier-payment evidence. Keep the missing invoice and restricted prior case explicit. Do not infer a new commercial relationship from absence in the available 90-day history.`, click **Apply scope and ask agent**, wait for **Scope clarification resolved.** and the new task to succeed.)
   - If a **Plain form fallback** appears, use it equivalently.

## 7. `[MODEL]` Agent challenge and policy check (skip by default)

1. Open the right assistant with **Chat** if closed. Select **Analyze**. Click **Draft a challenge** (fills composer), click **Send message**, wait for the new task to succeed.
2. Click **Draft a policy check**, click **Send message**, wait for success.
   - Expect: no fixed wording; confirm only that a response appears and stage text/version are inspected, not assumed changed.

## 8. Human review and Decision outputs

For each: select the stage, edit **Stage output**, fill **Reason for stage amendment**, click **Apply stage amendment**.

- **Human review** output: `Analyst checked the selected transaction comparison and considered the plausible supplier explanation. The invoice is unavailable [GAP-01]; prior case contents remain restricted [GAP-02]. No conclusion about intent or fund lineage is established.` Reason: `Record analyst assessment.`
- **Decision** output: `Proposed next action: obtain invoice corroboration and request authorized access to the prior case before considering closure. No closure, escalation approval, regulatory filing, or account restriction has been executed.` Reason: `Record proposed disposition only.`

## 9. Acknowledge and prepare the note

1. For each of the five editable stages (Investigate, Gather evidence, Analyze, Human review, Decision): select it, click **Acknowledge this output**, wait until **Acknowledged** is shown. Detect is already acknowledged.
2. Click the **Review** tab (or **Review & record**).
3. Fill **Analyst rationale**: `I checked the selected records and alternative supplier explanation. The invoice gap and restricted prior case remain unresolved. Further authorized evidence collection is proposed; no external decision or approval is confirmed.`
4. Click **Mark note reviewed**, then **Prepare case note**.
   - Expect: note with shared finding, stage outputs, rationale, references/gaps, and **External saving / approval: unconfirmed**.
5. Click **Copy case note** (if clipboard fails, report it; do not treat as failure of the app).

## 10. Invalidate review via shared fact

1. Click **Output**, open **Shared fact across all stages**.
2. Set **Shared beneficiary description** to: `Meridian Supply was not observed in the available 90-day history; the age of the commercial relationship is unknown.`
3. Set **Reason for shared fact amendment**: `Avoid equating absence from available history with a new commercial relationship.`
4. Click **Apply shared fact amendment**.
5. Click **Review**.
   - Expect: **Copy case note** unavailable; note review blocked until acknowledgments are renewed; five editable stages need re-review (Detect stays acknowledged).

## 11. Reopen saved work

1. Reload the page.
2. Click **Resume alert ALT-2041** (or pick the session in **Investigation sessions**).
   - Expect: saved amendment (Revision history), evidence and scope status persist; no new preparation task started.

## 12. Optional: alert without evidence

1. Click **Open alert ALT-2038 ...**, then **Prepare investigation**.
   - Expect: one missing source **SRC-00** and gap **GAP-01**; Analyze says no finding can be drawn.

## 13. Optional: layout and theme checks

- Click the sun/moon button; expect theme change.
- Click **Chat** to toggle the assistant; at width <= 1000 px, use **Toggle history** for sessions.
- Drag a sidebar divider (desktop) or focus it and press Left/Right/Home/End.

## 14. Report

Return a table of steps with pass/fail, plus screenshots for steps 2, 3.2, 5.5, 9.4, 10.5 and 11.2, and a list of skipped `[MODEL]` steps. State that results use fixtures and do not show live inference or real financial systems.

## Reset (only if asked)

Delete the ALT-2041 session from **Investigation sessions** to free the alert. Do not delete `.data`.
