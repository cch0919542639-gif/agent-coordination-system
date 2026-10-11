---
task_id: phase14-hermes-pilot-02
phase: phase14-hermes-controlled-worker-pilot
status: CANCELLED
owner: hermes-coordination-pilot
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase14-hermes-01
allowed_scope:
  - coordination/task-board/ready/2026-10-11_phase14-hermes-pilot-02_launcher-handoff.md
  - coordination/task-board/in_progress/2026-10-11_phase14-hermes-pilot-02_launcher-handoff.md
  - coordination/task-board/review/2026-10-11_phase14-hermes-pilot-02_launcher-handoff.md
  - coordination/progress/hermes-coordination-pilot.md
  - coordination/delivery/phase14-hermes-pilot-02-delivery-report.md
  - coordination/incidents/*hermes-pilot-02*.md
forbidden_scope:
  - scripts/**
  - integrations/**
  - docs/**
  - profiles/**
  - services/**
  - src/**
  - clients/**
  - other_task_cards
  - git_commit_push_merge
acceptance:
  - Activate exactly one owner-matching delivery for this task through the existing durable inbox contract.
  - Read the packet and protocol before claiming this task with claim_task.py.
  - Write a delivery report with the actual payload ID, changed files, validation result, and residual risks.
  - Run coordination validation and submit this task to review with submit_task.py, then stop.
  - Do not process other tasks or change product code, credentials, schedules, or approval settings.
expected_artifacts:
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Prove the Hermes launcher completes the same owner-strict, single-task handoff
as the OpenCode controlled launcher, using the existing Groq provider and an
operator-selected worker model. Desktop configuration remains unchanged.

## Context

Read `docs/operations/agent-task-execution-protocol.md` and the task named by
the activation payload. The operator requested this end-to-end Hermes test
on 2026-10-11. The source skill is supplied by the launcher; no global skill
installation is required.

## Constraints

Handle only this task, preserve all existing edits, and stop after submission.
Do not use Kanban, launch agents, pull, accept, review, commit, push, merge,
enable schedules, or bypass tool approval. Do not copy prompts, responses,
credentials, or session transcripts into delivery evidence.

## Implementation Notes

Run exactly one `worker activate hermes-coordination-pilot --json` and verify
the returned task ID and worker ID. Use `scripts/claim_task.py` and
`scripts/submit_task.py`, both with `--task-id phase14-hermes-pilot-02 --agent
hermes-coordination-pilot`. Write only the named report and progress file.
Record the payload ID from actual activation; do not invent execution evidence.

## Token And Resource Impact (If Applicable)

One supervised Hermes session is authorized by the user's request to run the
dispatch flow. It uses the existing configured provider and at most 24 tool
iterations. Cost is not measured in advance. Both existing cron jobs remain
paused. No automatic retries; delivery evidence remains in this repository.

## Validation Steps

1. Run `scripts/orchestrate.py validate` and record its real result.
2. Confirm the delivery report exists before submission.
3. Submit with `scripts/submit_task.py`, confirm success, and stop.

## Escalation Rules

If the activation names a different task, an approval is denied, or execution
would exceed scope, write a scoped incident and stop. Do not change provider
credentials, task ownership, schedules, or shared scripts to work around it.

## Cancellation

Cancelled by ORCHESTRATOR on 2026-10-11, superseded by the accepted
`phase14-hermes-pilot-04` normal invocation. The bring-up activated payload a95589198a5074df, claimed and submitted to review, but provider failures and continued execution required an operator stop and report correction. It was not accepted as a clean launcher run.
Do not redispatch this task or reset its delivery acknowledgement.
