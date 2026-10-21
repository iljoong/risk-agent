# Business Skill Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local business chat application that streams questions and runs PDF-to-HTML skill workflows as durable background tasks.

**Architecture:** A React/TypeScript frontend talks to a separate FastAPI backend. SQLite and an owner-scoped data directory hold durable application state; a separate Python worker executes complex tasks through Microsoft Agent Framework and GitHub Copilot SDK, using Foundry OpenAI and Claude endpoints with refreshable Azure credentials.

**Tech Stack:** Python, FastAPI, Pydantic, SQLite, Azure Identity, Microsoft Agent Framework, GitHub Copilot SDK/CLI, React, TypeScript, Vite, pytest, Vitest, React Testing Library, Playwright. Use pypdf for text extraction and SQLAlchemy/Alembic for SQLite persistence/migrations.

**Spec:** `docs\superpowers\specs\2026-10-21-business-skill-chat-design.md`

## Execution record

The original detailed steps below are the planning brief. This status record describes the delivered implementation; equivalent behavior tests sometimes use consolidated names rather than the proposed test names.

- [x] Task 1: model configuration, refreshable credentials, and native Agent Framework/Copilot bridge.
- [x] Task 2: owner/chat-isolated persistence, versioned migrations, history, and recoverable file cleanup.
- [x] Task 3: startup skill/tool discovery, explicit native skill preloading, and registered-tool-only permissions.
- [x] Task 4: bounded PDF subprocess extraction, page/chunk context, coverage warnings, and offset readers.
- [x] Task 5: passive HTML/CSS validation, scoped immutable artifact versions, and sandboxed preview/download.
- [x] Task 6: durable queue, worker leases, cancellation/retry, and subprocess termination/restart recovery.
- [x] Task 7: HTTP routing, idempotent turns, foreground streaming, background events, and cancellation races.
- [x] Task 8: sample RFP skill, PDF input validation, and native tool-to-artifact execution.
- [x] Task 9: React workspace, Markdown, uploads, skill/model selectors, progress, history, and future-auth mockup.
- [x] Task 10: setup/extension documentation, exact dependency restoration, browser workflows, final review and regression fixes.
- [ ] Remaining operator-only verification: live OpenAI inference and RFP output quality. Live Claude basic inference was verified on 2026-10-21 through the direct Anthropic Foundry SDK and the app gateway after the operator assigned the required role.

Local verification: 67 backend tests passed with local native-runtime tests enabled, covering OpenAI Responses/Completions and Anthropic Messages; two live tests were excluded. Eight frontend unit tests and four browser scenarios passed. Python/TypeScript checks and configured linters passed. The backend wheel contains its migration resources.

Independent review identified routing-cancellation resurrection, oversized artifact context, inaccessible dense PDF pages, partial-frame reconnect corruption, and cross-chat upload completion. Each was reproduced with a failing regression test and fixed. Upload contamination was regraded from minor to important because it puts another chat's IDs into the composer and blocks sending. No review findings remain deferred.

Follow-up diagnosis on 2026-10-21 reproduced Claude HTTP 401 PermissionDenied outside the app as well as through the gateway. The configured Claude hostname was corrected and Azure CLI credential selection documented. Azure CLI was signed in as the same VM managed identity, so switching credential selectors did not grant inference access. The operator assigned Cognitive Services User, after which both direct inference and native gateway streaming succeeded. The investigation also exposed a caller-owned Copilot client lifecycle leak; two native success/error regressions failed before the fix and passed afterward. The full backend suite then passed 69 tests with two live tests excluded, with typing and lint clean.

### Recorded implementation decisions

- Work directly in the non-Git directory and keep all work uncommitted, as requested; the cost is no Git rollback history.
- Treat the user's instruction to begin implementation as plan authorization and execute inline; the cost is locally created application files without another approval pause.
- Package Alembic migrations with the backend instead of a backend-relative external folder; future migrations must follow that packaged location.
- Use half-second local heartbeat/cancellation polling with sixty-second leases instead of ten-second heartbeat polling; the cost is more short SQLite writes.
- Keep owner identity on records and recreate native sessions per turn rather than add unused owners/session-mapping tables; future authentication requires an identity-mapping migration.
- Use deterministic lexical page/chunk retrieval and explicit coverage notes rather than model-generated summaries or implicit neighboring-page expansion; omitted passages may require a precise follow-up or offset tool read.
- Do not acquire machine credentials or make billable cloud requests without explicit operator configuration/opt-in; actual tenant permissions and model quality remain unverified.

## Global Constraints

