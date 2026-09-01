# Controlled Orchestration Architecture

## Decision

Extend the existing repository-first coordination system; do not replace it
with an external orchestrator. Task cards remain the lifecycle authority.
Runtime state is a small, local, Git-ignored projection that may be rebuilt
from task cards, monitor events, delivery records, and review evidence.

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
Admission and projection layer                (deterministic, read-only)
  - task/dependency validation
  - run-manifest projection
  - risk/approval evaluation
  - safe status and review bundle
                    |
                    v
Local execution layer                         (explicit operator action)
  - isolated Git worktree
  - immutable handoff payload
  - runtime preflight / capability registry
  - bounded heartbeat and retry accounting
                    |
                    v
Evidence layer                                (append-only, privacy bounded)
  - monitor events, validation result, review decision, incident
                    |
                    v
Read-only operator surfaces                   (no control side effects)
  - JSON commands first, TUI/dashboard later
```

## Canonical Data Boundaries

| Concern | Canonical source | Projection rule |
| --- | --- | --- |
| Task lifecycle, owner, scope, acceptance | task-card front matter | Never auto-correct a card. |
| Review decision | review report and task-card state | A worker can submit only; acceptance remains reviewer-owned. |
| Delivery evidence | delivery report plus validation output | Keep paths relative and omit private content. |
| Worker assignment | immutable local handoff payload | Acknowledgement follows durable write. |
| Run view | derived manifest keyed by task ID and attempt | Rebuildable; no second lifecycle state machine. |
| Runtime readiness | explicit preflight result | Discovery is not authorization or launch readiness. |
| Approval | reviewer/operator decision recorded as evidence | A missing approval always denies a critical action. |

## Run Manifest Contract

Each attempt has a local, Git-ignored manifest with only safe identifiers:

```text
run_id, project_id, task_id, attempt, state, dependency_task_ids,
execution_mode, branch_ref, worktree_id, adapter_id, risk_tier,
approval_required, retry_budget, evidence_refs, timestamps
```

It must not store task bodies, source content, credentials, prompts,
transcripts, absolute paths, or raw runtime output. `state` is an execution
projection (`planned`, `admitted`, `handoff_written`, `observed`, `blocked`,
`submitted`, `closed`) and never replaces task-card lifecycle state.

## Deterministic Control Rules

1. Validate task scope, dependencies, owner, branch allowlist, and worktree
   provenance before writing a handoff.
2. Map a task to a risk tier. Critical actions include external runtime launch,
   network transport, credential access, destructive Git, merge, and push.
3. Critical actions require an explicit, recorded operator approval; no agent,
   preflight, retry, or schedule may infer approval.
4. Retry only a bounded, idempotent handoff observation. A repeated failure
   creates an incident and blocks the run; it never loops indefinitely.
5. A worker can emit evidence and submit for review. It cannot accept,
   integrate, push, or mutate another task's lifecycle.
6. Cleanup is always a separately previewed operator action. It archives or
   prunes only verified, terminal worktrees.

## Review Bundle

A review bundle is a read-only, task-keyed index containing the task-card
path, branch/ref, changed-file summary, permitted validation results, delivery
report, review report, and unresolved incidents. It intentionally excludes
raw logs, prompts, source bodies, credentials, and local absolute paths.

## Operator Surface

JSON commands are the first interface: `plan`, `admit`, `run-status`, and
`review-bundle`. A future TUI/dashboard consumes these same JSON projections.
It has no direct execution buttons in the initial release; an operator still
uses the existing explicit worker activation command after approval.

## Phased Delivery

| Phase | Deliverable | Exit gate |
| --- | --- | --- |
| A. Architecture baseline | This decision record, contracts, task map | Independent architecture review. |
| B. Admission + manifest | Safe schema, dependency/cycle validation, deterministic plan command | Fixtures prove no writes in plan mode. |
| C. Controlled handoff | Approved manifest-to-existing-handoff bridge and retry budget | One supervised local task; no runtime launch. |
| D. Evidence + review bundle | Read-only task evidence bundle and status extensions | Privacy/safe-output tests and reviewer acceptance. |
| E. Worktree hygiene | Doctor, verified stale-entry detection, preview-only cleanup plan | No destructive action without exact approval. |
| F. Operator surface | Read-only TUI/dashboard built on JSON contracts | No credentials, socket listener, or execution control. |
| G. Supervised runtime pilot | One-shot adapter invocation only after separate approval | Independent safety review and rollback exercise. |
| H. Cross-machine design | Authenticated transport proposal and threat model | Design approval only; no transport implementation. |

## Explicit Non-Goals

- importing ClawChat source or storing gateway tokens;
- adding Electron, Tauri, a daemon, a remote listener, or a transcript store;
- replacing task cards with SQLite;
- autonomous launch, auto-review, auto-merge, auto-push, or cross-machine
  delivery;
- copying unverified behavior from external repositories.
