---
task_id: phase5-live-trial-01
phase: phase5-live-trial
status: DONE
owner: external-agent-live-02
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - phase5-live-readiness-02
allowed_scope:
  - docs/operations/**
  - coordination/**
  - scripts/** only if a tiny helper is strictly needed
forbidden_scope:
  - dashboard UI
  - new API features
  - unrelated domains
  - cloud/infra overbuild
acceptance:
  - Live-trial execution sheet/checklist created
  - Exact pilot sequence for one real task from dispatch to review defined
  - What to record during the pilot (timings, failures, manual interventions, incidents, review latency) defined
  - Post-trial retrospective template added
  - Delivery report created/updated
  - Validator passes cleanly
expected_artifacts:
  - docs
  - delivery_report
---
# Task Packet

## Objective

Prepare the first internal live-trial execution packet so the orchestrator can run a real pilot session and capture results consistently.

## Context

Phase5-live-readiness-01 delivered the readiness checklist and first-run operator checklist. Phase5-live-readiness-02 delivered the automated smoke-test helper. The next step is to package everything into a concrete trial execution sheet that guides the orchestrator through a single pilot task from dispatch to review, with structured recording and a retrospective template.

## Constraints

Do not add new API features, dashboard UI, cloud infrastructure, or unrelated domains. A tiny helper script is allowed only if strictly necessary.

## Implementation Notes

Create `docs/operations/coordination-live-trial-execution-sheet.md` as the single operator-facing trial execution document. Reference existing docs rather than duplicating them. Include a recording log table and a post-trial retrospective template.

## Validation Steps

Run the validator. Confirm all existing tests still pass.

## Escalation Rules

Raise an incident if the execution packet requires changes outside allowed scope or conflicts with existing operational docs.
