---
task_id: phase5-live-readiness-02
phase: phase5-live-readiness
status: DONE
owner: external-agent-live-02
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase5-live-readiness-01
allowed_scope:
  - scripts/**
  - docs/operations/**
  - coordination/**
  - tests/**
forbidden_scope:
  - dashboard UI
  - new API features
  - cloud/infra overbuild
  - unrelated domains
acceptance:
  - Small smoke-test helper script for coordination API created
  - Covers health, auth, basic lifecycle, incident path, heartbeat path, and repo-sync invocation
  - Script is safe for internal trial use only
  - Concise operator usage documentation added
  - Validator passes cleanly
  - All existing tests still pass
  - Create/update delivery report
expected_artifacts:
  - code_changes
  - docs
  - tests
  - delivery_report
---
# Task Packet

## Objective

Create a launch-day smoke-test helper so the orchestrator can run internal trial checks with fewer manual copy-paste steps.

## Context

The live-readiness checklist (phase5-live-readiness-01) defines a smoke-test sequence as curl commands. Automating those checks into a script reduces operator effort and catches regressions faster.

## Constraints

Keep the script safe for internal trial use. Do not add new API features, dashboard UI, cloud infrastructure, or unrelated domains.

## Implementation Notes

Create `scripts/smoke_test_coordination.py` as a standalone script. Use httpx for HTTP calls. Follow the same env-var convention as the agent CLI. Print clear pass/fail output for each check.

## Validation Steps

Run the smoke-script tests. Run the full coordination API test suite. Run the validator.

## Escalation Rules

Raise an incident if the script requires changes outside allowed scope or conflicts with the existing coordination API structure.
