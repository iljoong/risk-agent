# Investigation Evidence Desk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the selected evidence-first investigation workbench with a server-side demo connector, persisted amendments, AG-UI shared state and one restricted A2UI clarification.

**Architecture:** Keep the existing API, worker, SQLite repository and Copilot gateway. A scoped investigation service owns versioned domain commands and projections; worker preparation uses packaged fictional sources, while agent output changes are staged until successful task completion. Fixed React panels consume authoritative snapshots and a passive replayable AG-UI subscription.

**Tech Stack:** Python/FastAPI/Pydantic/SQLAlchemy/Alembic; React/TypeScript/Vite; compatible pinned official AG-UI schemas and v0.9-family A2UI React renderer; existing pytest, Vitest and Playwright.

**Spec:** `docs\superpowers\specs\2026-10-28-investigation-evidence-desk-design.md` (approved by user on 2026-10-28).

## Global Constraints

- One API, one worker, one globally running background task and one active turn per chat; no fourth process.
- Use server-derived `Scope(owner_id, chat_id)`; retain local host/origin guards and current provider/SDK boundaries.
- Fixed case: CASE-1041 / ALT-2041 / Harbour Components Ltd; always label the connector and records as fictional.
- Six stages: Detect, Investigate, Gather Evidence, Analyze, Human Review, Decision.
- Keep original AML priority High distinct from agent recommendations and human proposed disposition.
- Preserve SRC-07 as missing and SRC-04 as restricted; do not fabricate balances, complete ledger rows, fund lineage or source access.
- Compute GBP 48,000 incoming, GBP 45,500 outgoing, 94.79% rounded, and 56 minutes from the supplied records.
- Mutation request IDs are idempotent; stale revisions and conflicting reuse fail without losing the local draft.
- Publish task-generated output candidates only on success; cancellation, failure and stale bases cannot publish a completed draft.
- A2UI maximum: 64 KiB, 100 components, depth 12, one live clarification; answer maximum 16 KiB plus normal message-budget checks.
- No consequential financial actions; external save/approval remains unconfirmed.
- Use root PowerShell and `.venv`; preserve unrelated dirty files and prototype commits on the throwaway branch.

## Review Focus

- Two tabs amend the same investigation: the stale tab sees a conflict and retains its draft rather than replacing newer content (Tasks 1 and 5).
- Connector cancellation after a partial retrieval: source observations remain labeled partial, no completed evidence pack is published, and retry is explicit (Task 2).
- Agent proposes an update and then fails: the previous canonical output survives and the candidate never becomes reviewed/exportable (Task 3).
- Clarification answer is repeated after reload or cancellation: at most one continuation exists and a cancelled interaction never resumes (Task 6).
- A replay cursor belongs to another chat or is beyond the latest event: fail/rehydrate explicitly rather than leak data, skip frames or execute a run (Task 4).

---

## File responsibilities and public interfaces

Create `backend\src\skill_chat\investigations`:

- `schemas.py`: Pydantic state, command, source, output and clarification contracts.
- `fixtures.py`: packaged fictional source records and policy text, not runtime reads from `docs`.
- `connector.py`: async source connector protocol and demo implementation.
- `service.py`: scoped domain commands, version/history and atomic publication.
- `projection.py`: snapshot/watermark, AG-UI frames and cursor validation.
- `context.py`: bounded untrusted investigation context for actual agent turns.
- `surfaces.py`: restricted A2UI surface creation/action validation.

Modify existing storage metadata/migration/database, task service/worker, chat service/context,
tool registration and API composition only at their existing seams. Add
`api\investigations.py` and `tools\investigations.py`.

Create `web\src\investigations`:

- `types.ts`, `client.ts`, `events.ts`: investigation DTOs, commands and validated AG-UI transport.
- `InvestigationWorkbench.tsx`, `investigation.css`: selected C layout.
- `StageEditor.tsx`, `EvidencePanel.tsx`, `ReviewPanel.tsx`: focused host-owned controls.
- `ClarificationSurface.tsx`: restricted renderer and accessible host fallback.

Use the existing conversation, composer, sidebar, artifact preview, and task cards.
The host `App` retains model/skill/artifact selection responsibilities.

Use snake_case domain JSON. AG-UI/A2UI adapters alone use their required wire naming.
Stage IDs are `detect`, `investigate`, `gather_evidence`, `analyze`, `human_review`, `decision`.

## Task 1: Versioned, scoped investigation state

**Files:** Create investigation schemas/service; modify `storage\models.py`,
`storage\database.py`, `storage\repository.py`; create
`storage\migrations\versions\0002_investigations.py`; test
`backend\tests\test_investigations.py`, `test_migrations.py`.

**Interfaces produced:**

