# Example: Default-Mode Task Card

This example shows a task card using global defaults (no project profile active).

## Task Card

```markdown
---
task_id: phase9-docs-01
phase: phase9-documentation
status: READY
owner: UNASSIGNED
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase8-profile-03
allowed_scope:
  - docs/**
  - coordination/task-board/**
forbidden_scope:
  - src/**
  - services/**
acceptance:
  - Create operations guide for new contributors
  - Include setup, workflow, and review process
  - Validator passes
expected_artifacts:
  - docs
  - delivery_report
---

# Task Packet

## Objective

Write a contributor onboarding guide covering setup, daily workflow, and review process.

## Context

New external agents need a single document explaining how to receive assignments, execute within scope, and submit for review.

## Constraints

- Follow existing doc style in docs/operations/
- Do not reference profile-specific paths or roles
- Keep examples generic enough for any project

## Implementation Notes

Reference agent-task-execution-protocol.md for workflow details.

## Validation Steps

- Run python scripts/orchestrate.py validate
- Verify doc links resolve correctly

## Escalation Rules

Raise incident if doc scope conflicts with forbidden paths.
```

## What the Operator Sees

| Field | Value |
|-------|-------|
| execution_mode | REPO_FIRST (default) |
| branch | Not set (not needed) |
| worktree_path | Not set (not needed) |
| artifact paths | coordination/task-board/, coordination/progress/ (defaults) |
| role naming | Free-form agent name (external-agent-docs-01) |

## Operator Dispatch Flow (Default Mode)

1. Task card lands in `ready/` with standard front matter
2. Lead agent reads task packet — no profile lookup needed
3. Lead agent assigns to an available docs agent
4. Worker executes in main worktree (REPO_FIRST)
5. Worker updates `coordination/progress/external-agent-docs-XX.md`
6. Worker moves card to `review/`
7. Reviewer validates against acceptance criteria
8. On accept, card moves to `done/`

## Reviewer Checklist (Default Mode)

- [ ] Task card has all required front matter fields
- [ ] Changes stay within allowed_scope
- [ ] No edits in forbidden_scope
- [ ] Progress file updated
- [ ] Validation passed
- [ ] Delivery report attached (if expected)
