---
task_id: phase14-hermes-pilot-01
phase: phase14-hermes-controlled-worker-pilot
status: REVIEW
owner: hermes-coordination-pilot
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase14-hermes-01
execution_mode: REPO_FIRST
allowed_scope:
  - coordination/task-board/**
  - coordination/progress/**
  - coordination/delivery/**
  - coordination/incidents/**
forbidden_scope:
  - scripts/**
  - docs/**
  - services/**
  - src/**
  - clients/**
  - profiles/**
  - git_commit_push_merge
acceptance:
  - Read this task packet and `docs/operations/agent-task-execution-protocol.md` before claiming the task.
  - Create `coordination/delivery/phase14-hermes-pilot-01-delivery-report.md` with the task ID, changed-file list, validation note that no product code was changed, and residual risk that this is a supervised pilot.
  - Move this card to `review/` after the report is present.
  - Do not accept, review, merge, commit, push, launch another agent, or handle another task in this turn.
expected_artifacts:
  - coordination/delivery/phase14-hermes-pilot-01-delivery-report.md
---
# Task Packet

## Objective

Verify one complete Hermes controlled-worker handoff from assignment to
repository-based review submission without modifying product code.

## Context

Read `docs/operations/agent-task-execution-protocol.md` and
`docs/operations/hermes-controlled-worker-pilot.md`.

## Constraints

- This is a one-task supervised pilot.
- Work only inside `allowed_scope`.
- Do not use Hermes Kanban.
- Do not read, claim, or execute another task after this one.
- If the task card is not in `ready/` with owner `hermes-coordination-pilot`, stop without changes.

## Implementation Notes

Create the specified delivery report, update the worker progress file, then
submit this task to review through the repository task board.

## Token And Resource Impact (If Applicable)

Measured during this run: record only whether one Hermes cron turn occurred.
Do not collect prompts, responses, credentials, or transcripts.

## Validation Steps

1. Confirm the report exists.
2. Confirm the task card is in `review/`.
3. Confirm no product-code files were changed.

## Escalation Rules

Create an incident and stop for any missing/ambiguous handoff, scope conflict,
or requirement to access a second task.
