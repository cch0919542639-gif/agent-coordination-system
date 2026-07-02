---
task_id: phase4-coordination-api-08
phase: phase4-coordination-api-wave2
status: DONE
owner: external-agent-platform-08
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase4-coordination-api-07
allowed_scope:
  - services/coordination_api/**
  - tests/coordination_api/**
  - docs/specs/coordination-api-v1.md
  - coordination/**
forbidden_scope:
  - dashboard UI
  - heartbeat recovery
  - repo sync
  - unrelated domains
acceptance:
  - Add POST /tasks/{taskId}/reassign to close the old assignment and create a new one
  - Validate from_agent_id matches the current active assignment
  - Create a task_reassigned event preserving task history
  - Update the review endpoint reassign case to close the old assignment
  - Add focused tests for success and invalid paths
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
---
# Task Packet

## Objective

Implement a real reassignment flow for the coordination API so reassign is no longer only a review-status mapping.

## Context

The review endpoint already maps `reassign` to a status change, but without closing the old assignment or creating a new one. A dedicated endpoint is needed for the orchestrator to move continuation responsibility cleanly.

## Constraints

Keep this task limited to reassignment. Do not expand into incident resolution, heartbeat recovery, or dashboard UI.

## Implementation Notes

Follow `docs/specs/coordination-api-v1.md` for request shape and behavior. The dedicated endpoint accepts `from_agent_id`, `to_agent_id`, and `reason`. It closes the active assignment, creates a new one, sets status to `assigned`, and creates a `task_reassigned` event. Update the review endpoint so its `reassign` decision also closes the old assignment.

## Validation Steps

Run the coordination API test suite and add endpoint tests covering successful reassignment, wrong from_agent, nonexistent agent, nonexistent task, and missing fields.

## Escalation Rules

Raise an incident if the spec is too ambiguous about whether the review endpoint's reassign case should close the old assignment or leave it open.
