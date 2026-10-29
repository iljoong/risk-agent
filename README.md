# RCI Agent

RCI (Risk and Compliance Intelligent) Agent is a local, single-user general agent app with a finance focus, a Python API, React/TypeScript UI, and a separate durable task worker. Ask questions with streaming replies, review PDF evidence, use optional developer-installed skills, and save HTML reports or other draft artifacts alongside the conversation.

**Current scope:** RCI Agent combines a general agent workspace with a persistent, fictional investigation demo. The demo has six workflow stages, editable stage outputs, evidence inspection and human-reviewed draft notes. It is not a live anomaly detector, risk-scoring engine, banking/case-system integration, or regulatory decision system.

The optional `/customer-research` skill builds a cited public-web/news brief about an organization. It is not a customer due-diligence or compliance determination. Ordinary chat does not require a skill.

The current [product specification](docs/superpowers/specs/2026-10-27-rci-agent-design.md) and [transition scope](docs/superpowers/plans/2026-10-27-rci-agent-transition.md) replace the previous domain-specific design and planning documents. Operational commands below remain the source of truth for running the app.

For the proposed Azure production architecture, database and worker migration, and Durable Functions assessment, see [Deployment guidance](deployment/README.md). This is a target design, not an implemented production deployment.

## Prerequisites

- Windows, Python 3.11 or newer (verified with Python 3.12), and Node.js 22.12 or newer.
- GitHub Copilot CLI on PATH. SDK runtime configuration was verified against CLI **1.0.101**, `agent-framework-github-copilot` **2.1.0**, `agent-framework-core` **1.22.0**, and `github-copilot-sdk` **1.0.25rc1**.
- Microsoft Foundry model deployments for the providers you want to use, and an Azure identity with inference permission on those resources.
- Local Azure authentication, for example an Azure CLI session created with `az login`. The backend uses `azure.identity.aio.DefaultAzureCredential`; the browser never receives Azure tokens.

Foundry supplies inference through Copilot SDK's custom-provider configuration. A GitHub Copilot login is not used for model access. Claude uses the Anthropic Messages protocol; OpenAI uses the configured Responses or Chat Completions protocol.

## Setup

Run from the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .\backend
npm --prefix .\web ci
Copy-Item .env.example .env
```

The lock includes the tested preview Copilot SDK. To intentionally resolve fresh package versions instead, use `pip install --pre -e ".\backend[dev]"` and recheck compatibility; do not assume all preview SDK/CLI combinations are compatible.

Edit `.env` and replace the placeholder endpoints/deployment names. `APP_MODELS` is a JSON array. Every choice requires `id`, `label`, `provider`, `endpoint`, `deployment`, and `context_budget_tokens`. Optional `scope` defaults to `https://ai.azure.com/.default`; `wire_api` is `responses` or `completions` for OpenAI.

Model IDs are stable app IDs, not public model names. Use your actual Azure deployment names. Choose a context budget within the deployment's limits. Environment values override `.env`. Invalid or empty model configuration stops startup explicitly.

For Azure access, the identity needs the applicable inference role, such as **Cognitive Services OpenAI User** for Azure OpenAI and **Cognitive Services User** for Claude. Resource configuration and organization policies may require additional permissions. Do not paste access tokens into `.env`; refreshable tokens are acquired on demand for each provider request.

### Selecting the local Azure identity

`DefaultAzureCredential` tries managed identity before Azure CLI. On an Azure VM, a valid managed-identity token can therefore be selected even when that identity lacks permission to call Claude. A successful token acquisition does not establish inference permission.

To use your Azure CLI sign-in for local development, add this to `.env`, sign in using `az login` with an authorized account, and restart both API and worker:

```dotenv
AZURE_TOKEN_CREDENTIALS=AzureCliCredential
```

This retains `DefaultAzureCredential` and its refreshable token handling; it selects the Azure CLI credential instead of the rest of the chain. If Azure CLI itself is signed in as a managed identity, selecting it does not change the principal or grant additional permissions. The selected account still needs **Cognitive Services User**, or equivalent inference data actions, on the Foundry resource for Claude. Remove this setting to restore the normal credential chain.

