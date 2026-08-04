---
task_id: phase14-hermes-01
phase: phase14-hermes-controlled-worker-pilot
status: IN_PROGRESS
owner: codex
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase14-local-01
  - phase14-runtime-adapter-01
execution_mode: REPO_FIRST
allowed_scope:
  - docs/operations/**
  - coordination/**
  - integrations/hermes-coordination-worker/**
forbidden_scope:
  - services/**
  - src/**
  - clients/**
  - profiles/**
  - scripts/worker_poller.py
  - automatic_review_or_merge
acceptance:
  - Provide a standalone Hermes skill that consumes only the existing owner-strict worker activation payload and handles at most one eligible task per scheduled run.
  - Configure one local Hermes cron job at a ten-minute cadence, with an explicit one-task, review-only completion boundary.
  - Prove the skill and cron configuration do not invoke Hermes Kanban, auto-accept, merge, push, or select unassigned work.
  - Run a supervised single-task pilot from assigned handoff through repository-based review submission, or record an evidence-backed blocker.
  - Publish rollback instructions that pause/remove the cron job and remove the local skill without altering task cards.
expected_artifacts:
  - standalone_hermes_skill
  - cron_configuration_evidence
  - operator_guide
  - pilot_delivery_report
---
# Task Packet

## Objective

Establish a bounded Hermes worker that consumes the existing same-machine,
owner-strict activation handoff and executes at most one assigned task per
scheduled turn.

## Context

Read:

- `docs/operations/phase14-worker-bootstrap-guide.md`
- `docs/operations/agent-task-execution-protocol.md`
- `docs/operations/runtime-adapter-preflight-guide.md`
- `coordination/task-board/done/2026-07-18_phase14-local-01_worker-activation-command.md`

## Constraints

- Keep the repository task board as the lifecycle authority.
- Do not use or configure Hermes Kanban.
- Do not auto-accept, review, merge, commit, push, or launch another agent.
- Process no more than one owner-matching ready task in one Hermes cron turn.
- A task may be claimed only after the agent reads its task packet and protocol.
- Completion means move to `review/` with repository delivery evidence; an
  orchestrator still decides acceptance.
- The cron setup is local runtime configuration; use only explicit operator
  commands and document its job ID for rollback.

## Implementation Notes

- Reuse `worker activate <worker-id> --json`; do not add a second dispatcher.
- Install the reviewed skill through a verified local junction and attach it to
  one paused Hermes cron job.
- Keep the first end-to-end run supervised and record a blocker if no eligible
  assigned delivery is available.

## Token And Resource Impact (If Applicable)

Estimated: one model turn every ten minutes only when a matching handoff is
available. No busy loop, transcript collection, or Kanban polling. The job is
paused/removed to disable it; repo delivery evidence remains unchanged.

## Validation Steps

1. Verify the skill text states the owner, one-task, and review-only limits.
2. Inspect the created Hermes cron job and its schedule/prompt.
3. Run a supervised assigned-task handoff through review submission.
4. Run `python scripts/orchestrate.py validate` and record the result.

## Escalation Rules

Stop and open an incident if the pilot needs Hermes Kanban, credentials,
cross-machine communication, automatic review/merge/push, more than one task
per turn, or a change to the worker activation contract.
