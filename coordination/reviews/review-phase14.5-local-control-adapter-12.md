# Independent Review: phase14.5-local-control-adapter-12

- Review ID: `review-phase14.5-local-control-adapter-12`
- Task ID: `phase14.5-local-control-adapter-12`
- Phase: `phase14.5-local-control`
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_08`
- Reviewed commit: `ee8d1e7`
- Reviewed At: 2026-09-18
- Decision: needs_fix

## Summary

The L1 boundary is deliberately in-memory and avoids runtime, network,
credential, Git, persistence, and L2-enforcement claims. It has one release
blocking binding flaw: the adapter can launch for one request even when the
other five submitted records are cross-wired from the approved six-record set.

## Required Changes

1. **P1 — bind every submitted record exactly to the approval before calling
   the factory.** `scripts/local_control_adapter.py:52-64` validates the
   request's matching approval binding and selected record, then compares only
   the *set of agent IDs* for the other five records. It does not require each
   record to be the exact projection of a distinct approval binding, nor does
   it bind every record's task/run/approval/reference fields. A reproducible
   counterexample is: provision valid records, change record 2's
   `worktree_ref` to `worktrees/pilot/agent-01`, then submit the unchanged
   agent-01 request. `run_local_once()` returns `completed` and invokes the
   factory once. This accepts a six-record set that is no longer the exact
   six identity/grant/worktree binding required by the task card and contract.
   Require a one-to-one exact projection check across all six records before
   consuming the run, and add a factory-free regression test for this and for
   altered task/run/approval/reference fields on a nonselected record.

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

## Validation Check

- Focused L1 adapter/provisioner and L1 contract tests: **10 passed**.
- Affected Phase B.1--H fixture suite with isolated pytest base temp:
  **113 passed**.
- `D:\\codex work\\.venv\\Scripts\\python.exe scripts/orchestrate.py validate`:
  passed.
- `git diff ee8d1e7^ ee8d1e7 --check`: passed.
- L2 unchanged check: passed.
- Negative API/claim scan found only allowed policy literals; no operational
  runtime, network, credential, Git, worktree, persistence, or CLI API.
- Independent adversarial check reproduced the P1 above: a nonselected
  cross-wired record still resulted in `completed` and one fake-factory call.

## Scope Compliance

The implementation diff contains only the eight task-card-allowed files.
This review adds only its allowed review record and does not alter
implementation, lifecycle, runtime, credentials, network, Git state, or
worktrees.

## Accepted Artifacts

None pending the required P1 correction.

## Residual Risks

Even after correction, L1 is best-effort local controlled collaboration, not
a defense against malicious code or deliberate policy circumvention. Fake
process factories remain non-live execution; a separately recorded one-shot
operator approval and Phase H evidence remain necessary before a real start.
