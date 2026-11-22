---
task_id: direct-model-privacy-01
phase: agent-control-center
status: REVIEW
owner: ORCHESTRATOR
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - web/**
  - tests/scripts/test_direct_model.py
  - tests/scripts/test_agent_control.py
  - docs/operations/agent-control-center-guide.md
  - coordination/task-board/**
  - coordination/progress/direct-model-privacy.md
  - coordination/evidence/direct-model-privacy-01/**
  - coordination/delivery/direct-model-privacy-01-delivery-report.md
  - PROGRESS.md
  - PLAN.md
forbidden_scope:
  - existing sessions credentials and private transcripts
  - automatic worker dispatch execution merge push and release
acceptance:
  - Default direct model sessions require zero data retention and data collection denial.
  - The user can explicitly select ordinary mode per new session with clear retention and training disclosure.
  - Model catalog matches the selected policy and presents chat-capable models only.
  - Authorization, CSRF, secret handling, monitor read-only and existing clients retain their boundaries.
  - Run focused tests and prepare a locally accessible candidate without interrupting existing sessions.
expected_artifacts:
  - code_changes
  - tests
  - operator_guide
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective
Add an explicit ordinary privacy option for user-initiated direct-model sessions.

## Context
The user chose default zero data retention with an explicit ordinary mode. The
current ZDR-only catalog leaves almost no free chat-capable options and includes
non-chat decision models; free endpoints may also be rate-limited.

## Constraints
Do not downgrade policy implicitly. Keep credentials out of logs and process
arguments. Do not stop existing sessions, change provider account settings, merge,
push or publish. External model use requires user input in the console.

## Implementation Notes
Use a session-bound selection, existing direct-mode integration and narrow tests.
Ordinary mode uses provider/account policies and must disclose potential retention
and training. Model catalog selection does not guarantee route or quota availability.

## Validation Steps
Test default and explicit request payloads, catalog filtering, API roles/CSRF,
UI mode switching, and existing direct-model and monitoring regressions.

## Escalation Rules
Report invalid scope or policy ambiguity; do not claim a successful real model
request without observing the user's actual response.
