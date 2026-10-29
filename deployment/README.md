# RCI Agent: Azure production deployment

Status: proposed target architecture, not an implemented deployment.
Date: 2026-10-29.
Audience: application engineers, platform engineers and deployment operators.

## 1. Recommendation and scope

Use Azure Container Apps for the web/API and agent worker, Azure Database for
PostgreSQL Flexible Server for relational state, Blob Storage for documents and
artifacts, and Service Bus for durable work delivery.

Keep the agent execution runtime in a container. Introduce Durable Functions
only when long-lived workflow coordination, human waits, deadlines or parallel
steps justify a separate orchestration layer.

This document describes a production destination and migration gates. It does
not provision resources, supply executable infrastructure templates, or make
the current application production-ready. Refer to the [root README](../README.md)
for supported local installation and runtime commands.

The application remains a general agent with a finance focus and a fictional
investigation demo. Hosting it in production does not establish a live detector,
banking integration, regulatory workflow or compliance certification.

### Current implementation versus target

| Area | Current implementation | Production target |
| --- | --- | --- |
| Access | Loopback API; explicit extra frontend origin for temporary remote testing | Authenticated HTTPS ingress with deliberate proxy trust |
| Ownership | Shared `local` owner; account controls are placeholders | Server-derived user/workspace scopes and explicit authorization |
| Database | SQLite with WAL and `BEGIN IMMEDIATE` | PostgreSQL with migrated transactions, constraints and task locking |
| Files | Scoped local files under `.data` | Private Blob Storage plus bounded temporary execution files |
| Execution | One API process, one worker, one globally running task | Initially preserve limits; distributed coordination before scaling |
| Queue | Persisted database task records and polling | Transactional outbox plus Service Bus delivery |
| Runtime | Windows development environment with Copilot CLI/SDK | Validated, pinned Linux container runtime |
| Streaming | Application SSE and persisted events | Authenticated SSE with reconnect, replay and proxy validation |

Neither changing the database URL nor increasing replica counts is sufficient
to implement the target.

## 2. Target topology

```text
Browser
  |
  | HTTPS; Microsoft Entra ID authentication
  v
Azure Front Door Premium + WAF
  |
  | Private/restricted origin; prevent direct-origin bypass
  v
Azure Container Apps: web/API
  |-- Production-built React frontend and FastAPI
  |-- Authenticated API, file access and SSE
  |-- PostgreSQL: business state, events, tasks, outbox
  |
  v
Outbox publisher --> Azure Service Bus --> Container Apps: agent worker
                                              |-- Copilot SDK/CLI
                                              |-- Approved tools and skills
                                              |-- Foundry inference
                                              |-- PostgreSQL progress/publication
                                              `-- Blob Storage files/artifacts

