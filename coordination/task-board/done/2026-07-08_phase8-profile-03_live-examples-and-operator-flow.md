---
task_id: phase8-profile-03
phase: phase8-profile-layer
status: DONE
owner: external-agent-live-03
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase7-worktree-03
  - phase8-profile-01
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
  - Create concrete examples showing default-profile and project-profile execution differences
  - Show how lead-agent intake, dispatch, worker execution, and review change under a project profile
  - Keep examples aligned with the approved profile schema and current repo-first evidence model
  - Make the operator flow clear enough to use during real dispatch
  - Validator passes cleanly after the change
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---
# Task Packet

## Objective

Turn the new profile-layer design into operator-ready examples so future live dispatch does not depend on abstract schema docs alone.

## Context

Once the schema exists, operators still need to see how the flow changes in practice:

- what a default-project task looks like
- what a profile-driven task looks like
- what the lead agent needs to read before dispatch
- what the reviewer must verify before acceptance

This task closes that usability gap.

## Constraints

Do not start before `phase8-profile-01` is stable enough to use as the source of truth. This task may run in parallel with `phase8-profile-02` after the schema is frozen, but it must not redefine the schema itself.

## Implementation Notes

Good outputs would include sample task cards, sample profile-aware dispatch/review notes, and a short operations doc comparing default mode versus rental-rebuild-style mode. Keep it example-driven and practical.

## Validation Steps

Run `python scripts/orchestrate.py validate`. Manually verify that an operator could use the examples to dispatch and review one default task and one profile-specific task without guessing the intended flow.

## Escalation Rules

Raise an incident if the schema from `phase8-profile-01` is not stable enough to support examples, or if the examples expose missing profile fields that need backbone changes first.
