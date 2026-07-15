---
task_id: phase10-profile-enforcement-03
phase: phase10-profile-task-enforcement
status: DONE
owner: external-agent-platform-20
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase10-profile-enforcement-01
  - phase10-profile-enforcement-02
allowed_scope:
  - scripts/**
  - tests/**
  - docs/operations/**
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
  - When --profile is supplied for a mutating dispatch, record the resolved profile_name as the task card's scalar profile field
  - Preflight the resolved profile's structural validity before mutating task owner, reviewer, or metadata
  - Preserve --message-only as a non-mutating mode and preserve dispatch behavior when no profile is supplied
  - Reject unknown, malformed, or structurally invalid profiles with actionable stderr and no task-card mutation
  - Do not auto-populate execution mode, owner, reviewer, branch, worktree, artifact paths, or lifecycle state from a profile
  - Add focused regression coverage, update operator documentation and task template, and keep validator passing
expected_artifacts:
  - code_changes
  - focused_tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Make an explicit `--profile` selection durable task evidence by preflighting it
and recording its canonical `profile_name` on a dispatched task card.

## Context

Phase 10 task 01 centralized profile resolution. Task 02 made an explicit task
card `profile` enforce profile task-format constraints. Dispatch currently
accepts `--profile` only to render informational message context, so a
successfully dispatched task does not preserve which profile the operator chose.

Read before changing files:

- `docs/operations/profile-task-enforcement-runtime-plan.md`
- `scripts/profile_resolver.py`
- `scripts/dispatch_task.py`
- `scripts/validate_coordination_files.py`
- `coordination/task-board/done/2026-07-14_phase10-profile-enforcement-02_profile-aware-task-validation.md`

## Constraints

- `--profile` remains an explicit caller choice. Never consult `active` as a selector.
- Persist the resolved profile's portable `profile_name`, not a caller's
  machine-specific absolute path.
- Preflight must happen before any task-card write. A failed profile selection
  must leave owner, reviewer, execution metadata, and task profile unchanged.
- `--message-only` must not mutate task-card content, including `profile`.
- Do not infer or apply profile defaults. Existing `--execution-mode`, owner,
  reviewer, branch, worktree, and machine flags retain their current explicit
  semantics.
- Do not add path remapping, automatic worktree creation, profile inheritance,
  API changes, or lifecycle changes.

## Implementation Notes

Use `profile_resolver.load_profile()` for resolution. Reuse the existing profile
validation rules rather than duplicating schema logic. Structural preflight must
reject a profile that resolves but violates the current profile schema.

When dispatch is mutating and preflight succeeds:

```yaml
profile: rental-rebuild
```

is written to the task card using the resolved profile's `profile_name`. This
must occur alongside the existing owner/reviewer metadata write. Without
`--profile`, do not add, remove, or overwrite an existing task `profile` field.

Update the task packet template so `profile` is a documented optional scalar
field. Update operator docs to distinguish profile preflight/recording from
automatic profile configuration.

## Validation Steps

Run focused dispatch/profile tests and existing script tests, then run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate.ps1
```

Test at least:

1. profile name dispatch persists canonical profile name.
2. explicit profile file path persists the same canonical profile name.
3. `--message-only --profile` does not write task metadata.
4. malformed/unknown/schema-invalid profiles fail before any task mutation.
5. dispatch without `--profile` retains existing task profile metadata unchanged.

## Escalation Rules

Raise an incident if profile preflight requires a schema redesign, a global
validator rewrite, automatic defaults, artifact path remapping, or a decision
about profile inheritance.
