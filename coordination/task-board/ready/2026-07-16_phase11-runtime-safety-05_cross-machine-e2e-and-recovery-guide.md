---
task_id: phase11-runtime-safety-05
phase: phase11-orchestration-runtime-safety
status: READY
owner: external-agent-quality-02
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase11-runtime-safety-01
  - phase11-runtime-safety-02
  - phase11-runtime-safety-03
  - phase11-runtime-safety-04
allowed_scope:
  - tests/**
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - scripts/**
  - services/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Add end-to-end regression coverage for doctor, wave planning, immutable manifest creation, worktree dry-run/provisioning boundary, and worker handoff prerequisites.
  - Cover recovery evidence for wrong repository, missing runtime or task/profile reference, invalid dependency graph, invalid or duplicate manifest, unsafe/colliding worktree path, revision mismatch, and machine-affinity refusal.
  - Prove the tested flow does not claim, dispatch, review, merge, push, or mutate lifecycle without an explicit existing command.
  - Publish an operator runbook with commands, expected checkpoints, stop conditions, rollback/cleanup boundaries, and cross-machine handoff requirements.
  - Keep documentation truthful: this phase prepares safe dispatch but does not automatically launch or communicate with external agents.
expected_artifacts:
  - focused_tests
  - operator_docs
  - delivery_report
---
# Task Packet

## Objective

Act as the independent Phase 11 quality gate. Add an end-to-end regression
matrix and operator recovery guide proving that the safety tools compose into a
repeatable cross-machine preparation flow without silently changing task
lifecycle or directly launching external agents.

## Context

Phase 11 has delivered four sequential capabilities:

1. `orchestrate doctor` diagnoses repository/runtime/task/profile prerequisites.
2. `orchestrate wave-planner` proposes deterministic ready-task waves.
3. `orchestrate manifest` writes immutable operator-approved wave evidence.
4. `orchestrate worktree-provision` validates and optionally creates one local
   worktree from manifest evidence.

This task must verify their combined boundary and document safe recovery. It
does not change any runtime implementation.

Read before changing files:

- `docs/operations/phase11-orchestration-runtime-safety-plan.md`
- `coordination/completed/2026-07-16_phase11-orchestration-runtime-safety-intake.md`
- `docs/operations/phase11-wave-planner-operator-guide.md`
- `docs/operations/phase11-manifest-operator-guide.md`
- `docs/operations/phase11-worktree-provision-operator-guide.md`
- `docs/operations/lead-agent-orchestration-protocol.md`
- `docs/operations/agent-task-execution-protocol.md`

## Constraints

- Do not modify files under `scripts/**`; report an incident if a runtime
  behavior requires correction rather than weakening tests or documentation.
- Tests must use isolated temporary repositories/worktrees and clean up only
  artifacts created by their own fixture.
- Verify no unapproved command claims, dispatches, reviews, merges, pushes, or
  changes task-card lifecycle state.
- Describe manual external-agent dispatch honestly. Repo evidence remains the
  communication channel; no feature here provides autonomous agent messaging.
- Do not create dashboards, APIs, hosted services, or profile path remapping.

## Implementation Notes

The desired operator journey is:

`clone correct repo -> doctor -> wave planner -> operator approves selection ->
manifest -> worktree dry-run -> optional local provision -> send dispatch
message -> worker claims and delivers -> reviewer accepts`.

The runbook must clearly separate steps automated by local scripts from human
or external-agent actions. Include an explicit cleanup/recovery section rather
than deleting worktrees automatically.

## Validation Steps

1. Add focused end-to-end tests that exercise the supported command sequence
   and representative safety refusals.
2. Run the new focused tests and `python -m pytest tests/scripts/ -q`.
3. Run `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1`.
4. Verify every documentation command and claim against the current scripts.
5. Include exact commands and results in the delivery report.

## Escalation Rules

Create an incident and stop if a required end-to-end path reveals a runtime
defect, requires changing `scripts/**`, depends on live credentials/network
services, or cannot be represented truthfully in an operator runbook.
