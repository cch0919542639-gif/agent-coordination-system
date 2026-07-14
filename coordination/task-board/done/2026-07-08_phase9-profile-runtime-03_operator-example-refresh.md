---
task_id: phase9-profile-runtime-03
phase: phase9-profile-runtime
status: DONE
owner: external-agent-live-04
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase9-profile-runtime-01
  - phase9-profile-runtime-02
allowed_scope:
  - docs/operations/**
  - profiles/**
  - coordination/task-board/**
  - coordination/templates/**
forbidden_scope:
  - services/coordination_api/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Refresh examples and operator notes so they match the implemented profile runtime support
  - Clearly separate current supported behavior from future-state hooks
  - Keep review-flow guidance aligned with the actual review protocol
  - Make the docs safe to use as real operator instructions
  - Validator passes cleanly after the change
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---
# Task Packet

## Objective

Close the documentation/runtime gap by updating operator examples after the validator and dispatch layers gain first-pass profile support.

## Context

Phase 8 examples were valuable, but they got ahead of actual runtime support. This task refreshes those examples so they become safe, real operator guidance instead of partly future-state sketches.

## Constraints

Do not invent capabilities that validator/dispatch do not actually implement. Keep review outcome guidance aligned with the current protocol unless the underlying scripts are changed first.

## Implementation Notes

Likely outputs include revised examples, dispatch notes, review notes, and possibly a short runtime-usage guide that explains what profile support exists now versus what still remains deferred.

## Validation Steps

Run `python scripts/orchestrate.py validate`. Manually confirm that an operator following the refreshed docs would not be misled into using unsupported paths or review transitions.

## Escalation Rules

Raise an incident if current runtime support is still too thin to produce safe operator instructions, or if the docs reveal missing script behavior that should be promoted into a new backbone task first.