Use the deployment's Claude base endpoint, `https://YOUR-RESOURCE.services.ai.azure.com/anthropic`, not the Azure OpenAI `.openai.azure.com` hostname. Keep the scope `https://ai.azure.com/.default`. A Claude 401 with `PermissionDenied` can indicate missing inference data actions even when the token is valid; changing the deployment name or refreshing that same token will not resolve missing permissions.

## Centered chat layout prototype

The throwaway prototype on branch `prototype/centered-investigation-layout` compares a central stage workspace with right-hand chat (**A**), vertical workflow outline (**B**) and split output/evidence dock (**C**). Revised A keeps the workflow tracker, editable output, evidence and review tabs in the center, with the investigation assistant in the right sidebar. Run `npm --prefix .\web run prototype`, then open `http://127.0.0.1:5190/?prototype=centered-chat&variant=A`. Use the floating arrows or change `variant` to `B` or `C`. Drag the rail dividers (or focus them and use arrow keys) to resize both sidebars; C also has a resizable output/evidence split.

All amendments and simulated replies stay in memory. An available API supplies read-only session snapshots; otherwise the preview uses packaged fictional CASE-1041 data. No inference or backend mutation is performed. The state viewer exposes the current local state. The comparison preview is development-only. The ordinary app now implements A's central workspace and right-hand assistant with the real persisted investigation actions.

## Run

Use three PowerShell terminals at the project root:

```powershell
# Terminal 1: API
.\.venv\Scripts\python.exe -m uvicorn skill_chat.api.app:create_app --factory --host 127.0.0.1 --port 8000

# Terminal 2: durable background worker
.\.venv\Scripts\python.exe -m skill_chat.tasks.worker

# Terminal 3: frontend
npm --prefix .\web run dev -- --host 0.0.0.0 --port 5173
```

Open **http://127.0.0.1:5173**. Use the exact configured frontend origin, not a different localhost spelling. The Vite development server proxies `/api` and `/health` to port 8000. If that port is occupied, choose a free API port and set `VITE_API_BASE_URL` in `web\.env.local` to the API URL; restart the UI. Keep `APP_FRONTEND_ORIGIN` aligned with the UI's actual origin.

The frontend listens on all IPv4 interfaces for temporary remote testing; restrict port 5173 to your client IP in the Azure NSG and Windows Firewall. To permit your public frontend URL, add `APP_REMOTE_FRONTEND_ORIGIN=http://YOUR-VM-PUBLIC-IP:5173` to `.env` and restart both API and worker. This allows one exact additional origin; other origins and cross-site mutations remain blocked. The frontend proxies API requests with a loopback upstream host; keep port 8000 private and the API bound to loopback. The app still has one shared local workspace, no login and no HTTPS, so use fictional data only. Remove the remote-origin setting and use `--host 127.0.0.1` to return to local-only access.

Request IDs use browser cryptographic randomness even on HTTP origins where `crypto.randomUUID()` is unavailable. If an older tab shows `crypto.randomUUID is not a function`, reload it to load the updated frontend. This compatibility fallback does not encrypt HTTP traffic; use HTTPS and authentication for ongoing remote access.

The model selector comes from `APP_MODELS`; changing a chat's model affects future turns only. Ask a question or attach a text-based PDF and ask, for example: "Summarize the evidence, cite the relevant pages, and list gaps or questions for review." The welcome starters prepare ordinary chat prompts; they do not automatically select a skill. Choose an installed skill from Skills or type its slash command only when you want that extension. Skill selection popups show names only, without descriptions.

Use the sun/moon button in the header to switch between light and dark mode. On first visit, RCI Agent follows your system appearance; an explicit choice is saved in this browser. The theme covers the conversation, investigation desk, scope forms and app dialogs. Saved HTML artifacts retain their own styling inside the sandboxed preview.

Ask for a saved HTML report when needed. Open the resulting artifact card to preview/download HTML. Follow-ups use the latest saved artifact by default, including after reopening a chat; opening an older artifact selects that exact version instead. The context badge identifies the version being sent; its clear button excludes artifact context until another card is selected or the chat is reopened. Closing the preview does not discard saved content. Revisions create new saved versions.

