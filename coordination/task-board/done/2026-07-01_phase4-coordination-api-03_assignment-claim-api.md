---
task_id: phase4-coordination-api-03
phase: phase4-coordination-api-wave1
status: DONE
owner: external-agent-platform-03
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase4-coordination-api-02
allowed_scope:
  - services/coordination_api/**
  - tests/coordination_api/**
  - docs/specs/coordination-api-v1.md
  - docs/operations/**
  - coordination/**
forbidden_scope:
  - dashboard UI
  - notification layer
  - repo-sync worker
acceptance:
  - Add assign, poll-assigned-work, and claim endpoints for the coordination API MVP
  - Enforce task-state transitions and assignment ownership rules
  - Add tests for success and invalid-ownership paths
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Implement the first real orchestration loop endpoints so assigned work can be discovered and claimed through the control plane.

## Context

This is the first high-value automation slice. Once assign, poll, and claim work reliably, the system stops depending on you to relay every task start manually.

## Constraints

Keep this task limited to assignment discovery and claim behavior. Do not expand into progress, incidents, submissions, or review endpoints yet.

## Implementation Notes

Align request and response shapes with `docs/specs/coordination-api-v1.md`. The important part is ownership enforcement, valid state transitions, and traceable event creation.

## Validation Steps

Run the service test suite and add focused endpoint tests covering successful assignment/claim flows plus invalid claim attempts.

## Escalation Rules

Raise an incident if ownership or task-state rules in the API spec are too ambiguous to implement safely without first clarifying the contract.
