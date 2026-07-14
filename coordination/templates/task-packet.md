---
task_id: TASK-ID-HERE
phase: PHASE-ID-HERE
status: READY
owner: UNASSIGNED
reviewer: ORCHESTRATOR
priority: medium
dependencies: []
allowed_scope:
  - path/to/allowed/**
forbidden_scope:
  - path/to/forbidden/**
acceptance:
  - Define measurable acceptance criterion 1
  - Define measurable acceptance criterion 2
expected_artifacts:
  - code_changes
  - report
execution_mode: REPO_FIRST
branch: OPTIONAL-FOR-WORKTREE
worktree_path: OPTIONAL-FOR-WORKTREE
machine_id: OPTIONAL-FOR-DISTRIBUTED-RUNS
---

# Task Packet

## Objective

Describe exactly what this task must accomplish.

## Context

List the relevant background, linked specs, or backbone references.

## Constraints

State the rules the agent must obey.

## Implementation Notes

List any important implementation hints, dependencies, or assumptions.

## Validation Steps

Describe how the agent should verify the result before submission.

## Escalation Rules

State when the agent must stop and raise an incident instead of continuing.

## Optional Worktree Provenance

Use these front matter fields only when the task opts into worktree-aware execution:

- `execution_mode`: `REPO_FIRST` or `WORKTREE`
- `branch`: expected working branch for the task
- `worktree_path`: expected local worktree path
- `machine_id`: optional machine or runner identifier when the work is tied to a specific computer

Rules:

- existing repo-first tasks may omit these fields entirely
- `WORKTREE` tasks should set `branch` and `worktree_path`
- `machine_id` is optional unless the project or task explicitly requires machine pinning
