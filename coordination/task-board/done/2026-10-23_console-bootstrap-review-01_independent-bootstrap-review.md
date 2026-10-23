---
task_id: console-bootstrap-review-01
phase: console-delivery-01
status: DONE
owner: console-bootstrap-review-01
reviewer: ORCHESTRATOR
priority: high
dependencies: []
allowed_scope:
  - coordination/evidence/console-bootstrap-review-01/**
  - coordination/delivery/console-bootstrap-review-01-delivery-report.md
  - coordination/progress/console-bootstrap-review-01.md
forbidden_scope:
  - implementation source changes
  - live runtime or credential changes
  - remote publication
acceptance:
  - Review only after console-bootstrap-01 enters REVIEW with a clean fixed candidate commit and exact manifest.
  - Independently inspect init and serve validation, replay byte preservation, staging permissions, foreign schema and binding refusals, partial initialization behavior and finite local-only service startup.
  - Verify all26 accepted P1a source pins remain exact and only authorized bootstrap paths changed from5daa318.
  - Perform one focused bootstrap pytest invocation capped300seconds and one disposable new-directory initialization and login-view smoke check; capture child process outcomes without wrapper interruption.
  - Record security and correctness findings or an exact-commit accepted recommendation in independent evidence and canonical delivery; no self acceptance.
expected_artifacts:
  - independent_review
  - verification_evidence
  - delivery_report
execution_mode: REPO_FIRST
---
# Task Packet

## Objective

Independently assess the downloadable-console bootstrap increment. Source REVIEW is required before substantive checking; this is a review relation, not a DONE implementation dependency.

## Context

Authoritative board C:/Users/angel/.codex/worktrees/integration-context-01/codex work, candidate C:/Users/angel/.codex/worktrees/console-download-candidate/codex work on codex/console-bootstrap-01. P1a base5daa318 accepted. Read source task and report and current roadmap.

## Constraints

Read implementation files only; write own review evidence/reports. Synthetic isolated state directories only; no existing account/runtime use or parent service change. Never print tokens or copy account data to repository. No source repairs. Avoid subprocess-per-baseline-file audits: batch Git tree maps. Only one focused pytest run, hard timeout300seconds, retain logs/JUnit and observed returncode; do not interrupt runner while a child is running except for genuine timeout/safety. No third-party code or provider execution.

## Implementation Notes

Verify state paths are external and canonical, state publication is new-only, Windows ACL applied before credentials, replay validates schema/role/project/root and token/hash consistency without mutation, and serve creates nothing when unavailable/misbound. Check no enable/worker side effects, clear port conflict, finite duration and clean owned server shutdown in synthetic smoke test. Use largest-risk probes as focused checks, not mirrored implementation tests. Preserve original failures. Record any untested platform boundary.

## Token And Resource Impact (If Applicable)

One independent reviewer, one focused pytest invocation and one bounded disposable init/HTTP smoke run. No additional provider/LLM runtime, polling schedule or real credentials. Any further test run requires orchestrator direction.

## Validation Steps

Confirm exact commit/diff/pins; inspect code and submitted tests, run focused suite, independently exercise new-directory setup and seven authenticated views; verify Viewer mutations refuse and runtime remains disabled. Run authoritative coordination validator, submit report to REVIEW with recommendation and limitations.

## Escalation Rules

Report source security/correctness defects with concrete reproduction. Do not silently modify implementation or expand production/credential scope. No user-action-required deployment claims from same-host fixture tests.
