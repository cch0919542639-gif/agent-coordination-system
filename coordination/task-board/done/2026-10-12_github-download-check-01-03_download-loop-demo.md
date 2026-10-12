---
task_id: github-download-check-01-03
phase: local-download-verification
status: DONE
owner: opencode-coordination-pilot
reviewer: LOCAL_LOOP
priority: high
dependencies:
  - github-download-check-01-02
allowed_scope:
  - coordination/task-board/ready/2026-10-12_github-download-check-01-03_download-loop-demo.md
  - coordination/task-board/in_progress/2026-10-12_github-download-check-01-03_download-loop-demo.md
  - coordination/task-board/review/2026-10-12_github-download-check-01-03_download-loop-demo.md
  - coordination/evidence/github-download-check-01/final.json
  - coordination/delivery/github-download-check-01-03-delivery-report.md
  - coordination/progress/opencode-coordination-pilot.md
forbidden_scope:
  - scripts/**
  - integrations/**
  - tests/**
  - docs/**
  - coordination/plans/**
  - coordination/reviews/**
  - other_task_cards
  - credentials
  - git_commit_push_merge
acceptance:
  - Preserve the exact owner-matching acknowledged payload.
  - Deliver the pinned JSON artifact and truthful report; reviewer verifies independently.
  - Submit only this task to REVIEW and stop.
expected_artifacts:
  - delivery_report
execution_mode: REPO_FIRST
local_loop_checks_sha256: 8ac1143c264337843e2cd8e194e765115a05ff98df3a73387ccd298f5ffe4cf5
---
# Task Packet

## Objective

Read the accepted coordination/evidence/github-download-check-01/stage2.json and write coordination/evidence/github-download-check-01/final.json with exactly {"status":"completed","value":21,"workers":["opencode","hermes"]}. Submit truthful delivery evidence and stop.

## Context

This is a finite, operator-authorized local download verification. Read PLAN.md,
PROGRESS.md and docs/operations/agent-task-execution-protocol.md. Codex owns
control and LOCAL_LOOP checks the exact JSON. No other task may be selected.

## Constraints

Write only allowed paths. Preserve source, plans, other cards, credentials and
existing edits. No review, accept, dispatch, agents, commit, push or merge.

## Implementation Notes

Claim only this task. Use submit_task.py --task-id github-download-check-01-03 --agent opencode-coordination-pilot
--payload-id YOUR_ACK --summary 'truthful short summary' --artifact 'coordination/evidence/github-download-check-01/final.json'
for canonical reporting, validation and submission. On IN_PROGRESS repair,
skip claim and fix the review findings using the same ACK. Never reset receipts.

## Validation Steps

Check the artifact exists, run coordination validation, and submit. LOCAL_LOOP
compares JSON independently and may return needs_fix within two attempts.

## Escalation Rules

Stop on unsafe scope, wrong identity or unavailable provider. Do not fabricate
completion, alter check contracts or perform any unassigned work.
