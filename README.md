# Workroom

A local, single-user business chat app with a Python API, React/TypeScript UI, and a separate durable task worker. Ask short questions with streaming replies, or invoke a skill to process PDF attachments and save HTML presentations alongside the conversation.

The sample skills are `/rfp-response` and `/rfp_analysis`. The first drafts evidence-aware response slides. The second compares an RFP/proposal against a fictional supplier knowledge pack, ranks bid risks and saves a cited HTML risk report. Both distinguish source facts from unsupported claims. Other business skills and agent-only tools can be added by developers.

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

## Run

Use three PowerShell terminals at the project root:

```powershell
# Terminal 1: API
.\.venv\Scripts\python.exe -m uvicorn skill_chat.api.app:create_app --factory --host 127.0.0.1 --port 8000

# Terminal 2: durable background worker
.\.venv\Scripts\python.exe -m skill_chat.tasks.worker

# Terminal 3: frontend
npm --prefix .\web run dev -- --host 127.0.0.1 --port 5173
```

Open **http://127.0.0.1:5173**. Use the exact configured frontend origin, not a different localhost spelling. The Vite development server proxies `/api` and `/health` to port 8000. If that port is occupied, choose a free API port and set `VITE_API_BASE_URL` in `web\.env.local` to the API URL; restart the UI. Keep `APP_FRONTEND_ORIGIN` aligned with the UI's actual origin.

The model selector comes from `APP_MODELS`; changing a chat's model affects future turns only. Attach a PDF, choose `/rfp-response` from Skills or type it in the composer, and send your request. Open the resulting artifact card to preview/download HTML. Follow-ups use the latest saved artifact by default, including after reopening a chat; opening an older artifact selects that exact version instead. The context badge identifies the version being sent; its clear button excludes artifact context until another card is selected or the chat is reopened. Closing the preview does not discard saved content. Revisions create new saved versions.

`/health/live` checks the API process. `/health/ready` also requires a recent worker heartbeat; it returns 503 when the worker is missing. Readiness is not a cloud inference test. Background jobs remain queued if the worker is unavailable.

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

The name must match its folder and contain lowercase letters, numbers, hyphens, or underscores. Restart API and worker after adding/editing skills. Invalid definitions fail startup. Each sample includes three evaluation prompts in its `evals\evals.json`; live model quality requires evaluation with your configured deployments.

### RFP risk-analysis sample

Attach `samples\synthetic-rfp.pdf`, choose `/rfp_analysis`, and ask: "Analyze this RFP against our company references, identify bid risks and publish the risk report." The skill produces a pre-proposal assessment when no proposal exists; it can also review a supplied proposal or selected saved draft. A proposal without its RFP can be assessed for commitment risks, with buyer requirements explicitly unverified. Its final summary accompanies a saved HTML risk register with source citations, supplier fact IDs, mitigations and a human-owned bid/no-bid recommendation.

`skills\rfp_analysis\references` contains the fictional **Cedarbridge Digital Services** profile, product/security knowledge, delivery/commercial baseline and risk-scoring method. Intentional certification, backup-residency, service-level, staffing and budget gaps exercise the analysis. These files are synthetic test data, not your real company information. Replace their contents with reviewed developer-provided knowledge for a real use case and restart both processes; do not mistake the sample for actual due diligence.

The agent reads bundled Markdown references with `read_skill_reference(filename, character_offset, max_characters)`. Only simple Markdown filenames within the explicitly selected skill's `references` folder are allowed; no skill/path override or redirected path is accepted. Responses contain at most 2,000 characters, with continuation offsets. References are shared developer-installed knowledge, not owner-specific uploads. No general filesystem permission is enabled.

### Custom tools

For custom tools, create a Python module in the project-root `tools` folder and export `TOOLS: tuple[ToolRegistration, ...]`. Import `ToolRegistration` and `ToolContext` from `skill_chat.tools.context`. Each registration has a unique name, description, Pydantic arguments model, and asynchronous handler with signature `(arguments: BaseModel, context: ToolContext) -> str`. See the built-in tools in `backend\src\skill_chat\tools`.

`context.scope` and `context.skill_id` are injected by the server. Arguments must not contain owner/chat/skill overrides or unrestricted paths. Installed tool modules are trusted developer code, not sandboxed user plugins. Do not install untrusted modules.

Users cannot invoke tools directly. The agent gets only registered tools, with general shell/filesystem/network capabilities disabled. Built-in tools are `read_document`, `read_artifact`, `read_skill_reference`, and `publish_html`. Readers return at most 2,000 characters per call and accept a `character_offset`; follow `next_offset` and PDF `next_page` metadata to continue reading. Dense pages and large saved drafts remain accessible without exceeding the tool response bound.

## Limits and safety

- PDF only: 25 MiB, 500 pages, 2,000,000 extracted characters, thirty-second extraction timeout by default. These limits are configurable in `.env`.
- No OCR. Scanned-only, encrypted, and malformed PDFs fail clearly; partially scanned PDFs produce missing-page warnings.
- Context is owner/chat scoped, page-aware, budgeted, and explicit about partial coverage.
- HTML uses passive HTML/CSS only. Scripts, event handlers, external resources, frames, forms, and active links are rejected. The preview runs in an opaque sandbox with restrictive CSP. Downloaded files are drafts that still require review.
- Foreground answers default to a two-minute timeout; background jobs to thirty minutes. Intent classification uses the selected model with a five-second deadline and may add latency before streaming.
- The account panel only previews future sign-in/member/account-switching controls. Those actions are disabled.
- **Do not expose this app to a shared network.** Local owner checks prepare the data model for authentication; they do not authenticate users or isolate against other software running under your OS account. The app rejects nonloopback requests and unapproved mutation origins.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest .\backend\tests -m "not live" -q
.\.venv\Scripts\python.exe -m mypy --config-file .\backend\pyproject.toml .\backend\src\skill_chat
.\.venv\Scripts\python.exe -m ruff check .\backend\src
npm --prefix .\web run lint
npm --prefix .\web run test -- --run
npm --prefix .\web run build
npm --prefix .\web run test:e2e
```

Playwright uses separate test-only API and worker processes on ports 18961/18962 with deterministic provider responses, a generated PDF, and a separate `.data\e2e` database. It does **not** demonstrate live model quality or cloud permissions. If Chromium is missing, run `npm --prefix .\web exec playwright install chromium`.

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

For an additional billable RFP-generation check with a synthetic PDF and the default selected model, also set `APP_RUN_LIVE_SKILL_TESTS=1` before that command. It checks saved slides, page references, and evidence-gap labeling, with a maximum three-minute deadline.

Live Claude authentication and basic inference were verified on 2026-10-21 through both the direct Anthropic Foundry SDK and the app's Agent Framework/Copilot gateway after the operator assigned Cognitive Services User to the VM's managed identity. Azure CLI in this environment signs in as that same managed identity. Live OpenAI inference and full RFP-generation quality remain unverified; the successful Claude greeting does not establish either.
