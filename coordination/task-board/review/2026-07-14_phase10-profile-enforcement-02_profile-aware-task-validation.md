---
task_id: phase10-profile-enforcement-02
phase: phase10-profile-task-enforcement
status: REVIEW
owner: external-agent-platform-19
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase10-profile-enforcement-01
allowed_scope:
  - scripts/**
  - tests/**
  - docs/operations/**
  - profiles/**
  - coordination/templates/**
  - coordination/task-board/**
  - coordination/progress/**
  - coordination/delivery/**
forbidden_scope:
  - services/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Support an optional scalar profile front matter field that explicitly references a profile by name or path
  - Reject a profiled task when its profile cannot be resolved or parsed, while preserving validation compatibility for unprofiled tasks
  - Enforce the selected profile's allowed_statuses and allowed_execution_modes only when those fields are present on the task
  - Enforce profile-declared additional required front matter fields and required markdown sections without weakening core requirements
  - Keep profile defaults informational; do not auto-populate execution mode, owner, reviewer, paths, or lifecycle state
  - Add focused regression coverage and update operator-facing runtime documentation
  - Coordination validator passes cleanly
expected_artifacts:
  - code_changes
  - focused_tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Add additive validation for task cards that explicitly declare a project
profile, using the shared Phase 10 resolver without changing default-mode task
behavior.

## Context

`phase10-profile-enforcement-01` introduced `scripts/profile_resolver.py` as
the shared loader for profile-aware scripts. Phase 9 validates profile files,
but task cards currently do not state which profile applies and are never
checked against its declared constraints.

The task-level selector is a new optional scalar front matter field:

```yaml
profile: rental-rebuild
```

It is always explicit. `active: true/false` remains non-operative and cannot
select a profile.

Read before changing files:

- `docs/operations/profile-task-enforcement-runtime-plan.md`
- `profiles/schema-profile-v1.md`
- `scripts/profile_resolver.py`
- `scripts/validate_coordination_files.py`
- `coordination/task-board/done/2026-07-14_phase10-profile-enforcement-01_profile-runtime-resolver.md`

## Constraints

- Unprofiled task cards must retain current validation behavior.
- A task `profile` is a scalar profile name or path, never a list.
- Profile defaults are preferences only. Do not auto-fill or require an omitted
  `execution_mode`, owner, reviewer, branch, worktree, or artifact path.
- Enforce a profile's allowed status/mode only for values actually present on
  the task card.
- Core task requirements and the default `coordination/` artifact layout remain
  authoritative.
- Do not add path remapping, automatic profile activation, dispatch persistence,
  schema version changes, or profile inheritance.

## Implementation Notes

Use `profile_resolver.load_profile()` rather than adding a new parser. Extend
the coordination validator so a profiled task fails with a path-specific,
actionable error if its profile cannot be resolved or parsed.

For a resolved profile, inspect `task_format` defensively. Enforce only these
additive constraints when declared:

- `allowed_statuses`
- `allowed_execution_modes`
- additional `required_front_matter`
- additional `required_sections`

Do not treat profile `default_status` or `default_execution_mode` as required
values. Test unprofiled compatibility, missing/malformed profiles, narrowed
status/mode sets, missing extra field/section, and valid profiled task cards.

## Validation Steps

Run focused tests for profile-aware task validation and existing script tests,
then run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate.ps1
```

Confirm a representative unprofiled task still passes unchanged, and a profile
with `active: true` is not applied unless the task explicitly declares
`profile`.

## Escalation Rules

Raise an incident if profile enforcement requires changing core task lifecycle
states, moving coordination artifacts, modifying existing task cards in bulk,
or deciding how profile inheritance should work.
