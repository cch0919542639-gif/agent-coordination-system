---
task_id: phase14-hermes-pilot-04
phase: phase14-hermes-controlled-worker-pilot
status: DONE
owner: hermes-coordination-pilot
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase14-hermes-01
allowed_scope:
  - coordination/task-board/ready/2026-10-11_phase14-hermes-pilot-04_fresh-launcher.md
  - coordination/task-board/in_progress/2026-10-11_phase14-hermes-pilot-04_fresh-launcher.md
  - coordination/task-board/review/2026-10-11_phase14-hermes-pilot-04_fresh-launcher.md
  - coordination/progress/hermes-coordination-pilot.md
  - coordination/delivery/phase14-hermes-pilot-04-delivery-report.md
  - coordination/incidents/*hermes-pilot-03*.md
forbidden_scope:
  - scripts/**
  - integrations/**
  - docs/**
  - profiles/**
  - products/**
  - other_task_cards
  - git_commit_push_merge
acceptance:
  - Activate exactly one owner-matching delivery and record its actual payload ID.
  - Read the packet and protocol before claiming with claim_task.py.
  - Write truthful delivery evidence using coordination/templates/delivery-report.md and pass validation.
  - Submit this task to review using submit_task.py, verify success, and stop.
expected_artifacts:
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Verify a fresh Hermes launcher invocation completes activation, claim, delivery,
validation, and review submission without operator recovery or product edits.

## Context

The user's 2026-10-11 request authorizes this supervised dispatch test. The
launcher supplies the repository worker skill and uses the existing Groq
provider with a worker-local `qwen/qwen3.8-27b` selection.
This fresh run supersedes interrupted pilots 02 and 03 for the clean-exit
criterion. Do not edit either task or its report.

## Constraints

Handle this task only. Preserve existing edits. Do not use Kanban, launch
agents, change credentials or schedules, approve tools, accept, review, pull,
commit, push, merge, or copy private transcripts into evidence.

## Implementation Notes

After activation, read this packet and the task execution protocol, then claim
with `scripts/claim_task.py --task-id phase14-hermes-pilot-04 --agent
hermes-coordination-pilot`. Write a concise delivery report in the existing
template, using the real payload ID. Run validation and fix any report findings.
Submit using `scripts/submit_task.py` with the same task ID and agent. The submit
script updates progress. Do not claim submission succeeded before verification.

## Token And Resource Impact (If Applicable)

One normal worker session is authorized using existing Groq credentials. Use
concise relevant context and at most 24 iterations. No automatic session retry;
the native schedule is disabled and legacy cron jobs are paused.

## Validation Steps

Run `scripts/orchestrate.py validate`, confirm the report exists, submit,
verify the card reached `review/`, and stop. Record provider limits as residual
risks; this pilot does not prove capacity for larger product tasks.

## Escalation Rules

If the payload names another task, approval is denied, or the provider prevents
completion, create a scoped incident and stop without changing ownership or
provider configuration.
