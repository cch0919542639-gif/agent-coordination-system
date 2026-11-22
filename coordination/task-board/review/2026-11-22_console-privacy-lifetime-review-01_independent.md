---
task_id: console-privacy-lifetime-review-01
phase: agent-control-center
status: REVIEW
owner: console-privacy-lifetime-reviewer
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - coordination/evidence/console-privacy-lifetime-review-01/**
  - coordination/progress/console-privacy-lifetime-reviewer.md
  - coordination/delivery/console-privacy-lifetime-review-01-delivery-report.md
forbidden_scope:
  - source changes during review
  - credentials existing sessions and private transcripts
  - external provider calls live worker execution merge push and publication
acceptance:
  - Independently inspect both privacy mode and lifetime changes against fixed main base.
  - Verify privacy defaults mode binding and display, role isolation, cookie/session lifecycle and owned cleanup.
  - Check installed launcher consistency, regressions, source closure and release evidence limits.
  - Report concrete findings with repro and paths, and exact validation and residual risks.
expected_artifacts:
  - independent_review
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective
Review the user's direct-model privacy and manual-lifetime changes independently.

## Context
Fixed source candidate `1f4fb5a236800e9ba9330e438c56666a7d24327b`, base
`69b5ce5acde565e24cee10f3ce19bf0a28279f10`. Default privacy is ZDR; ordinary
mode must be explicitly selected. Server, login and Agent sessions were changed
to manual stop at the user's direction. The prior monitor and Hermes constraints
remain; the user deferred cross-machine testing.

## Constraints
Read only. Do not inspect credentials, private transcripts or existing session
contents. No provider calls, remote writes, production services or source fixes.
Use disposable fixtures for any test. Report recommendations, not self-acceptance.

## Implementation Notes
Review the complete diff, especially any race or misleading display that could
silently weaken privacy, persistent session cleanup, manual-stop behavior, CSRF,
compatibility and any source files needed for a fresh install.

## Validation Steps
Inspect code and run bounded focused checks as appropriate; preserve exact test
commands and failures. The lead will record the findings and perform fixes.

## Escalation Rules
Report incomplete scope, inconsistencies or unexpected effects; do not modify
candidate or claim production acceptance.
