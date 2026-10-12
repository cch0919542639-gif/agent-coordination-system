---
task_id: phase14-opencode-pilot-02
phase: phase14-opencode-controlled-worker-pilot
status: DONE
owner: opencode-coordination-pilot
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase14-opencode-01
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
  - Consume only this owner-strict assigned delivery.
  - Write a coordination-only delivery report and submit this card to review.
  - Do not handle a second task or alter product code.
expected_artifacts:
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Verify that the paused OpenCode scheduled poller can autonomously consume one
assigned delivery and submit repository evidence to review.

## Context

Read `docs/operations/agent-task-execution-protocol.md` and
`docs/operations/opencode-controlled-worker-pilot.md`.

## Constraints

- This is the only task permitted during this supervised test.
- Do not use Kanban, auto-approval, review, merge, commit, push, or product
  source paths.
- Stop after submitting this card to review.

## Implementation Notes

Write the delivery report, update worker progress, and submit through the task
board. Do not store prompts, responses, or credentials.

## Token And Resource Impact (If Applicable)

One scheduled OpenCode model call is authorized for this test. The automation
must be paused immediately after the test outcome is observed.

## Validation Steps

1. Confirm the report exists.
2. Confirm this card reaches `review/`.
3. Confirm no product-code files changed.

## Escalation Rules

Open an incident and stop if the handoff is missing, a second task is visible,
or scope would expand beyond coordination evidence.
