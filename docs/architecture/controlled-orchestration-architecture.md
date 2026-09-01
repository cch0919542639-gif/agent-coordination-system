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

## Phased Delivery

| Phase | Deliverable | Exit gate |
| --- | --- | --- |
| A. Architecture baseline | This decision record, contracts, task map | Independent architecture review. |
| B. Agent registry + admission | Agent profiles, capability matching, capacity six, dependency/cycle validation | Fixtures prove rejected/accepted admission without a launch. |
| C. Durable dispatch | Idempotent outbox/inbox, context packets, acknowledgement protocol | Restart and duplicate-delivery tests pass. |
| D. Worktree and context lifecycle | Provisioned isolated worktrees and bounded context assembly | Six concurrent dry-run allocations do not collide. |
| E. Lease and recovery | Heartbeats, expiry, retry budget, incident routing | Simulated disconnect recovers or blocks deterministically. |
| F. Evidence and review queue | Review bundle, validation routing, dependency unlock | End-to-end graph reaches review without manual relaying. |
| G. Operator surface | Dashboard/API and approval queue | Human sees only decisions and exceptions, not relay work. |
| H. Six-agent pilot | Six registered adapters under supervised policy | Six-Agent Acceptance Scenario passes. |
| I. Cross-machine expansion | Authenticated transport, threat model, and controlled rollout | Separate design approval and security review. |

## Explicit Non-Goals

- importing ClawChat source or storing gateway tokens;
- adding Electron, Tauri, a transcript store, or a credential store;
- replacing task cards with SQLite;
- auto-review, auto-merge, auto-push, or unapproved sensitive actions;
- copying unverified behavior from external repositories.
