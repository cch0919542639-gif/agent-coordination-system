---
task_id: phase5-live-readiness-01
phase: phase5-live-readiness
status: DONE
owner: external-agent-live-01
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase4-coordination-api-13
allowed_scope:
  - docs/operations/**
  - docs/specs/**
  - coordination/**
  - scripts/**
forbidden_scope:
  - dashboard UI
  - new API features
  - cloud/infra overbuild
  - unrelated domains
acceptance:
  - Live-readiness checklist created
  - First-run operator checklist created
  - Required environment variables and startup order documented in one concise operator-facing doc
  - Minimal smoke-test sequence defined for internal launch day
  - Rollback / stop conditions documented for first live trial
  - Validator passes cleanly
  - Create/update delivery report
expected_artifacts:
  - code_changes
  - docs
  - delivery_report
---
# Task Packet

## Objective

Prepare a first internal live-readiness package for the coordination system so the orchestrator can run a controlled internal trial with minimal setup risk.

## Context

The coordination API has been built, hardened, and tested through phase4-coordination-api tasks 01–13. The next step is live trial. The orchestrator needs a single operator-facing package that covers readiness checks, startup order, smoke testing, and rollback conditions.

## Constraints

Do not add new API features, dashboard UI, cloud infrastructure, or unrelated domains. Keep the package concise and actionable.

## Implementation Notes

Create the readiness checklist as one comprehensive doc. Reference existing docs (startup guide, API spec, rollout guide) rather than duplicating them. The smoke-test sequence should be a copy-pasteable curl sequence.

## Validation Steps

Run the validator. Confirm all existing tests still pass.

## Escalation Rules

Raise an incident if the readiness package requires changes outside allowed scope or conflicts with existing operational docs.