- `InvestigationService(repository: Repository)`.
- `create(owner_id: str, model_id: str, client_request_id: str) -> dict` creates
  the chat and demo investigation atomically; duplicate creation returns the same session.
- `get(scope: Scope) -> InvestigationSnapshot`.
- `apply(scope: Scope, command: InvestigationCommand) -> CommandReceipt`.
- `InvestigationCommand`: `client_request_id`, `expected_revision`, discriminated
  `action`, validated action payload. Initial actions: amend output/shared fact,
  acknowledge stage, select current stage, review note, prepare note.
- `InvestigationSnapshot`: `chat_id`, `case_id`, `connector`, `revision`,
  `current_stage`, `sources`, `shared_facts`, `outputs`, `history`, `review`,
  `clarification`, `external_status`. Each output has stage, text, version,
  evidence IDs and re-review status; external status is always unconfirmed.
- `CommandReceipt`: `chat_id`, `revision`, `sequence`, optional `turn_id/task_id`.

Tables: one `investigations` row per owner/chat with JSON state and integer revision;
`investigation_commands` for scoped idempotent receipts; append-only
`investigation_revisions`; `investigation_ui_events` with unique integer delivery
IDs; `investigation_candidates` keyed by task with base revision and staged data.
Creation request IDs are unique per owner. Foreign keys cascade with chat deletion.
Use bounded strings/lists in schema validation, never unchecked arbitrary state patches.

- [ ] Write `test_investigation_commands_are_scoped_idempotent_and_version_checked`:
  duplicate payload returns the same revision; changed payload with reused ID and
  stale revision raise Conflict; another owner/chat raises NotFound.
- [ ] Write amendment/review tests: a stage edit flags downstream outputs, a shared
  fact flags all outputs, a reason is required, prior versions survive, reviewing
  stale outputs fails, and later amendments invalidate prepared notes.
- [ ] Extend migration tests: upgrade an actual 0001 database with a saved chat,
  preserve it, reach 0002, retain known unversioned-schema adoption and reject
  unknown schemas. Compare known initial/current metadata explicitly; never
  stamp an arbitrary database merely because it has a chats table.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_investigations.py .\backend\tests\test_migrations.py -q` and confirm new tests fail.
- [ ] Implement the contracts, migration and transaction-owning command service.
  Compose future queue writes through a shared SQLAlchemy Connection. Each accepted
  content mutation commits state, revision, receipt, history and state event together.
  Do not overwrite original alert fields or execute external actions.
- [ ] Run the same focused command to green; commit only this task's changed files,
  with the required Copilot co-author trailer.

## Task 2: Durable demo connector preparation

**Files:** Create `fixtures.py`, `connector.py`; modify investigation service,
`tasks\service.py`, `tasks\worker.py`, `storage\repository.py`;
test `backend\tests\test_investigation_connector.py`, `test_tasks.py`, `test_worker.py`.

**Interfaces consumed:** Task 1 state and transactional service.

**Interfaces produced:**

- `InvestigationConnector.retrieve(source_id: str) -> Awaitable[SourceResult]`.
- `DemoInvestigationConnector`: fixed allowlisted SRC-01 through SRC-07 only.
- `InvestigationService.prepare(scope, command, registry_fingerprint) -> CommandReceipt`.
- Shared-transaction variants of `Repository.create_turn` and `TaskService.enqueue`
  accept optional `connection: Connection`; preserve all existing callers.
- Internal turn request metadata:
  `investigation = {operation: "prepare" | "agent", base_revision: int, snapshot: dict}`.
  Only server code sets this field; do not expose it on generic TurnRequest.
- `stage_candidate(scope, task_id, base_revision, payload)` and
  `publish_candidates(connection, scope, task, terminal_state)` on investigation service.

- [ ] Write preparation tests asserting exact transaction arithmetic, source IDs,
  fixture/retrieval timestamps, missing invoice and restricted prior case outcomes;
  assert preparation makes zero gateway calls.
- [ ] Add duplicate preparation, active-turn lock, cancellation after a partial
  result, explicit retry, interrupted-worker recovery, and independent-case-session tests.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_investigation_connector.py .\backend\tests\test_tasks.py .\backend\tests\test_worker.py -q` and confirm new failures.
- [ ] Implement fixture-backed async retrieval in the existing worker. Queue turn,
  task, command receipt and initial projection atomically. Use current queue states,
  cancellation and timeouts, not a second scheduler or browser timer.
- [ ] Preserve partial source observations in staged task data and expose them as
  provisional progress; only publish the evidence pack on successful finish.
  Non-material task telemetry does not silently alter the content base revision.
  Finish/cancel/recovery hooks use the same transaction as domain publication.
