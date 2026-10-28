---
task_id: console-handoff-ui-01
phase: console-handoff-01
status: DONE
owner: ORCHESTRATOR
reviewer: console-handoff-review-01
priority: high
dependencies: []
allowed_scope:
  - web/api.py
  - web/static/index.html
  - web/static/app.js
  - web/static/app.css
  - scripts/console_setup.py
  - tests/scripts/test_handoff_console.py
  - docs/operations/github-handoff-guide.md
  - coordination/evidence/console-handoff-ui-01/**
  - coordination/progress/console-handoff-ui-01.md
  - coordination/delivery/console-handoff-ui-01-delivery-report.md
forbidden_scope:
  - other implementation owner files
  - live accounts credentials runtime or provider changes
  - push merge or external activation
acceptance:
  - Add optional handoff adapter/config and cached handoff view while old seven-view/login/setup behavior remains compatible.
  - Use existing Operator preview and Administrator one-use confirmation for explicit sync/dispatch, Viewer read-only, exact expected SHA fields retained.
  - Provide usable handoff/evidence status and eligible existing READY task dispatch UI with no network on navigation/poll and no raw paths/body/argv exposure.
  - Role/stale-plan/CSRF/unconfigured cases and focused affected checks pass; guide explains sender and worker watch/execute setup with no live activation.
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

Implement console API/frontend integration and operator guide against frozen backend interface. Backend owner creates github_handoff module concurrently; use optional/lazy import and stub tests until ready, no edits in backend files. This pilot dispatches existing READY cards; task-authoring UI remains later work.

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


## Authorized rework

ORCHESTRATOR reopens after independent91a needs-fix report. Apply coordination/evidence/console-handoff-01/fix-contract.md. One additional focused pytest invocation <=300seconds for affected scope/deadline paths; preserve initial delivery/manifest and red/timeout results. No unrelated changes or publication. Parent serially commits after both return REVIEW.


## Additional narrow boundary correction

Lead found redundant whole-scope path_key rejects240character base plus supported /** while backend validates base. Remove redundant wholepath check and add maximumsupported-boundary test. Preserve30pass currentrun as prior evidence; authorize one additional focused invocation <=300seconds for changed scope boundary/projection cases, no broad rerun. Resume same owner and report exact finalhashes.
