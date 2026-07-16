---
task_id: phase11-runtime-safety-02
phase: phase11-orchestration-runtime-safety
status: REVIEW
owner: external-agent-platform-22
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase11-runtime-safety-01
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
  - Add an orchestrate command that deterministically proposes execution waves from task-card dependencies without changing any task card or assignment.
  - Distinguish runnable READY tasks from tasks blocked by missing, unfinished, cyclic, or invalid dependencies with actionable diagnostics.
  - Make ordering stable across runs and make filtering explicit rather than silently selecting a profile or phase.
  - Add focused tests for independent tasks, linear dependencies, fan-in or fan-out dependencies, missing dependencies, cycles, and no-mutation behavior.
  - Document safe operator usage, output interpretation, and the boundary between planning and dispatch.
expected_artifacts:
  - code_changes
  - focused_tests
  - operator_docs
  - delivery_report
---
# Task Packet

## Objective

Implement a read-only dependency wave planner for the lead agent. Given task
cards, it must propose the deterministic groups that are eligible to run in
parallel and explain why every other candidate is not eligible. It must never
claim tasks, change owners, move cards, or trigger dispatch.

## Context

Phase 11 task 01 introduced `orchestrate doctor` to make an execution
environment diagnosable before dispatch. This task adds the next safety layer:
the lead agent must understand task dependency order before asking multiple
external agents to work concurrently.

Read before changing files:

- `docs/operations/phase11-orchestration-runtime-safety-plan.md`
- `coordination/completed/2026-07-16_phase11-orchestration-runtime-safety-intake.md`
- `docs/operations/lead-agent-orchestration-protocol.md`
- `docs/operations/worker-assignment-policy.md`
- `scripts/orchestrate.py`
- `scripts/doctor.py`

## Constraints

- Planning is read-only: do not write, move, claim, dispatch, commit, push,
  create worktrees, or change task-card fields.
- Use task-card metadata as the source of dependency truth. Do not infer
  dependencies from filenames, owners, or phase names.
- A dependency is satisfied only by a task in a terminal accepted state defined
  by the existing lifecycle. Document the precise interpretation implemented.
- Expose filtering through explicit arguments only; no automatic profile or
  project selection.
- Return a non-zero exit status for malformed graph inputs that make a complete
  plan unreliable, while still showing actionable diagnostics where safe.
- Do not implement run manifests, worktree creation, task claiming, or API
  integration; those belong to later Phase 11 tasks.

## Implementation Notes

Follow the delegated subcommand pattern in `scripts/orchestrate.py`. Prefer a
machine-readable option only if it can be added with focused tests and clear
human output; do not add dependencies. Stable ordering should be explicit, so
the same repository state produces the same wave proposal.

## Validation Steps

1. Add focused graph fixtures/tests for independent tasks, a linear chain,
   fan-out or fan-in, a missing dependency, a cycle, and invalid metadata.
2. Assert fixture task-card bytes are unchanged before and after every planner
   invocation.
3. Run focused planner tests and `python -m pytest tests/scripts/ -q`.
4. Run `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1`.
5. Include exact commands and results in the delivery report.

## Escalation Rules

Create an incident and stop if the existing task-card lifecycle cannot define
dependency satisfaction unambiguously, if planner correctness requires
mutating task state, or if the required graph input is absent outside isolated
test fixtures.