Shared platform:
VNet/private connectivity, managed identities, Key Vault, Container Registry,
Azure Monitor/Application Insights, backups, CI/CD and infrastructure as code
```

The outbox publisher is a logical responsibility. It can initially run with a
controlled worker process; it does not require another public service.

For an internal employee-only installation, private corporate connectivity can
replace a public Front Door entry point. Choose and validate the specific
Front Door-to-Container Apps private-origin integration for the selected region,
environment and SKU before deploying. Public origin restriction is not equivalent
to a private endpoint.

### Azure resources

| Component | Recommended service | Deployment responsibility |
| --- | --- | --- |
| Edge | Front Door Premium and WAF | TLS, routing, request filtering and origin restriction |
| User identity | Microsoft Entra ID | Approved users/groups, app roles and authentication policy |
| Web/API | Container Apps | Built UI, API adapters, authorization and streaming |
| Agent worker | Separate Container App without public ingress | Task execution, cancellation, tools and staged output |
| Database | PostgreSQL Flexible Server | Scoped records, revisions, tasks, event cursors and audit history |
| Files | Blob Storage | Private documents, extraction outputs and versioned artifacts |
| Work delivery | Service Bus | Task-ID messages, redelivery and dead-letter handling |
| Models | Microsoft Foundry | Approved deployments, inference permission and quotas |
| Images | Azure Container Registry | Immutable image digests, scanning and controlled access |
| Secrets | Key Vault | External service secrets and rotation |
| Telemetry | Azure Monitor and Application Insights | Correlation, operational dashboards and alerts |

Separate development, staging and production resources, identities and data.
Do not share production task queues, orchestration histories or model credentials
with test environments.

## 3. Web, identity and API boundary

Serve a production build of React, not Vite's development or preview server.
Keep UI and API under one external origin where practical. The web/API deployment
may include a reverse-proxy container to serve static files and route API traffic.

Authenticate both UI and API with Entra ID. Either use platform authentication
with a verified trusted-header boundary or validate tokens in the application.
Do not accept identity headers from arbitrary clients. Restrict allowed tenants
and users explicitly; authentication alone is not workspace authorization.

Replace the shared `local` owner with authenticated, server-derived user and
workspace identifiers. Define workspace membership and viewer/editor/admin roles
before enabling collaboration. Enforce scope on every record, event stream,
revision, tool execution, upload and download.

The current loopback, trusted-host and origin checks must be replaced through a
reviewed production access design, not removed:

- Trust forwarded headers only from the actual ingress path.
- Allow the exact external HTTPS host/origin and retain CSRF protection for
  cookie-authenticated mutations.
- Prevent bypass of edge authentication or WAF through a direct origin URL.
- Keep CORS restrictive; do not allow wildcard credentialed access.
- Keep model credentials and service credentials out of browser configuration.
- Authenticate SSE and verify authorization again on reconnect.
- Keep the artifact preview opaque and sandboxed with restrictive CSP.

`APP_REMOTE_FRONTEND_ORIGIN` is a temporary testing feature, not the production
authentication, authorization or ingress configuration.

## 4. Database and file migration

### PostgreSQL

Use PostgreSQL as the authoritative source for business and task state:
chats, turns, investigations, amendments, revision checks, file metadata,
task attempts, event cursors, authorization records and audit history.

Retain SQLAlchemy and Alembic where appropriate, but adapt SQLite-specific
behavior, including `PRAGMA` settings, `BEGIN IMMEDIATE`, task claiming, indexes,
uniqueness rules, JSON behavior and migration assumptions.

Use database transactions and row-level locking or equivalent conditional
updates to enforce one active turn per chat. Implement task ownership with
renewable leases and fencing tokens. Use unique constraints for scoped client
request IDs so concurrent submissions cannot create duplicate operations.

Configure bounded connection pools for API, workers and migration jobs. Set
statement and transaction timeouts; do not keep database transactions open
during model inference or network tool calls.

Use private connectivity, TLS and least-privilege database identities. Separate
schema migration permissions from normal application permissions. Configure HA,
backup retention and recovery testing against agreed availability, RPO and RTO
requirements; select sizing from measured load rather than demo traffic alone.

### Blob Storage

Keep original PDFs, extraction products and generated artifact versions in
private containers. Store scoped identifiers, metadata and checksums in
PostgreSQL; derive blob names on the server, not from caller-provided paths.

Use API-mediated downloads or narrowly scoped, short-lived access URLs after
authorization. Keep uploaded documents untrusted and retain extraction limits,
timeouts and partial-coverage warnings. Do not serve generated HTML as trusted
application-origin content.

Blob writes and database commits are not a single transaction. Stage outputs
under execution-specific keys, then publish their metadata only after the
successful task transaction. Make reconciliation and orphan cleanup scope-aware
and safe for in-flight writes.

Local container disk is temporary scratch space only. Give each run an isolated
runtime directory and clean it up with bounded retention. Preserve SDK permission
restrictions, disabled host/config discovery and selected-skill-only references.

Do not place the current SQLite WAL database on Azure Files as a shortcut:
[SQLite WAL does not work over network filesystems](https://www.sqlite.org/wal.html).

## 5. Worker and Service Bus design

Keep the agent worker separate from HTTP request handling. Package Python,
Copilot CLI, the pinned SDK dependencies, approved skills and tool registrations
in a tested image. Build the React frontend separately; build tools need not
remain in the production runtime image.

Linux container compatibility must be established through real SDK/CLI smoke
checks in staging. Existing mocked tests and a Windows development run are not
proof that subprocess startup, permissions, credentials, PDF extraction and
cancellation work in the target image.

### Submission and completion protocol

1. In one PostgreSQL transaction, validate scope/revision, create the turn/task
   and insert an outbox record.
2. The outbox publisher sends a task-ID message to Service Bus. Publication
   retries can produce duplicates.
3. The worker atomically claims eligible database state and receives a lease,
   attempt identity and fencing token. Duplicate deliveries must not start
   another active execution.
4. The worker renews ownership, honors cancellation/deadlines, and persists
   bounded progress/events. Configure Service Bus lock renewal for the expected
   task duration, or adopt an explicit database-owned dispatch/acknowledgment
   protocol; a message lock alone is not execution ownership.
5. On success, publish staged outputs and terminal state transactionally, guarded
   by the current execution token and investigation revision.
6. Acknowledge the delivery after durable handling. A recovery/reconciliation
   process handles crashes between these boundaries.

Service Bus is a delivery mechanism, not the source of truth for task state.
Duplicate detection does not provide exactly-once execution. Dead-letter
malformed or repeatedly unprocessable messages and alert operators; redrive
requires checking authoritative task state.

### Failure, retry and cancellation

- Keep one active turn per chat and the existing global task limit until an
  explicit concurrency redesign is implemented.
- Redelivery of an already completed task is a no-op, not another agent run.
- A lease that expires during uncertain tool execution becomes interrupted or
  requires reconciliation. Do not automatically replay possible side effects.
- Distinguish safe dispatch retries from retries of model calls and tools.
  Even a read-only repeated model call can incur duplicate inference charges.
- Retry interrupted/failed work explicitly as a linked attempt with stable
  operation identifiers and tool-level idempotency where supported.
- Cancellation is cooperative. Stop between bounded operations, cancel the
  agent session when possible, and reject late output using task state/fencing.
- An expired or replaced worker must not be able to publish after ownership
  has moved. Fencing checks must apply to authoritative writes.

Run the polling worker with at least one replica initially. Do not expect HTTP
traffic scaling to wake a worker for database-only queued work. Queue-driven
scaling can be introduced after idempotency, leases, drain behavior and
cross-chat concurrency are proven.

## 6. Durable Functions assessment

Durable Functions is an alternative workflow coordinator, not a requirement for
durable task execution. The current visible investigation stages are persisted,
human-controlled application state; they are not automatically a six-step
orchestration.

### When to introduce it

Consider Durable Functions for explicit multi-step workflows with durable waits,
deadlines, parallel evidence collection or external completion signals.
Do not hold an agent process or activity open while waiting for a human.

```text
API
  |
  v
