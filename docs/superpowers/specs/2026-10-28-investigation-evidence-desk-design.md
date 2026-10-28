# Investigation evidence desk with demo connector

Date: 2026-10-28
Status: Design for approval; not implemented.

## Intent and decisions

Turn the selected C prototype into a working investigation demo in the existing
RCI application. The analyst should inspect evidence, direct the agent, amend
stage outputs, and prepare a reviewed note without losing the case context.

The user selected **C, Evidence desk**, and requested implementation with a
**mock live connector for the demo app**. Their earlier requirements are to
rename chat sessions to investigation sessions, show the current workflow stage
above the workspace, propagate analyst amendments throughout the workflow, and
use AG-UI for bidirectional interaction. The user supplied `docs\scenario` and
`docs\research\ag-ui-a2ui-integration.md`.

Implementation choices below are recommendations, not additional user decisions.
The fictional financial-crime scenario is the scope of this demo, not evidence
that a general compliance product or regulated controls have been delivered.

## Goals and non-goals

Deliver a persistent six-stage workbench, a server-side demo source connector,
reconnect-safe shared state, actual configured-agent conversations with amended
context, and one bounded dynamic clarification form.

Do not add real banking/case-system integrations, monitoring rules, risk scores,
external writes, regulatory actions, multi-user authentication, arbitrary agent
UI, or automatic case closure. Do not copy the prototype's simulated agent
responses into the application or claim mocked source access is a live-system
retrieval. Do not require cloud inference to retrieve the demo evidence.

Preserve ordinary chat, PDF review, optional skills, existing artifacts and their
context-selection semantics, local guards, scoped files, provider configuration,
and the one-API/one-worker deployment. No fourth long-running process is needed.

## Workbench

Use the chosen C hierarchy: existing sidebar; investigation header and persistent
six-stage tracker; transaction timeline and evidence register; then editable stage
output and the existing conversation/composer. Keep source inspection, policy,
reviewed note, gaps, and revision history accessible in the same workspace.

The stages are Detect, Investigate, Gather Evidence, Analyze, Human Review, and
Decision. Audit history spans every stage. Selecting a stage inspects its output;
it must not silently advance the workflow. Explicit actions move the current stage
and permit returning to an earlier one.

The sidebar is titled **Investigation sessions** and its main creation action is
**New investigation**. That action creates a new, independent investigation of the
fixed demo case. Existing chats remain ordinary conversations and can still be
created through a secondary **New conversation** action, reopened, renamed and
deleted. Internal chat IDs and existing HTTP routes remain compatible.

Every investigation shows a persistent **Demo connector / fictional records**
label. Connector execution status, original AML priority, agent recommendation,
human review, and external decision status remain separate facts. Do not display
inferred completion percentages, hidden reasoning, or confidence scores.

The permanent shell, workflow navigation and human review controls are trusted
React components, not agent-authored A2UI.

## Mock live connector

Implement a bounded backend connector with an explicit interface and a
`DemoInvestigationConnector` implementation. It runs in the existing worker,
asynchronously retrieving fixed fictional records from a packaged scenario
fixture. It is not a browser-only mock, another server process, or an arbitrary
URL proxy. API requests cannot supply file paths, endpoints, owners or credentials.

The demo contains only CASE-1041 / ALT-2041 / Harbour Components Ltd. Every newly
created investigation gets its own scoped snapshot, revisions and action history;
the shared fictional case identifier does not merge separate sessions.

On **Prepare investigation**, the API durably queues a connector preparation
task. Expose queued/running/result states and observable source outcomes as the
worker proceeds. Preserve cancellation, deadlines, restart interruption and
explicit retry. Preparation can succeed with explicitly recorded evidence gaps;
a missing source is not equivalent to a failed preparation task.

Return the records, exact amounts, transaction times, KYC version, policy passages
and qualifiers from the supplied scenario. SRC-07 yields a missing-invoice result;
SRC-04 yields a restricted-case result. Do not add a control that magically makes
either source available. Record actual demo connector execution time separately
from the stipulated source snapshot time and source effective/review dates.