- Python backend; React and TypeScript frontend.
- Use Microsoft Agent Framework and GitHub Copilot SDK.
- Run locally for a single user initially, but include data isolation and background task execution now.
- Show mockup UI for future authentication and multiple users; do not implement those capabilities yet.
- Accept PDF attachments only.
- Use Microsoft Foundry for OpenAI and Claude models. Use Azure Identity `DefaultAzureCredential` for backend model authentication.
- Users select models in each chat. Model choices are supplied through environment configuration.
- Only agents invoke tools; users explicitly select skills, not tools.
- A single worker processes one background job at a time; other jobs remain visibly queued.
- Default limits are a two-minute foreground deadline and a thirty-minute background deadline; make those operator-configurable.
- Proposed upload limit: 25 MiB per file, configurable by the operator.
- Tokens stay in process memory and out of database records, browser responses, job payloads, logs, and generated artifacts.
- Do not initialize Git or create commits; the user chose uncommitted local files.
- Use Windows paths and PowerShell commands. No application implementation or dependency installation happens until this plan is reviewed and an execution method selected.

## Review Focus

- A model removed from configuration while a saved chat references it: show an actionable error; never substitute another model. Covered in Task 7.
- A duplicate send or competing SSE subscription: produce one turn and one execution, including races. Covered in Task 7.
- Worker termination after writing a file but before publishing its record: never expose an incomplete artifact as successful; recover only scoped orphan files. Covered in Tasks 5 and 6.
- A partly scanned PDF with some extractable pages: warn about missing pages rather than implying complete analysis. Covered in Task 4.
- A legacy SDK or CLI lacking refreshable provider callbacks: stop at a documented compatibility gate rather than ship expiring static tokens. Covered in Task 1.

---

## File Structure

The folder is empty except for the approved design and visual mockups. Create these files only during approved execution. Each task's Files block owns its exact paths.

```text
.gitignore                         # Ignore local data, environments, and mockup session state
.env.example                       # Document server-side settings without credentials
README.md                          # Windows setup, startup, extension, and verification instructions
backend\
  pyproject.toml                   # Backend dependencies and test/type/lint configuration
  requirements.lock               # Exact tested dependency resolution
  alembic.ini
  migrations\env.py
  migrations\versions\0001_initial.py
  src\skill_chat\
    config.py                     # Environment parsing and public model metadata
    contracts.py                  # Scope, context messages, agent request/events
    agents\gateway.py             # Agent Framework/Copilot bridge and cancellation
    agents\credentials.py         # Refreshable DefaultAzureCredential token providers
    storage\database.py           # Engine, sessions, migrations
    storage\models.py             # Database rows
    storage\repository.py         # Scoped transactions and ownership checks
    storage\files.py              # Scoped path resolution and staged writes
    extensions\registry.py        # Skill/tool discovery and fingerprint
    tools\context.py              # Typed trusted-tool contract and injected scope
    tools\documents.py            # Agent-only PDF/context reader
    tools\artifacts.py            # Agent-only artifact reader/publisher
    documents\ingestion.py        # PDF validation and page-aware extraction
    documents\context.py          # Bounded context assembly and page retrieval
    artifacts\service.py          # HTML validation, versions, publish/download
    tasks\service.py              # State machine, queue claims, cancellation, retry
    tasks\worker.py               # Worker CLI, heartbeats, agent execution
    chat\routing.py               # Structured intent classification
    chat\service.py               # Turn submission and foreground generation
    api\app.py                    # Application lifecycle, CORS/origin guards, health
    api\schemas.py                # Public request/response models
    api\chats.py                   # History and turn routes
    api\attachments.py            # Upload and ingestion status routes
    api\tasks.py                  # Task status/cancel/retry routes
    api\artifacts.py              # Preview/download routes
    api\events.py                 # Owned SSE and replay
  tests\
    conftest.py
    test_config.py
    test_agent_gateway.py
    test_storage.py
    test_extensions.py
    test_documents.py
    test_artifacts.py
    test_tasks.py
    test_chat.py
    test_api.py
    test_live_foundry.py
skills\rfp-response\SKILL.md         # Sample developer skill
web\
  package.json
  package-lock.json
  index.html
  vite.config.ts
  tsconfig.json
  src\
    main.tsx
    App.tsx
    styles.css
    api\client.ts
    api\types.ts
    api\events.ts
    chat\ChatSidebar.tsx
    chat\ChatView.tsx
    chat\Composer.tsx
    chat\ModelPicker.tsx
    chat\TaskCard.tsx
    artifacts\ArtifactPanel.tsx
    account\AccountDialog.tsx
    tests\workspace.test.tsx
    tests\events.test.ts
  e2e\rfp-workflow.spec.ts
  playwright.config.ts
```

Use focused modules and existing library primitives, not generic plugin frameworks. Add standard package initializer files as required. Do not add mockup server state or credential files to deliverables.

## Verification Conventions

Create the root virtual environment during Task 1. Run backend commands from the project root with `.\.venv\Scripts\python.exe`. Editable install: `.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"`. Run frontend commands with `npm --prefix .\web ...`. Install only after declaring dependencies or encountering a missing prerequisite.

