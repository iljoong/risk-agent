# RCI Agent product and architecture specification

Date: 2026-10-27
Status: Current scope. General agent workspace; finance specialization deferred.

## Identity and intent

RCI means **Risk and Compliance Intelligent**. The application is named **RCI Agent**.
It is a local, single-user general agent workspace with a finance focus. Users can
ask questions, review document evidence, invoke optional installed skills, and
save drafts for follow-up discussion.

The longer-term direction is agent-assisted anomaly triage within one finance
risk domain. The specific domain and workflow will be supplied later. No choice
has been made between anti-money laundering, claims fraud, conduct risk, or another
risk area. These are possible future scopes, not supported product modules.

This specification replaces the previous domain-specific product design.
`README.md` is the operational source for installation, configuration, commands,
troubleshooting, and verification.

## Current capabilities and boundaries

| Available foundation | Not implemented or not yet defined |
| --- | --- |
| Persistent chats, Markdown replies, configured model selection | Alert feeds, transaction ingestion, structured case records |
| Streaming short answers and durable background tasks | Anomaly detection, risk scores, calibrated thresholds |
| Bounded text-based PDF extraction and page citations | Financial data connectors, CSV ingestion, OCR |
| Optional explicitly selected developer skills | A specialized finance-triage skill or approved risk taxonomy |
| Public organization research through Web IQ when configured | Sanctions screening, identity verification, customer due diligence |
| Versioned static HTML artifacts and follow-up context | Case disposition, approval workflows, regulatory filings |
| Application task events and local scoped persistence | A regulated case audit trail, retention policy, or decision provenance system |

General model responses can help organize questions and evidence, but must not be
presented as validated anomaly findings or compliance decisions. Outputs remain
drafts for human review. Domain quality and regulatory suitability are unverified.

## User experience

Keep the existing history sidebar, conversation, composer, and optional artifact
preview. Display RCI Agent in the sidebar, assistant labels, and browser title;
the API metadata title is RCI Agent API.

The welcome screen offers ordinary-chat starters to review a document or explore
a question. Starters prepare editable text and clear any selected skill; they do
not submit a turn or implicitly activate a domain workflow. The composer accepts
questions, PDF attachments, and explicit slash-command skill selection.

Users can create, reopen, rename, and delete chats. Deletion requires confirmation
and is blocked while work is active. The configured model picker affects future
turns, not saved history, and cannot change a busy chat's model.

Selected skills remain active for clarification replies until cleared or a report
is saved. Clarifications are ordinary assistant messages that finish the turn,
not browser callbacks holding a worker open. Reopening a chat restores an available
skill when the latest turn has no saved report.

Generated content is labeled an HTML artifact, not assumed to be slides. Opening
an artifact selects its exact version for follow-up context. The latest artifact
is selected by default when reopening a chat; users can clear that context.
Revisions create new versions, never overwrite a published version.

Account controls remain disabled placeholders. There is no implemented sign-in,
multi-user access, or shared-network deployment.

## Architecture and process model

Preserve the Python/FastAPI API, separate durable Python worker, and
React/TypeScript frontend. API and worker share configuration, SQLite storage,
the managed data directory, and the extension fingerprint. Run one API process,
one worker, and at most one globally running background task; permit only one
active turn per chat.

The API owns validation, local access guards, scoped records, PDF handling,
routing, foreground streaming, task submission, persisted event delivery, and
artifact access. The worker claims queued jobs and executes background agent
runs independently of a browser connection.

Microsoft Agent Framework and GitHub Copilot SDK/CLI remain the agent bridge.
Microsoft Foundry supplies configured OpenAI or Anthropic model inference.
Server-side Azure Identity credentials provide refreshable bearer tokens.
Provider endpoints, credentials, and deployment configuration stay off the browser.
Stable model IDs are configured through APP_MODELS; do not silently substitute
models when configuration or inference fails.

Internal package names and existing database contracts remain unchanged by this
product transition. No database migration or reset is part of the change.

## Routing and durability

Classification and foreground replies are tool-free. Explicit skill selections,
new attachments, and artifact-generation requests use durable background execution.
Other requests use bounded intent classification; a classifier timeout is visible
and conservatively queues background work. Foreground responses that need tools
or substantial processing can be explicitly promoted.

