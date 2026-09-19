# Review Report

- Review ID: `review-phase14.5-pilot-approval-fanout-20`
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_16`
- Task ID: `phase14.5-pilot-approval-fanout-20`
- Phase: `phase14.5-phase-h-pilot-fix`
- Reviewed commits: `c846af4`, follow-up `939f8ea`
- Decision: accepted
- Reviewed At: `2026-09-19`

## Summary

The follow-up resolves the detached-state replay.  A single caller-owned set
now contains the exact pilot-admission marker and all six per-binding markers,
so a retained admission state necessarily retains the consumed binding fence.
All six legitimate bindings remain launchable once under fake children.

## Findings

- **P1 resolved.** `consumed_binding_tokens` was removed.  The shared
  `consumed_run_ids` state now stores both the exact admission token and each
  binding marker.  The executor and live seam prove six legitimate launches,
  then verify a replay using retained state denies with zero fake spawn/Popen.
- No additional acceptance failure found.

## Verified Evidence

- Six legitimate approved bindings pass once in the injected executor and
  live-runner seams; duplicate/restarted-state replay, foreign, expired,
  malformed, cross-wired, and second-pilot fixtures deny under the shared
  state.
- Existing strict controls remain present: exact approval/record binding,
  launch-time approval validation, worktree-only context, fixed wrapper
  provenance, `shell=False`, explicit environment, output suppression,
  lease stopping, no retry/fallback, redacted result projection, and L1
  `best_effort` terminology.
- Scope is compliant for the reviewed implementation diff.  No forbidden
  `services/`, `src/`, `database/`, `cloud/`, or `profiles/` path changed.
- This review used fake children only.  It did not run OpenCode, a real Popen,
  network/model request, credential/provider access, or Git worktree action.

## Validation Check

- `py_compile scripts/local_control_provision.py scripts/local_control_adapter.py scripts/local_opencode_executor.py scripts/local_opencode_live_runner.py` — passed.
- Focused provision/adapter/executor/live-runner/pilot-contract suite with isolated basetemp — **34 passed**.
- Affected Phase B.1--H suite with isolated basetemp — **131 passed**.
- `scripts/orchestrate.py validate` — passed.
- `git diff c846af4^ c846af4 --check` — passed.

## Scope Compliance

PASS. The reviewed commit changes only task-allowed scripts, tests,
documentation, and coordination evidence; it changes no forbidden path.

## Required Changes

- None.

## Accepted Artifacts

- `scripts/local_opencode_executor.py`
- `scripts/local_opencode_live_runner.py`
- `tests/scripts/test_local_opencode_executor.py`
- `tests/scripts/test_local_opencode_live_runner.py`
- `docs/operations/phase14.5-local-opencode-executor-contract.md`
- `docs/operations/phase14.5-six-agent-pilot-protocol.md`
- `coordination/delivery/phase14.5-pilot-approval-fanout-20-delivery-report.md`
