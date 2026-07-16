---
task_id: phase11-runtime-safety-03
phase: phase11-orchestration-runtime-safety
status: DONE
owner: external-agent-platform-23
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase11-runtime-safety-01
  - phase11-runtime-safety-02
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
  - Add an explicit command that writes an immutable run manifest only after operator-supplied task selection passes preflight.
  - Record repository identity and revision, selected tasks and wave, owner and reviewer, explicit profile selections, command context, and creation timestamp.
  - Reject duplicate manifest IDs, unknown or non-runnable task selections, and invalid explicit profiles without changing task lifecycle or assignment state.
  - Add focused tests for manifest success, reproducibility fields, invalid inputs, duplicate protection, and no-mutation behavior.
  - Document the approval boundary between wave planning, manifest creation, and actual dispatch.
expected_artifacts:
  - code_changes
  - focused_tests
  - operator_docs
  - delivery_report
---
# Task Packet

## Objective

Implement an operator-invoked immutable run manifest. After the lead agent has
used `doctor` and `wave-planner`, it must be able to persist an auditable record
of the chosen execution wave without changing task lifecycle, ownership, or
worker state.

## Context

Phase 11 task 01 verifies whether an execution environment is safe to use.
Task 02 proposes which ready tasks may run in parallel. This task bridges those
read-only decisions to later dispatch and worktree preparation by writing a
stable manifest that another machine or reviewer can inspect.

Read before changing files:

- `docs/operations/phase11-orchestration-runtime-safety-plan.md`
- `coordination/completed/2026-07-16_phase11-orchestration-runtime-safety-intake.md`
- `docs/operations/phase11-wave-planner-operator-guide.md`
- `docs/operations/lead-agent-orchestration-protocol.md`
- `scripts/doctor.py`
- `scripts/wave_planner.py`
- `scripts/orchestrate.py`

## Constraints

- Manifest creation is explicit and may write only its own manifest artifact;
  it must not move or edit task cards, assign owners, create branches,
  worktrees, commits, or remote operations.
- Reuse existing task and profile parsing/validation helpers. Do not create a
  second task-card or profile parser.
- Record only explicit profile choices. Never use `active` as an automatic
  selector and never remap artifact paths.
- The stored data must be deterministic for a fixed command input except for a
  documented creation timestamp.
- Treat a manifest as immutable: duplicate IDs must fail rather than overwrite.
- Do not implement actual dispatch, claim, reviewer routing, or worktree
  provision; those remain separate operations.

## Implementation Notes

Use the established delegated-subcommand pattern in `scripts/orchestrate.py`.
Choose a repository-controlled manifest directory under `coordination/` and
document its schema and naming convention. The command may accept an explicit
wave/task selection, but it must validate that the selection is eligible using
the planner's supported contract before writing output.

## Validation Steps

1. Add focused tests for valid creation, stable recorded fields, duplicate ID
   rejection, unknown/non-runnable task rejection, invalid profile rejection,
   and lifecycle no-mutation.
2. Run focused manifest tests and `python -m pytest tests/scripts/ -q`.
3. Run `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1`.
4. Include exact commands and results in the delivery report.

## Escalation Rules

Create an incident and stop if the current planner cannot reliably establish
task eligibility, if manifest output requires lifecycle mutation, or if the
desired artifact schema conflicts with existing coordination validation.
