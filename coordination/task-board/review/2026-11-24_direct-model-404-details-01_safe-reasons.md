---
task_id: direct-model-404-details-01
phase: agent-control-center
status: REVIEW
owner: ORCHESTRATOR
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - web/direct_model_bridge.py
  - web/agent_control.py
  - tests/scripts/test_direct_model.py
  - coordination/task-board/**
  - coordination/delivery/direct-model-404-details-01-delivery-report.md
  - PROGRESS.md
forbidden_scope:
  - credentials private transcripts and existing sessions
  - automatic merge push and publication
acceptance:
  - Show safe actionable classifications for supported OpenRouter 404 errors.
  - Do not expose arbitrary provider text credentials prompt data or URLs.
  - Retain generic failure behavior for unrecognized malformed or oversized responses.
  - Test provider boundary and console propagation using isolated fixtures.
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective
Improve direct model HTTP 404 diagnostics while keeping provider data private.

## Context
The bridge currently discards the provider body and only reports HTTP status.

## Implementation Notes
Classify bounded provider messages into a narrow allowlist of fixed explanations.

## Escalation Rules
Report unrecognized errors honestly; do not weaken credential protection.

## Constraints
No real credentials private transcripts or disruption of existing sessions.

## Validation Steps
Run focused direct-model and Agent tests and coordination validation.