Backend tests use temporary SQLite databases/directories and injected fake agents/credentials. Tests must not acquire real Azure tokens unless explicitly marked live. Add `live` marker and an opt-in environment gate; normal test collection must not instantiate `DefaultAzureCredential`.

Each task follows red/green: add the named tests, run the targeted command and confirm the expected missing implementation or behavioral failure, implement, then rerun the same command. Do not count missing third-party dependencies or broken test setup as the intended red result. Preserve an uncommitted checkpoint after each task; do not run Git commands.

### Task 1: Verify the SDK Bridge and Environment-Driven Models

**Files:** Create `backend\pyproject.toml`, `backend\requirements.lock`, `.gitignore`, `.env.example`, `backend\src\skill_chat\config.py`, `backend\src\skill_chat\contracts.py`, `backend\src\skill_chat\agents\gateway.py`, `backend\src\skill_chat\agents\credentials.py`, `backend\tests\conftest.py`, `backend\tests\test_config.py`, `backend\tests\test_agent_gateway.py`, `backend\tests\test_live_foundry.py`.

**Interfaces:**
- `load_settings(env: Mapping[str, str]) -> Settings`; settings include model choices, local data root, loopback bind, exact allowed frontend origin, task limits, and upload limit.
- `ModelChoice`: `id`, `label`, `provider`, `endpoint`, `deployment`, `scope`, `wire_api`, `context_budget_tokens`; parse JSON `APP_MODELS`. Default model is `APP_DEFAULT_MODEL_ID` or first choice.
- `Scope(owner_id: str, chat_id: str)`; `ContextMessage(role: Literal["system", "user", "assistant"], content: str)`.
- `AgentRequest(run_id: str, scope: Scope, model_id: str, messages: tuple[ContextMessage, ...], skill_id: str | None)`.
- `AgentEvent`: discriminated `text_delta`, `stage`, `tool_status`, `completed`, `error`, with typed payloads; no reasoning event.
- `AgentGateway.stream(request: AgentRequest) -> AsyncIterator[AgentEvent]`; `AgentGateway.cancel(run_id: str) -> None` is asynchronous.
- `create_token_provider(scope: str) -> Callable[[], Awaitable[str]]`, backed by process-owned Azure credentials and their cache.

- [ ] **Step 1:** Inspect the current official Python SDK/integration sources and CLI requirements. Record exact compatible versions and supported calls for custom providers, token callbacks, explicit skill activation, custom tools, event streaming, and cancellation. Choose the documented `GitHubCopilotAgent` route, or the narrow Agent Framework adapter allowed by the spec. Do not proceed with the product if essential APIs cannot be supported.
- [ ] **Step 2:** Declare/install the backend dependencies and test tooling, then add failing tests: `test_models_reject_duplicate_ids_and_invalid_endpoints`, `test_default_model_must_exist`, `test_non_loopback_bind_is_rejected`, `test_gateway_streams_without_reasoning`, `test_each_provider_request_uses_refreshable_callback`, `test_missing_callback_support_is_explicit_error`. Assert both OpenAI and Anthropic endpoint mappings, exact 25 MiB/120 s/1800 s defaults, no real credential acquisition, and cancellation reaching the SDK run.

  Representative config assertions after parsing a fixture containing two valid choices:
  ```python
  assert settings.upload_limit_bytes == 25 * 1024 * 1024
  assert settings.foreground_timeout_seconds == 120
  assert settings.background_timeout_seconds == 1800
  assert [choice.id for choice in settings.models] == ["proposal-openai", "proposal-claude"]
  ```