Display the enumerated transactions and compute GBP 48,000 incoming, GBP 45,500
outgoing, 94.79% rounded, and 56 minutes from those records. The four selected
transactions are not a complete ledger. Unprovided balances remain unknown.
Absence from the available 90-day history is a supplied scenario assertion, not
deduced from the displayed sample. Nothing establishes fund lineage or intent.

The original alert trigger and High priority are immutable source facts.
Analyst wording and structured findings live separately.

## Authoritative state and amendments

Store one investigation per server-derived owner/chat scope. Persist the current
stage, collected source outcomes and locators, shared facts, each stage output,
output version, review requirements, analyst rationale and note preparation state.
Add SQLAlchemy metadata and a new Alembic revision; do not alter the initial
migration or reset existing data.

Each successful domain mutation advances a monotonic investigation revision.
Mutations require a client request ID and expected revision. Apply the mutation,
revision/history entry, response receipt and outward state event atomically.
An identical retry returns the saved receipt; reuse with a different payload or
a stale revision conflicts. Refresh and preserve the user's unsaved draft on a
conflict instead of overwriting newer work.

An amendment records actor, actual timestamp, stage, before/after content, reason
and revision. Shared-fact changes invalidate all affected outputs; a stage-output
change invalidates dependent downstream outputs. The initial dependency model is
the ordered six-stage chain, with shared facts feeding all stages. Do not silently
rewrite analyst-approved prose as if it were the same version.

Every stage and subsequent agent run receives the current canonical shared facts
and relevant amended upstream outputs. Historical responses retain their original
revision. The note is assembled from the current versions and visibly marks stale
outputs. Any material change clears prior note review and invalidates a prepared
copyable note. Acknowledging an output records the current revision, not an
approval of a financial action.

While a connector or agent task is active, reject conflicting investigation
mutations. The analyst may inspect sources or edit a local unsaved draft. On
completion, refresh authoritative state before accepting amendments. This avoids
silently discarding human edits or publishing results against obsolete inputs.

Keep bounded source access, failures and versioned amendments in a local
application history. Do not call it a certified regulatory audit trail.

## Agent interaction

Use the existing configured Copilot SDK gateway and registered-tool boundary for
investigation conversations. Snapshot the authoritative investigation revision in
the submitted turn; include its bounded evidence, limitations and amended stage
outputs as explicitly untrusted context. Exceeding context limits must produce
an explicit coverage warning or request to narrow scope, not silent truncation.

Provide a scoped registered tool for reading the investigation and proposing
structured output updates. The tool receives the scope from ToolContext; it does
not accept owner/chat/path overrides. Restrict changes to permitted draft fields
and require the expected investigation revision and supported evidence IDs.
It cannot change the alert, approve a disposition, remove access failures, mark
a note reviewed, or execute external actions.

Stage agent output candidates against the current task. Publish them as new
versions only when that task succeeds and still matches its base revision.
Cancellation/failure must not publish a completed draft. Preserve any observable
source failures rather than pretending the whole run succeeded.

The **Challenge the concern** action submits a real new turn using current
context; its result can update analysis and the draft through the scoped tool.
The **Check policy requirements** action similarly uses the supplied fictional
policy passages. Do not hard-code a fake assistant answer or claim live model
quality from deterministic tests.

No human question holds the sole worker slot. A clarification finishes the turn;
an answer becomes an ordinary new turn with the resolved current context.
Durable SDK checkpoint/resume and a new waiting-task lifecycle are out of scope.

## AG-UI boundary

Use actual typed AG-UI state/activity envelopes, not renamed application stage
strings. Keep a dedicated scoped, persisted UI event log with one unique delivery
ID per emitted frame. An investigation snapshot and its delivery watermark come
from one consistent database transaction.

Expose a passive investigation subscription accepting an after cursor and
Last-Event-ID. Emit SSE id fields with AG-UI JSON data. Reconnect after the cursor
without restarting or claiming foreground execution; ignore duplicate delivery
IDs. Invalid checkpoints trigger explicit snapshot rehydration.

