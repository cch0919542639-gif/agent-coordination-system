---
task_id: phase8-profile-01
phase: phase8-profile-layer
status: DONE
owner: external-agent-architecture-01
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase7-worktree-03
allowed_scope:
  - docs/operations/**
  - profiles/**
  - scripts/**
  - coordination/templates/**
  - tests/** if needed
forbidden_scope:
  - services/coordination_api/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Define a first profile schema for project-specific coordination behavior
  - Clearly separate core engine rules from project-specific policy
  - Identify which current behaviors remain global defaults versus profile overrides
  - Document how task format, role mapping, artifact mapping, and branch/PR policy fit into the schema
  - Validator passes cleanly after the change
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---
# Task Packet

## Objective

Define the first profile-layer backbone so this coordination system can stay multi-project capable while supporting project-specific execution rules.

## Context

Current strategy notes already point to the same conclusion: rental-rebuild compatibility should not rewrite the core coordination engine. Instead, project-specific task formats, role names, artifact locations, and branch/PR expectations should be expressed through a project profile layer.

## Constraints

Do not hardcode rental-rebuild behavior into the global defaults. Keep the first version additive and documentation-first if needed. If validator/script implementation is too large for one pass, define the schema and explicit follow-up hooks rather than overbuilding.

## Implementation Notes

Likely touchpoints include a new `profiles/` directory structure, one or more operations docs describing the schema, and possibly limited script/validator scaffolding if the design is stable enough. The schema should at least cover:

- task card format policy
- role mapping
- artifact mapping
- branch/PR policy
- optional worktree-related policy

## Validation Steps

Run `python scripts/orchestrate.py validate`. Manually confirm the resulting design keeps default behavior intact while making project-specific overrides explicit and reviewable.

## Escalation Rules

Raise an incident if the schema cannot cleanly separate core behavior from project-specific policy, or if adopting profile support would require a breaking migration of existing coordination artifacts.