- [ ] **Step 3:** Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_config.py .\backend\tests\test_agent_gateway.py -q`; expect behavioral/import failures for the application functions.
- [ ] **Step 4:** Implement the interfaces and tested bridge; use SDK-native typed configuration internally. Configure no unrestricted built-in tools. Add token-refresh tests simulating expiry between two provider requests. Expose sanitized model IDs/labels separately from full server settings.
- [ ] **Step 5:** Rerun Step 3; expect all pass. Record resolved dependencies in `requirements.lock`. Add opt-in live tests that stream with one configured model of each provider and skip clearly without user configuration; do not claim live success when skipped.

### Task 2: Owner-Scoped Persistence, History, and Managed Files

**Files:** Create `backend\alembic.ini`, `backend\migrations\env.py`, `backend\migrations\versions\0001_initial.py`, `backend\src\skill_chat\storage\database.py`, `models.py`, `repository.py`, `files.py` in that directory, and `backend\tests\test_storage.py`.

**Interfaces:**
- `Database(settings: Settings)` and `Database.migrate() -> None`.
- `Repository.create_chat(owner_id: str, model_id: str, title: str) -> ChatRecord`; `list_chats(owner_id: str) -> list[ChatRecord]`; `get_chat(scope: Scope) -> ChatRecord`; `rename_chat(scope: Scope, title: str) -> ChatRecord`; `delete_chat(scope: Scope) -> None`.
- `Repository.transaction()` scopes database work; typed records expose IDs and lifecycle fields from the schema.
- `FileStore.root_for(scope: Scope) -> Path`; `resolve(scope: Scope, object_id: str) -> Path`; `stage(scope: Scope, content: bytes) -> StagedFile`; `commit(staged: StagedFile) -> StoredFile`; `cleanup_deleted_chats() -> None`.

- [ ] **Step 1:** Add `test_every_chat_query_is_owner_scoped`, `test_cross_chat_child_ids_are_rejected`, `test_traversal_and_symlink_escape_are_rejected`, `test_delete_busy_chat_is_conflict`, `test_interrupted_delete_resumes_only_scoped_cleanup`. Assert a synthetic second owner cannot see or delete the first owner's data, including by directly supplying a valid child ID.

  Ownership assertions:
  ```python
  chat = repository.create_chat("owner-a", "proposal-openai", "RFP")
  assert repository.list_chats("owner-b") == []
  with pytest.raises(NotFound):
      repository.get_chat(Scope("owner-b", chat.id))
  ```
  Define shared `NotFound`, `Conflict`, `InvalidInput`, and `Unavailable` application exceptions in `contracts.py` in this task; HTTP translation belongs to Task 7.
- [ ] **Step 2:** Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_storage.py -q`; expect missing repository behavior.
- [ ] **Step 3:** Implement migrations for owners/chats/turns/attachments/tasks/events/artifacts/versions and provider-session mappings. Use foreign keys, unique owner/chat/request idempotency keys, WAL, and short transactions. Resolve one local owner server-side. Keep explicit owner/chat predicates even for guessed valid IDs. Implement marked deletion and recoverable scoped file cleanup.
- [ ] **Step 4:** Rerun Step 2; expect all pass, including migration of a new database and reopening existing records.

### Task 3: Startup Skill and Agent-Only Tool Registry

**Files:** Create `backend\src\skill_chat\extensions\registry.py`, `backend\src\skill_chat\tools\context.py`, `backend\tests\test_extensions.py`; modify `backend\src\skill_chat\agents\gateway.py`.

**Interfaces:**
- `discover_extensions(skills_dir: Path, tools_dir: Path) -> ExtensionRegistry`.
- `ExtensionRegistry.skills`: immutable skill ID/name/description/source records; `fingerprint: str`; `tools`: typed registrations.
- `ToolContext(scope: Scope, run_id: str, task_id: str | None)` is injected by the host.
- Each developer module exports `TOOLS: tuple[ToolRegistration, ...]`; a registration carries a unique name, description, Pydantic argument model, and asynchronous handler receiving validated arguments plus `ToolContext`.
- Gateway construction accepts `ExtensionRegistry`; `AgentRequest.skill_id` activates exactly that registered skill.

- [ ] **Step 1:** Add `test_immediate_skill_children_are_discovered`, `test_invalid_duplicate_and_escaping_extensions_fail_startup`, `test_registry_fingerprint_changes_with_resources`, `test_explicit_skill_is_activated`, `test_tool_scope_cannot_be_overridden_by_arguments`, `test_unregistered_runtime_permissions_are_denied`.

  For a fixture containing one valid skill and one agent tool:
  ```python
  registry = discover_extensions(skills_dir, tools_dir)
  assert [skill.id for skill in registry.skills] == ["rfp-response"]
  assert len(registry.tools) == 1
  assert registry.fingerprint
  ```