Selected skills stay active for follow-up replies, including clarification answers. Reopening a chat restores its latest turn's available skill when that turn has not saved a report. Publishing a report clears the skill so ordinary artifact questions still use foreground routing. Use the **Clear skill** button on the composer chip to return to regular chat earlier. Skills ask questions as ordinary chat messages and end that turn; answer in the composer while the skill remains selected. No worker is held waiting for a browser callback.

`/health/live` checks the API process. `/health/ready` also requires a recent worker heartbeat; it returns 503 when the worker is missing. Readiness is not a cloud inference test. Background jobs remain queued if the worker is unavailable.

### Investigation evidence desk

Back up `.data` before upgrading an existing installation. Restore both dependency locks using the setup commands, then restart **both API and worker**: the investigation migration, registered tools and extension fingerprint must match. No fourth process is needed.

Start from the **Alerts (fictional demo)** list: selecting an alert creates its one linked case, or resumes it if it already exists. Nothing is prepared automatically; the desk shows the alert and its starting question, and you prepare evidence when ready. Only ALT-2041 has packaged demonstration evidence; other alerts record an explicit source gap. The review-by date is a reminder, not regulatory advice. **New investigation** remains for referrals or manual leads and creates an independent, unlinked CASE-1041 demonstration. **New conversation** retains ordinary chat, PDFs, skills and artifacts. The evidence-first desk implements the [approved investigation design](docs/superpowers/specs/2026-10-28-investigation-evidence-desk-design.md) and the [alert-first start](docs/superpowers/specs/2026-10-29-alert-first-investigation-start-design.md); the selected throwaway prototype remains in Git on `prototype/investigation-workbench`, not as an application entry point. Upgrading applies Alembic revision `0003` (adds `investigations.alert_id`); back up `.data` first.

**Prepare investigation** queues the backend demo connector. It retrieves packaged fictional records asynchronously without cloud inference. This is a mock of live retrieval, not a connection to a financial system. The transaction comparison is GBP 48,000 incoming, GBP 45,500 outgoing, 94.79% over 56 minutes; this does not establish intent or fund lineage. SRC-04 remains restricted and SRC-07 remains missing. Source inspection distinguishes the fixture snapshot/version from the retrieval timestamp.

The six-stage tracker stays above the central working area. **Output**, **Evidence** and **Review** tabs separate stage amendments, source inspection and note review; switching tabs retains unsaved stage and review drafts. The **Investigation assistant** conversation and composer sit in the right sidebar. Drag either sidebar divider, or focus it and use Left/Right arrows, to resize; Home/End select its minimum/maximum width. On narrower screens, history and chat open as drawers; use **Chat** to open the assistant and its close button to return to the workspace. Closing the assistant does not discard its message draft. Ordinary conversations retain their full-width chat view.

Clicking a stage inspects its output; **Make current stage** changes workflow state explicitly. Amend any output with a reason, or edit the shared beneficiary description. Amendments are persisted and enter subsequent agent context; affected reviews and prepared notes are invalidated. Original source records and the original High AML alert are not overwritten. If another tab changes the revision, the local draft is retained for comparison and explicit reapplication.

**Draft a challenge** and **Draft a policy check** populate the existing composer; **Send message** runs the actual configured agent and may be billable. Its scoped output proposals become canonical only after successful execution. Preparation alone is inference-free. Cancelling or closing the browser does not publish an incomplete proposal. Oversized amended context fails explicitly; narrow the output or select a larger configured context budget.

**Clarify investigation scope** opens a restricted official A2UI v0.9 surface. Its validated response queues one new durable turn; no worker waits for the user. Pending/resolved/cancelled status survives reopening. A plain accessible form is available if rendering fails. The pilot permits only fixed text/layout/input/submit components: 64 KiB, 100 components, depth 12, one pending surface, and answers up to 16 KiB plus the selected model's budget. It does not permit arbitrary agent-authored screens.

AG-UI `STATE_SNAPSHOT` frames project authoritative state with bounded recent revision metadata, not accumulating previous output bodies. Complete prior text remains available in paged **Revision history** (`GET /api/chats/{chat_id}/investigation/history`). `ACTIVITY_SNAPSHOT` uses the bridge convention `activityType: "a2ui-surface"` with complete `content.a2ui_operations`, surface revision and status. Passive subscriptions resume scoped delivery cursors; invalid cursors rehydrate the snapshot without restarting work. Conversation text retains the existing turn stream; this is not full AG-UI text/tool lifecycle support.

