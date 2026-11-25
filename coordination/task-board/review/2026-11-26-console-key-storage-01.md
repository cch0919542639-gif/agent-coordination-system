---
task_id: console-key-storage-01
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
  - coordination/delivery/console-key-storage-01-delivery-report.md
  - PROGRESS.md
forbidden_scope:
  - real credentials and private transcripts
  - automatic merge push or publication
acceptance:
  - Optional encrypted local provider key storage for direct and team models.
  - No plaintext key retrieval through console APIs or exposure in model messages.
  - Bind saved credentials to user and exact provider endpoint; provide save and delete.
  - Clearly disclose that same-Windows-account native processes are not isolated.
  - Validate permissions persistence scope and rejection paths with synthetic keys.
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
execution_mode: REPO_FIRST
---
# Key storage

## Objective
Allow users to save provider API keys locally for later use without retyping.

## Context
Current direct and team fields are memory-only. The user requested encrypted
storage; strict OS identity isolation was previously deferred.

## Implementation Notes
Use Windows Credential Manager and do not return stored secrets to the browser.

## Constraints
Never access actual saved user keys during implementation or tests.

## Escalation Rules
If secure storage is unavailable, fail closed and retain manual entry.

## Validation Steps
Use synthetic credentials and isolated fake stores; verify Windows API separately.
