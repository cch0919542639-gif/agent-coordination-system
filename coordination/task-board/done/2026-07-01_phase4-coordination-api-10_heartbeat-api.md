---
task_id: phase4-coordination-api-10
phase: phase4-coordination-api-wave2
status: DONE
owner: external-agent-platform-10
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase4-coordination-api-03
  - phase4-coordination-api-08
allowed_scope:
  - services/coordination_api/**
  - tests/coordination_api/**
  - docs/specs/coordination-api-v1.md
  - coordination/**
  - docs/operations/**
forbidden_scope:
  - dashboard UI
  - repo sync
  - unrelated domains
acceptance:
  - Add POST /tasks/{taskId}/heartbeat to extend the claim lease
  - Add POST /heartbeat/expired to list expired assignments
  - Add POST /tasks/{taskId}/recover to recover an expired task
  - Add focused tests for heartbeat, expiry detection, and recovery
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
---
# Task Packet

## Objective

Implement heartbeat and lease recovery so in-progress work can recover safely when an agent disappears.

## Context

Tasks can be claimed and worked on, but there is no mechanism to detect when an agent has stopped heartbeating. Without lease expiry, abandoned work stays locked.

## Constraints

Keep this task limited to heartbeat, expiry detection, and recovery. Do not expand into repo sync, dashboard UI, or unrelated domains.

## Implementation Notes

Follow `docs/specs/coordination-api-v1.md` for the heartbeat request shape. Add a `lease_expires_at` column to the assignments table (migration v2). Set an initial lease on claim (5 min). Heartbeat refreshes it. Recovery closes the expired assignment and sets the task to `assigned`.

## Validation Steps

Run the coordination API test suite and add endpoint tests covering heartbeat, expiry detection, recovery success, and invalid paths.

## Escalation Rules

Raise an incident if the lease duration design or recovery behavior is too ambiguous to implement safely.
