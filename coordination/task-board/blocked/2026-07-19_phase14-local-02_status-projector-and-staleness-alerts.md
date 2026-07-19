---
task_id: phase14-local-02
phase: phase14-local-observability
status: BLOCKED
owner: external-agent-platform-33
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - scripts/**
  - tests/scripts/**
  - docs/operations/**
  - coordination/task-board/**
  - coordination/progress/**
  - coordination/delivery/**
forbidden_scope:
  - services/**
  - src/**
  - database/**
  - cloud/**
  - profiles/**
acceptance:
  - Add a project-aware status command that derives a deterministic local status snapshot from registered project task cards, monitor events, delivery records, progress reports, and incidents.
  - Emit a human-readable summary and machine-readable JSON without changing any task card, delivery record, Git branch, or remote state.
  - Detect and report at least: pending review delivery, acknowledged ready delivery with a non-ready card state, task-card/progress mismatch, monitored worker branch omission, and stale in-progress progress evidence using a documented configurable threshold.
  - Exclude raw task bodies, source code, credentials, absolute local paths, and inbox payload content from generated status output.
  - Add focused tests with temporary registries/project boards and document the 10-minute monitor-to-status operating loop plus alert semantics.
expected_artifacts:
  - status_projector_command
  - status_snapshot_schema
  - focused_tests
  - operator_documentation
  - delivery_report
---
# Task Packet

## Objective

Add evidence-derived local status projection so coordination progress updates
automatically after every monitor cycle without granting the system authority to
claim, review, accept, merge, or rewrite lifecycle records.

## Context

Read before editing:

- `AGENTS.md`, `PLAN.md`, `PROGRESS.md`, and `TASKS.md`
- `docs/operations/agent-core-behavior-policy.md`
- `docs/operations/token-efficiency-policy.md`
- `docs/operations/codex-heartbeat-operator-guide.md`
- `scripts/remote_ref_monitor.py`
- `scripts/routing_runner.py`
- `scripts/worker_poller.py`
- `scripts/project_registry.py`
- `coordination/monitor/local-agent-compliance.md`

The existing monitor and routing ledger are authoritative event evidence. Task
cards remain authoritative for lifecycle state. A status snapshot is an
observability projection only.

## Constraints

- The command must be read-only with respect to task cards, delivery state,
  project registries, and Git state. Its only optional write is an atomically
  produced Git-ignored local snapshot under `coordination/monitor/`.
- Do not launch workers, invoke model APIs, call HTTP services, fetch Git, or
  create branches/worktrees.
- Do not copy task bodies, source code, absolute local paths, raw inbox
  payloads, credentials, or private content into the snapshot or test data.
- State anomalies are alerts for the orchestrator; never auto-correct them.
- Preserve current monitor and worker command compatibility.

## Implementation Notes

- A suitable CLI shape is `python scripts/orchestrate.py status --json` plus
  a non-JSON operator summary. Integrate it with the entrypoint only if the
  behaviour remains deterministic and read-only.
- Derive task state from minimal front matter only. Use relative task paths or
  task IDs in output; do not serialize body text.
- Document a default stale threshold and a way to override it for supervised
  testing. Staleness must be based on recorded evidence, not guessed agent
  activity.
- Make the operator heartbeat run monitor/routing first, then status projection
  as two bounded steps.

## Validation Steps

1. Run focused status-projector tests covering each required alert.
2. Run relevant monitor, routing, and worker activation regression tests.
3. Run the bounded project test suite specified by the implementation.
4. Manually confirm a snapshot contains no raw task body, absolute local path,
   inbox contents, or credential-shaped text.

## Escalation Rules

Create an incident and stop if the implementation needs to change task
lifecycle, acknowledge deliveries, launch a worker, make a network call, or
inspect private product data.

## Cancellation

Cancelled by the operator on 2026-07-19 after the worker could not create its
required Git branch. The uncommitted implementation attempt was discarded.
Do not re-dispatch this task; use `phase14-local-03` with a provisioned
worktree instead.
