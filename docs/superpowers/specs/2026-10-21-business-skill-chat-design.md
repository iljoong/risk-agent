# Business skill chat application

Date: 2026-10-21
Status: Implemented locally with completed local verification and independent review fixes. Live Claude authentication and basic inference were verified on 2026-10-21 after the operator granted the VM's managed identity the required inference role. Live OpenAI inference and full RFP-generation quality remain unverified.

## Intent

Give business users a familiar chat workspace in which custom skills complete substantial work, rather than only answering questions. Customer research, RFP analysis, and RFP response generation are motivating use cases. The first sample demonstrates attaching an RFP PDF and producing draft HTML slides, followed by questions about that saved result.

The application is implemented in `backend` and `web`; setup and verification commands are in the root README. The browser mockups remain throwaway design artifacts.

## User decisions

- Python backend; React and TypeScript frontend.
- Use Microsoft Agent Framework and GitHub Copilot SDK.
- Run locally for a single user initially, but include data isolation and background task execution now.
- Show mockup UI for future authentication and multiple users; do not implement those capabilities yet.
- ChatGPT-like layout: left chat-history sidebar, main conversation, attachments and skill invocation in the composer.
- Markdown responses, visible progress, and animated activity indicators.
- A collapsible right panel previews generated HTML. The user accepted the overall visual direction.
- Distinguish short questions from long or complex tasks. Stream short answers; run complex work asynchronously over HTTP.
- Persist generated content with its chat and make it available to follow-up questions.
- Discover developer-provided skills from the application's skills folder at startup; include a sample skill.
- Discover developer-provided custom tools too. Only agents invoke tools; users explicitly select skills, not tools.
- Accept PDF attachments only.
- Use Microsoft Foundry for OpenAI and Claude models. Use Azure Identity `DefaultAzureCredential` for backend model authentication.
- Users select models in each chat. Model choices are supplied through environment configuration.

## Proposed engineering decisions

The decisions in this section and the detailed behavior below are the assistant's recommendations, not statements that the user separately requested every detail.

- FastAPI provides the HTTP API; React with Vite provides the separate frontend.
- SQLite persists application records and a durable task queue. A separate Python worker executes queued jobs. No Redis or external database is required locally.
- An owner identity exists from day one; the local server supplies one fixed local owner. Clients cannot choose an owner through a request field or header.
- A sample `rfp-response` skill demonstrates the complete PDF-to-HTML workflow. Production customer-research integrations and other business skills will be supplied later by developers.
- Text-based PDF extraction only initially. OCR, password-protected PDFs, and other document formats are excluded and produce actionable errors.
- Generated slides are self-contained HTML/CSS, without arbitrary scripts or external assets. A presentation can be read by scrolling between slides.
- Bind local services to loopback. This version is not suitable for shared-network hosting.
- Public application name, exact typography, and icon choices remain builder decisions. "Workroom" in mockups is only a placeholder; do not use OpenAI branding or imply affiliation.

## Goals, non-goals, and anti-goals

### Goals

Deliver a working local application with persistent chat history, streaming answers, explicit skill invocation, durable background jobs, PDF attachments, saved HTML artifacts, and artifact-grounded follow-up questions. Make extension points usable by a developer adding skills or tools later.

### Non-goals

- Real user login, member management, account switching, sharing, or tenant administration.
- Hosted deployment, infrastructure provisioning, or creating Foundry deployments.
- Production implementations of all motivating business workflows.
- OCR, office-document uploads, PowerPoint export, or arbitrary generated web applications.
- Autonomous access to unrelated files, general shell execution, or arbitrary web browsing.
- A graphical skill or tool editor, runtime plugin installation, or hot reload of extensions.
- Automatic failover between models, hidden provider substitution, or resumable execution from an arbitrary agent step.

### Anti-goals

Do not fabricate company capabilities or claim that an RFP requirement is satisfied without evidence. Do not claim a task succeeded if output generation, persistence, authentication, or provider calls failed. Do not let generated HTML execute in the application origin. Do not treat owner-prefixed storage paths as a substitute for authorization or genuine authentication.