- [ ] Run focused tests to green and commit this task's files with the co-author trailer.

## Task 3: Actual agent context and success-only output updates

**Files:** Create investigation `context.py`, `tools\investigations.py`; modify
`extensions\registry.py`, `chat\service.py`, `documents\context.py`,
`tasks\worker.py`, `tasks\service.py`; test
`backend\tests\test_investigation_agent.py`, `test_context.py`, `test_chat.py`.

**Interfaces consumed:** Task 2 internal metadata and staged publication.

**Interfaces produced:**

- `build_investigation_context(snapshot: InvestigationSnapshot, budget_bytes: int) -> str`
  includes revision, amended outputs, source locators, policy, counterevidence and
  explicit limitations as untrusted evidence. Reject an unusable budget or include
  explicit partial-coverage warnings; expose a bounded reader for omitted material.
- `investigation_tools(repository) -> list[ToolRegistration]` registers
  `read_investigation(character_offset, max_characters)` and
  `propose_investigation_output(expected_revision, stage_id, text, evidence_ids)`.
  Readers follow the existing 2,000-character continuation convention.
- All turns submitted to an investigation snapshot server state and use the durable
  background path; ordinary chats retain their current routing behavior.

- [ ] Write tests that the gateway sees the analyst's latest amendments and revision,
  old messages remain historical, unrelated chat data never enters context, and
  oversized context is explicitly bounded.
- [ ] Test injected tools: reject unsupported evidence IDs, external action fields,
  owner/path overrides and stale revisions. Assert proposal is invisible until
  task success, and remains invisible on cancellation/failure/recovery.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_investigation_agent.py .\backend\tests\test_context.py .\backend\tests\test_chat.py -q` and confirm new failures.
- [ ] Implement actual gateway integration without changing SDK/provider versions.
  Reject content mutations while any turn is active, including generic turn submissions.
  Persist the input snapshot on the turn; retries cannot silently rebase a stale
  analysis. A changed base requires a new request.
- [ ] Run focused tests to green; commit this task's files with the co-author trailer.

## Task 4: Scoped API and replayable AG-UI state

**Files:** Create `api\investigations.py`, investigation `projection.py`;
modify `api\app.py`, `api\schemas.py`, repository summaries, dependency manifests/lock;
test `backend\tests\test_investigation_api.py`.

**Interfaces consumed:** Tasks 1-3 service, queued work and snapshots.

**HTTP contract:**

- `POST /api/investigations`: `{model_id, client_request_id}` returns creation receipt.
- `GET /api/chats/{chat_id}/investigation`: `{snapshot, sequence}` read consistently.
- `POST /api/chats/{chat_id}/investigation/actions`: typed versioned command.
- `GET /api/chats/{chat_id}/investigation/events?after=N`: passive SSE with durable
  id fields and official AG-UI JSON envelopes.
- Existing chat summaries add optional investigation metadata; existing routes remain valid.

**Interfaces produced:**

- `snapshot_with_watermark(scope) -> tuple[InvestigationSnapshot, int]`.
- `read_ui_events(scope, after: int) -> list[dict]`.
- `STATE_SNAPSHOT` frames use complete authoritative state; ACTIVITY_SNAPSHOT is
  reserved for Task 6. Keep legacy turn streaming independent.

- [ ] Add tests for snapshot/watermark consistency, distinct IDs per frame, replay
  without task execution, cross-scope/future/malformed cursor rejection, and no
  foreground cancellation when a passive subscriber disconnects.
- [ ] Add route tests for local-origin guards, stale/reused commands and active work.
- [ ] Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_investigation_api.py .\backend\tests\test_api.py -q` and confirm new failures.
- [ ] Verify current upstream AG-UI schema APIs and pin compatible Python/TypeScript
  official schema packages; update manifests and locks before restoring dependencies.
  Validate envelopes instead of hand-casting application dictionaries.
- [ ] Implement the thin routes, scoped cursor semantics and consistent projection.
  Keep scoped sequence checkpoints; invalid checkpoints produce a documented
  rehydration response, never an inferred valid watermark.
- [ ] Run focused tests to green and commit this task's files with the co-author trailer.

## Task 5: Evidence-first production workbench

**Files:** Create frontend investigation types/client/events/workbench/editor/evidence/review/CSS;
modify `App.tsx`, `chat\ChatSidebar.tsx`, `api\types.ts`, `api\client.ts`;
test `web\src\tests\investigation.test.tsx`, `events.test.ts`, existing workspace tests.

**Interfaces consumed:** Task 4 HTTP/domain types and existing App conversation handlers.

**Interfaces produced:**

- `InvestigationWorkbench({snapshot, busy, onCommand, conversation})` composes
  fixed React panels around the existing conversation/composer subtree.
