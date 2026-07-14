---
task_id: phase7-worktree-03
phase: phase7-worktree-aware-coordination
status: READY
owner: UNASSIGNED
reviewer: ORCHESTRATOR
priority: medium
dependencies:
  - phase7-worktree-01
  - phase7-worktree-02
allowed_scope:
  - scripts/**
  - docs/operations/**
  - coordination/templates/**
  - coordination/task-board/**
  - tests/** if needed
forbidden_scope:
  - services/coordination_api/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Extend validator or review logic so opted-in worktree-aware tasks can be checked consistently
  - Update operator-facing docs to explain when and how to use branch/worktree provenance
  - Keep non-worktree tasks valid and easy to operate
  - Ensure review guidance explains how provenance affects acceptance
  - Validator passes cleanly after the change
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---

# Task Packet

## Objective

Close the first worktree-aware wave by teaching the validator, reviewer guidance, and operator docs how to reason about branch and worktree provenance without weakening the existing repo-first workflow.

## Context

Once metadata and dispatch support exist, the system still needs review and operator clarity. Without that, branch/worktree fields become passive notes instead of meaningful coordination state.

## Constraints

Do not turn worktree provenance into a hard requirement for every task. The new rules should apply to tasks that opt in, while preserving simple repo-first operation for the rest of the system.

## Implementation Notes

Likely touchpoints include validator rules, review guidance, daily orchestration docs, and possibly the multi-computer setup guide. Keep the operator story concise and example-driven.

## Validation Steps

Run `python scripts/orchestrate.py validate`. Confirm both ordinary tasks and worktree-aware tasks validate correctly. Manually check that reviewer/operator docs explain what to verify before acceptance.

## Escalation Rules

Raise an incident if the validator cannot distinguish optional provenance from required provenance cleanly, or if review expectations would become ambiguous for existing tasks.
