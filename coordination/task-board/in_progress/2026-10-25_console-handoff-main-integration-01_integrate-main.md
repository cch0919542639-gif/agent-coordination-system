---
task_id: console-handoff-main-integration-01
phase: console-handoff-01
status: IN_PROGRESS
owner: ORCHESTRATOR
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - console-main-readiness-01
  - console-handoff-review-01
allowed_scope:
  - .gitattributes
  - PROGRESS.md
  - docs/operations/console-download-guide.md
  - docs/operations/console-release-status.md
  - coordination/evidence/console-release-01/**
  - coordination/evidence/console-handoff-main-integration-01/**
  - coordination/delivery/console-handoff-main-integration-01-delivery-report.md
forbidden_scope:
  - new product logic or test edits without concrete failing evidence
  - main merge before required live dual-machine gate
  - live credentials permission changes provider runner watch or schedule activation
acceptance:
  - Integrate exact mainc3682d3 into PR9a82c5a7 without history rewrite or lost guards.
  - Resolve only five publication metadata conflicts and prove product/test blobs equal the union of accepted parents.
  - Preserve both parents acceptance snapshots, refresh portable pins and task count.
  - Run bounded core/legacy and handoff-specific regressions with native exits logs JUnit.
  - Verify a clean clone and publish a fast-forward PR9 candidate targeting main while retaining draft and live-pilot gates.
expected_artifacts:
  - delivery_report
  - verification_evidence
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Advance PR9 onto current main and prepare a verifiable integrated candidate.

## Context

User requested the next step after reviewed PR6 main promotion. Mainc3682d3
contains accepted entry guards and console; featurea82c5a7 contains independently
accepted handoff source1feeca7. Both parents remain recoverable in merge history.

## Constraints

No new external model call. Reuse accepted code; this is deterministic integration
and metadata verification. Preserve original failed tests and optional harness
limits. Do not imply synthetic peers prove a real two-computer/provider pilot.

## Implementation Notes

Merge normally; do not rebase or force-push. Conflicts are attributes, manifest,
verification summary, guide and release status. Preserve scopes and guard behavior.

## Validation Steps

Two isolated bounded invocations: eight core/legacy files and two handoff files,
each up to300seconds. Check raw/blob pins, parent composition, canonical reviews,
board validator and fresh clone. Only harmless local Git/runner fixtures.

## Escalation Rules

Stop publication for unresolved failures, unexpected product deltas or pin mismatch.
Keep PR9 draft until its real dual-machine acceptance gate is separately completed.
