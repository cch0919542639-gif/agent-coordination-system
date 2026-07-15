---
task_id: phase10-profile-enforcement-04
phase: phase10-profile-task-enforcement
status: REVIEW
owner: external-agent-quality-01
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase10-profile-enforcement-02
  - phase10-profile-enforcement-03
allowed_scope:
  - tests/**
  - docs/operations/**
  - profiles/**
  - coordination/templates/**
  - coordination/task-board/**
  - coordination/progress/**
  - coordination/delivery/**
forbidden_scope:
  - scripts/**
  - services/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Add an end-to-end regression matrix covering default-mode and explicitly profiled task flows through dispatch and validation
  - Verify canonical profile recording survives a normal task lifecycle handoff without path remapping or automatic defaults
  - Verify unprofiled tasks remain compatible and profile preflight failures are non-mutating
  - Refresh operator guidance with a safe Phase 10 profile workflow and an explicit current-capability versus deferred-capability table
  - Do not modify runtime scripts or alter profile enforcement behavior
  - Full script regression suite and coordination validator pass
expected_artifacts:
  - focused_tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Close Phase 10 with independent end-to-end regression coverage and operator
guidance that reflects the profile runtime now actually implemented.

## Context

Phase 10 now has three accepted implementation steps:

- shared profile resolution
- explicit task-card profile validation
- dispatch profile preflight and canonical profile recording

This final task must verify the combined behavior from an operator perspective.
It is a quality gate, not a new runtime feature task.

Read before changing files:

- `docs/operations/profile-task-enforcement-runtime-plan.md`
- `profiles/schema-profile-v1.md`
- `scripts/profile_resolver.py`
- `scripts/dispatch_task.py`
- `scripts/validate_coordination_files.py`
- Phase 10 done task cards and review reports under `coordination/task-board/done/` and `coordination/reviews/`

## Constraints

- Do not modify anything under `scripts/**`; report an incident if tests expose
  a runtime defect.
- Do not represent profile defaults, `active`, artifact mapping, worktree
  policy, reviewer routing, or path remapping as automatic behavior.
- All coordination artifacts remain under `coordination/` for the current
  runtime.
- Keep tests self-cleaning: temporary task cards and temporary profiles must be
  removed even when a test fails.
- Do not expand into API, dashboard, worktree provisioning, or profile
  inheritance work.

## Implementation Notes

Add or extend tests to cover this matrix:

| Flow | Required evidence |
|---|---|
| Default mode | dispatch and validator work without a `profile` field |
| Named profile | mutating dispatch stores canonical `profile_name`; validator enforces it |
| Profile file path | dispatch stores the same canonical name, not machine-specific path |
| Profile rule failure | a persisted profile constrains declared status/mode/additional requirements |
| Preflight failure | unknown/malformed/schema-invalid profiles leave protected task fields unchanged |
| Message-only | context may render but no task-card mutation occurs |

Update operator documentation with one compact Phase 10 command sequence:

1. run `validate.ps1` to validate profile files
2. dispatch with `--profile <name-or-path>` when profile constraints are wanted
3. explain that dispatch records `profile_name`, but does not apply defaults or
   remap artifact paths
4. run validator before submission/review

Add a table of current capabilities and deferred capabilities. Keep every claim
aligned to actual scripts.

## Validation Steps

Run the full script test suite and coordination validator:

```powershell
python -m pytest tests/scripts/ -q
powershell -ExecutionPolicy Bypass -File scripts\validate.ps1
```

Manually read the operator guide once as a new worker and verify it cannot
direct someone to a non-existent profile path, automatic worktree, or
profile-specific artifact directory.

## Escalation Rules

Open an incident rather than modifying runtime scripts if the end-to-end matrix
reveals a behavior mismatch, missing safety boundary, or documentation claim
that cannot be made truthful without a new implementation task.
