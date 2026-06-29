---
task_id: phase1-live-02
phase: phase1-live-pilot
status: DONE
owner: external-agent-tools-01
reviewer: ORCHESTRATOR
priority: medium
dependencies: []
allowed_scope:
  - scripts/**
  - docs/**
  - coordination/**
forbidden_scope:
  - src/**
  - database/**
  - infra/**
acceptance:
  - Improve the coordination validator with at least one additional useful check
  - Document the new validation behavior in scripts or docs
  - Keep the script runnable with the existing command
  - Do not break current templates or sample files
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---

# Task Packet

## Objective

Enhance the validator so the repo-first coordination workflow becomes harder to misuse.

## Context

The current validator already checks required sections and labels. This task is intended to test a safe tooling improvement during the first live pilot.

## Constraints

Changes must remain small, understandable, and fully inside scripts/docs/coordination. Do not introduce external dependencies.

## Implementation Notes

Good enhancement examples include:

- validating allowed task status values
- validating review decision values
- checking that sample file names match obvious conventions

Choose one or two small improvements rather than widening scope.

## Validation Steps

Run:

```bash
python scripts/validate_coordination_files.py
```

Document what new rule was added and verify existing sample files still pass.

## Escalation Rules

Raise an incident if the improvement requires changing the coordination protocol itself rather than just validator behavior.