- [ ] **Step 2:** Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_extensions.py .\backend\tests\test_agent_gateway.py -q`; expect discovery/registration failures.
- [ ] **Step 3:** Implement deterministic discovery, frontmatter/path validation, resource hashing, SDK-native registration, and an allowlist-based permission hook. Support synchronous registry construction but asynchronous handlers. Reject unknown selected skills. Never import code from uploads; developer tool modules are trusted installation-time code.
- [ ] **Step 4:** Rerun Step 2; expect all pass with SDK calls mocked at the verified bridge boundary.

### Task 4: PDF Validation, Extraction, and Bounded Context

**Files:** Create `backend\src\skill_chat\documents\ingestion.py`, `backend\src\skill_chat\documents\context.py`, `backend\src\skill_chat\tools\documents.py`, `backend\tests\test_documents.py`; modify `storage\repository.py` and `config.py`.

**Interfaces:**
- `validate_pdf(filename: str, content: bytes, settings: Settings) -> ValidatedPdf`.
- `extract_pdf(pdf: ValidatedPdf) -> ExtractedDocument`, with page text, missing-text page numbers, warnings, and extraction status.
- `AttachmentService.upload(scope: Scope, filename: str, content: bytes) -> AttachmentRecord`; store pending extraction, not synchronous unbounded parsing.
- `ContextBuilder.build(scope: Scope, model_id: str, question: str, artifact_version_id: str | None) -> tuple[ContextMessage, ...]`.
- Agent-only `read_document` accepts attachment ID and bounded page selection; returns page text/references, never arbitrary paths.

- [ ] **Step 1:** Add `test_pdf_signature_and_size_are_enforced`, `test_encrypted_malformed_and_image_only_pdfs_are_rejected`, `test_mixed_scanned_pages_produce_warning`, `test_pdf_text_never_becomes_system_instructions`, `test_context_is_scoped_bounded_and_page_referenced`. Generate small PDFs in fixtures; assert 25 MiB + 1 byte fails and missing pages are explicitly named.

  For a generated two-page PDF whose second page is image-only:
  ```python
  document = extract_pdf(validate_pdf("rfp.pdf", mixed_pdf, settings))
  assert document.missing_text_pages == (2,)
  assert document.warnings
  assert document.pages[0].number == 1
  ```
- [ ] **Step 2:** Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_documents.py -q`; expect ingestion/context failures.
- [ ] **Step 3:** Implement pypdf extraction in a bounded child process so timeout can terminate only that specific parser. Set configurable defaults of 500 pages, 30 extraction seconds, and 2,000,000 extracted characters. Use page-aware lexical retrieval with neighboring pages and explicit coverage notes; reserve response/instruction tokens inside each model's configured context budget. Disclose partial retrieval and refuse unsupported claims of exhaustive coverage.
- [ ] **Step 4:** Rerun Step 2; expect all pass, including timeout cleanup and a follow-up using saved extracted text after restart. Ingestion execution is wired to the worker in Task 6.

### Task 5: Safe HTML Artifacts and Immutable Versions

**Files:** Create `backend\src\skill_chat\artifacts\service.py`, `backend\src\skill_chat\tools\artifacts.py`, `backend\tests\test_artifacts.py`; modify `storage\repository.py` and `documents\context.py`.

**Interfaces:**
- `ArtifactService.publish(scope: Scope, run_id: str, task_id: str, html: str, title: str, parent_version_id: str | None) -> ArtifactVersion`.
- `ArtifactService.get(scope: Scope, version_id: str) -> ArtifactVersion`; `read_html(scope: Scope, version_id: str) -> str`.
- Agent-only `read_artifact` and `publish_html` use IDs and injected `ToolContext`; tool arguments cannot specify owner/chat.
- Artifact versions contain plain textual slide content, source references, producing turn/task, and immutable managed HTML.

- [ ] **Step 1:** Add `test_versions_are_immutable_and_owner_scoped`, `test_publish_rejects_scripts_external_assets_forms_and_active_urls`, `test_pending_file_is_not_a_published_artifact`, `test_artifact_text_is_available_to_context`, `test_cancelled_task_cannot_publish_success`.

  Parameterize rejection against these inputs, asserting `InvalidInput` and zero published versions:
  ```python
  unsafe_html = [
      "<script>alert(1)</script>",
      '<img src="https://example.com/tracker">',
      '<a href="javascript:alert(1)">Open</a>',
      "<style>@import 'https://example.com/style.css';</style>",
  ]
  ```
