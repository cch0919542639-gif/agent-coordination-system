---
task_id: phase4-coordination-api-13
phase: phase4-coordination-api-wave3
status: DONE
owner: external-agent-platform-13
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase4-coordination-api-01
  - phase4-coordination-api-11
allowed_scope:
  - services/coordination_api/**
  - tests/**
  - docs/operations/**
  - docs/specs/coordination-api-v1.md
  - coordination/**
  - requirements.txt
forbidden_scope:
  - dashboard UI
  - repo sync redesign
  - cloud/infra overbuild
  - unrelated domains
acceptance:
  - API key enforcement clearly configurable via env vars and documented
  - Coordination API runs with explicit base URL, port, DB path, and API key settings
  - Startup/usage guide added as docs/operations/coordination-api-startup-guide.md
  - Auth-required and auth-disabled modes covered by tests
  - Workflow semantics unchanged unless strictly required
  - Validator passes cleanly
  - All existing tests still pass
  - Create/update delivery report
expected_artifacts:
  - code_changes
  - tests
  - docs
  - delivery_report
---
# Task Packet

## Objective

Harden runtime configuration and authentication for the coordination API so it is ready for internal live use.

## Context

The coordination API currently has an auth skeleton that is disabled by default. Settings for host, port, DB path, and API keys exist but are not fully documented. Before the API can be used in a live internal deployment, these settings must be clearly configurable, tested, and documented.

## Constraints

Do not change workflow semantics (state transitions, event shapes, response formats). Stay within allowed scope.

## Implementation Notes

Focus on config surface area, documentation, and test coverage. The existing auth middleware is functionally correct but needs test coverage for both enabled and disabled modes and a startup guide for operators.

## Validation Steps

Run the auth test suite, the full coordination API test suite, and the validator.

## Escalation Rules

Raise an incident if the config surface requires changes outside allowed scope or if auth hardening conflicts with the agent CLI design.
