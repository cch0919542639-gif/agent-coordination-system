---
task_id: multi-provider-monitor-failures-01
phase: agent-control-center
status: REVIEW
owner: ORCHESTRATOR
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - scripts/console_monitor.py
  - scripts/worker_process_guard.py
  - scripts/console_setup.py
  - tests/scripts/test_console_monitor.py
  - coordination/task-board/**
  - coordination/delivery/multi-provider-monitor-failures-01-delivery-report.md
  - PROGRESS.md
forbidden_scope:
  - actual user credentials or live monitor state
  - automatic merge push and publication
acceptance:
  - Identify the cause of both monitor tests failing on candidate and baseline.
  - Fix product or tests only when supported by isolated evidence.
  - Validate independently with disposable fixtures and report residual risk.
expected_artifacts:
  - investigation
  - tests
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective
Investigate two monitor startup regressions observed during multi-provider testing.

## Context
Two real Windows supervisor tests failed on the candidate and unchanged baseline.

## Implementation Notes
Use isolated synthetic test data; preserve monitoring semantics and user sessions.

## Escalation Rules
Record environmental dependencies and unsupported failure modes without guessing.

## Constraints
Do not access user monitor secrets or interrupt existing sessions.

## Validation Steps
Reproduce, fix the confirmed root cause and rerun affected tests.
