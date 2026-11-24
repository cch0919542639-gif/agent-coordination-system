---
task_id: parallel-model-orchestration-01
phase: agent-control-center
status: REVIEW
owner: ORCHESTRATOR
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - web/**
  - tests/scripts/**
  - docs/operations/agent-control-center-guide.md
  - coordination/task-board/**
  - coordination/delivery/parallel-model-orchestration-01-delivery-report.md
  - PROGRESS.md
forbidden_scope:
  - actual user credentials or live conversations
  - automatic merge push or publication
acceptance:
  - Allow multiple separately configured direct model workers and an explicit planner.
  - Split an explicitly submitted text task into bounded model assignments and run them concurrently.
  - Display assignments progress independent results and failures without claiming file or command execution.
  - Keep keys session scoped and preserve existing permission privacy and lifecycle boundaries.
  - Validate with isolated fake model providers and prepare independent review.
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective
Enable one user submitted task to be automatically decomposed among multiple direct text models.

## Context
The existing direct model supports only one active instance per login.

## Implementation Notes
No automatic filesystem or shell access is added. Bound tasks and participant counts.

## Escalation Rules
Do not expose credentials or silently claim model output was executed.

## Constraints
Preserve existing runtime and user data; no real provider calls during isolated tests.

## Validation Steps
Exercise planning, parallel execution, partial failures, authorization and cleanup.