Review and export require completed evidence preparation, acknowledgment of all affected stage outputs, and an analyst rationale in **Review & record**. Note references and recorded gaps come from the collected evidence pack, never uncollected placeholders. Human proposed disposition can be recorded by amending the Decision output. Preparing or copying a note does not save to another system, close a case, approve a disposition, or execute a financial action; external saving/approval remains **unconfirmed**.

The matched A2UI packages require Zod 3.25.76, which still has an upstream constrained-collection resource-exhaustion advisory (GHSA-mrhx-c7xc-m3w5). Surface structure is checked against the fixed bounded template before renderer/schema processing; this is not a claim that the dependency advisory is resolved. DOMPurify is overridden to patched 3.4.17; the restricted catalog renders plain React text, not Markdown/HTML.

### Persistence and task behavior

SQLite, managed PDFs, artifacts, and isolated runtime directories live in `.data` by default. Set `APP_DATA_DIR` to change that location. API and worker must use the same configuration and data directory. Run one API process and one worker; multi-process API deployment is not supported. Packaged Alembic migrations run transactionally at startup. Back up `.data` before upgrading. Old unreferenced managed files are cleaned on startup within their owner/chat scope, with a sixty-second grace period for in-flight writes.

Only one task runs globally at a time, and only one turn is active per chat. Queued tasks survive restart. Expired running jobs become interrupted after their sixty-second lease expires; they do not silently replay tool calls. Retry explicitly to create a new linked task. Closing the browser does not cancel background jobs, but disconnecting a short foreground stream interrupts that response.

Task cancellation is cooperative between bounded operations. PDFs parse in a separate process with a timeout, so a blocked parser cannot hang the API. API/worker startup and extension registries must match.

## Skills and tools

Put each developer skill in `skills\<skill-name>\SKILL.md`:

```markdown
---
name: example-skill
description: Explain what the skill does and when to use it.
---

Instructions using the available scoped tools.
```

The name must match its folder and contain lowercase letters, numbers, hyphens, or underscores. Restart API and worker after adding/editing skills. Invalid definitions fail startup. Each AML skill and customer-research include three evaluation prompts in their `evals\evals.json`; live model quality requires evaluation with your configured deployments.

### Optional AML investigation skills

Select one skill from **Skills**, or type its slash command in the composer. These are optional instructions for the configured agent, not a new detector, approved bank policy pack, calculation engine, live connector, or automatic six-skill workflow. Ordinary chat and the investigation desk do not require them.

| Skill | Analyst output | Example request |
|---|---|---|
| `/aml-case-context` | Opening case brief and context gaps. | Explain the recorded alert trigger, customer context, and what needs checking. |
| `/aml-transaction-behaviour` | Source-linked transaction assessment. | Assess the prepared transaction indicators against available expectations and history. |
| `/aml-hypothesis-review` | Balanced hypotheses, counterevidence, and distinguishing checks. | Challenge the concern and compare plausible legitimate explanations. |
| `/aml-policy-applicability` | Versioned case-specific requirements and human approval checklist. | Identify which supplied procedures apply and which checks remain incomplete. |
| `/aml-investigation-readiness` | Evidence completeness, blockers, and next permitted checks. | Assess whether the evidence supports a recommendation; keep required gaps blocking readiness. |
| `/aml-case-narrative` | Editable, cited draft for analyst review. | Draft a case note that preserves amendments, counterevidence, and unresolved gaps. |

For the fictional CASE-1041, use **Prepare investigation** before requesting evidence-backed workbench updates. Skills read the saved scope and amendments; requested stage proposals are published only after successful execution and still require human review. They do not acknowledge outputs, alter the original alert priority, or execute a disposition. In ordinary conversations, provide the relevant case/policy material; a PDF is optional.

Supply applicable bank-approved typology definitions and policy versions for real applicability assessments. The demo policies are explicitly fictional and do not supply a complete real approval path. Missing authority stays unknown. Transaction assessments use the server's verified preparation metrics or identified approved calculation outputs; missing or mismatched calculations are reported, not performed by language-model arithmetic. Missing required evidence cannot produce a ready result.

