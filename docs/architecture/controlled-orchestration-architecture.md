# Controlled Orchestration Architecture

## Decision

Extend the existing repository-first coordination system into a control plane
for at least six registered external agents. Task cards remain the lifecycle
authority. The control plane autonomously schedules ordinary task work,
delivers bounded context, records acknowledgements, and routes evidence; it
never autonomously approves or performs a high-risk action.

This design borrows the useful boundaries from the reviewed projects:

- ClawChat: separate presentation from transport and recover a read-only UI
  after transient connection loss. We do not adopt its credential persistence,
  remote WebSocket gateway, or node-mode design.
- `orca-cli/orca`: isolated worktrees, explicit dependency graph, review
  bundle, and a small operator interface. We do not adopt it as a dependency
  or make its SQLite database authoritative.
- ORCA: deterministic lifecycle control, risk gates, bounded retries, and
  human approval as an auditable state transition. We do not adopt its daemon,
  transcript store, or autonomous execution mode.
- Munder Difflin: per-agent ownership, atomic one-file mailboxes, an
  append-only event feed, and a single Git committer. We do not adopt its
  Electron/PTY interface, auto-installer, secret broker, autonomous "god"
  approval model, or its unverified OpenCode bridge.

## Architecture

```text
Task cards + reviews + delivery reports       (authoritative, versioned)
                    |
                    v
Admission and scheduling layer                (deterministic control plane)
  - task/dependency validation
  - six-or-more agent capacity and capability matching
  - run manifest, lease, and dependency projection
  - risk/approval evaluation
  - idempotent dispatch and retry policy
                    |
                    v
Agent connector layer                          (durable, bounded delivery)
  - isolated Git worktree
  - immutable context/handoff payload
  - adapter registry and runtime capability checks
  - acknowledgement, heartbeat, cancellation, and bounded recovery
                    |
                    v
Evidence layer                                (append-only, privacy bounded)
  - monitor events, validation result, review decision, incident
                    |
                    v
Operator surfaces                              (approval and observability)
  - JSON/API first, TUI/dashboard later
  - human approval queue for critical actions only
```

## Canonical Data Boundaries

| Concern | Canonical source | Projection rule |
| --- | --- | --- |
| Task lifecycle, owner, scope, acceptance | task-card front matter | Never auto-correct a card. |
| Review decision | review report and task-card state | A worker can submit only; acceptance remains reviewer-owned. |
| Delivery evidence | delivery report plus validation output | Keep paths relative and omit private content. |
| Worker assignment | immutable local handoff payload | Acknowledgement follows durable write. |
| Agent registration | versioned adapter profile plus local credential reference | Credentials never enter cards, manifests, logs, or events. |
| Dispatch | append-only outbox/inbox records with idempotency key | Retry reuses the same key; duplicate delivery cannot create a second attempt. |
| Liveness | lease and heartbeat evidence | Scheduler may recover only after lease expiry and retry-budget checks. |
| Run view | derived manifest keyed by task ID and attempt | Rebuildable; no second lifecycle state machine. |
| Runtime readiness | explicit preflight result | Discovery is not authorization or launch readiness. |
| Approval | reviewer/operator decision recorded as evidence | A missing approval always denies a critical action. |

## Local Delivery Transport

For the initial same-machine connector, the durable outbox/inbox protocol is
implemented as one message file per immutable envelope. The producing connector
writes it in its own private run directory using a temporary file followed by an
atomic rename. The scheduler alone validates it, appends a sanitized event
record, and writes any recipient delivery record. A connector never writes a
different connector's inbox, a shared board, a task card, or Git metadata.

The append-only event feed is evidence and can be replayed to reconstruct a
derived run view; it is not a second task lifecycle authority. A future shared
operator summary is scheduler-owned rather than co-edited. This adopts Munder
Difflin's useful file-ownership and single-committer pattern while retaining
this project's signed-envelope, lease-fencing, local-control, and explicit
human-approval contracts.

## Trusted Connector and Approval Contract

An external agent may be automatically started only through a pre-approved
connector grant. A grant is created by an explicit operator decision and is
scoped to a project, adapter version, named agent identity, allowed task
classes, maximum concurrent runs, worktree root, network policy, and expiry.
The grant is revocable immediately. It is not a credential and must not be
stored in Git; the scheduler stores only its opaque local reference and status.

