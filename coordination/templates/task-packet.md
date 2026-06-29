---
task_id: TASK-ID-HERE
phase: PHASE-ID-HERE
status: READY
owner: UNASSIGNED
reviewer: ORCHESTRATOR
priority: medium
dependencies: []
allowed_scope:
  - path/to/allowed/**
forbidden_scope:
  - path/to/forbidden/**
acceptance:
  - Define measurable acceptance criterion 1
  - Define measurable acceptance criterion 2
expected_artifacts:
  - code_changes
  - report
---

# Task Packet

## Objective

Describe exactly what this task must accomplish.

## Context

List the relevant background, linked specs, or backbone references.

## Constraints

State the rules the agent must obey.

## Implementation Notes

List any important implementation hints, dependencies, or assumptions.

## Validation Steps

Describe how the agent should verify the result before submission.

## Escalation Rules

State when the agent must stop and raise an incident instead of continuing.