Durable orchestrator
  |-- Schedule bounded activities
  |-- Dispatch agent task to container worker
  |-- Wait for correlated completion/cancellation/deadline
  `-- Coordinate authorized human responses when the product requires them
```

Use an idempotent scheduling activity/outbox boundary for dispatch and a
retryable, correlated completion notification. Define how missed notifications
are reconciled against database state. The browser continues to use the API;
do not expose privileged Durable management endpoints or keys directly.

### Responsibilities and constraints

| Concern | Required treatment |
| --- | --- |
| Ownership | Durable owns workflow scheduling; worker owns agent execution; PostgreSQL owns business records |
| Determinism | Orchestrator code must replay deterministically; put model calls, database access and tools outside it |
| Activity delivery | Activities are at-least-once; make outputs and side effects idempotent |
| Cancellation | Terminating an orchestration does not forcibly kill a running activity; retain cooperative cancellation |
| Timeouts | Durable waits can be long-lived; individual activities still face hosting timeouts and process restarts |
| Persistence | Inputs, outputs and history are persisted; pass small IDs/status values instead of full evidence or secrets |
| Streaming | Keep progress/token events and authenticated SSE in the application |
| Updates | Version workflows and activities so deployments do not break in-flight replay |
| Retention | Purge workflow history under an explicit retention/deletion policy |

