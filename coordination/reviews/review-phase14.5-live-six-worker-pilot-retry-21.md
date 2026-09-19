# Review Report

- Review ID: `review-phase14.5-live-six-worker-pilot-retry-21`
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_17`
- Task ID: `phase14.5-live-six-worker-pilot-retry-21`
- Phase: `phase14.5-phase-h-live-pilot`
- Reviewed commit: `b03bef6`
- Decision: needs_fix
- Reviewed At: `2026-09-19`

## Summary

The fresh approval record is distinct from task 19, carries six unique
agent/grant/worktree bindings, preserves the reviewed wrapper digest and L1
`best_effort` label, and records no prohibited sensitive material.  The six
worktrees currently resolve to the reviewed detached commit and are clean.
The incident correctly records a terminal no-retry safety stop rather than
attempting diagnosis through child output or provider configuration.

However, the evidence does not establish the requested six actual concurrent
OpenCode child-start attempts.  Six `stopped_safety_signal` projections prove
only that six runner calls reached a terminal fail-closed result.  That result
is also the runner's category for a failed Popen/spawn boundary, and the
record contains neither a privacy-safe child-start attestation nor enough
per-binding ordering/concurrency evidence to distinguish six real child starts
from six pre-child failures.  It must not claim that OpenCode was invoked until
that distinction is independently checkable.

## Findings

- The one-shot record has a launch-time approval ID, a current 15-minute run
  window, six distinct exact bindings, the accepted `OPENCODE_PROJECT_WORKTREE`
  mapping name only, wrapper digest, and bounded lease/stop policy.  No
  credential, configuration value, endpoint, prompt, source body, raw child
  output, or absolute path appears in the record, delivery, or incident.
- The six terminal records are unique by agent, grant, and worktree; all are
  `stopped_safety_signal`, with `no_retry_no_fallback_matching_stop_only`.
  The incident preserves the intended L1 claim: best-effort control, not a
  sandbox or enforced isolation boundary.
- Read-only worktree checks show each allocated `worker-01` through
  `worker-06` at detached `cad70bf7858f3eace5d68c7683feb4cde6c0901b` with an
  empty porcelain status.  The review worktree has one unrelated pre-existing
  Phase 10 task-card modification; it is outside this commit and untouched.
- The task 21 diff is limited to its allowed coordination evidence files;
  `git diff --check b03bef6^ b03bef6` passed.  No implementation, runtime, or
  lifecycle history was changed by this review.
- Focused control/provision/adapter/executor/live-runner tests passed
  (`33 passed`), and `scripts/orchestrate.py validate` passed.  These tests
  exercise fake process seams; they do not supply the missing live
  child-start/concurrency evidence.

## Required Changes

- **P1 — add privacy-bounded launch evidence before claiming an actual six-worker live attempt.**  A follow-up must record, for each exact binding, a safe
  `child_start_attested`/`child_not_started` outcome and a non-sensitive
  ordering or shared-launch-window fact sufficient to verify all six were
  started concurrently (or revise the delivery claim to the actually verified
  serial/failed boundary).  The projection must not expose PID, executable or
  wrapper path, argv, environment values, output, prompts, provider settings,
  credentials, or endpoints.  Preserve the consumed approval and do not retry
  task 21's tokens.
- **P2 — correct the now-stale Phase H protocol gate in a separately scoped
  documentation packet.**  Its statement that no real pilot has run conflicts
  with this submitted task's claimed live attempt.  The update must distinguish
  an attempted-but-unattested safety stop from verified OpenCode child starts;
  it must not upgrade L1 to a sandbox claim.

## Accepted Artifacts

- None pending the P1 evidence correction.

## Scope Compliance

PASS for the reviewed task 21 commit: its five changed files are all within
`coordination/**`, the card's only allowed implementation area.  This review
adds only its required review record.  No forbidden scope changed.  The
separate existing Phase 10 task-card modification remains unmodified.

## Validation Check

- `scripts/orchestrate.py doctor --task-id phase14.5-live-six-worker-pilot-retry-21` — passed.
- Focused provision/adapter/executor/live-runner pytest suite with isolated
  basetemp — `33 passed`.
- `scripts/orchestrate.py validate` — passed.
- `git diff --check b03bef6^ b03bef6` — passed.
- `git diff --name-only b03bef6^ b03bef6` — five files, all within task 21
  `allowed_scope`.
