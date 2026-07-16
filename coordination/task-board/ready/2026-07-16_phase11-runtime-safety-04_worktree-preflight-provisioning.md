---
task_id: phase11-runtime-safety-04
phase: phase11-orchestration-runtime-safety
status: READY
owner: external-agent-platform-24
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase11-runtime-safety-03
allowed_scope:
  - scripts/**
  - tests/scripts/**
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - services/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Add an explicit worktree preflight command that consumes an immutable manifest and reports eligibility without mutation in dry-run mode.
  - Validate manifest identity, repository revision, requested task membership, worktree path safety, existing-path collisions, and machine-affinity requirements when declared.
  - Add an opt-in provisioning operation that creates only the approved Git worktree after preflight success and never claims, dispatches, pushes, or changes task-card lifecycle.
  - Add focused tests for dry-run, valid provisioning, invalid manifest, unsafe path, collision, machine-affinity refusal, and no-lifecycle-mutation behavior.
  - Document setup, dry-run, recovery, cleanup boundaries, and the fact that an operator still sends the worker dispatch message.
expected_artifacts:
  - code_changes
  - focused_tests
  - operator_docs
  - delivery_report
---
# Task Packet

## Objective

Implement the opt-in worktree safety boundary for an operator-approved run
manifest. The command must first preflight a requested task's isolated working
directory, then optionally create that Git worktree only after all checks pass.

## Context

Phase 11 now has read-only environment diagnosis, deterministic dependency-wave
planning, and immutable run evidence. This task prepares the isolated checkout
that an external worker may use, without treating preparation as task claim or
agent dispatch.

Read before changing files:

- `docs/operations/phase11-orchestration-runtime-safety-plan.md`
- `docs/operations/phase11-manifest-operator-guide.md`
- `docs/operations/lead-agent-orchestration-protocol.md`
- `docs/operations/worker-assignment-policy.md`
- `scripts/manifest.py`
- `scripts/doctor.py`
- `scripts/orchestrate.py`

## Constraints

- Provisioning must require an explicit manifest ID/path and explicit task
  selection. Never infer a task from the current directory or active profile.
- `--dry-run` must execute all validations but create no directories, worktrees,
  branches, task-card changes, assignments, commits, pushes, or network calls.
- The non-dry-run operation may create only a local Git worktree at a validated
  path. It must not create remote branches or push commits.
- Reject absolute/relative path traversal outside the operator-supplied approved
  worktree root, existing path collisions, unknown manifest/tasks, stale or
  mismatched repo revisions, and incompatible machine affinity.
- Reuse manifest and profile helpers; do not duplicate parsers or introduce API
  changes.
- Document cleanup but do not implement destructive automatic cleanup.

## Implementation Notes

Use the established delegated-subcommand pattern in `scripts/orchestrate.py`.
Separate pure preflight logic from the one local Git worktree creation call so
tests can prove dry-run and failure paths are side-effect-free. The command
should provide clear recovery guidance instead of attempting repairs.

## Validation Steps

1. Add focused tests for manifest validation, dry-run, path traversal refusal,
   collisions, machine-affinity refusal, successful local provisioning, and no
   task lifecycle mutation.
2. Run focused tests and `python -m pytest tests/scripts/ -q`.
3. Run `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1`.
4. Include exact commands, local-only assumptions, and cleanup limitations in
   the delivery report.

## Escalation Rules

Create an incident and stop if safely provisioning requires automatic remote
operations, branch creation, task-card mutation, or ambiguity in an existing
manifest's task/machine requirements.
