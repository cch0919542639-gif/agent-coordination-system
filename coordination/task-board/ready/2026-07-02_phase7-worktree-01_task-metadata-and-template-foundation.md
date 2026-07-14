---
task_id: phase7-worktree-01
phase: phase7-worktree-aware-coordination
status: READY
owner: UNASSIGNED
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - coordination/templates/**
  - coordination/task-board/**
  - scripts/**
  - docs/operations/**
  - tests/** if needed
forbidden_scope:
  - services/coordination_api/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Define how task packets represent optional branch and worktree provenance
  - Keep existing tasks valid even if they do not use worktree-aware fields
  - Document the semantics of each new field and when it is optional vs required
  - Add only the minimum validator or template support needed for the metadata foundation
  - Validator passes cleanly after the change
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---

# Task Packet

## Objective

Create the metadata and template foundation for worktree-aware coordination so later dispatch and review automation can attach branch and worktree provenance consistently.

## Context

The current coordination system tracks owner, reviewer, scope, and lifecycle state, but it does not yet capture which git branch or worktree a worker is expected to use. The roadmap in `docs/operations/orca-comparison-and-roadmap.md` identifies this as the next high-leverage upgrade.

## Constraints

Do not force a breaking migration across all existing task cards. The new metadata must be optional unless a task explicitly opts into worktree-aware execution. Keep the first version repo-first and deterministic.

## Implementation Notes

Likely touchpoints include the task packet template, validator rules, and one or more operator docs describing the new fields. Favor a small number of well-named fields over many speculative ones.

## Validation Steps

Run `python scripts/orchestrate.py validate`. Confirm existing task cards still validate. Confirm the updated template and any example task cards clearly show how branch/worktree metadata should be used.

## Escalation Rules

Raise an incident if the field design creates ambiguity between task ownership and machine/worktree ownership, or if a non-breaking introduction cannot be achieved safely.
