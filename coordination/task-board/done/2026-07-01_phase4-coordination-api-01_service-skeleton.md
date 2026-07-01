---
task_id: phase4-coordination-api-01
phase: phase4-coordination-api-wave1
status: DONE
owner: external-agent-platform-01
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - services/coordination_api/**
  - tests/coordination_api/**
  - docs/roadmap/coordination-system-implementation-plan.md
  - docs/specs/coordination-api-v1.md
  - coordination/**
forbidden_scope:
  - src/billing/**
  - dashboard UI
  - deployment infrastructure
acceptance:
  - Add a runnable coordination API service skeleton
  - Add a health endpoint
  - Add config loading and API-key auth skeleton
  - Produce a delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Scaffold the coordination API service so the repo has a real starting point for the control-plane MVP.

## Context

The repo already has the coordination protocol, API spec, and implementation plan. What it lacks is the first runnable service shell that later tasks can extend.

## Constraints

Keep this task focused on service scaffolding only. Do not implement the full endpoint set, database schema, or dashboard in this task.

## Implementation Notes

A pragmatic FastAPI-based layout is preferred because it matches the current Python script ecosystem. A good result may include application startup, settings/config, auth skeleton, and a health route with a minimal test.

## Validation Steps

Run the relevant test or startup checks for the new service skeleton and keep the delivery report explicit about what is scaffolded versus what remains for later tasks.

## Escalation Rules

Raise an incident if the repo needs a broader platform or packaging decision before the service skeleton can be created safely.
