---
task_id: phase9-profile-runtime-01
phase: phase9-profile-runtime
status: DONE
owner: external-agent-platform-16
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase8-profile-03
allowed_scope:
  - scripts/**
  - profiles/**
  - docs/operations/**
  - tests/** if needed
forbidden_scope:
  - services/coordination_api/**
  - src/**
  - database/**
  - cloud/infra/**
acceptance:
  - Extend validation so profile files are discovered and checked explicitly
  - Enforce profile_name uniqueness, schema_version expectations, and subset constraints for core-defined sets
  - Keep existing coordination validation behavior intact for non-profile artifacts
  - Document what the validator now supports versus what remains deferred
  - Validator passes cleanly after the change
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---
# Task Packet

## Objective

Build the first validator/runtime bridge for the profile layer so profiles are not just declared in docs but also checked by the coordination tooling.

## Context

Phase 8 defined the profile schema and created the first real profile instance, but profile files are still invisible to the validator. This task turns profile syntax and boundary constraints into real checks.

## Constraints

Do not redesign the schema. Implement only the checks already implied by `schema-profile-v1.md` and accepted phase8 decisions. Keep existing task-card validation stable.

## Implementation Notes

Likely work includes `validate_coordination_files.py`, script documentation, and focused tests. Good checks include:

- profile file discovery under `profiles/`
- required top-level fields
- `profile_name` uniqueness
- `schema_version` compatibility
- subset rules for `allowed_statuses` and `allowed_execution_modes`
- path safety for artifact mappings

## Validation Steps

Run `python scripts/orchestrate.py validate`. Add or update focused tests if needed. Confirm invalid sample profiles would be caught conceptually, even if not all failure fixtures are committed into the main tree.

## Escalation Rules

Raise an incident if the accepted schema is too ambiguous to validate safely, or if implementing profile checks would require breaking the current task-card validator contract.
