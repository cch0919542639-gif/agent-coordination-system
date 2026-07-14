---
task_id: phase9-profile-runtime-02
phase: phase9-profile-runtime
status: DONE
owner: external-agent-platform-17
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase9-profile-runtime-01
allowed_scope:
  - scripts/**
  - docs/operations/**
  - tests/** if needed
forbidden_scope:
  - services/coordination_api/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Extend dispatch flow with an explicit profile reference or context
  - Make dispatch output show which profile is being applied and what remains manual
  - Preserve current task lifecycle and repo-first evidence model
  - Do not overclaim support for automatic profile path remapping unless actually implemented
  - Validator passes cleanly after the change
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---
# Task Packet

## Objective

Teach dispatch about explicit profile context so the orchestrator can say "this task is being run under profile X" without pretending the whole engine is already fully profile-native.

## Context

Phase 8 examples exposed a gap: operators need profile context during dispatch, but the current scripts do not expose it. This task closes that gap in a controlled way.

## Constraints

Do not silently change where task cards live unless the scripts genuinely support it. The first version may be metadata/message-level support rather than full path remapping. Keep current repo-first task flow intact.

## Implementation Notes

Likely touchpoints include `dispatch_task.py`, `orchestrate.py`, script docs, and focused tests. Good outcomes include:

- `--profile` flag or equivalent
- profile mention in dispatch output
- clear wording about supported versus manual follow-up

## Validation Steps

Run `python scripts/orchestrate.py validate`. Demonstrate dispatch with and without a profile context. Confirm ordinary non-profile tasks still dispatch cleanly.

## Escalation Rules

Raise an incident if the requested dispatch behavior depends on profile path remapping that is not yet stable, or if a profile context would mislead workers about automation that does not exist.
