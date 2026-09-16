# Independent Review: phase14.5-six-agent-pilot-08

- Review ID: review-phase14.5-six-agent-pilot-08
- Task ID: phase14.5-six-agent-pilot-08
- Phase: phase14.5-six-agent-pilot
- Reviewer: CODEX_INDEPENDENT_REVIEWER_04
- Reviewed commits: a05b36e, 6b1e01c, 7baae7c, ce559e2
- Reviewed At: 2026-09-17
- Decision: accepted

## Summary

The delivery safely documents Phase H as a pre-approval protocol, retains an
open incident for the absent real-pilot prerequisites, and runs only
deterministic fake-clock fixtures. The corrective commits now require exact
task/run-bound approval provenance, current accepted adapter evidence,
component-safe references, and six exact connector bindings. This is accepted
only as a safe pre-approval deliverable; it is not acceptance of a live pilot.

## Findings

- Resolved: `exact_approval()` now requires the exact task/run-bound,
  one-shot, enabled approval schema, six grants/identities/worktree and
  evidence references, deny-network, forbidden action list, bounded timeout,
  and current run window. `accepted_adapter()` also requires accepted, current
  sandboxed-one-shot evidence bound to the approval's adapter ID/version.
- Resolved: `safe_ref()` now rejects `.` and `..` components at every depth,
  including in approval and adapter evidence. Exact six-field connector
  records are now set-bound to the approved agent/grant/enforcement/worktree
  tuples and tested against cross-wire, duplicate, and missing-field cases.
- Resolved: `within_root()` requires every approved worktree reference to be a
  component-safe child of the declared root. The cross-root denial regression
  confirms a separately safe reference cannot escape that allocation root.
- No runtime, network, credential, filesystem persistence, Git worktree,
  merge, push, or cleanup API is present in the implementation/test boundary.
- The delivery report and incident accurately state that no real connector
  instance, credential, network, runtime, worktree, Git, merge, push, or
  cleanup action was attempted. They do not claim real pilot execution.

## Required Changes

none

## Validation Check

- `python -m py_compile tests/scripts/test_six_agent_pilot_preflight.py` — passed.
- Combined Phase B.1–H fixture suite after `ce559e2`
  (`test_six_agent_pilot_preflight`,
  `test_durable_scheduler`, `test_controlplane_admission`,
  `test_supervised_opencode_launcher`, `test_worktree_context`,
  `test_lease_recovery`, `test_evidence_review`, and
  `test_operator_surface`) — 89 passed.
- `python scripts/orchestrate.py validate` — passed.
- `git diff 7baae7c..ce559e2 --check` — passed.

## Scope Compliance

- The six implementation files changed by `a05b36e` are all within the
  permitted documentation, tests, and coordination paths. No forbidden
  application, database, cloud, or profile path changed.
- The task card remains `REVIEW`. This reviewer added only this review record;
  no implementation, lifecycle, Git-history, runtime-state, credential, or
  network operation was performed.

## Accepted Artifacts

- `docs/operations/phase14.5-six-agent-pilot-protocol.md`
- `tests/scripts/test_six_agent_pilot_preflight.py`
- `coordination/incidents/20260917-02_phase14.5-six-agent-pilot-preflight-gate.md`
- `coordination/delivery/phase14.5-six-agent-pilot-08-delivery-report.md`

## Residual Risks

- No live pilot has run. Six actual admitted enforcement-capable connector
  instances, an exact operator approval, and a separately reviewed effectful
  adapter remain mandatory gates for any future real execution.
