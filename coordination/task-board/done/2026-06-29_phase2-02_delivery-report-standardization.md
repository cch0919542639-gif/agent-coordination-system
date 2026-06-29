---
task_id: phase2-02
phase: phase2-productionization
status: DONE
owner: external-agent-tools-02
reviewer: ORCHESTRATOR
priority: high
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
  - Standardize what a delivery report must contain for future tasks
  - Add or update a delivery report template in the repo
  - Update docs or validator support so the standard is clear and harder to skip
  - Keep the existing validator runnable with the same command
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---

# Task Packet

## Objective

Tighten the weakest gap surfaced in Phase 1 by making delivery-report expectations explicit and harder to omit.

## Context

Several accepted pilot tasks succeeded without a separate delivery report artifact even when the task packet listed one. This task should reduce that ambiguity for future phases.

## Constraints

Keep the change bounded. Do not redesign the whole workflow or introduce external dependencies.

## Implementation Notes

Possible approaches include:

- adding a delivery report template
- documenting when it is mandatory
- extending validator support if the rule can be enforced cleanly

## Validation Steps

Run:

```bash
python scripts/validate_coordination_files.py
```

Document what the new delivery-report standard is and how future agents should comply.

## Escalation Rules

Raise an incident if enforcing the standard requires protocol changes broader than this task allows.