Do not keep both an independent database scheduler and a Durable scheduler
deciding the same task's next step. Task records can remain an execution ledger,
but ownership of scheduling and reconciliation must be unambiguous.

Configure a supported Durable backend separately from the application's
PostgreSQL database. Durable execution history is not the business audit ledger
or a replacement for the application's transactional records.

### Running the agent inside a Function activity

This is possible to evaluate, but is not the default recommendation. Prefer
Functions Premium with a custom Linux container if full control of SDK/CLI and
system dependencies is needed. Verify plan-specific activity timeouts, memory,
subprocess behavior, networking, writable directories and shutdown behavior.

Flex Consumption does not support custom container images; do not assume the
same image can be deployed there. Functions supports other container hosting
options, which should be assessed against supported Durable backend/runtime
combinations before selection.

A single large activity is not a checkpoint of the agent's internal execution.
After a crash it can run again; persisting the workflow around it does not make
each tool call exactly-once or make cancellation instantaneous.

## 7. Scaling, availability and streaming

The current API maintains process-local foreground execution and cancellation
state. Keep one API replica until distributed turn ownership, cancellation and
event delivery have been implemented. This initial configuration has an
availability limitation and must not be presented as an HA deployment.

For the resilient target:

- Move active execution coordination out of API-process memory.
- Enforce concurrency and authorization in the database, not session affinity.
- Treat rollout overlap as concurrency: replica limits alone do not guarantee
  that old and new processes never run simultaneously.
- Drain workers on deployment; stop claiming new work and finish or explicitly
  interrupt existing execution before shutdown.
- Persist bounded event batches with stable cursors, and reconnect/replay SSE
  after network or proxy disconnects.
- Validate streaming, buffering, idle timeouts and maximum request duration
  through the complete edge/ingress path. Heartbeats do not necessarily remove
  absolute request-duration limits.
- Keep durable task execution independent of browser connection lifetime.

Avoid active-active regional execution until task fencing, data ownership,
file replication and recovery behavior are explicitly designed.

## 8. Security, operations and recovery

Use managed identities for supported service access and grant only necessary
Foundry inference, queue, storage and registry permissions. Keep remaining
external-service secrets in Key Vault. Production must not depend on a
developer's `az login` session.

Validate private DNS and egress for PostgreSQL, storage, messaging, Foundry and
approved external tools. Public web-search queries leave the application; retain
the public-query guidance without describing it as automated DLP.

Record request, task, attempt, model/runtime version and workflow identifiers
for correlation. Do not log full prompts, documents, credentials or sensitive
tool outputs by default. Keep business audit history separate from operational
logs and apply authorization and retention to both.

Alert on queue age, dead-letter count, expired leases, missing workers, task
failure rate, inference throttling, latency, storage/database capacity and
unexpected model cost. Apply user/workspace quotas and model concurrency budgets.

Define backup and restore procedures for PostgreSQL and Blob Storage, including
versioning/soft-delete settings appropriate to the data policy. Coordinate record
and file recovery; database point-in-time recovery alone does not restore a
matching file set. Reconcile queues and task ownership before resuming execution.

Set recovery objectives, region/data-residency requirements and operational
ownership before sizing resources or committing to an availability target.

## 9. Delivery and migration sequence

| Phase | Deliverable | Exit gate |
| --- | --- | --- |
| 1. Design | Access model, task semantics, region, retention and recovery objectives | Reviewed decisions; no implied multi-user support |
| 2. Container runtime | Pinned images and production UI serving | SDK/CLI runtime and cancellation smoke checks pass |
| 3. Persistence | PostgreSQL and Blob adapters with migrations/import tooling | Scoped behavior, revisions, file integrity and restore tested |
| 4. Identity | Entra authentication and workspace authorization | Cross-user API, SSE, tool and file isolation demonstrated |
| 5. Execution | Outbox, queue consumer, leases and fencing | Duplicates, crashes, cancellation and uncertain outcomes handled |
| 6. Staging | Private services, HTTPS ingress, monitoring and CI/CD | End-to-end and failure-injection acceptance checks pass |
| 7. Cutover | Backed-up data, controlled migration and worker drain | Reconciliation complete; operator approves traffic switch |
| 8. Scale | Distributed API/worker coordination | No cross-chat overlap violations or stale publications |
| 9. Optional orchestration | Durable workflow layer | Business need and scheduling ownership explicitly approved |

