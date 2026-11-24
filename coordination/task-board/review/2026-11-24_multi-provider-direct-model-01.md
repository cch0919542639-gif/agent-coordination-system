---
task_id: multi-provider-direct-model-01
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
  - coordination/delivery/multi-provider-direct-model-01-delivery-report.md
  - PROGRESS.md
forbidden_scope:
  - storing or exposing real credentials
  - live external requests without user-provided credentials
  - automatic merge push and publication
acceptance:
  - Support OpenRouter DeepSeek Agnes AI and user-specified HTTPS OpenAI-compatible API endpoints.
  - Bind provider endpoint model and privacy to a direct session without forwarding keys to other agents.
  - Keep OpenRouter zero-retention routing default and do not represent other providers as zero retention.
  - Preserve backwards compatibility and test UI API subprocess and protocol failure paths.
expected_artifacts:
  - code_changes
  - tests
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective
Add multi-provider direct text model calls using provider-specific keys.

## Context
Existing direct sessions only target OpenRouter. The user requested DeepSeek,
Agnes AI, and a custom OpenAI-compatible API in addition.

## Implementation Notes
Never send provider-specific privacy parameters to unrelated providers.

## Escalation Rules
Report unverified live provider capabilities and avoid claims about data retention.

## Constraints
Do not read actual user keys, existing sessions or private transcripts.

## Validation Steps
Test transport, API authorization, subprocess, provider selection and stale views.