- [ ] **Step 2:** Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_artifacts.py -q`; expect missing publication behavior.
- [ ] **Step 3:** Implement HTML parsing with an explicit passive HTML/CSS allowlist and rejection diagnostics, not regex-only sanitization. Stage files, then atomically record publication only for a matching active task/owner. Download responses use attachment disposition and safe names; preview uses a separate restrictive HTML response/iframe path. Recover only old scoped unreferenced staging files, never active task output.
- [ ] **Step 4:** Rerun Step 2; expect all pass. Inject a failure between staged write and database commit and assert the resulting file is not visible as a completed version.

### Task 6: Durable Background Worker and Task Lifecycle

**Files:** Create `backend\src\skill_chat\tasks\service.py`, `worker.py`, and `backend\tests\test_tasks.py`; modify `storage\repository.py`.

**Interfaces:**
- `TaskService.enqueue(scope: Scope, turn_id: str, model_id: str, skill_id: str | None, registry_fingerprint: str, kind: Literal["ingest", "agent"]) -> TaskRecord`.
- `claim_next(worker_id: str) -> TaskRecord | None`; `heartbeat(task_id: str, worker_id: str) -> None`; `request_cancel(scope: Scope, task_id: str) -> TaskRecord`; `retry(scope: Scope, task_id: str) -> TaskRecord`; `recover_expired() -> int`.
- `TaskService.append_event(scope: Scope, task_id: str, event: AgentEvent) -> StoredEvent`; sequence IDs increase per turn.
- `Worker.run_once() -> bool` is asynchronous; CLI entry `python -m skill_chat.tasks.worker`.

- [ ] **Step 1:** Add `test_competing_claims_execute_once`, `test_queued_work_survives_restart`, `test_expired_running_lease_is_interrupted_not_replayed`, `test_completion_cancellation_race_has_one_terminal_state`, `test_retry_retains_original_inputs`, `test_registry_mismatch_fails_without_execution`, `test_worker_crash_cannot_publish_partial_success`.

  After claiming an enqueued job, advancing an injected clock beyond its lease, and recovering:
  ```python
  assert task_service.recover_expired() == 1
  assert repository.get_task(scope, task.id).state == "interrupted"
  assert task_service.claim_next("replacement-worker") is None
  ```
  Add `Repository.get_task(scope: Scope, task_id: str) -> TaskRecord` here; it always checks owner and chat.
- [ ] **Step 2:** Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_tasks.py -q`; expect lifecycle failures.
- [ ] **Step 3:** Implement one-at-a-time worker execution, transactional claims, ten-second heartbeats and sixty-second leases, bounded provider/tool deadlines, durable real-stage events, and idempotent cancellation. Run PDF extraction jobs before dependent agent tasks and store their attachment references. Retry creates a linked new task; missing model/skill is a visible error. Never automatically replay expired running jobs.
- [ ] **Step 4:** Rerun Step 2; expect all pass using a fake clock rather than real lease sleeps. Exercise a subprocess worker terminated by its exact PID and verify queued work remains and running work becomes interrupted.

### Task 7: Turn Routing, HTTP API, and Reconnectable Events

**Files:** Create `backend\src\skill_chat\chat\routing.py`, `chat\service.py`, `api\app.py`, `api\schemas.py`, `api\chats.py`, `api\attachments.py`, `api\tasks.py`, `api\artifacts.py`, `api\events.py`, `backend\tests\test_chat.py`, `backend\tests\test_api.py`.

**Interfaces:**
- `Router.classify(scope: Scope, message: str, attachment_ids: tuple[str, ...], skill_id: str | None, model_id: str) -> Literal["foreground", "background"]` is asynchronous.
- `ChatService.submit(scope: Scope, request: TurnRequest) -> TurnReceipt` is asynchronous; receipt has `turn_id`, `mode`, optional `task_id`, and `events_url`.
- `ChatService.stream(scope: Scope, turn_id: str, after_event_id: int | None) -> AsyncIterator[StoredEvent]`; claim foreground execution atomically on first subscription.
- API paths: `GET /api/models`, `GET /api/skills`, `GET|POST /api/chats`, `GET|PATCH|DELETE /api/chats/{chat_id}`, `POST /api/chats/{chat_id}/attachments`, `GET /api/chats/{chat_id}/attachments/{attachment_id}`, `POST /api/chats/{chat_id}/turns`, `GET /api/chats/{chat_id}/turns/{turn_id}/events`, `POST /api/chats/{chat_id}/turns/{turn_id}/cancel`, `GET /api/chats/{chat_id}/tasks/{task_id}`, `POST .../cancel`, `POST .../retry`, `GET /api/chats/{chat_id}/artifacts/{version_id}/preview`, `GET .../download`, `GET /health/live`, `GET /health/ready`.
- `TurnRequest`: `client_request_id`, `message`, `attachment_ids`, `skill_id`, `model_id`, `artifact_version_id`; owner fields are forbidden.
- `StoredEvent`: integer `id`, discriminated `type`, JSON `data`; SSE uses `id`, `event`, and JSON `data` fields. Public errors carry stable `code`, safe `message`, and `correlation_id`.

- [ ] **Step 1:** Add tests for explicit skill/background routing, direct short-answer streaming, PDF ingestion dependency, artifact-question foreground routing, explicit promotion, five-second configurable classifier timeout, invalid classification error, and no tool access for classification.
- [ ] **Step 2:** Add `test_duplicate_send_and_sse_subscriptions_execute_once`, `test_busy_chat_returns_409`, `test_removed_selected_model_does_not_fallback`, `test_disconnect_interrupts_only_foreground`, `test_background_events_replay_after_reconnect`, `test_all_child_endpoints_reject_cross_owner_ids`, and `test_origin_guards_and_preview_headers`. Verify history CRUD and confirmed delete cleanup too.

  Receipt idempotency assertions:
  ```python
  first = await chat_service.submit(scope, request)
  second = await chat_service.submit(scope, request)
  assert first.turn_id == second.turn_id
  assert first.task_id == second.task_id
  ```
