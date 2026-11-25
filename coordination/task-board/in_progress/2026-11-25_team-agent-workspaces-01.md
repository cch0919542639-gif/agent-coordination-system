---
task_id: team-agent-workspaces-01
phase: agent-control-center
status: IN_PROGRESS
owner: ORCHESTRATOR
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - web/**
  - tests/scripts/**
  - docs/operations/agent-control-center-guide.md
  - coordination/task-board/**
  - coordination/incidents/**
  - coordination/delivery/team-agent-workspaces-01-delivery-report.md
  - PROGRESS.md
  - DECISIONS.md
forbidden_scope:
  - user credentials and private transcripts
  - changes to running installation or actual user projects during tests
  - automatic merge push or publication
acceptance:
  - Integrate OpenCode and supported Hermes sessions into automatic multi-agent work alongside direct models.
  - Use explicitly selected workspaces and preserve actual work while preventing false claims of isolation.
  - Expose real progress results and any required permission requests to the operator.
  - Preserve existing provider privacy stop cleanup and authorization boundaries.
  - Verify with isolated workspaces and synthetic agents and document actual runtime limitations.
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective
Support real workspace work by OpenCode and Hermes in the automatic multi-agent team.

## Context
Direct models currently provide text-only work. OpenCode returned a reply in the live console; Hermes installed gateway is currently blocked by existing safety guards.

## Implementation Notes
Use existing owned native ACP sessions and preserve operator-controlled approval; do not claim OS-level sandboxing.

## Escalation Rules
If current Hermes gateway cannot support the existing protection boundaries, report it and keep fail-closed behavior.

## Constraints
Do not read credentials or private user conversations. Do not alter the running console during development.

## Validation Steps
Exercise simulated worker model assignments, workspace paths, permissions, stop and cleanup in disposable fixtures.
