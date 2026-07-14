---
task_id: phase7-worktree-02
phase: phase7-worktree-aware-coordination
status: READY
owner: UNASSIGNED
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase7-worktree-01
allowed_scope:
  - scripts/**
  - coordination/task-board/**
  - docs/operations/**
  - tests/** if needed
forbidden_scope:
  - services/coordination_api/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Extend dispatch flow to support branch/worktree assignment metadata
  - Keep current dispatch behavior working for non-worktree tasks
  - Include worktree provenance in dispatch output when present
  - Document CLI usage and safety expectations for the new dispatch path
  - Validator passes cleanly after the change
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---

# Task Packet

## Objective

Upgrade the dispatch path so the lead agent can assign not just an owner, but also branch and worktree provenance for tasks that opt into worktree-aware execution.

## Context

Phase 6 gave the system a lead-agent-friendly dispatch command and ready-to-send dispatch message generation. The next step is to make that dispatch flow branch/worktree-aware so parallel agents can be isolated more safely and reviewed with clearer provenance.

## Constraints

Do not require actual worktree creation automation unless it is trivial and clearly safe. The first priority is metadata, CLI contract, and dispatch output. Preserve existing dispatch behavior for tasks that remain repo-first only.

## Implementation Notes

The likely home is `dispatch_task.py` plus `orchestrate.py` help text and related operations docs. The best first version may attach fields such as branch name and worktree path without trying to manage the full lifecycle of git worktrees yet.

## Validation Steps

Run `python scripts/orchestrate.py validate`. Demonstrate dispatch on both a normal task and a worktree-aware task. Confirm the message output changes only when the provenance fields are present.

## Escalation Rules

Raise an incident if the dispatch contract depends on metadata not yet settled in `phase7-worktree-01`, or if safe fallback behavior for non-worktree tasks cannot be maintained.
