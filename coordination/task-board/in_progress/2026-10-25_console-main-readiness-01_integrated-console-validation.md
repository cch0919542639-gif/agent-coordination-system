---
task_id: console-main-readiness-01
phase: console-delivery-01
status: IN_PROGRESS
owner: ORCHESTRATOR
reviewer: ORCHESTRATOR
priority: high
dependencies:
  - console-entry-guards-01
allowed_scope:
  - .gitattributes
  - PROGRESS.md
  - docs/operations/console-download-guide.md
  - docs/operations/console-release-status.md
  - coordination/evidence/console-release-01/**
  - coordination/evidence/console-main-readiness-01/**
  - coordination/delivery/console-main-readiness-01-delivery-report.md
forbidden_scope:
  - product logic or test changes
  - live runtime credentials provider activation or schedules
  - PR9 feature integration
acceptance:
  - Preserve reviewed product/test blobs from c3c6a38 and all18 accepted prior snapshots.
  - Refresh current release status and pin two reviewed legacy entry scripts plus three accepted entry-guard snapshots.
  - Run bounded integrated core and legacy entry regressions against final pinned source bytes with logs JUnit and native exit.
  - Verify fresh clone pins imports task count and coordination data before exact-head PR6 merge to main.
expected_artifacts:
  - delivery_report
  - verification_evidence
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Verify PR6 integrated candidate and refresh deterministic publication metadata before
main promotion, following the user's review-then-merge and continue instructions.

## Context

Base c3c6a383297326213b3c9904e9bfcfc3b7264fc6 includes independently accepted
PR10 source and original console/SID reviews. No new product logic is authored here.
ORCHESTRATOR performs deterministic integration evidence checks, not an independent
model code review of its own source. Existing independent source reviews remain authoritative.

## Constraints

Preserve earlier failures and original92e1248/CP950 evidence. Do not claim new
physical-host acceptance or production qualification. Git LF normalization must
preserve product/test blobs. No additional model calls or provider startup.

## Implementation Notes

Update document and manifest metadata only. After successful fixed-source validation,
record acceptance and publish a fast-forward metadata commit to PR6's existing branch.
Merge only after final head/base checks. Retain all source review provenance.

## Validation Steps

One300second eight-file regression invocation; manifest raw/blob verification;
fresh autocrlf clone isolated imports and board count; validators and diff checks.

## Escalation Rules

Stop merge on test failure, source delta, pin mismatch, unexpected branch movement
or conflict. Do not hide a failed check or expand into PR9 integration.
