---
task_id: phase4-coordination-api-06
phase: phase4-coordination-api-wave2
status: READY
owner: external-agent-platform-06
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase4-coordination-api-03
allowed_scope:
  - services/coordination_api/**
  - tests/coordination_api/**
  - docs/specs/coordination-api-v1.md
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - dashboard UI
  - repo-sync worker
  - notification layer
acceptance:
  - Add POST /tasks/{taskId}/artifacts to register delivery evidence
  - Add POST /tasks/{taskId}/submit to move work into review
  - Enforce minimum evidence or delivery summary rules for submission
  - Add focused tests for success and invalid submission cases
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Implement the evidence-registration and submit-for-review endpoints so agent work can move from execution into formal review with structured delivery metadata.

## Context

Repo artifacts are still the evidence layer, but the control plane now needs explicit references to those artifacts before a task can enter review cleanly.

## Constraints

Keep this task limited to artifact registration and submission behavior. Do not implement review decisions, reassignment, or repo-sync rendering in this task.

## Implementation Notes

Align request and response shapes with `docs/specs/coordination-api-v1.md`. Submission should be intentionally strict enough to avoid empty review handoffs. If you need a minimum rule, prefer the spec's guidance that submission requires at least one artifact or a delivery summary.

## Validation Steps

Run the coordination API test suite and add endpoint tests covering successful artifact registration, successful submit, and invalid submit attempts with missing evidence.

## Escalation Rules

Raise an incident if the spec is too ambiguous on the exact minimum submission evidence rule to implement safely.
