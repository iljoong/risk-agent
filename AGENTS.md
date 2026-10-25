# Repository maintenance guide

## Start here

Workroom is a local, single-user business chat application: a Python/FastAPI API,
a separate durable task worker, and a React/TypeScript frontend. Preserve this
deployment model unless the requested change explicitly replaces it.

Read `README.md` before changing setup, configuration, runtime behavior, or
extensions. It is the operational source for installation, running the three
processes, troubleshooting, and verification. Use Windows PowerShell commands
from the repository root and the root `.venv` for Python.

For architectural rationale, consult
`docs\superpowers\specs\2026-10-21-business-skill-chat-design.md` and the companion
plan in `docs\superpowers\plans`. These are historical design/execution records;
check their claims against current code and tests before relying on them.

## Change boundaries

| Area | Where to work |
| --- | --- |
| HTTP routes, request/response validation, local access guards | `backend\src\skill_chat\api` |
| Routing, foreground streaming, promotion to durable execution | `backend\src\skill_chat\chat` |
| Queue lifecycle, cancellation, recovery, worker execution | `backend\src\skill_chat\tasks` |
| Copilot SDK bridge, provider configuration, Azure credentials | `backend\src\skill_chat\agents` |
| SQLite schema, migrations, scoped records and managed files | `backend\src\skill_chat\storage` |
| PDF extraction and bounded model context | `backend\src\skill_chat\documents` |
| HTML validation, publication and versioning | `backend\src\skill_chat\artifacts` |
| Skill discovery and agent-only tool registration | `backend\src\skill_chat\extensions`, `backend\src\skill_chat\tools` |
| UI and browser API/SSE contracts | `web\src`, especially `web\src\api` |
| Developer-installed skill instructions, references and evaluations | `skills` |

Keep API adapters thin and reuse the existing services and repository. Shared
backend contracts live in `contracts.py`; HTTP schemas live in `api\schemas.py`.
When changing API payloads or events, update the corresponding TypeScript types,
client/decoder, consumers, and focused tests together.

## Invariants to preserve

- **Local access:** keep loopback, trusted-host, and mutation-origin guards.
  The default `local` owner is a scope identifier, not authentication. Account
  controls remain placeholders; multi-user/network deployment needs an explicit
  design rather than relaxed guards.
- **Scoped data:** use server-derived `Scope(owner_id, chat_id)` and repository/
  file-store helpers for records and files. Tools receive scope and selected
  skill through `ToolContext`, never through caller-supplied overrides or paths.
- **Durability:** support one API process, one worker, one globally running task,
  and one active turn per chat. Preserve idempotent submission, persisted events,
  cancellation, deadlines, and explicit retry. Expired running jobs become
  interrupted rather than automatically replaying side effects. API and worker
  must share configuration, data directory, and extension fingerprint.
- **Storage evolution:** change SQLAlchemy metadata and add a corresponding
  Alembic revision under `storage\migrations\versions`; preserve existing
  revisions and migration coverage. Startup applies migrations transactionally.
  Use temporary data in tests and back up real `.data` before upgrades.
- **Agent boundary:** classification and foreground replies are tool-free.
  Background runs receive only registered tools and the explicitly selected
  skill. Preserve SDK permission checks, isolated runtime directories, disabled
  host/config discovery, and refreshable server-side provider credentials.
- **Untrusted inputs:** retain bounded, timed PDF extraction, page/offset
  continuation, and explicit partial-coverage warnings. Generated artifacts must
  pass HTML/CSS validation and stay in an opaque sandbox with restrictive CSP.
  Publish revisions as new versions; expose staged artifacts only after success.
- **Errors and secrets:** use existing `AppError` subclasses and explicit
  task/event failures. Keep credentials server-side and out of logs, browser
  settings, and committed files. Web search queries leave the app; retain the
  public-query guidance without claiming automated DLP protection.

## Extensions and dependencies

Before editing a skill, read its `SKILL.md` and relevant bundled references.
Frontmatter names must match directory names; the discovered identifier is
authoritative. For example, the risk-analysis skill is `rfp-analysis`, not
`rfp_analysis`. Preserve synthetic-data labels and source/evidence distinctions.
Update that skill's evaluation prompts when its expected behavior changes.

Follow `README.md` and `backend\src\skill_chat\tools\context.py` for new tool
registrations. A root `tools` directory is optional and holds trusted developer
code, not user plugins.
Keep reference readers restricted to the selected skill's Markdown references.
Restart both API and worker after extension changes. Bundled scripts/assets do
not grant the runtime shell, filesystem, or JavaScript execution permissions.

Use `backend\requirements.lock` and `web\package-lock.json` for reproducible
installs. Intentional dependency changes must keep their manifests and locks
consistent. SDK upgrades also require reviewing `assert_sdk_compatibility` in
`agents\gateway.py` and running the opt-in local runtime checks documented in
the README; passing mocked tests alone does not establish SDK compatibility.

## Validation and handoff

Run the smallest relevant checks first, adding regression tests for changed
behavior in the existing suites. Use these root-level PowerShell commands as
appropriate:

```powershell
.\.venv\Scripts\python.exe -m pytest .\backend\tests -m "not live and not runtime" -q
.\.venv\Scripts\python.exe -m mypy --config-file .\backend\pyproject.toml .\backend\src\skill_chat
.\.venv\Scripts\python.exe -m ruff check .\backend\src
npm --prefix .\web run lint
npm --prefix .\web run test -- --run
npm --prefix .\web run build
npm --prefix .\web run test:e2e
```

Backend tests use temporary storage and injected gateways. Frontend unit tests
use Vitest/Testing Library; Playwright starts isolated fixture API/worker/UI
processes with test data. Use it for cross-process UI workflows, not as proof of
live inference quality. Consult `README.md` before opting into SDK runtime or
billable Foundry/skill tests; ordinary validation must remain offline.

Update `README.md` when user-facing setup, configuration, commands, or behavior
changes. Keep this guide aligned when maintenance boundaries change, and prefer
pointers over duplicating operational details. Documentation-only edits need no
application test run. Before handoff, inspect the diff for unintended files;
keep local secrets, runtime data, caches, build output, and test artifacts
untracked, and leave unrelated user changes intact.