Each connector has a stable `agent_id`, key fingerprint, and capability profile.
Every control-plane message is authenticated by the connector transport and
contains a short-lived capability token bound to one run attempt. The approval
and adapter allowlist bind a worker to its assigned worktree, fixed runtime and
argv, bounded process-tree timeout/stop handling, and no credentials, merge,
push, destructive cleanup, or task-card mutation. A policy denial is terminal,
never a prompt to retry by another route.

### L1: local controlled collaboration (default)

L1 is a `best_effort` local collaboration control, not a security sandbox. It
reduces accidental cross-task activity, runaway process trees, unsafe Git
actions, unbounded retries, and sensitive-data propagation through separate
worktree provenance, fixed runtime/argv allowlists, process-tree timeout/stop
handling, six real registered local workers, and durable
scheduler/lease/review evidence. It does not claim to protect against
malicious code, prompt-injection-directed circumvention, enforced filesystem
restrictions, independent OS process identity, or denied network egress.

### L2: platform-enforced isolation (optional hardening)

L2 is separate from L1 and is required before claiming enforced restricted
writes, independent process identity, or denied network egress. It needs
independently verifiable platform evidence for each asserted property during
admission and immediately before launch. L2 is not a prerequisite for an L1
pilot and cannot weaken L1's critical-action approval gates.

## Durable Scheduler Protocol

The scheduler is the sole writer of task-card lifecycle state. External agents
never move cards or edit progress files; they send signed status/evidence
messages to the scheduler, which validates and applies the corresponding
transition with an expected task revision. A conflicting revision creates a
reconciliation incident and cannot silently overwrite repository evidence.

Every outbox/inbox record uses this envelope:

```text
message_id, idempotency_key, type, project_id, task_id, run_id, attempt,
lease_epoch, sender_agent_id, issued_at, expires_at, context_snapshot_ref,
context_snapshot_hash, payload_ref, capability_token_ref
```

`message_id` is immutable; `idempotency_key` is unique for one logical action;
and a new attempt increments `lease_epoch`. The scheduler rejects expired,
unauthenticated, duplicated, or stale-epoch acknowledgement, heartbeat,
submission, and cancellation messages. Persisting the outbox transition and
task revision is atomic; on restart, the scheduler replays pending records and
reconciles only through these keys and epochs.

Leases declare an acknowledgement deadline, heartbeat interval, expiry, and
retry budget. Cancellation invalidates the current capability token. Late work
may be retained as forensic evidence but cannot update a card, unlock a
dependency, or enter review.

## Dependency and Context Contracts

A task is runnable only when every hard dependency has a verified `DONE`
task-card transition, or when an explicit operator override records why that
dependency is waived. `blocked`, `rejected`, `cancelled`, missing, cyclic, and
revision-conflicted dependencies never unlock downstream work. The admission
validator rejects cycles, invalid fan-in, duplicate task ownership, and
unbounded optional dependencies before any dispatch.

The scheduler builds one immutable context snapshot per attempt. It contains
only an allowlisted task-card projection, protocol/version references,
dependency evidence references, and project-relative paths. It records a
content hash, maximum byte/token size, sensitivity label, schema version, and
expiry. Untrusted task text is data, not executable instruction; context
assembly never expands it into shell commands or connector configuration.

## Run Manifest Contract

Each attempt has a local, Git-ignored manifest with only safe identifiers:

```text
run_id, project_id, task_id, attempt, state, dependency_task_ids,
execution_mode, branch_ref, worktree_id, adapter_id, capability_profile,
risk_tier, approval_required, lease_expires_at, retry_budget, evidence_refs,
timestamps
```

It must not store task bodies, source content, credentials, prompts,
transcripts, absolute paths, or raw runtime output. `state` is an execution
projection (`planned`, `admitted`, `handoff_written`, `observed`, `blocked`,
`submitted`, `closed`) and never replaces task-card lifecycle state.

## Deterministic Control Rules

1. Validate task scope, dependencies, owner, branch allowlist, worktree
   provenance, adapter capability, and available concurrency slot before
   creating an idempotent dispatch.
2. Deliver a bounded context packet automatically: task-card reference,
   acceptance criteria, dependency evidence references, permitted project
   context, and callback endpoints. Never require a user to copy this between
   agents.