## User experience

### Chat workspace

Use the accepted three-column layout: history, conversation, and optional artifact preview. The preview collapses to give chat more space. Use familiar monochrome icons, restrained surfaces, readable message spacing, and accessible controls.

Support creating, opening, renaming, and deleting chats. Deletion requires confirmation and is blocked while a chat has active work; the user must stop that work first. Persist messages and timestamps. Show interrupted and failed responses distinctly.

The composer accepts text and PDF attachments. Typing `/` opens a searchable skill picker populated from the startup registry. Selecting a skill creates an explicit skill identifier in the send request, not merely an untrusted instruction string. Unknown explicit skills show an error rather than running ordinary chat. Tools never appear as slash commands or user-callable execution endpoints.

The model picker lists only configured choices. The selected model is saved with the chat and captured on each turn/task. A model cannot be changed while that chat has active work. Changing it affects future turns only, starts a compatible agent session, and retains application-owned conversation and artifact context.

Markdown rendering disables raw HTML and restricts unsafe link schemes. Show a spinner and concise stage/tool statuses while work is active. Do not expose hidden model reasoning. Offer stop controls for streams and tasks.

### Account placeholder

At the bottom of history, show "Local workspace" and "Account & access." Its panel shows the current local identity and disabled sign-in, workspace-member, and account-switching controls marked as future functionality. Do not choose an identity provider or present fake successful login behavior.

### Artifacts

Show saved artifact cards in the conversation. Opening a card reveals the HTML presentation in the right panel and offers download. Preview rendering uses an iframe sandbox with scripts, same-origin access, forms, navigation, and network access disallowed, plus restrictive content security policy. Serve raw artifact downloads as attachments with safe filenames and MIME headers.

New generations and revisions create immutable artifact versions, linked to their producing turn/task. Failed tasks may leave explicitly incomplete output, but cannot publish it as a completed presentation. The user can reopen a completed version after restarting the app.

## Backend and agent integration

### Process boundaries

1. Frontend: browser UI only; no Azure credentials or raw provider configuration.
2. API: owner resolution, validation, records, PDF ingestion, routing, foreground streaming, event delivery, and artifact access.
3. Worker: claims durable jobs, restores scoped context, invokes the agent, writes progress and artifacts.

API and worker share the local SQLite database and managed data directory. The worker does not depend on a browser connection. Use transactional queue claims, SQLite WAL, bounded database transactions, task leases/heartbeats, and an explicit one-worker deployment initially. A single worker processes one background job at a time; other jobs remain visibly queued.

### Agent roles and compatibility boundary

Use Microsoft Agent Framework's Python GitHub Copilot integration as the preferred common agent interface. GitHub Copilot SDK/runtime supplies the agentic execution loop, tool calls, skill loading, and provider-backed generation. Do not create two competing histories or run two independent agent loops for one turn.

Foundry provides inference, not a hosted Foundry Agent Service in this design. A GitHub Copilot account is not the intended authentication path. The SDK's local CLI runtime remains a runtime dependency even when inference uses external provider configuration.

The implementation plan must begin by verifying a mutually compatible Python Agent Framework package, Copilot SDK, and Copilot CLI version against the required provider callback, skills, tools, streaming, and cancellation APIs. Inspect exact signatures rather than copying incompatible snippets.

Preferred bridge: `GitHubCopilotAgent` with SDK-backed provider and skill configuration. If the selected integration version cannot expose required SDK capabilities, a narrow Agent Framework adapter around an explicitly managed Copilot SDK session is an allowed builder decision. This is not permission to discard either framework or silently replace Copilot execution with a direct model call. Stop and report a material incompatibility if neither supported route works.

### Model configuration and credentials

Define one server-side JSON environment variable, `APP_MODELS`, containing an ordered list of model choices. Each entry has:

- Unique stable `id` and human-readable `label`.
- `provider`: `openai` or `anthropic`.
- Foundry `endpoint` and `deployment` name.
- Token `scope`, defaulting to the documented Foundry inference scope `https://ai.azure.com/.default`.
- For OpenAI, the supported wire API: `responses` or `completions`.
- A context budget suitable for the deployment, so the application does not assume a universal context window.

Use deployment names, not hardcoded public model identifiers. No API keys or access tokens belong in this variable. Validate structure, duplicate IDs, HTTPS endpoints, provider-specific endpoint forms, and context budgets at startup. An optional `APP_DEFAULT_MODEL_ID` selects a configured choice; otherwise the first configured entry is the default. Invalid configuration fails readiness with a clear message.

Expose a sanitized model-list endpoint with IDs and labels, not tokens or credentials. Do not silently remove a configured model or switch a user's selected model on failure.

Create backend `DefaultAzureCredential` instances and refreshable token providers for API and worker processes. Supply token acquisition through the Copilot SDK's on-demand bearer-token provider interface. Never freeze a startup access token into long-lived session configuration. Tokens stay in process memory and out of database records, browser responses, job payloads, logs, and generated artifacts.

OpenAI and Claude use provider-appropriate API formats and endpoint paths; do not assume that Claude is OpenAI-compatible. A long task must still work when token refresh is needed. Local Azure credentials and appropriate Foundry inference permissions are prerequisites. Credential and permission failures are visible; no API-key or GitHub-login fallback.

## Routing, streaming, and durable execution

### Classification

Explicit skill invocation always becomes a background task. New PDF ingestion and requests to generate or revise artifacts also take the background path. A question about an already processed PDF or saved presentation can take the short-answer path.

For remaining natural-language requests, use a bounded structured intent-classification call with the selected model to choose question versus complex task. This classifier cannot invoke tools. Classification adds some latency; "immediate streaming" means no task-queue wait for a short answer, not a guarantee of zero routing or model latency. Use a short configurable classifier deadline. On invalid output or failure, return a visible routing error rather than guessing silently.

If an ostensibly short question requires expensive work, explicitly promote the turn to a background task and notify the client. Do not run unbounded work inside a foreground response. Default limits are a two-minute foreground deadline and a thirty-minute background deadline; make those operator-configurable.

### HTTP behavior

Submit a turn through HTTP with attachment IDs, optional skill ID, selected model ID, and a client request ID for idempotency. Persist it once. Return its turn ID and either foreground or queued mode; queued submissions use HTTP 202 and include a task ID and status/event URLs.

The UI opens a per-turn SSE event endpoint after submission. In foreground mode, generation starts on subscription, after rechecking the turn state and owner, so a second subscription cannot start a second run. Stream text deltas and persist the final answer. If the foreground connection is lost, cancel execution and mark an incomplete turn as interrupted; already completed turns remain complete and partial text remains visibly incomplete.

For background mode, persist progress and sequenced events independently of SSE. Reconnecting clients use event IDs to replay missed progress and reload the persisted final result. Also provide a task-status GET endpoint. Browser closure or switching chats does not stop a background job.

Permit only one active turn/task per chat. Return an explicit conflict if another submission arrives while that chat is busy; never silently interleave histories. Other chats can be opened and used while a task runs.

### Task lifecycle

States: `queued`, `running`, `cancel_requested`, `succeeded`, `failed`, `cancelled`, and `interrupted`.

Persist stage progress, timestamps, model ID, selected skill, owner/chat references, and structured errors. Use real stages and indeterminate activity, not invented percentage completion.

Cancellation is idempotent. Queued tasks can be cancelled immediately; running tasks request SDK cancellation and stop between bounded operations. Completion and cancellation use transactional state checks so a cancelled task cannot subsequently publish success.

Queued jobs survive process restarts. Jobs with expired running leases become `interrupted`; do not automatically repeat potentially side-effecting tool calls. Show a user-triggered retry action that creates a new task linked to the original and uses the original model, skill, and inputs. If the model or skill no longer exists, fail retry clearly.