- `subscribeInvestigation(chatId, sequence, signal)` validates official AG-UI
  schemas, deduplicates IDs and requests rehydration on checkpoint errors.
- Client commands return `CommandReceipt`; typed conflict errors retain the local
  editor content and offer refresh/reapply rather than silent replacement.

- [ ] Write UI tests for C evidence-first hierarchy, selected versus current stage,
  every-stage editing with a required reason, shared-context propagation, stale-note
  blocking, conflict draft retention, and reopening an ordinary conversation.
- [ ] Add decoder tests for split frames, duplicates, malformed payloads, stale
  checkpoints and independent chat cursors.
- [ ] Run `npm --prefix .\web run test -- --run` and confirm new tests fail.
- [ ] Implement C with responsive source inspection and accessible forms. Preserve
  model/skill/artifact context, cancel/retry and PDF handlers in App. Do not retain
  the prototype's simulated responses or local canonical state as production logic.
- [ ] Rename sidebar actions as specified, add New conversation, and refresh summaries
  after server mutations. Preserve a local unsaved draft while authoritative state
  refreshes; disable application of conflicting edits during active work.
- [ ] Run frontend lint/unit/build commands to green and commit this task's files
  with the co-author trailer.

## Task 6: Restricted A2UI scope clarification

**Files:** Create backend investigation `surfaces.py`, frontend
`ClarificationSurface.tsx`; modify action schema/service/projection, client types,
dependency manifests/locks; test `backend\tests\test_investigation_surfaces.py`
and frontend investigation tests.

**Interfaces consumed:** Tasks 1-5 action receipts, AG-UI activities and host commands.

**Interfaces produced:**

- `build_scope_surface(clarification_id: str, revision: int, question: str) -> list[dict]`.
- Actions `request_clarification`, `resolve_clarification`, `cancel_clarification`
  in the domain-command union. Resolution carries interaction ID/revision and
  bounded `answer`, not arbitrary renderer context.
- Persisted interaction status pending/resolved/cancelled; a complete activity
  snapshot has stable surface/message ID, activity revision and A2UI operations.
- `ClarificationSurface({activity, onResolve, onCancel})` owns renderer state only;
  host validates action names/IDs and sends the versioned domain command.

- [ ] Test exactly-once resolution and turn enqueue in one transaction, duplicate
  submission after reload, stale/cancelled interactions, foreign IDs, forbidden
  components/actions, size/depth limits and rebuilding from a complete snapshot.
- [ ] Test renderer failure leaves ordinary chat/navigation/evidence usable and the
  host's accessible fallback can resolve the same validated interaction.
- [ ] Run focused backend and frontend tests and confirm new failures.
- [ ] Verify and pin a compatible official v0.9-family A2UI React/core package pair.
  Implement a catalog limited to text, layout, one input and submit. The scope
  clarification is host-requested, not an unrestricted agent UI authoring tool.
  Answer queues one new ordinary background turn; never hold a worker for a person.
- [ ] Run focused tests plus lint/type checks to green; commit this task's files
  with the co-author trailer.

## Task 7: End-to-end workflow and operational handoff

**Files:** Create `web\e2e\investigation-workflow.spec.ts`; extend
`backend\tests\e2e_server.py`; update README and approved design status.
Remove prototype-only `chat\InvestigationPrototype.tsx`, `PrototypeSwitcher.tsx`,
`investigation-prototype.css`, `main.tsx` development entry and package prototype
script from the implementation branch. The throwaway branch keeps their history.

**Interfaces consumed:** Completed Tasks 1-6; existing isolated Playwright harness.

- [ ] Add a deterministic injected provider that exercises the actual scoped update
  tool and context contract instead of bypassing domain publication.
- [ ] Add E2E coverage: create, prepare, inspect, challenge, amend, reload/reopen,
  acknowledge dependencies, review and prepare a note. Assert material edits
  invalidate review, source gaps remain open, external status remains unconfirmed,
  and ordinary conversation/artifact/cancel/retry workflows still function.
- [ ] Run `npm --prefix .\web run test:e2e` to identify new integration failures;
  implement any missing cross-process wiring without relaxing guards or production contracts.
- [ ] Update README with backup/restart steps, demo labels, model billing boundary
  and normal three-process commands. Remove prototype entry points, not historical
  prototype branches, and preserve unrelated user changes.
- [ ] Run backend offline pytest, mypy and ruff, plus frontend lint/unit/build/E2E
  commands from README. No SDK runtime/live/billable tests without explicit consent.
- [ ] Inspect the final diff and run one fresh whole-branch review. Address defects
  and rerun their focused checks. Commit only task-owned changes with the co-author
  trailer; do not merge to main automatically.
