---
task_id: phase1-live-01
phase: phase1-live-pilot
status: DONE
owner: external-agent-docs-01
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - docs/**
  - coordination/**
forbidden_scope:
  - src/**
  - database/**
  - infra/**
acceptance:
  - Create a short onboarding quickstart for external agents joining the repo-first workflow
  - Document the exact first five actions a new agent must take after pulling the repo
  - Include links to the task board, templates, protocol, and validator usage
  - Keep all changes inside docs and coordination folders
expected_artifacts:
  - docs
  - delivery_report
---

# Task Packet

## Objective

Create a concise onboarding quickstart that helps a new external agent begin work correctly with minimal human explanation.

## Context

This is part of the first live GitHub collaboration pilot. The goal is to reduce setup confusion and make the first assignment loop smoother.

## Constraints

Do not modify application code or infrastructure. Keep the document practical and short enough for first-day use.

## Implementation Notes

The quickstart should reference the execution protocol, the readiness concepts, the coordination folder structure, and the validator command.

## Validation Steps

Confirm the document gives a new agent enough information to:

- find an assigned task
- move the task card correctly
- update progress
- raise an incident
- prepare for review

## Escalation Rules

Raise an incident if key onboarding steps are still ambiguous after reading the current coordination docs.