Delete operations remove related records and managed files only within the selected owner's chat. Because filesystem and database updates are not one atomic transaction, use a deletion marker and idempotent cleanup that can resume after interruption. Never recursively delete an unresolved or broad path.

## Persistence and isolation

Persist owners, chats, messages/turns, attachments, tasks, task events, artifacts/versions, and any provider-session mapping. The application's records are the source of truth; SDK sessions are replaceable execution state.

Every object belongs to an owner and a chat where applicable. Query and validate both, including parent-child relationships. Server-side owner filtering applies to history, message reads, attachments, task events/status/cancel/retry, artifact preview, download, and cleanup. Worker claims and context loading retain the same owner scope.

Store files in an application-controlled directory using opaque owner/chat/object IDs, not user-supplied paths or filenames. Original names are display metadata only. Check resolved paths and reject traversal and symlink escapes. Keep SDK working directories/session state scoped as well.

Resolve the local owner server-side. Future authentication will replace that resolver with a verified identity mapping. Test isolation with synthetic separate owners despite the single-user UI. This is application-level separation, not an OS security boundary against other users or trusted developer code on the machine.

Use exact allowed frontend origins and request-origin checks for mutations; do not enable wildcard credentialed CORS. Reject nonlocal hosting configuration in this version. Do not expose an unauthenticated network service by default.

## PDF ingestion and context

Validate file type/signature as well as extension; reject other formats. Proposed upload limit: 25 MiB per file, configurable by the operator. Bound page counts, extraction time, extracted text size, and model context before parsing or sending content.

Use a maintained Python PDF text extractor, chosen by the builder. Extract page-separated text into managed storage and persist ingestion status. Reject malformed, encrypted, and image-only documents with a useful explanation. Flag mixed documents whose pages have no extractable text so users know analysis may be incomplete. Do not silently invent OCR output.

Treat PDF text and generated artifact contents as untrusted data, never as permission to call tools or override system instructions. Tools accept scoped attachment/artifact IDs, not unrestricted filesystem paths.

For each turn, load only that owner's chat history and relevant attachments/artifact versions. Keep the current artifact selection as a concrete ID/version in the request so "this draft" is not inferred from another chat. Include page references and artifact metadata in context.

Bound context to the configured model budget. For large documents, use page-aware chunks and bounded retrieval/summaries, retaining source references. Do not silently truncate decisive content or claim full analysis if limits prevent it. Do not create a global cross-chat index.

## Extension contract

### Skills

Each immediate child of the application's `skills` directory contains `SKILL.md` with a unique name and description in frontmatter, plus optional trusted developer resources. Scan at process startup. Validate names, frontmatter, duplicate IDs, and paths; malformed extensions fail readiness with diagnostics rather than being silently ignored.

API and worker must load the same registry revision. Persist a registry fingerprint in task records; if the worker's revision differs, fail the task explicitly rather than run changed instructions. Adding or editing extensions requires restarting the processes.

Register skills with the SDK's supported skill-loading mechanism and expose only safe metadata to the UI. An explicit selection must activate that skill, not merely make it discoverable. The implementation must verify the provider's exact activation API. Users cannot upload skills through the PDF attachment feature.

### Tools

Developer Python tool modules live in the application's tools folder and export typed tool definitions through one documented export convention chosen by the builder. Validate registrations at startup and register them with the agent. Treat these modules as trusted installed application code, not sandboxed user plugins.

Include scoped tools for reading processed PDFs, reading saved artifacts, and publishing validated HTML artifacts. The tool execution context supplies owner, chat, and task identity; the model cannot override them through arguments. Disable general built-in shell, unrestricted filesystem, and network tools. Use an explicit allowlist and permission handler; do not approve every runtime permission request.

Tools have no user-facing execution routes. App endpoints still upload files, manage tasks, and fetch artifacts; those are not generic arbitrary-tool invocation endpoints.

### Sample RFP skill

Inputs: one or more successfully processed RFP PDFs in the current chat and an optional user instruction.

Stages: read sources, extract requirements, draft response narrative, generate and validate HTML slides, and publish the artifact.

