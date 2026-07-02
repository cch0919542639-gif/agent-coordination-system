---
task_id: phase4-coordination-api-09
phase: phase4-coordination-api-wave2
status: DONE
owner: external-agent-platform-09
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase4-coordination-api-05
allowed_scope:
  - services/coordination_api/**
  - tests/coordination_api/**
  - docs/specs/coordination-api-v1.md
  - coordination/**
forbidden_scope:
  - heartbeat recovery
  - repo sync
  - dashboard UI
  - unrelated domains
acceptance:
  - Add POST /incidents/{incidentId}/resolve to close open incidents
  - Validate resolver_id and that the incident exists and is open
  - Update incident status to resolved with resolution_summary, resolver_id, and resolved_at
  - Create an incident_resolved event linked to the incident's task
  - Add focused tests for success and invalid paths
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
---
# Task Packet

## Objective

Implement incident resolution so open blockers can be formally closed by the orchestrator through the coordination API.

## Context

The open incident endpoint already creates structured blocker records. The missing piece is formal resolution so the orchestrator can close incidents and document the outcome.

## Constraints

Keep this task limited to incident resolution. Do not expand into heartbeat recovery, repo sync, or dashboard UI.

## Implementation Notes

Follow `docs/specs/coordination-api-v1.md` for request shape and behavior. The endpoint accepts `resolver_id` and `resolution_summary`, updates the incident record, and creates an `incident_resolved` event.

## Validation Steps

Run the coordination API test suite and add endpoint tests covering successful resolution, nonexistent incident, already-resolved incident, and missing resolver_id.

## Escalation Rules

Raise an incident if the spec is too ambiguous about whether resolution should auto-close the task or just update the incident state.
