---
task_id: phase10-profile-enforcement-01
phase: phase10-profile-task-enforcement
status: DONE
owner: external-agent-platform-18
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase9-profile-runtime-03
allowed_scope:
  - scripts/**
  - tests/**
  - docs/operations/**
  - profiles/**
  - coordination/task-board/**
  - coordination/progress/**
  - coordination/delivery/**
forbidden_scope:
  - services/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Create one shared profile runtime resolver used by dispatch_task.py instead of a duplicate local parser
  - Resolve a profile by name or explicit path and report clear errors for missing or malformed front matter
  - Preserve existing dispatch behavior when no profile is supplied
  - Do not use active true/false as a selector or implement artifact path remapping
  - Add focused regression tests and update the runtime contract documentation
  - Coordination validator passes cleanly
expected_artifacts:
  - code_changes
  - focused_tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Create the shared, explicit profile resolver that later Phase 10 scripts will
use for safe profile-aware behavior.

## Context

Phase 9 added a local `load_profile()` helper in `scripts/dispatch_task.py`.
That was appropriate for informational dispatch context, but profile-aware task
validation now needs one shared contract rather than independent parsers.

Read before changing files:

- `docs/operations/profile-task-enforcement-runtime-plan.md`
- `coordination/completed/2026-07-14_phase10-profile-task-enforcement-intake.md`
- `profiles/schema-profile-v1.md`
- `scripts/dispatch_task.py`
- `scripts/validate_coordination_files.py`

## Constraints

- Keep profile selection explicit through a name or path supplied by the caller.
- `active` remains informational and must not select a profile automatically.
- Parsing or resolving a profile must not be described as complete schema
  validation; schema validation remains a separate validator preflight.
- Do not remap `coordination/` paths or change task lifecycle behavior.
- Do not alter existing no-profile dispatch output or command semantics.

## Implementation Notes

Place reusable logic in a clearly named script module suitable for both dispatch
and validator-facing consumers. It may expose structured errors or result data,
but should avoid hidden global state. Refactor `dispatch_task.py` to consume
this module and retain its current profile context output.

Add focused tests for name resolution, explicit path resolution, missing file,
malformed front matter, and no-profile dispatch compatibility.

## Validation Steps

Run focused tests for the resolver and dispatch behavior, then run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate.ps1
```

Manually verify that `--message-only --profile` and `--output - --profile`
remain clean, pipeable output modes.

## Escalation Rules

Raise an incident instead of broadening scope if the shared resolver requires a
schema redesign, artifact path remapping, automatic profile activation, or an
unfrozen task-card metadata decision.
