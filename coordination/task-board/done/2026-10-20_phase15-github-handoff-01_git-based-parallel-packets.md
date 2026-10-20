---
task_id: phase15-github-handoff-01
phase: phase15-github-01
status: DONE
owner: codex-phase15-github-lead
reviewer: codex-phase15-github-review
priority: high
dependencies: []
allowed_scope:
  - .gitattributes
  - coordination_runtime/__init__.py
  - coordination_runtime/offline_inbox.py
  - coordination_runtime/state_controller.py
  - tests/scripts/test_offline_inbox.py
  - docs/operations/phase15-offline-inbox-contract.md
  - coordination/plans/phase15-github-01.md
  - docs/operations/phase15-github-handoff-guide.md
  - coordination/evidence/phase15-github-01/**
  - coordination/task-board/*/*phase15-github*.md
  - coordination/task-board/*/*phase15-two-host-pilot*.md
  - coordination/progress/*phase15-github*.md
  - coordination/progress/codex-phase15-two-host-lead.md
  - coordination/delivery/phase15-github*.md
  - coordination/reviews/*phase15-github*.md
  - coordination/incidents/*phase15-two-host*.md
  - coordination/plans/phase15-two-host-01.md
  - PLAN.md
  - PROGRESS.md
  - TASKS.md
  - DECISIONS.md
forbidden_scope:
  - Unrelated history, credentials, peer connections, provider calls, service activation, push and merge
acceptance:
  - Artifacts are scoped and evidence-backed with exact file pins.
  - No publication or two-host execution is claimed from local preparation.
expected_artifacts:
  - report
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Prepare two disjoint GitHub-only task packets and a minimal publishable branch.

## Context

Read PLAN.md, PROGRESS.md, TASKS.md, coordination/plans/phase15-github-01.md,
agent-task-execution-protocol.md and worker-assignment-policy.md.

## Constraints

This user-authorized direction replaces direct-host runtime with GitHub handoff.
Keep historical failure evidence and byte-identical offline code. Publishing
requires an exact-target decision after preparation/review. No B activation.

## Implementation Notes

Lead selects five pinned source inputs unchanged from accepted offline inbox.
Cancel the old direct-host pilot by scope supersession, not by declaring TLS fixed.
Prepare independent review and exact publication scope. Worker cards stay BLOCKED
until publication/assignment. Work spans integration and isolated publication trees.

## Validation Steps

Run coordination validator, source pin/link/scope checks and baseline tests in
the isolated publication candidate. Use independent review for shared workflow.
Record all commands/outcomes; distinguish preparation from actual host results.

## Escalation Rules

Source mismatch, scope expansion, failed checks or unclear publication authority
means stop and report; no automatic push, merge, credentials or provider action.
