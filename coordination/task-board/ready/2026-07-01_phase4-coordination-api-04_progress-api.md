---
task_id: phase4-coordination-api-04
phase: phase4-coordination-api-wave2
status: READY
owner: external-agent-platform-04
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase4-coordination-api-03
allowed_scope:
  - services/coordination_api/**
  - tests/coordination_api/**
  - docs/specs/coordination-api-v1.md
  - coordination/**
forbidden_scope:
  - dashboard UI
  - repo-sync worker
  - unrelated application domains
acceptance:
  - Add POST /tasks/{taskId}/progress to the coordination API MVP
  - Enforce ownership and task-state validation for progress updates
  - Record a progress event for each accepted update
  - Add focused tests for valid and invalid update paths
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
---
# Task Packet

## Objective

Implement the progress update endpoint so an agent can report current execution status without relying on a manual chat relay.

## Context

Wave 1 proved task assignment and claiming. The next missing step is structured progress reporting that the control plane can persist and audit.

## Constraints

Keep this task limited to progress reporting behavior. Do not expand into incidents, artifact attachment, submission, review, reassignment, or heartbeat logic.

## Implementation Notes

Align the request and response shape with `docs/specs/coordination-api-v1.md`. The important parts are ownership checks, valid task-state handling, and append-only event creation. If a valid update should move a claimed task into `in_progress`, do it intentionally and cover it in tests.

## Validation Steps

Run the coordination API test suite and add focused endpoint tests for successful progress updates plus invalid owner or invalid state cases.

## Escalation Rules

Raise an incident if the spec is too ambiguous about whether progress updates are allowed from `claimed`, `in_progress`, or both.
