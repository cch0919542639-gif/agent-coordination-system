---
task_id: phase15-github-review-01
phase: phase15-github-01
status: DONE
owner: codex-phase15-github-review
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - coordination/evidence/phase15-github-01/independent*
  - coordination/delivery/phase15-github-review-01-delivery-report.md
  - coordination/progress/codex-phase15-github-review.md
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

Independently review the GitHub-only workflow and selective publication candidate.

## Context

Read PLAN.md, PROGRESS.md, TASKS.md, coordination/plans/phase15-github-01.md,
agent-task-execution-protocol.md and worker-assignment-policy.md.

## Constraints

This user-authorized direction replaces direct-host runtime with GitHub handoff.
Keep historical failure evidence and byte-identical offline code. Publishing
requires an exact-target decision after preparation/review. No B activation.

## Implementation Notes

Do not edit source plan/cards. Check both worktrees and source pins, no TLS gate,
disjoint A/B scopes, actionable cases, finite budgets, release/claim/review rules,
publication allowlist and no invented host execution. Write findings and hashes.

## Validation Steps

Run coordination validator, source pin/link/scope checks and baseline tests in
the isolated publication candidate. Use independent review for shared workflow.
Record all commands/outcomes; distinguish preparation from actual host results.

## Escalation Rules

Source mismatch, scope expansion, failed checks or unclear publication authority
means stop and report; no automatic push, merge, credentials or provider action.
