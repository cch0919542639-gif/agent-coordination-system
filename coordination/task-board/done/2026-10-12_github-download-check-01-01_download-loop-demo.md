---
task_id: github-download-check-01-01
phase: local-download-verification
status: DONE
owner: opencode-coordination-pilot
reviewer: LOCAL_LOOP
priority: high
dependencies: []
allowed_scope:
  - coordination/task-board/ready/2026-10-12_github-download-check-01-01_download-loop-demo.md
  - coordination/task-board/in_progress/2026-10-12_github-download-check-01-01_download-loop-demo.md
  - coordination/task-board/review/2026-10-12_github-download-check-01-01_download-loop-demo.md
  - coordination/evidence/github-download-check-01/stage1.json
  - coordination/delivery/github-download-check-01-01-delivery-report.md
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
local_loop_checks_sha256: 290d2a91e349c3f61ff46f9365285fa08943e750c74f67f953f8364dab0cba78
---
# Task Packet

## Objective

Write coordination/evidence/github-download-check-01/stage1.json. On the first submission deliberately write {"stage":1,"agent":"opencode","value":6} to demonstrate bounded repair; then submit a truthful report. On a same-task needs_fix repair, correct value to7. Never accept your own work.

## Context

This is a finite, operator-authorized local download verification. Read PLAN.md,
PROGRESS.md and docs/operations/agent-task-execution-protocol.md. Codex owns
control and LOCAL_LOOP checks the exact JSON. No other task may be selected.

## Constraints

Write only allowed paths. Preserve source, plans, other cards, credentials and
existing edits. No review, accept, dispatch, agents, commit, push or merge.

## Implementation Notes

Claim only this task. Use submit_task.py --task-id github-download-check-01-01 --agent opencode-coordination-pilot
--payload-id YOUR_ACK --summary 'truthful short summary' --artifact 'coordination/evidence/github-download-check-01/stage1.json'
for canonical reporting, validation and submission. On IN_PROGRESS repair,
skip claim and fix the review findings using the same ACK. Never reset receipts.

## Validation Steps

Check the artifact exists, run coordination validation, and submit. LOCAL_LOOP
compares JSON independently and may return needs_fix within two attempts.

## Escalation Rules

Stop on unsafe scope, wrong identity or unavailable provider. Do not fabricate
completion, alter check contracts or perform any unassigned work.
