---
task_id: phase14-local-03
phase: phase14-local-observability
status: READY
owner: external-agent-platform-33
reviewer: ORCHESTRATOR
priority: high
dependencies: []
execution_mode: WORKTREE
branch: agent/external-agent-platform-33/phase14-local-03
worktree_path: worktrees/phase14-local-03
machine_id: local-codex-workstation
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
  - Add a project-aware status command that derives deterministic local status from registered project task-card front matter, monitor events, delivery records, progress reports, and incidents.
  - Emit human-readable and JSON output without modifying task cards, delivery records, Git branches, or remote state; an atomic Git-ignored local snapshot is the only optional write.
  - Detect pending review delivery, acknowledged ready delivery with non-ready card state, task/progress mismatch, monitored worker-branch omission, and stale in-progress evidence with a documented configurable threshold.
  - Exclude task bodies, source code, credentials, absolute local paths, and inbox payload content from output.
  - Add isolated focused tests and document the monitor-to-status operating loop.
expected_artifacts:
  - status_projector_command
  - focused_tests
  - operator_documentation
  - delivery_report
---

# Task Packet

## Objective

Re-implement the evidence-derived status projector in the pre-provisioned
worktree recorded above. This task replaces the cancelled `phase14-local-02`.

## Worktree Contract

The ORCHESTRATOR provisions the exact branch and worktree before dispatch. Work
only in `worktrees/phase14-local-03`; do not create, switch, rename, or delete
branches or worktrees. If that path is unavailable or points to another task,
open an incident and stop.

## Context

Read `AGENTS.md`, `PLAN.md`, `PROGRESS.md`, `TASKS.md`, the local compliance
rules, `scripts/remote_ref_monitor.py`, `scripts/routing_runner.py`,
`scripts/worker_poller.py`, and `scripts/project_registry.py` before editing.
Task cards remain lifecycle authority; the snapshot is read-only observability.

## Constraints

- Do not auto-claim, accept, merge, correct lifecycle state, launch workers,
  call network services, fetch Git, or expose private task data.
- Use front matter and relative IDs only in output. State anomalies are alerts,
  never automatic corrections.
- Preserve existing monitor and worker command compatibility.

## Implementation Notes

The worker must use only the provisioned worktree. The status command may be
added to `orchestrate.py` only as a deterministic, read-only entrypoint.

## Validation Steps

Run focused projector tests, relevant monitor/routing/activation regressions,
the bounded suite required by the implementation, `orchestrate.py validate`,
and a manual safe-output inspection.

## Escalation Rules

Stop with an incident for a missing worktree, Git write failure, unavailable
test runtime, required lifecycle mutation, or any private-data requirement.
