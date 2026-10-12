---
task_id: phase14-main-integration-01
phase: phase14-local-agent-loop
status: IN_PROGRESS
owner: codex
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase14-loop-publication-01
allowed_scope:
  - scripts/**
  - integrations/**
  - tests/scripts/**
  - docs/operations/**
  - coordination/**
  - README.md
  - PLAN.md
  - PROGRESS.md
  - TASKS.md
  - DECISIONS.md
forbidden_scope:
  - products/**
  - agent-usage-collector/**
  - unrelated_existing_edits
  - credentials
  - production
  - remote_main_update_before_clean_validation_and_review
acceptance:
  - Prepare a reviewable main-based integration of the verified local-loop branch while preserving current main functionality.
  - Resolve conflicts from repository evidence and pass appropriate integrated validation/tests.
  - Provide a concrete GitHub PR targeting main with exact commit/test evidence and any residual risks.
  - Apply the existing clean-gate merge policy once integration validation and independent review pass.
expected_artifacts:
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Continue the pending main-integration preparation requested on2026-10-12.
Prepare and review the exact merge candidate, then apply main's existing
DECISIONS.md clean-gate policy dated2026-07-21: after clean validation and
accepted review, commit, merge and push without additional confirmation.

## Context

The accepted publication is c04bad5 on codex/local-agent-completion-loop.
main is currently7b0a22e and has six conflicts with that branch. Existing PRs1
and2 target intermediate branches. Use the clean attached publication worktree
for codex/main-local-agent-loop-integration based on the current origin/main.

## Constraints

The user's continue instruction authorizes local integration/conflict repair,
tests, documentation and a reviewable PR. Preserve the dirty original checkout
and earlier publication branches/PRs. The user's continue instruction and the
linked existing clean-gate policy authorize integration after validation and
accepted independent review. No automatic worker
schedules, credentials, production or unrelated feature work.

## Implementation Notes

Local merges are authorized preparation. Preserve main's launcher-validation,
status-projector and existing command entrypoints while adding local-loop.
Retain historical external review evidence truthfully; fix schema only as
needed. Update current docs to describe the candidate without claiming merged.

## Validation Steps

Run integrated coordination validation, relevant Python compilation, Git diff
checks and the combined scripts test suite. Inspect runtime differences from
the actual provider-tested source; use a fresh bounded real run if relevant
runtime behavior changes. Record a main-targeted PR and exact evidence.

## Escalation Rules

Stop only blocked work. Escalate unresolved safety, validation or review concerns
with the concrete PR, verified head/base and test evidence.
Do not infer acceptance from a clean Git merge or bypass checks/branch protection.
