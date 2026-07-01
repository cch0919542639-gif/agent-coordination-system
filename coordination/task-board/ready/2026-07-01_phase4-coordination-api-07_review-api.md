---
task_id: phase4-coordination-api-07
phase: phase4-coordination-api-wave2
status: READY
owner: external-agent-platform-07
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase4-coordination-api-06
allowed_scope:
  - services/coordination_api/**
  - tests/coordination_api/**
  - docs/specs/coordination-api-v1.md
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - reassignment API
  - heartbeat recovery
  - dashboard UI
acceptance:
  - Add POST /tasks/{taskId}/review to record structured review decisions
  - Map valid decisions to valid task-state transitions
  - Record a review event and persist review findings
  - Add focused tests for accepted, needs_fix, rejected-style, and invalid decision paths
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Implement the review endpoint so the orchestrator can close the loop with a structured acceptance or return-for-fix decision inside the control plane.

## Context

Wave 2 is complete only when an agent can submit and you can answer with a formal review decision that updates task state and preserves findings.

## Constraints

Keep this task limited to review decisions. Do not implement the separate reassign endpoint or heartbeat/lease recovery in this task.

## Implementation Notes

Follow `docs/specs/coordination-api-v1.md` for decision values and event behavior. Make the state mapping explicit in code and tests. If `reassign` is represented as a review decision but the separate reassignment endpoint does not yet exist, document the MVP handling clearly.

## Validation Steps

Run the coordination API test suite and add endpoint tests for accepted, needs_fix, rejected, and invalid decision cases.

## Escalation Rules

Raise an incident if the spec is too ambiguous about how to represent `reassign` before the dedicated reassignment endpoint exists.
