---
task_id: phase6-lead-agent-01
phase: phase6-lead-agent-automation
status: DONE
owner: external-agent-platform-14
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - scripts/**
  - coordination/templates/**
  - docs/operations/**
  - coordination/task-board/**
  - tests/** if a lightweight script test is added
forbidden_scope:
  - services/coordination_api/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Add an `orchestrate.py intake` path that can generate a draft phase intake artifact from CLI input
  - Define a stable output location and filename convention for generated intake drafts
  - Support at least objective, scope, dependencies, and candidate task decomposition inputs
  - Document usage and constraints for the new intake command
  - Validator passes cleanly after the change
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---
# Task Packet

## Objective

Implement the first usable version of `python scripts/orchestrate.py intake` so the lead agent can convert a user requirement into a draft repo-backed phase intake without hand-writing the whole markdown file.

## Context

The repo already has a phase intake template at `coordination/templates/phase-intake.md`, a real-project intake guide at `docs/operations/real-project-intake-guide.md`, and a unified script entrypoint at `scripts/orchestrate.py`. What is missing is a script-assisted intake command that reduces manual orchestration work.

## Constraints

Keep the first version simple and deterministic. Do not add network calls, LLM dependencies, or coordination API changes. Favor a template-driven draft generator over ambitious automation.

## Implementation Notes

You may add a dedicated helper script and wire it into `scripts/orchestrate.py`. The command should be useful from day one even if some fields are still manually edited after generation. If adding tests feels disproportionately heavy, document the manual validation path clearly.

## Validation Steps

Run `python scripts/orchestrate.py validate`. Demonstrate the new command with a sample intake draft and confirm the output matches the phase-intake template structure.

## Escalation Rules

Raise an incident if the desired CLI contract conflicts with existing script conventions, or if generating draft task decomposition requires assumptions that cannot be expressed safely in a deterministic first version.