- [ ] **Step 3:** Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_chat.py .\backend\tests\test_api.py -q`; expect missing routes/service behavior.
- [ ] **Step 4:** Implement bounded classification with selected-model structured output; persist turns before streaming and use 202 for queued work. Repeated `client_request_id` with identical payload returns the original receipt; reuse with a changed payload returns 409. Foreground generation requires an atomic claim and later subscriptions replay saved events rather than rerun. Expose safe stage events, persisted final messages, scoped task status, model changes, and artifact selection.
  Upload saves validated bytes with pending status. Submission creates any required ingestion jobs and the dependent agent job under the same turn, and the worker runs dependencies first. This avoids orphan ingestion jobs without a turn. The attachment status endpoint reports pending/processing/ready/failed. Chat GET returns persisted messages, active task summaries, and completed artifact versions so reopening needs no private SDK-history endpoint. Turn cancellation covers foreground execution and delegates to task cancellation for background turns.
- [ ] **Step 5:** Implement app lifespan, migration/readiness checks, worker-heartbeat readiness, exact-origin CORS/mutation guards, and credential-free diagnostics. Preview headers include sandbox/content restrictions and block network; Markdown safety is implemented in Task 9.
- [ ] **Step 6:** Rerun Step 3; expect all pass. Confirm no endpoint can execute an arbitrary named tool and no response leaks full provider settings.

### Task 8: End-to-End Sample RFP Skill

**Files:** Create `skills\rfp-response\SKILL.md`; modify `backend\src\skill_chat\tools\documents.py`, `tools\artifacts.py`, `extensions\registry.py`, and `backend\tests\test_tasks.py`.

**Interfaces:**
- Skill ID is exactly `rfp-response`; metadata describes drafting HTML response slides from attached RFP PDFs.
- Stages are `read_sources`, `extract_requirements`, `draft_narrative`, `generate_slides`, `publish`.
- Use only the scoped document/artifact tools from Tasks 4 and 5. Plain skill instructions/resources are loaded through the verified SDK mechanism, not ad hoc user prompt concatenation.

- [ ] **Step 1:** Add `test_rfp_skill_publishes_page_referenced_draft`, `test_rfp_skill_marks_missing_supplier_evidence`, `test_rfp_skill_failure_leaves_no_completed_presentation`, and `test_followup_and_revision_reference_exact_version`. Use a fake gateway/tool interaction for deterministic state assertions and an opt-in live skill smoke test for actual model behavior.

  Deterministic fixture output must preserve these facts in artifact text:
  ```python
  assert "Needs confirmation" in artifact.text_content
  assert "RFP.pdf, page 1" in artifact.text_content
  assert revision.parent_version_id == artifact.id
  ```
- [ ] **Step 2:** Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_tasks.py -k rfp -q`; expect missing sample behavior.
- [ ] **Step 3:** Write the developer skill with the six default slide topics from the spec, required page citations, and exact `Needs confirmation` labeling for unsupported supplier claims. Publish a self-contained passive HTML/CSS draft plus textual metadata; revisions reference a parent version. Require at least one valid PDF and never contact external parties.
- [ ] **Step 4:** Rerun Step 2; expect all pass. Check the live smoke test's factual/evidence assertions only when real configured access is available; record any unverified live behavior explicitly.

### Task 9: React Workspace, Streaming UI, and Artifact Preview

**Files:** Create the `web` package/configuration and all `web\src` files listed in File Structure.

**Interfaces:**
- `ApiClient` methods mirror Task 7 schemas; generate or maintain matching discriminated TypeScript types without `any`.
- `subscribeTurn(chatId: string, turnId: string, afterId: number | undefined, signal: AbortSignal): AsyncIterable<TurnEvent>` uses authenticated-free local HTTP fetch streaming, safe parsing, event IDs, and bounded reconnect/backoff.
- `Composer` emits `{message, attachmentIds, skillId}`; `ModelPicker` consumes configured `{id,label}[]`; `ArtifactPanel` receives a concrete owner-checked preview URL/version, never raw HTML rendered in the app DOM.

- [ ] **Step 1:** Scaffold React/TypeScript/Vite with declared packages for icons, Markdown/GFM, tests, and accessibility helpers. Add failing tests for slash-skill selection, PDF-only uploads with visible errors, model selection persistence, disabled account controls, history actions, streaming spinner/status, cancel/retry, artifact selection/version, and chat busy controls.
- [ ] **Step 2:** Add `test_split_sse_chunks_and_duplicate_replay_do_not_duplicate_text` and UI tests asserting raw Markdown HTML/unsafe links are inert, iframe sandbox has neither scripts nor same-origin permissions, and failure/interrupted states are not styled as success.

  Preview assertions:
  ```typescript
  const preview = screen.getByTitle("HTML slide preview");
  expect(preview).toHaveAttribute("sandbox", "");
  expect(screen.getByRole("button", { name: "Sign in" })).toBeDisabled();
  ```
