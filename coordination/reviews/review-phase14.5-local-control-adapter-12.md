# Independent Review: phase14.5-local-control-adapter-12

- Review ID: `review-phase14.5-local-control-adapter-12`
- Task ID: `phase14.5-local-control-adapter-12`
- Phase: `phase14.5-local-control`
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_08`
- Reviewed commits: `ee8d1e7`, `c160e20`
- Reviewed At: 2026-09-18
- Decision: needs_fix

## Summary

The P1 implementation flaw is fixed: every submitted record now has to be
the exact projection of its distinct approval binding before a factory call.
One narrow test-coverage correction remains: the committed regression test
only changes a nonselected grant, rather than covering the requested
nonselected worktree and additional binding fields.

## Required Changes

1. **P2 — expand the repository regression to the required nonselected
   fields.** `tests/scripts/test_local_control_adapter.py` exercises a
   nonselected `grant_id` alteration only. Add factory-free denials for a
   nonselected cross-wired `worktree_ref` and representative other binding
   fields (at minimum task/run/approval plus one scheduler/lease/review or
   digest reference). The implementation correctly denies these in independent
   re-review, but the requested deterministic regression coverage is absent.

## Findings

- Approval validation has an exact schema, one-shot/current-window checks,
  six unique agent/grant/worktree values, component-safe descendant worktrees,
  fixed request-bound runtime/argv, bounded timeout, stop authority, and the
  exact prohibited-action list.
- Invalid request, consumed run, invalid approval, invalid selected binding,
  malformed record shape, and duplicate selected-record paths return before
  the injected factory. The run is consumed before the sole injected call; a
  timeout calls only the injected process's `terminate_tree()` and returns
  safe `best_effort` evidence.
- Success output omits argv and uses the `best_effort` control label. The new
  L1 modules do not call themselves a sandbox or claim enforced filesystem,
  OS-process-identity, or network-egress isolation.
- `scripts/effectful_adapter.py` and `scripts/connector_provision.py` are
  unchanged from the parent commit. No real runtime, connector, network,
  credential, Git/worktree, merge, push, cleanup, filesystem persistence, or
  CLI behavior was found in the L1 modules.
- The original P1 is fixed in `scripts/local_control_adapter.py`: records must
  have the exact field set; each is mapped to a distinct approved agent; every
  task/run/approval field and all twelve binding fields match; and all records
  carry the `best_effort` and process-tree-stop markers. The factory remains
  unreachable if any one record differs.

## Validation Check

- Focused L1 adapter/provisioner and L1 contract tests: **11 passed**.
- Affected Phase B.1--H fixture suite with isolated pytest base temp:
  **114 passed**.
- `D:\\codex work\\.venv\\Scripts\\python.exe scripts/orchestrate.py validate`:
  passed.
- `git diff ee8d1e7 c160e20 --check`: passed.
- L2 unchanged check: passed.
- Negative API/claim scan found only allowed policy literals; no operational
  runtime, network, credential, Git, worktree, persistence, or CLI API.
- Independent adversarial checks changed a nonselected worktree, task ID, run
  ID, approval ID, and scheduler reference in turn. Each returned
  `deny_unbound_approval` without a factory call.

## Scope Compliance

The implementation diff contains only the eight task-card-allowed files.
This review adds only its allowed review record and does not alter
implementation, lifecycle, runtime, credentials, network, Git state, or
worktrees.

## Accepted Artifacts

None pending the narrow required regression-coverage correction.

## Residual Risks

Even after correction, L1 is best-effort local controlled collaboration, not
a defense against malicious code or deliberate policy circumvention. Fake
process factories remain non-live execution; a separately recorded one-shot
operator approval and Phase H evidence remain necessary before a real start.
