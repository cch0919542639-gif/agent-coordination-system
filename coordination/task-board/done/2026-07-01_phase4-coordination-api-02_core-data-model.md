---
task_id: phase4-coordination-api-02
phase: phase4-coordination-api-wave1
status: DONE
owner: external-agent-platform-02
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase4-coordination-api-01
allowed_scope:
  - services/coordination_api/**
  - tests/coordination_api/**
  - docs/specs/coordination-api-v1.md
  - coordination/**
forbidden_scope:
  - dashboard UI
  - agent CLI
  - unrelated application domains
acceptance:
  - Add the core MVP data model for agents, tasks, assignments, events, incidents, reviews, and artifacts
  - Add initial migrations or schema bootstrap
  - Prove the schema initializes cleanly
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Create the durable state model for the coordination control plane so later API endpoints have a real persistence layer to work against.

## Context

The coordination API spec already defines the MVP entities. This task converts that model into runnable database schema and migrations.

## Constraints

Do not broaden into assignment logic or endpoint business rules yet. Keep the task focused on schema design, persistence primitives, and validation that the schema can be created cleanly.

## Implementation Notes

Prefer a migration-backed approach instead of ad hoc table creation. Keep naming and enum choices aligned with `docs/specs/coordination-api-v1.md`.

## Validation Steps

Run the schema or migration checks needed to prove a fresh environment can initialize the core data model successfully.

## Escalation Rules

Raise an incident if the schema design cannot be aligned cleanly with the API spec without first resolving a contract ambiguity.