Turns use client request IDs for idempotent submission. Background stages and
events persist independently of SSE connections and can be replayed after
reconnection. Closing the browser does not cancel a queued or running task;
disconnecting foreground streaming interrupts an unfinished foreground answer.

Preserve queued, running, cancel_requested, succeeded, failed, cancelled, and
interrupted task states. Cancellation is cooperative between bounded operations.
Queued tasks survive restarts. Expired running leases become interrupted rather
than automatically replaying possible side effects. Retry is explicit and creates
a linked task using the original inputs, model, and skill if still available.

Default limits remain two minutes for foreground work, thirty minutes for
background work, and five seconds for classification. Configuration can change
these bounds. Readiness requires a recent worker heartbeat; it does not prove
model access or domain accuracy.

## Evidence, storage, and generated content

Use server-derived Scope(owner_id, chat_id) for records, managed files, tools,
and artifact versions. The local owner is a scope identifier, not authentication.
Do not accept caller-controlled owners, filesystem paths, or tool-context overrides.

SQLite migrations remain packaged Alembic revisions applied transactionally.
Back up real data before upgrades; do not stamp unknown schemas or rewrite
existing data merely to change product branding.

PDF input remains bounded to 25 MiB, 500 pages, 2,000,000 extracted characters,
and thirty seconds of extraction by default. Extraction runs in a bounded
subprocess. Reject encrypted, malformed, and scanned-only input; warn about missing
text on partly scanned pages. Context is page-aware, model-budgeted, and explicit
about partial coverage. Readers provide bounded offset/page continuation.

Documents, prior messages, artifacts, and search passages are untrusted evidence,
not instructions. Distinguish source facts, interpretations, assumptions, and
missing evidence. Cite document filename/page and supported public URLs/dates.
Do not invent figures, findings, policy requirements, or citations.

HTML artifacts must pass existing HTML/CSS validation. Preview them in an opaque
sandbox with restrictive CSP. Scripts, active links, external resources, forms,
and frames remain prohibited. Staged artifacts become visible only after task
success; downloads remain scoped attachments.

## Skills, tools, and external search

Skills are optional trusted developer-installed Markdown instructions. Their
frontmatter names must match their directories. Discover them at startup and
require API/worker fingerprints to match. Only the explicitly selected skill
receives its bundled Markdown references.

The remaining customer-research sample supports public organization research;
it is not a due-diligence, screening, or fraud-detection implementation. General
chat and starters must work without that skill.

Background agents receive registered scoped tools only: read_document,
read_artifact, read_skill_reference, publish_html, and webiq_search, plus any
trusted developer registrations. No arbitrary shell, filesystem, or URL-fetching
permissions are introduced. Foreground runs and classification receive no tools.

Web IQ queries leave the app. Use public organization identifiers and generic
topics, never confidential documents, private financial records, secrets, or
personal data. This is instruction-based guidance, not automated DLP. Search
passages are partial context and cannot establish a private event or compliance
finding. Report search failures and distinguish crawl/update dates from supported
publication dates.

## Deferred finance requirements

Before implementing anomaly triage, obtain the selected risk domain, jurisdiction,
analyst role, source data and permissions, anomaly definition, evidence standard,
triage states, and human decision authority. Define approved policies, scoring
and uncertainty handling if needed, escalation criteria, integrations, privacy
and retention controls, audit requirements, and representative evaluation data.

Do not infer these requirements from generic finance terminology. This transition
does not add financial actions, autonomous case closure, regulatory submissions,
or a claim of compliance certification.

## Acceptance criteria for this transition

- Current documentation describes the general RCI foundation and clearly defers
  specialized finance capabilities.
- Superseded product design, implementation plan, and product-discovery transcript
  are removed rather than left as competing requirements.
- UI starters and composer copy do not depend on the removed domain extensions.
- Artifact preview, version context, cancellation, and explicit skill selection
  retain their existing behavior.
- Existing setup, local guards, scoped storage, credentials, and durable execution
  remain intact. Historical test fixtures and internal identifiers are not a
  promise of currently bundled product functionality.