After adding these skills, restart **both API and worker** to load the matching extension fingerprint. The 18 AML evaluation prompts cover normal assessments, missing inputs, unsupported claims, and instruction/approval boundaries. Structural validation is not a live-model evaluation or evidence of AML-domain accuracy.

The agent reads bundled Markdown references with `read_skill_reference(filename, character_offset, max_characters)`. Only simple Markdown filenames within the explicitly selected skill's `references` folder are allowed; no skill/path override or redirected path is accepted. Responses contain at most 2,000 characters, with continuation offsets. References are shared developer-installed knowledge, not owner-specific uploads. No general filesystem permission is enabled.

### Custom tools

For custom tools, create a Python module in the project-root `tools` folder and export `TOOLS: tuple[ToolRegistration, ...]`. Import `ToolRegistration` and `ToolContext` from `skill_chat.tools.context`. Each registration has a unique name, description, Pydantic arguments model, and asynchronous handler with signature `(arguments: BaseModel, context: ToolContext) -> str`. See the built-in tools in `backend\src\skill_chat\tools`.

`context.scope` and `context.skill_id` are injected by the server. Arguments must not contain owner/chat/skill overrides or unrestricted paths. Installed tool modules are trusted developer code, not sandboxed user plugins. Do not install untrusted modules.

Users cannot invoke tools directly. The agent gets only registered tools, with general shell/filesystem/network capabilities disabled. Built-in tools are `read_document`, `read_artifact`, `read_skill_reference`, `publish_html`, and `webiq_search`. Readers return at most 2,000 characters per call and accept a `character_offset`; follow `next_offset` and PDF `next_page` metadata to continue reading. Dense pages and large saved drafts remain accessible without exceeding the tool response bound.

Investigation runs also receive `read_investigation` and `propose_investigation_output`. They use server-owned session scope and current task/revision checks; they cannot change the original alert, human review status or external systems.

`publish_html` returns a chat-scoped `download_url` for the final answer; it becomes downloadable when the task succeeds. Reports use static, validated HTML/CSS. Bundled extension scripts and assets do not grant the runtime permission to run Python, JavaScript, shell commands, or arbitrary filesystem access.

### Web IQ search and customer research

Set `WEBIQ_API_KEY` in the project-root `.env` (or process environment) using a key from your Microsoft Web IQ profile, then restart **both API and worker**. Web IQ currently requires approved access; model-provider Azure authentication does not configure this search key. The app still starts without it, but searches fail with an explicit configuration message. The key stays on the server and is excluded from settings serialization; do not use a frontend `VITE_` variable.

The shared `webiq_search(query, kind="web", max_results=5, language="en", region="US")` tool is registered for ordinary background chat and **every selected skill**, including new developer skills without additional per-skill wiring. Use `kind="news"` for news, and `language="ko", region="KR"` for Korean research. Queries are 1-1,000 characters; this app caps results at 10 per call to bound model context. Foreground chat and classification remain tool-free; search requests route or promote to background execution.

The tool uses documented `POST https://api.microsoft.ai/v3/search/web` and `/news` endpoints with `x-apikey`, explicit `contentFormat="passage"`, and `maxLength=1500`; web search uses strict SafeSearch. It does not fetch arbitrary URLs. Each response includes source titles/URLs, passages, publisher when available, update/crawl dates and a retrieval timestamp. Output is bounded to 20,000 characters with explicit truncation/omission indicators; the upstream response limit is 1 MiB and each call has a thirty-second deadline. Empty results remain empty; authentication, rate-limit, transport and malformed-response failures are surfaced, not treated as successful empty searches. There is no hard freshness/date-filter parameter in these documented endpoints; dates in queries are hints, and update/crawl dates must not be presented as publication dates.

Choose `/customer-research` and ask, for example: **"Research Microsoft. Summarize its public business strategy and recent news, cite sources, and identify questions for further review."** No PDF is required. The skill uses web and news, prioritizes official sources, cites its findings, labels hypotheses and evidence gaps, and asks for clarification when the organization is ambiguous. It returns a chat brief by default; ask for a saved HTML report if needed. Public research is supplementary context, not verification of a private event, anomaly, or compliance finding.

