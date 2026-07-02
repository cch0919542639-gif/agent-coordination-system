---
task_id: example-ref-01
phase: example-demo
status: READY
owner: UNASSIGNED
reviewer: ORCHESTRATOR
priority: medium
dependencies: []
allowed_scope:
  - docs/**
  - coordination/**
forbidden_scope:
  - src/**
  - services/**
  - scripts/**
  - database/**
acceptance:
  - Describe what measurable outcome this task must produce
  - List each acceptance criterion separately
expected_artifacts:
  - code_changes
  - report
---

# Task Packet

## Objective

Describe exactly what this task must accomplish. Be specific enough that an agent can execute without guessing.

Example: *Create a markdown report listing all coordination API endpoints with their HTTP methods, paths, and expected response shapes.*

## Context

List the relevant background, linked specs, or backbone references.

Example: *The API is defined in `docs/specs/coordination-api-v1.md`. The routes are implemented in `services/coordination_api/routes.py`.*

## Constraints

State the rules the agent must obey.

Example: *Do not modify any Python source code. Do not read or write to the database. All output must be plain markdown.*

## Implementation Notes

List any important implementation hints, dependencies, or assumptions.

Example: *Use the existing endpoint documentation in the source code comments. Cross-reference with the routes file to ensure no endpoint is missed.*

## Validation Steps

Describe how the agent should verify the result before submission.

Example: *Confirm every endpoint listed in `routes.py` appears in the report. Confirm HTTP methods match. Confirm response shapes match the API spec.*

## Escalation Rules

State when the agent must stop and raise an incident instead of continuing.

Example: *Raise an incident if the routes file or API spec is missing. Raise an incident if the required information cannot be found in the allowed scope.*
