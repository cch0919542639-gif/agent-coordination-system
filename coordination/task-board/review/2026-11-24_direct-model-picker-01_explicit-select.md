---
task_id: direct-model-picker-01
phase: agent-control-center
status: REVIEW
owner: ORCHESTRATOR
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - web/static/**
  - tests/scripts/test_direct_model.py
  - coordination/task-board/**
  - coordination/delivery/direct-model-picker-01-delivery-report.md
  - PROGRESS.md
forbidden_scope:
  - credentials and private transcripts
  - automatic merge push and publication
acceptance:
  - Provide an explicit model dropdown sourced from the selected privacy catalog.
  - Preserve manual model ID input and privacy catalog reset.
  - Test selection and changing privacy without accessing credentials.
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective
Make the OpenRouter model list visibly selectable after the user reported that
the browser input suggestions did not appear.

## Context
The earlier datalist did not expose a visible list in the user browser.

## Implementation Notes
Keep a manual ID field alongside the privacy-filtered native select.

## Escalation Rules
Report provider errors and leave the task in review until validated.

## Constraints
Do not expose credentials, inspect private transcripts, or interrupt existing work.

## Validation Steps
Run direct-model tests, JavaScript syntax and coordination validation.