- [ ] **Step 3:** Run `npm --prefix .\web run test -- --run`; expect missing workspace behavior after test setup works.
- [ ] **Step 4:** Implement the accepted layout using the saved mockups as direction, not production code. Use a collapsible history/preview on small screens, keyboard-accessible controls and slash picker, reduced-motion support, escaped Markdown with GFM, and real event-driven task stages. Upload attachment IDs before submission; PDF ingestion itself remains background work.
- [ ] **Step 5:** Implement separate foreground versus background disconnect behavior, history refresh after completion, model IDs unavailable in current configuration, immutable artifact versions, and the explicitly disabled future account panel. Do not invent a real authentication provider.
- [ ] **Step 6:** Rerun Step 3 and `npm --prefix .\web run build`; expect tests pass and production TypeScript build succeeds.

### Task 10: Browser Workflow, Operations, and Handoff Documentation

**Files:** Create `web\e2e\rfp-workflow.spec.ts`, `web\playwright.config.ts`, `README.md`; modify `.env.example`, `backend\tests\test_api.py`, `backend\tests\test_live_foundry.py`, and package scripts.

**Interfaces:**
- API startup: `.\.venv\Scripts\python.exe -m uvicorn skill_chat.api.app:create_app --factory --host 127.0.0.1 --port 8000`.
- Worker startup: `.\.venv\Scripts\python.exe -m skill_chat.tasks.worker`.
- Frontend startup: `npm --prefix .\web run dev -- --host 127.0.0.1 --port 5173`; configured allowed origin must exactly match.
- Automated E2E harness injects a deterministic fake `AgentGateway` through test application construction, never a production environment bypass or fixture endpoint.

- [ ] **Step 1:** Add a browser scenario: select configured model, attach a generated text PDF, invoke `/rfp-response`, see queued/running stages, close/reopen the page, open the saved slides, and ask an artifact-grounded follow-up. Assert the final reply references that artifact and the PDF page, not merely that a card exists.

  After the reopen and artifact-grounded answer:
  ```typescript
  await expect(page.getByTitle("HTML slide preview")).toBeVisible();
  await expect(page.getByTestId("latest-assistant-message")).toContainText("RFP.pdf, page 1");
  await expect(page.getByTestId("latest-assistant-message")).toContainText("Version 1");
  ```
- [ ] **Step 2:** Add browser coverage for model change, cancellation, safe malicious-output preview, visible provider failure, and persisted history after API/worker restart. Run `npm --prefix .\web run test:e2e`; expect the new behavior assertions to fail before missing integration is fixed.
- [ ] **Step 3:** Fix only integration issues exposed by the scenarios. Document Windows prerequisites, exact dependency restoration, all process commands, environment JSON shape using deployment placeholders rather than invented model names, Azure identity setup and RBAC, PDF/OCR limits, local-only security boundary, and extension exports/restart requirements. Document the compatibility versions established in Task 1 and provider preflight commands.
- [ ] **Step 4:** Run `.\.venv\Scripts\python.exe -m pytest .\backend\tests -m "not live" -q`, backend configured lint/type checks, `npm --prefix .\web run test -- --run`, `npm --prefix .\web run build`, and `npm --prefix .\web run test:e2e`; expect all applicable checks pass. Keep E2E helper processes attached and terminate them after verification.
- [ ] **Step 5:** If user-supplied Foundry configuration is available, run `.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_live_foundry.py -m live -q` with the explicit opt-in gate and confirm both configured providers. Otherwise report live inference unverified, not complete. Never print access tokens while diagnosing.
- [ ] **Step 6:** Remove only task-created temporary fixtures/artifacts, retain source and useful mockups, and summarize the working deliverable and any real external blockers. Leave all changes uncommitted.

## Dependency Order and Self-Review

Execute Tasks 1-10 sequentially. This is one integrated vertical product rather than independent projects: the UI's observable behavior depends on scoped records, the queue, provider execution, and artifact lifecycle. No workflow or parallel worker pool is needed.

Coverage checked against the approved spec:

- UX/history/models/account placeholders: Tasks 7 and 9.
- Both SDKs/Foundry/refreshable credentials: Task 1, with live verification in Task 10.
- Owner isolation/file safety: Tasks 2, 4, 5, and 7.
- Background routing/state/restart/cancellation: Tasks 6 and 7.
- PDF-only ingestion/context limits: Task 4.
- Extension discovery and explicit skill/agent-only tools: Tasks 3 and 8.
- Artifacts/version context/sandboxing: Tasks 4, 5, 8, and 9.
- Operational readiness/documentation/acceptance: Task 10.

The five Review Focus cases each have named tests in their owning task. Public interfaces use the same scope, request, event, and model identifiers throughout; records are defined by Task 2 and consumed rather than recreated downstream. No omitted feature is implicitly approved, and no real resource credential or inference result is assumed.
