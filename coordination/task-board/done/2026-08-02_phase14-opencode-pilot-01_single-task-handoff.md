---
task_id: phase14-opencode-pilot-01
phase: phase14-opencode-controlled-worker-pilot
status: DONE
owner: opencode-coordination-pilot
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase14-runtime-adapter-01
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
  - Read this task packet and the execution protocol before claiming.
  - Write a delivery report with no product-code changes and residual risk.
  - Submit this card to review after the report exists.
  - Handle no second task and perform no acceptance, merge, commit, or push.
expected_artifacts:
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Verify one OpenCode controlled-worker handoff from owner-strict assignment to
repository review submission without modifying product code.

## Context

Read `docs/operations/agent-task-execution-protocol.md` and
`docs/operations/opencode-controlled-worker-pilot.md`.

## Constraints

- Process only this assigned task.
- Do not use Kanban, automatic approval, review, merge, commit, or push.
- Do not edit product code.

## Implementation Notes

Create the required delivery report and progress evidence, then submit this
card to review and stop.

## Token And Resource Impact (If Applicable)

One authorized OpenCode model run. Do not record prompts, responses,
credentials, or transcripts in the repository.

## Validation Steps

1. Confirm the delivery report exists.
2. Confirm the card is in `review/`.
3. Confirm no product-code files changed.

## Escalation Rules

Open an incident and stop if the handoff is absent, ambiguous, outside scope,
or would require a second task.