3. Require an acknowledgement and heartbeat lease. Expired work is retried
   only within its budget; otherwise it becomes an incident and enters the
   human decision queue.
4. Map a task to a risk tier. Critical actions include external runtime launch,
   network transport, credential access, destructive Git, merge, and push.
5. Critical actions require an explicit, recorded operator approval; no agent,
   preflight, retry, or schedule may infer approval.
6. A worker can emit evidence and submit for review. It cannot accept,
   integrate, push, or mutate another task's lifecycle.
7. Cleanup is always a separately previewed operator action. It archives or
   prunes only verified, terminal worktrees.

## Review Bundle

A review bundle is a read-only, task-keyed index containing the task-card
path, branch/ref, changed-file summary, permitted validation results, delivery
report, review report, and unresolved incidents. It intentionally excludes
raw logs, prompts, source bodies, credentials, and local absolute paths.

## Operator Surface

JSON commands are the first interface: `plan`, `admit`, `dispatch`,
`run-status`, `review-bundle`, and `approval-queue`. A future TUI/dashboard
consumes these same projections. Normal dispatch is automatic after a task is
admitted; only a critical-action approval can activate a sensitive connector,
merge, push, or destructive operation.

## Six-Agent Acceptance Scenario

The system is not considered ready until a restart-safe pilot proves all of
the following with at least six registered agents:

1. A mixed dependency graph of at least eight tasks is admitted; independent
   tasks are dispatched to up to six agents without manual content relaying.
2. Each worker receives its context packet, acknowledges it, updates lease
   evidence, and submits review evidence through the control plane.
3. Dependency completion automatically unlocks downstream work exactly once.
4. One worker restart and one lease expiry recover within the configured
   budget; an exhausted budget becomes a routed incident rather than a loop.
5. Review submissions are automatically queued, while merge and push remain
   blocked until a recorded human approval.
6. Restarting the control plane neither loses an accepted dispatch nor creates
   duplicate worktrees, runs, or notifications.
7. Six actual registered local workers, rather than six mocks, complete the
   L1 scenario with `best_effort` evidence; fault injection uses a fake clock
   and deterministic connector test harness in addition to the live supervised
   run. This is not a sandbox or enforced filesystem/network isolation claim.
   L2 acceptance is optional and separately requires independently verifiable
   restricted writes, process identity, and denied network egress.

## Phased Delivery

| Phase | Deliverable | Exit gate |
| --- | --- | --- |
| A. Architecture baseline | This decision record, contracts, task map | Independent architecture review. |
| B. Connector grants + admission | Identity, capability grant lifecycle, sandbox verification, capacity six, dependency/cycle validation | Fixtures prove revocation and rejected/accepted admission without launch. |
| B.1 Supervised local launcher | One grant-bound OpenCode process launcher with immutable manifest validation, bounded timeout, safe terminal outcome, and operator stop | One separately approved local pilot starts exactly one allowlisted runtime and emits acknowledgement or a terminal incident without lifecycle mutation. This is not a claim of full OS sandbox enforcement. |
| C. Durable scheduler | Single-writer task revisions, authenticated idempotent atomic-file outbox/inbox, append-only event projection, context snapshots | Restart, stale-message, and duplicate-delivery tests pass. |
| D. Worktree and context lifecycle | Provisioned isolated worktrees and bounded context assembly | Six concurrent dry-run allocations do not collide or leak scope. |
| E. Lease and recovery | Heartbeats, fencing epochs, expiry, retry budget, incident routing | Simulated disconnect and late submission recover or block deterministically. |
| F. Evidence and review queue | Review bundle, validation routing, DONE-only dependency unlock | End-to-end graph reaches review without manual relaying. |
| G. Operator surface | Dashboard/API and approval queue | Human sees only decisions and exceptions, not relay work. |
| H. Six-agent pilot | Six actual registered local workers under L1 supervised policy | L1 Six-Agent Acceptance Scenario passes with `best_effort` evidence; optional L2 isolation is separately evidenced. |
| I. Cross-machine expansion | Authenticated transport, threat model, and controlled rollout | Separate design approval and security review. |

## Explicit Non-Goals

- importing ClawChat source or storing gateway tokens;
- adding Electron, Tauri, a transcript store, or a credential store;
- replacing task cards with SQLite;
- auto-review, auto-merge, auto-push, or unapproved sensitive actions;
- copying unverified behavior from external repositories.