The first supported subset is STATE_SNAPSHOT / STATE_DELTA for authoritative
workspace state and ACTIVITY_SNAPSHOT for clarification surfaces. Prefer complete
state snapshots for the small initial workspace; do not emit fake deltas or tool
telemetry. Existing conversation text can continue using its established turn
stream; this version does not claim complete AG-UI text/tool lifecycle support.

User actions travel through scoped, validated, idempotent domain API commands,
not directly from a browser JSON patch into persisted state. The accepted result
is projected back through the AG-UI stream and supplies the next actual agent
run's context. AG-UI does not provide authorization or durability by itself.

Choose and pin compatible official protocol/schema dependencies during
implementation, checking current upstream APIs. Do not replace the inference
gateway or introduce a CopilotKit runtime solely to render the shell.

## Bounded A2UI clarification

Pilot one actual A2UI clarification surface for requesting or narrowing the
investigation scope. Use a matched, pinned v0.9-family protocol and React renderer
combination as recommended in the supplied research; verify accepted envelopes.

Carry its surface operations in an AG-UI activity with an explicitly documented
bridge convention. A restricted catalog permits text, layout, a text input and
an explicit submit button only. No arbitrary HTML, URLs, media, scripts, external
navigation, financial actions or host-control replacements are allowed.

Validate update size, component count/depth and action payloads on both sides.
The surface is at most 64 KiB, 100 components, depth 12, and one live clarification
per investigation. Answers are at most 16 KiB, subject also to the normal message
budget. Unknown actions/components and oversized updates fail visibly while
fixed navigation, conversation and evidence remain usable.

Persist pending/resolved/cancelled clarification state with its surface revision.
An answer checks scope, pending status and expected revision, records a unique
resolution, and queues at most one new ordinary turn atomically. Duplicate
submission cannot trigger a second run. Reload rebuilds the surface from a
complete snapshot instead of replaying cumulative create operations blindly.

The host provides an accessible plain-form fallback and cancellation control if
the renderer fails. This pilot does not allow arbitrary model-designed workflows.

## Review and export

Require current dependent outputs, analyst rationale and explicit human review
before preparing a reviewed note. Preserve all remaining gaps and citations.
Record proposed disposition as human input; the agent cannot approve it.

Provide a copyable, version-identified note for the existing external workflow.
Preparing/copying does not mark the case externally saved, closed, escalated,
filed, restricted or approved. External status stays unconfirmed. Keep downloaded
HTML artifacts on the existing passive validation/sandbox path.

## Operational and rollout boundary

Keep the prototype and its alternatives captured on
`prototype/investigation-workbench` (selection commit `a0e93eb`). Implement on a
separate feature branch, remove prototype-only files/entry points from that
implementation, and do not merge or commit unrelated existing user changes.

Document migration backup, API/worker restart, the mock connector label, new
investigation creation and offline verification in README. The existing three
processes and model configuration remain the operational model. A connector
preparation does not call cloud inference; actual agent requests use the configured
provider and may be billable.

The 2026-10-27 general-workspace specification remains the baseline except for
this explicitly added fictional investigation demo. Ordinary chat must continue
to work without a finance skill or investigation record.

## Acceptance and verification

Use temporary data and injected gateways for ordinary validation. Add focused
tests for migration preservation, scoped isolation, demo source outcomes and
arithmetic, duplicate/stale actions, transactional state/event ordering, cursor
replay, clarification validation and exactly-once resolution, amended context,
success-only output publication, review invalidation, and external-status bounds.

Exercise the C layout in Playwright: create an investigation, prepare the demo
pack, inspect a source, challenge a finding, apply an amendment, reconnect/reopen,
acknowledge affected outputs, review and prepare the note. Confirm earlier review
is invalidated after a material amendment. Verify an ordinary conversation and
existing artifact selection/cancel/retry behavior remain available.

Run the relevant existing backend and frontend lint/type/build/offline test
commands from README. Use the existing isolated E2E API/worker/UI harness.
Do not run live provider tests or upgrade the Copilot SDK implicitly.
Passing these checks demonstrates the demo workflow and transport, not real
financial-crime detection or regulatory suitability.
