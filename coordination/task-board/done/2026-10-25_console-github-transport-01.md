---
task_id: console-github-transport-01
phase: console-handoff-01
status: DONE
owner: ORCHESTRATOR
reviewer: console-handoff-review-01
priority: high
dependencies: []
allowed_scope:
  - coordination_runtime/github_handoff.py
  - scripts/github_handoff.py
  - tests/scripts/test_github_handoff.py
  - coordination/evidence/console-github-transport-01/**
  - coordination/progress/console-handoff-platform-01.md
  - coordination/delivery/console-github-transport-01-delivery-report.md
forbidden_scope:
  - other implementation owner files
  - live accounts credentials runtime or provider changes
  - push merge or external activation
acceptance:
  - Implement frozen HandoffService and finite CLI using external bound state and configured Git queue/evidence transport.
  - Prove cross-clone immutable claim and local dedupe, identity/revision guards, configured runner hash and owned Job once-only execution without formal acceptance.
  - Automatically discover and validate published acceptance reports with raw hashes JUnit and exact revision, expose cached safe status and freshness.
  - Local bare remote end-to-end synthetic runner and failure/replay/outbox tests pass; no source worktree/index or provider mutation.
expected_artifacts:
  - implementation
  - tests
  - delivery_report
execution_mode: WORKTREE
branch: codex/console-handoff-sync-01
worktree_path: C:/Users/angel/.codex/worktrees/console-download-candidate/codex work
---
# Task Packet

## Objective

Implement backend transport/evidence synchronization and peer receive/optional approved-runner execution. Keep minimum stdlib code; no new broker or crypto/OS identity claims. Coordinate interface issues with orchestrator before changing contract.

## Context

Read authoritative board context and docs/operations/github-handoff-mvp-contract.md. Candidate worktree is console-download-candidate at clean92e1248 on new codex/console-handoff-sync-01; source/board integration-context-01. User explicitly requests improvements after verified5002422acceptance.

## Constraints

Only listed candidate source/test paths; own evidence/progress/delivery lives on source board. Preserve other owner edits; NO git add or commit during parallel work. Parent commits the integrated result. Do not change frozen interface silently; report blockers. No live account/state/service/credential changes or provider calls. Real GitHub remote never mutated in tests; use local bare fixture.

## Implementation Notes

Use existing stdlib facilities/JobProcess and preserve backwards defaults. Source docs contract is frozen and imports must stay acyclic. Claim/submit via board scripts as assigned owner; source hash bind your deliverable, final integrated commit supplied by parent. Python3.13 already installed, no package installs.

## Token And Resource Impact (If Applicable)

At most3pytest invocations per implementer, <=300seconds each; timeout children, fresh system-temp paths, concise stdout with retained logs/JUnit/native exit. No wrapper interruption mid-child except actual timeout. No full repo suite by default. Two owners disjoint parallel, one independent integration reviewer. No actual polling schedule installed; only bounded test loops.

## Validation Steps

Run focused tests plus proportionate affected checks; retain failures and scope/hashes, validate source board and diff, write canonical delivery and submit REVIEW. Do not accept own task.

## Escalation Rules

Report missing interface, source overlap, private data or unsupported containment. Continue independent safe work, no speculative framework or payload-controlled command execution.

## Authorized validation budget adjustment (2026-10-25)

ORCHESTRATOR observed third invocation native1 with60passed/1failed in235.23s. The only failure is timeout fixture replacing approved runner without refreshing its configured hash, causing expected RUNNER_CHANGED refusal. Authorize one additional focused pytest invocation <=300s after test-only fixture repair, preserving60passing coverage on identical product bytes and original failure. No full rerun absent product changes. Capture exact source/test diff and before/after hashes; any new product fix requires proportional rerun scope discussion with lead, not automatic green claim.


## Authorized rework

ORCHESTRATOR reopens after independent91a needs-fix report. Apply coordination/evidence/console-handoff-01/fix-contract.md. One additional focused pytest invocation <=300seconds for affected scope/deadline paths; preserve initial delivery/manifest and red/timeout results. No unrelated changes or publication. Parent serially commits after both return REVIEW.


## Additional narrow safe-error correction

After7pass/1scope-error-boundary-fail, authorize one additional <=300second focused invocation. Convert existing StateError from shared path_key into service-safe categories at every caller boundary (_card/_blob/evidence). Preserve validation strength and all original results; cover malformed card and evidence member paths plus affected scope/deadline checks. No unrelated source work.
