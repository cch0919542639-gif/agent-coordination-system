# Review Report

- Review ID: review-phase14.5-lease-supervisor-project-context-18
- Reviewer: CODEX_INDEPENDENT_REVIEWER_14
- Task ID: phase14.5-lease-supervisor-project-context-18
- Phase: phase14.5-phase-h-supervision
- Reviewed commit: `fdf1e83`
- Decision: accepted
- Reviewed At: 2026-09-19 03:45

## Summary

The follow-up resolves both P1 findings. The change now projects the exact
lease constraints through the six durable records and proves hard-ceiling
stopping with a fake child. The complete boundary remains L1 `best_effort`,
with no real runtime or credential action.

## Findings

- Previous P1: resolved. `_record()` now projects
  `heartbeat_interval_seconds`, `missed_heartbeat_threshold`, and
  `per_child_hard_ceiling_seconds`; the adapter's exact record schema and
  binding keys include the same three values. The provision test asserts all
  six records retain the approved `(5, 2, 60)` values.
- Previous P1: resolved. The hard-ceiling fake-child test checks a stop at the
  ceiling, one matching spawn/tree termination, consumed `run-01`, and no
  retry.
- No additional findings.

## Verified Evidence

- Launch-time materialization rejects a draft at provision time; the exact
  approval ID binds the complete draft plus `launch_time`, and a consumed run
  is recorded before injected spawn.
- Network exception context accepts only
  `OPENCODE_PROJECT_WORKTREE == request.worktree_ref`; arbitrary roots,
  cross-wiring, and default-exception environment input deny before spawn.
  The boundary neither reads host environment/provider configuration nor
  includes it in results.
- The executor retains fixed `opencode.exe`, `shell=False`, empty/default
  child environment, redacted results, fake spawn seam, matching-tree stop,
  and `best_effort` terminology.  No OpenCode, Popen, network, provider,
  credential, or Git worktree action was performed in this review.
- Adapter compatibility is preserved: its record projection accepts the
  additional validated lease fields, while executor `_base_records()` passes
  the exact adapter schema into the pre-existing `_bound()` check.
- Scope is compliant: all follow-up changes are within the amended task-card
  scope. The resolved incident documents the narrow adapter/test scope
  extension.

## Validation Check

- `py_compile scripts/local_control_provision.py scripts/local_control_adapter.py scripts/local_opencode_executor.py scripts/local_opencode_live_runner.py` — passed.
- Focused provision/adapter/executor/live-runner suite with isolated basetemp — passed.
- Affected Phase B.1–H suite with isolated basetemp — passed.
- `scripts/orchestrate.py validate` — passed.
- `git diff --check 8068e67^..fdf1e83` — passed.
- The previously claimed four `test_worktree_provision.py` permission failures
  remain outside the changed paths and are not needed for this accepted,
  fake-only boundary review.

## Scope Compliance

PASS. No forbidden `services/`, `src/`, `database/`, `cloud/`, or `profiles/`
path was changed.

## Required Changes

- None.

## Accepted Artifacts

- `scripts/local_control_provision.py`
- `scripts/local_control_adapter.py`
- `scripts/local_opencode_executor.py`
- `tests/scripts/test_local_control_provision.py`
- `tests/scripts/test_local_opencode_executor.py`
- `docs/operations/phase14.5-local-opencode-executor-contract.md`
- `docs/operations/phase14.5-six-agent-pilot-protocol.md`
- `coordination/delivery/phase14.5-lease-supervisor-project-context-18-delivery-report.md`