Use infrastructure as code and separate reviewed environment parameters.
Provision resources before deploying applications. Run schema migrations once
as a controlled job with a privileged migration identity, rather than having
every replica race to apply them at startup.

For initial cutover, pause writes and task claims, drain or explicitly interrupt
active runs, back up `.data`, import records and scoped files, and reconcile
counts, relationships and checksums before directing users to the new endpoint.
Never silently restart previously running tasks during migration.

Use expand/contract migrations for subsequent releases. Roll back application
images only when they remain schema-compatible. After production accepts new
writes, reverting to the old SQLite snapshot is data loss, not an ordinary
rollback; use a rehearsed recovery/reconciliation procedure.

### Production acceptance checklist

- HTTPS, approved identity policy and direct-origin bypass protection work.
- Two users cannot access each other's records, streams, files or tool context.
- Duplicate submission and queue delivery do not create duplicate executions.
- Simulated worker death does not silently replay uncertain side effects.
- Stale workers and cancelled tasks cannot publish staged output.
- PostgreSQL constraints preserve one active turn per chat and revision checks.
- PDF limits, source-gap labels and artifact sandbox/CSP remain effective.
- Streaming reconnects recover events without restarting tasks.
- API/worker image, skill and extension versions remain compatible per run.
- Database/file restore and queue reconciliation are rehearsed.
- Model quotas, budgets, alerts and operational ownership are configured.
- The deployment is not described as HA until distributed coordination and
  availability tests justify that claim.

## 10. Repository implementation boundaries

| Area | Primary location |
| --- | --- |
| Authentication, ingress checks and HTTP validation | `backend\src\skill_chat\api` |
| Foreground execution ownership and streaming | `backend\src\skill_chat\chat` |
| Queue lifecycle, cancellation and execution | `backend\src\skill_chat\tasks` |
| PostgreSQL migration and Blob-backed file services | `backend\src\skill_chat\storage` |
| Provider credentials and container SDK compatibility | `backend\src\skill_chat\agents` |
| Runtime registration and selected-skill tool boundaries | `backend\src\skill_chat\extensions`, `backend\src\skill_chat\tools` |
| Browser authentication and SSE contracts | `web\src\api` and consumers |
| Proposed deployment documentation and future infrastructure | `deployment` |

Keep API adapters thin and preserve shared backend/TypeScript contract alignment.
Keep local installation supported unless a separate approved change replaces it.
Do not invent configuration variables or deployment commands before their
corresponding implementation exists.

## 11. References

- [Container Apps ingress](https://learn.microsoft.com/en-us/azure/container-apps/ingress-overview)
- [Container Apps authentication](https://learn.microsoft.com/en-us/azure/container-apps/authentication)
- [Container Apps storage](https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts)
- [Container Apps scaling](https://learn.microsoft.com/en-us/azure/container-apps/scale-app)
- [Durable orchestration constraints](https://learn.microsoft.com/en-us/azure/durable-task/common/durable-task-code-constraints)
- [Durable programming model and at-least-once activities](https://learn.microsoft.com/en-us/azure/durable-task/common/programming-model-overview)
- [Durable instance management and termination](https://learn.microsoft.com/en-us/azure/durable-task/common/durable-task-instance-management)
- [Durable persistence and serialization](https://learn.microsoft.com/en-us/azure/durable-task/durable-functions/durable-functions-serialization-and-persistence)
- [Functions hosting and timeouts](https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale)
- [SQLite WAL limitations](https://www.sqlite.org/wal.html)

Service capabilities, regional availability and plan limits must be rechecked
when implementing this proposal. No production sizing or cost estimate is
established by this document.
