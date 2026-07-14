---
task_id: phase8-profile-02
phase: phase8-profile-layer
status: DONE
owner: external-agent-docs-02
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase8-profile-01
allowed_scope:
  - profiles/**
  - docs/operations/**
  - coordination/templates/**
  - tests/** if needed
forbidden_scope:
  - services/coordination_api/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Create the first rental-rebuild profile instance using the approved schema
  - Express rental-rebuild-specific task format and artifact conventions without changing global defaults
  - Make role mapping and branch/PR expectations explicit and reviewable
  - Document any unresolved gaps that still require core-engine support
  - Validator passes cleanly after the change
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---
# Task Packet

## Objective

Create the first concrete project profile for `rental-rebuild` so the system can support that project's conventions without turning them into universal rules.

## Context

You already identified several rental-rebuild-specific needs with strategic value:

- markdown-oriented task conventions
- project-specific specialist roles
- distinct artifact mapping such as `completed/` and `handoffs/`
- branch/PR lifecycle expectations

Those are useful, but they belong in a project profile rather than in the core engine itself.

## Constraints

This task depends on `phase8-profile-01`. Do not invent a schema. Use the approved or frozen profile structure from that task. Do not change the global coordination defaults to fit rental-rebuild.

## Implementation Notes

Likely outputs include a `profiles/rental-rebuild/` directory, a profile document or config file, and short operator notes explaining what differs from the default profile. It is acceptable to mark some behaviors as "declared but not yet enforced" if the current scripts do not yet consume that rule directly.

## Validation Steps

Run `python scripts/orchestrate.py validate`. Manually verify that the resulting profile makes rental-rebuild conventions explicit without altering existing non-profile tasks or default coordination artifacts.

## Escalation Rules

Raise an incident if the schema from `phase8-profile-01` is still ambiguous, or if rental-rebuild needs a core-engine capability that cannot be represented safely as a profile declaration yet.
