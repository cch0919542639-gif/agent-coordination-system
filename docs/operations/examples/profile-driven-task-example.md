# Example: Profile-Driven Task Card (Rental Rebuild)

> **Runtime Status**: `--profile` dispatch context (`dispatch_task.py`) IS implemented — it loads and parses the profile YAML and includes context in the dispatch message. Profile schema validation (`validate_coordination_files.py`) is a separate step. Profile-aware path remapping, auto-activation, and profile-specific task-card validation are NOT implemented — those remain future hooks. The `active` field in profile front matter has no runtime effect. See each section below for what is currently supported vs manual.

This example shows a task card using the `rental-rebuild` project profile.

## Profile: rental-rebuild

```yaml
profile_name: rental-rebuild
schema_version: "1.0"
active: false  # Note: active field has NO runtime effect. Operator decides whether to use --profile.
task_format:
  default_execution_mode: WORKTREE
artifact_mapping:
  coordination_structure:
    task_board: "rental-rebuild/coordination/task-board/"
    progress: "rental-rebuild/coordination/progress/"
branch_pr_policy:
  branch_prefix_format: "{type}/{project_slug}/{task_id}-{short_slug}"
  pr_title_format: "[{PROJECT}] [{TASK_ID}] Short outcome statement"
worktree_policy:
  enabled: true
  default_path_prefix: "worktrees/rental-rebuild/"
```

### What the validator checks for this profile (separate step, NOT done by --profile):

Run `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1` to check:
- `profile_name` (rental-rebuild) must be unique across `profiles/`
- `schema_version` must be `"1.0"`
- `allowed_statuses` and `allowed_execution_modes` must be subsets of the core engine's values
- `artifact_mapping` paths must not escape the repo root
- All required keys (`profile_name`, `schema_version`, `description`) must be present

### What dispatch sees when using `--profile rental-rebuild`:

The profile context is loaded and displayed in the dispatch message, including:
- default execution mode: WORKTREE
- owner/reviewer naming conventions
- artifact path overrides (informational — NOT used for file placement)
- worktree policy settings

The dispatch message explicitly separates script-supported behavior from manual follow-up required by the operator.

## Task Card

```markdown
---
task_id: rental-rebuild-backend-03
phase: phase4-api
status: READY
owner: UNASSIGNED
reviewer: project-lead
priority: high
dependencies:
  - rental-rebuild-backend-02
allowed_scope:
  - rental-rebuild/src/api/**
  - rental-rebuild/tests/**
forbidden_scope:
  - rental-rebuild/src/core/**
  - shared/**
acceptance:
  - Implement tenant search endpoint
  - Add integration tests
  - OpenAPI spec updated
expected_artifacts:
  - code_changes
  - delivery_report
execution_mode: WORKTREE
branch: feat/rental-rebuild/rental-rebuild-backend-03-tenant-search
worktree_path: worktrees/rental-rebuild/rental-rebuild-backend-03
machine_id: dev-machine-01
---

# Task Packet

## Objective

Implement the tenant search API endpoint with filtering and pagination.

## Context

Rental rebuild backend needs a search endpoint for the tenant management module.

## Constraints

- Follow rental-rebuild API conventions
- Use project-specific test framework
- Branch must follow project naming: feat/rental-rebuild/{task_id}-{slug}

## Implementation Notes

- Work in assigned worktree only (set explicitly via `--worktree-path`)
- Use project-specific role names (backend-engineer, project-lead) — these are manual conventions; assign via `--owner`/`--reviewer`
- Operational artifacts remain under `coordination/` — profile `artifact_mapping` is informational only, not enforced by scripts

## Validation Steps

- Run rental-rebuild test suite
- Verify OpenAPI spec is valid
- Check branch naming matches project convention

## Escalation Rules

Raise incident if worktree conflicts with another agent or if core module changes are needed.
```

## What the Operator Sees

| Field | Value | Set By |
|-------|-------|--------|
| execution_mode | WORKTREE | Operator via `--execution-mode WORKTREE` (profile default is informational only) |
| branch | feat/rental-rebuild/rental-rebuild-backend-03-tenant-search | Operator via `--branch` |
| worktree_path | worktrees/rental-rebuild/rental-rebuild-backend-03 | Operator via `--worktree-path` |
| artifact paths | `coordination/task-board/`, `coordination/progress/` etc. | Actual runtime paths — profile `artifact_mapping` is manual convention only |
| role naming | project-lead (reviewer), backend-engineer (owner pattern) | Manual convention — operator assigns via `--owner`/`--reviewer` |

## Operator Dispatch Flow (Profile-Driven Mode)

> `--profile rental-rebuild` IS supported. Profile context is informational. Path remapping and field auto-population are NOT script-automated. Profile schema validation is a separate step (NOT done by `--profile`).

### Script-supported steps:

1. Task card lands in `coordination/task-board/ready/` (default path — NOT remapped)
2. Lead agent dispatches with `--profile rental-rebuild` — `dispatch_task.py` loads the profile YAML and includes context in the dispatch message
3. The dispatch message tells the worker what behaviour is script-supported vs manual follow-up

### Manual/operator steps:

4. Operator reads the profile manually for project-specific conventions (naming, artifact paths)
5. Operator checks worktree availability and machine affinity
6. Operator assigns with `--execution-mode WORKTREE --branch ... --worktree-path ... --machine-id ...`
7. Worker creates/switches to assigned worktree
8. Worker updates `coordination/progress/backend-engineer-XX.md` (default path — NOT remapped)
9. Worker opens PR with project-formatted title
10. Worker moves card to `coordination/task-board/review/`
11. Reviewer validates against project-specific acceptance criteria
12. On accept, `review_task.py` moves card to `done/` (no profile-specific routing)

## Reviewer Checklist (Profile-Driven Mode)

> Review routing uses `review_task.py` with standard decisions (accepted/needs_fix/reassign/rejected). Profile-aware review automation is not implemented.

- [ ] Task card has all required front matter + profile-specific fields (manual check)
- [ ] execution_mode matches profile default (manual check — not script-enforced)
- [ ] branch follows project naming convention (manual check)
- [ ] worktree_path is valid and isolated (manual check)
- [ ] Changes stay within allowed_scope (project paths)
- [ ] No edits in forbidden_scope (core modules, shared)
- [ ] Progress file updated
- [ ] PR title follows project format (manual check)
- [ ] Project-specific tests pass
- [ ] Delivery report attached
