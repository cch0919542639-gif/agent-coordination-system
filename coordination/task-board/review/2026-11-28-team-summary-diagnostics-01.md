---
task_id: team-summary-diagnostics-01
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
  - coordination/delivery/**
  - coordination/incidents/**
  - coordination/reviews/**
  - PROGRESS.md
forbidden_scope:
  - real credentials or private transcripts
  - modification of the running console or existing worktrees during testing
  - automatic merge push or publication
acceptance:
  - Diagnose the observed summary failure from available evidence without claiming unknown causes.
  - Fix reproducible summary failure handling while preserving partial worker results.
  - Surface only fixed safe categories without raw provider data or secrets.
  - Validate provider failure timeout incomplete output and successful summarization.
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
execution_mode: REPO_FIRST
---
# Team summary failure diagnosis

## Objective
Investigate the first three-agent summary failure and repair supported causes.

## Context
All workers completed; a first summary failed, and a shorter later run succeeded.
The first failure's specific error was discarded before the later run replaced it.

## Implementation Notes
Keep provider information sanitized and preserve current model/privacy settings.

## Constraints
Do not inspect credentials or private transcripts; use isolated synthetic tests.

## Escalation Rules
Report unrecoverable historical details as unknown instead of inventing causes.

## Validation Steps
Exercise failure and success paths and credential redaction in disposable fixtures.