Queries leave the app for Microsoft Web IQ. Agent and skill instructions prohibit sending confidential documents, private financial evidence, secrets or personal data; use public organization identifiers and generic topics only. This is instruction-based guidance, **not an automated DLP guarantee**. Search content is untrusted, partial evidence and cannot establish compliance or substantiate an allegation. Saved HTML retains URLs as plain text because active external links remain prohibited.

API references: [Quick start](https://webiq.microsoft.ai/documentation/quick-start/), [Web search](https://webiq.microsoft.ai/documentation/api-reference/web/), [News search](https://webiq.microsoft.ai/documentation/api-reference/news/). The new skill's three evaluation prompts cover cited research, ambiguous customers and confidential-query/fabrication requests. Live search and model-quality evaluation require your configured key and deployment.

## Limits and safety

- PDF only: 25 MiB, 500 pages, 2,000,000 extracted characters, thirty-second extraction timeout by default. These limits are configurable in `.env`.
- No OCR. Scanned-only, encrypted, and malformed PDFs fail clearly; partially scanned PDFs produce missing-page warnings.
- Context is owner/chat scoped, page-aware, budgeted, and explicit about partial coverage.
- HTML uses passive HTML/CSS only. Scripts, event handlers, external resources, frames, forms, and active links are rejected. The preview runs in an opaque sandbox with restrictive CSP. Downloaded files are drafts that still require review.
- Foreground answers default to a two-minute timeout; background jobs to thirty minutes. Intent classification uses the selected model with a five-second deadline and may add latency before streaming. A classification timeout is logged and shown as a progress notice, then conservatively queues background execution instead of failing the request. Explicit skills bypass classification. Foreground promotion instructions are not included in background runs.
- The account panel only previews future sign-in/member/account-switching controls. Those actions are disabled.
- Outputs are drafts for human review, not verified financial findings or regulatory advice. Dedicated case audit trails, approved risk policies, decision controls, and domain validation have not been implemented.
- **Do not expose this app to a shared network.** Local owner checks prepare the data model for authentication; they do not authenticate users or isolate against other software running under your OS account. The app rejects nonloopback requests and unapproved mutation origins.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest .\backend\tests -m "not live and not runtime" -q
.\.venv\Scripts\python.exe -m mypy --config-file .\backend\pyproject.toml .\backend\src\skill_chat
.\.venv\Scripts\python.exe -m ruff check .\backend\src
npm --prefix .\web run lint
npm --prefix .\web run test -- --run
npm --prefix .\web run build
npm --prefix .\web run test:e2e
```

Playwright uses separate test-only API and worker processes on ports 18961/18962 with deterministic provider responses, a generated synthetic PDF, and a separate `.data\e2e\rci-agent` database. This keeps older test databases untouched. It does **not** demonstrate live model quality or cloud permissions. If Chromium is missing, run `npm --prefix .\web exec playwright install chromium`.

To exercise actual Agent Framework and Copilot CLI processes against a local model HTTP fixture (no Azure credentials or cloud calls):

```powershell
$env:APP_RUN_RUNTIME_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_runtime.py -m runtime -q
Remove-Item Env:APP_RUN_RUNTIME_TESTS
```

This checks native streaming through OpenAI Responses, Chat Completions, and Anthropic Messages, explicit skill preloading before inference, repeated bearer callback acquisition, and the scoped tool-to-artifact execution loop. It is separate from live Foundry verification.

To explicitly run real provider checks after configuring `.env` and your Azure identity:

```powershell
$env:APP_RUN_LIVE_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest .\backend\tests\test_live_foundry.py -m live -q
Remove-Item Env:APP_RUN_LIVE_TESTS
```

This makes billable model requests and requires at least one configured OpenAI and Claude deployment. Normal tests neither acquire real Azure tokens nor contact model endpoints.

Keep `APP_RUN_LIVE_SKILL_TESTS` unset: the legacy opt-in skill-generation test targets an extension no longer bundled with RCI. Historical test fixtures and internal `skill_chat` package identifiers are not product features and do not define the current scope.

Successful provider authentication or a greeting does not establish finance-domain accuracy, anomaly-triage quality, or regulatory suitability. Those require a defined workflow and separately reviewed evaluation data.
