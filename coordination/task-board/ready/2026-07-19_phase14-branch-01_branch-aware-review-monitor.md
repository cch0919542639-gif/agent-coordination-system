---
task_id: phase14-branch-01
phase: phase14-branch-aware-monitoring
status: READY
owner: external-agent-platform-31
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase14-local-01
allowed_scope:
  - scripts/**
  - tests/scripts/**
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - services/**
  - src/**
  - clients/**
  - cloud/infra/**
  - profiles/**
acceptance:
  - Extend the local-only project registry with an explicit, validated allowlist of monitorable worker branches while retaining default-branch behavior when no worker branch is configured.
  - Scan only the configured default branch plus explicitly configured worker branches, using bounded Git ref/object inspection without checkout, lifecycle mutation, process/agent launch, HTTP, credentials, or public APIs.
  - Emit one idempotent review_submitted event with the actual worker ref and commit when an allowed worker branch contains a REVIEW task card, and route it to the orchestrator through the existing policy.
  - Preserve per-project/per-ref state so an unchanged worker ref produces no duplicate event and a new commit on one branch does not suppress another allowed branch.
  - Add isolated temporary-remote tests for allowed worker-branch review detection, default-only compatibility, unconfigured-branch exclusion, duplicate-poll behavior, and no task-card or commit mutation.
  - Update the monitor operator guide with the branch registration format, bounded cadence/resource impact, recovery/disable procedure, and the usage-mvp-01 verification recipe.
expected_artifacts:
  - branch_aware_monitor_code
  - focused_tests
  - operator_guide_update
  - delivery_report
---
# Task Packet

## Objective

Make the local monitor discover review evidence submitted on explicitly
registered worker branches, so the orchestrator receives a safe
`review_submitted` event without manual branch inspection.

## Context

Read:

- `PLAN.md`
- `PROGRESS.md`
- `docs/operations/phase14-same-machine-worker-automation-plan.md`
- `docs/operations/phase12-monitor-operator-guide.md`
- `docs/operations/codex-heartbeat-operator-guide.md`
- `docs/operations/agent-task-execution-protocol.md`
- `scripts/project_registry.py`
- `scripts/remote_ref_monitor.py`
- `scripts/event_ledger.py`
- `scripts/routing_runner.py`
- `tests/scripts/test_remote_ref_monitor.py`

## Constraints

- Registry configuration remains ignored, local runtime state. Do not commit
  machine paths, live delivery records, credentials, prompts, source code, or
  task body content.
- Use an explicit per-project branch allowlist. Do not broaden collection to
  every remote branch and do not infer branch eligibility from branch names.
- The monitor remains evidence-only: it must not claim, move, review, merge,
  commit, push, create a worktree, or launch a process/agent.
- Retain the existing low-frequency bounded poll and default-branch behavior.
- Event payloads must retain repository, actual ref, commit, task ID, event
  type, owner, and reviewer only; never embed raw task-card content or
  absolute paths in worker-facing data.

## Implementation Notes

Add an optional `monitor_branches` (or equivalently clear documented name)
field to `ProjectEntry`, serialized round-trip through the local registry.
The effective scan set is the default branch plus a de-duplicated explicit
allowlist. Track last-seen commits by project and branch, retaining state for
unseen configured branches rather than replacing the whole per-project map.

The first operator validation is the existing registered project:
`agent-usage-collector`, worker branch
`agent/external-agent-research-01/usage-mvp-01`, task `usage-mvp-01`.

## Validation Steps

1. Run focused branch-aware monitor tests using isolated temporary remotes.
2. Run `python -m pytest tests/scripts/ -q`.
3. Run `python scripts/orchestrate.py validate`.
4. Demonstrate the documented `usage-mvp-01` branch registration and one
   detected/routed `review_submitted` event; record only sanitized event
   metadata as delivery evidence.

## Escalation Rules

Create an incident and stop if branch-aware evidence requires scanning all
remote branches, a remote API, credentials, automatic lifecycle mutation, a
process/agent launch, or a breaking event-ledger schema migration.
