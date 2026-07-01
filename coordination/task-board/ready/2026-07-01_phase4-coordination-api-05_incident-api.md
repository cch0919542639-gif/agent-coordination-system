---
task_id: phase4-coordination-api-05
phase: phase4-coordination-api-wave2
status: READY
owner: external-agent-platform-05
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
  - heartbeat workers
  - dashboard UI
  - unrelated application domains
acceptance:
  - Add POST /tasks/{taskId}/incidents to the coordination API MVP
  - Create structured incident records linked to tasks and agents
  - Support safe blocked-task transitions and incident events
  - Add focused tests for success and invalid ownership or state paths
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
---
# Task Packet

## Objective

Implement structured blocker reporting so an executing agent can stop safely and raise a first-class incident through the control plane.

## Context

The repo-first process already treats blockers as explicit incidents. The API now needs the same capability so blocked work is visible without waiting for manual message relays.

## Constraints

Keep this task limited to incident creation and blocked-task handling. Do not implement heartbeat recovery, automated notifications, or reviewer resolution flows in this task.

## Implementation Notes

Follow `docs/specs/coordination-api-v1.md` for request shape and behavior. The core behaviors are: create an incident record, preserve agent and task references, and produce a task event. If task status moves to `blocked`, make the rule explicit in tests.

## Validation Steps

Run the coordination API test suite and add focused tests for successful incident creation plus invalid owner, invalid task state, or missing task cases.

## Escalation Rules

Raise an incident if the spec is not clear enough on whether incident creation is allowed only for the assigned owner or also for an orchestrator client.
