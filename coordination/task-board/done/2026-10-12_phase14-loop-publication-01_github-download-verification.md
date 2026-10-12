---
task_id: phase14-loop-publication-01
phase: phase14-local-agent-loop
status: DONE
owner: codex
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase14-local-loop-01
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
  - git_merge
acceptance:
  - Publish only the local-loop changes and necessary download prerequisites on a scoped GitHub branch.
  - Verify an actual fresh GitHub clone without original runtime registry, inbox, receipts or private transcripts.
  - Execute a new finite OpenCode-Hermes-OpenCode chain using existing local installations and providers, and verify completed replay.
  - Record final tests, remote commit identity, actual artifacts and portable setup limitations.
expected_artifacts:
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Publish the accepted local completion loop and verify downloaded GitHub data
can reproduce it. User authorized GitHub push and actual verification on
2026-10-12. Use the managed publication checkout and a fresh remote clone.

## Context

Read the accepted phase14-local-loop-01 evidence. The publication base is
codex/hermes-launcher-parity; create codex/local-agent-completion-loop for this
scope. Existing schedules remain disabled. Do not publish local credentials,
runtime state, private transcripts or unrelated dirty working-tree changes.

## Constraints

No merge, force push, production or credential changes. Preserve original
checkout and prior draft PR. Use new task/run IDs and fresh local registry;
never copy/reset old ACKs to simulate remote completion.

## Implementation Notes

Remove machine-specific Python assumptions and reuse existing registry,
worker, task-card and controller helpers for a minimal download bootstrap.
Models still require installed OpenCode/Hermes and existing provider setup.

## Validation Steps

Run focused tests and coordination validation in publication and remote
checkouts. Check exact remote commit and file hashes. Run real bounded workers
on fresh task packets and confirm independent checks, DONE, zero-launch replay.

## Escalation Rules

Stop a failed verification run with retained evidence. Do not call fake-worker
tests a real provider execution, claim another physical machine was tested,
or merge a branch without explicit authorization.
