# Independent Review: phase14.5-local-control-adapter-12

- Review ID: `review-phase14.5-local-control-adapter-12`
- Task ID: `phase14.5-local-control-adapter-12`
- Phase: `phase14.5-local-control`
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_08`
- Reviewed commits: `ee8d1e7`, `c160e20`, `529c248`
- Reviewed At: 2026-09-18
- Decision: accepted

## Summary

The P1 implementation flaw and the P2 regression gap are fixed. Every
submitted record must be the exact projection of its distinct approval binding
before a factory call, and permanent tests cover the requested nonselected
worktree plus task/run/approval/reference mutations.

## Required Changes

None.

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
- The P2 regression is fixed in
  `test_every_non_selected_record_binding_field_denies_before_factory`.
  Nonselected grant, worktree, task, run, approval, and scheduler mutations
  each return `deny_unbound_approval`, make zero factory calls, and do not
  appear in the returned evidence.

## Validation Check

- Focused L1 adapter/provisioner and L1 contract tests: **12 passed**.
- Affected Phase B.1--H fixture suite with isolated pytest base temp:
  **115 passed**.
- `D:\\codex work\\.venv\\Scripts\\python.exe scripts/orchestrate.py validate`:
  passed.
- `git diff ee8d1e7 529c248 --check`: passed.
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

- `scripts/local_control_adapter.py`
- `scripts/local_control_provision.py`
- `tests/scripts/test_local_control_adapter.py`
- `tests/scripts/test_local_control_provision.py`
- `docs/operations/phase14.5-local-control-adapter-contract.md`
- `coordination/delivery/phase14.5-local-control-adapter-12-delivery-report.md`

## Residual Risks

Even after correction, L1 is best-effort local controlled collaboration, not
a defense against malicious code or deliberate policy circumvention. Fake
process factories remain non-live execution; a separately recorded one-shot
operator approval and Phase H evidence remain necessary before a real start.