Default draft: approximately six slides covering executive summary, understanding, proposed approach, requirements/evidence gaps, delivery assumptions, and open questions. The builder may adjust slide count to fit content.

Distinguish RFP facts, proposed approach, assumptions, and unknown supplier evidence. Include PDF/page references for extracted requirements. Mark missing company qualifications, pricing, delivery commitments, and compliance evidence as "Needs confirmation." Do not submit responses or contact external parties.

Publish one self-contained HTML/CSS presentation and textual slide content/metadata for follow-up context. The same chat can explain evidence gaps or request a revised version. Source material cannot authorize tools or escape the chat's storage scope.

## Operational behavior and acceptance

Provide clear local startup instructions for frontend, API, worker, environment configuration, Azure sign-in/permissions, and the SDK/CLI runtime. Dependency versions must be mutually tested and recorded; preview installation flags should be documented if the chosen versions require them.

Structured logs include correlation IDs and lifecycle errors, without access tokens, full PDFs, generated confidential content, or hidden reasoning by default. Liveness and readiness distinguish an HTTP process from usable configuration, extension registry, database, and worker heartbeat. Provider preflight checks are explicit and do not silently make model calls during every health request.

The implementation is acceptable when:

1. A configured Foundry OpenAI model and a configured Foundry Claude model can each stream a short answer using refreshable Azure credentials, with no GitHub-login dependency.
2. The model picker reflects environment choices, persists selection, and rejects invalid/unavailable IDs without substitution.
3. Uploading a supported PDF and explicitly invoking the sample skill produces a queued task, observable real stages, and a saved HTML slide artifact.
4. The job continues after the browser closes; reopening the chat restores its status and completed output.
5. Cancellation, provider failures, classifier failures, process interruption, and retry produce explicit consistent states rather than false success or duplicate execution.
6. Follow-up answers can cite the current chat's PDF pages and saved artifact version, including after restart and model change.
7. Synthetic cross-owner requests cannot read, modify, run, download, or subscribe to another owner's objects.
8. Generated HTML cannot execute scripts or reach the parent app/network; unsafe Markdown cannot inject active content.
9. Invalid PDFs and limits yield actionable errors; unsupported OCR is disclosed.
10. Developer-added skills and tools are discovered after restart; invalid definitions or API/worker registry mismatches are reported.
11. Chat history management persists, confirmed deletions are scoped, and future account controls remain nonfunctional and clearly labelled.

Use focused backend tests for ownership, queue state transitions, routing, extension validation, and provider token callbacks; frontend tests for streaming/task rendering, selection, and artifact safety; and an end-to-end PDF-to-artifact-to-follow-up flow. Mock providers for repeatable tests, but verify real configured Foundry access separately before claiming live provider integration works.

## Decisions left to the builder

Exact maintained PDF library, CSS/icon library, typed tool export name, package versions, internal module boundaries, endpoint naming, context-retrieval implementation, and test runners. Choose simple supported options and document them. These choices must preserve this design's observable behavior and security boundaries.

No deployment IDs, endpoints, Azure identity details, or credentials have been provided or verified against a live resource. Use environment-driven configuration and clearly distinguish mocked validation from live integration.

## Design artifacts and references

Mockups are under `.superpowers\brainstorm\1210-1792569104\content`:

- `rfp-workspace.html`: accepted overall visual direction.
- `local-workspace-v2.html`: proposed local mode, future account panel, and background job UI.

Exclude `.superpowers` session state and the local data directory from source control when a repository is initialized.

Primary documentation consulted:

- https://github.com/microsoft/agent-framework/tree/main/python/packages/github_copilot
- https://github.com/github/copilot-sdk/blob/main/docs/auth/byok.md
- https://github.com/github/copilot-sdk/blob/main/docs/features/skills.md
- https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-claude
- https://learn.microsoft.com/azure/foundry/foundry-models/how-to/configure-entra-id

This workspace was not a Git repository when inspected. The user explicitly chose to keep the design uncommitted. Do not initialize a repository or create commits unless separately authorized.
