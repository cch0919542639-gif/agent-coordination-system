---
task_id: dual-intake-20261025-01
phase: console-handoff-live-pilot-01
status: READY
owner: handoff-pilot-receiver
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - artifacts/dual-intake-20261025-01/**
forbidden_scope:
  - coordination/task-board/**
  - coordination/reviews/**
  - scripts/**
acceptance:
  - The named physical peer receives exactly one hash-bound dispatch and publishes RECEIVED.
  - Repeated receive preserves one inbox row and the same dispatch and run identity.
  - Coordinator synchronization observes RECEIVED while this formal card remains READY.
  - No runner provider workspace task lifecycle or permission mutation occurs.
expected_artifacts:
  - handoff_receipt
execution_mode: REPO_FIRST
---
# Transport-only pilot card

## Objective

Verify a real two-computer GitHub handoff without executing task code.

## Context

Pinned code1d7b85b60b56299a161aba90a53d0078120d84af; isolated queue and external
stores described by the pilot runbook. This packaged card is not dispatched yet.

## Constraints

Do NOT claim, move, execute, submit or accept this formal task automatically.
Receiver runs without --execute, runner is null and execution_enabled is false.
Do not run a provider, worker launcher, watch, scheduler or permission editor.

## Implementation Notes

Only the transport records assignment, claim and RECEIVED. Preserve the immutable
claim/store; a future execution pilot must use a new task, queue and fresh stores.

## Validation Steps

Compare exact card SHA, dispatch/run identity, one inbox row and observed RECEIVED
before/after a second no-execute receive. No workspace or execution payload should
be created. Sender's copied formal card must remain byte-identical READY.

## Escalation Rules

Stop on stale code, occupied queue, wrong peer/owner, conflicting claim, nonzero
command exit or unexpected RUNNING/FINISHED/FAILED/UNKNOWN. Do not reset/clean,
delete receipts, alter config or create a new store to steal an existing claim.
