# Independent Review: phase14.5-local-opencode-live-runner-15

- Reviewer: `CODEX_INDEPENDENT_REVIEWER_11`
- Review ID: `review-phase14.5-local-opencode-live-runner-15`
- Task ID: `phase14.5-local-opencode-live-runner-15`
- Phase: `phase14.5-phase-h-live-runner`
- Reviewed At: `2026-09-18`
- Reviewed commits: `4b9a8dd`, follow-ups `bb2e67d`, `bd152e0`
- Decision: accepted

## Summary

The live runner is accepted as a minimal L1 `best_effort` process seam. It retains no user-specific raw wrapper path in source; its input-only wrapper provenance is bound to a safe path digest and exact approval/run IDs before Popen.

## Findings

Follow-ups resolve the original source-held-path defect and its missing coverage. `test_mismatched_wrapper_digest_never_calls_popen` supplies an otherwise valid launcher with a distinct digest, receives `deny_invalid_launcher`, and observes zero fake Popen calls. Relative, unsafe/changed, altered-PowerShell, cross-wired approval, and malformed-schema launcher inputs also deny before Popen. The live seam preserves standard-library-only constrained Popen, fixed `-NoProfile -NonInteractive -File` PowerShell invocation, `shell=False`, explicit non-inherited child environment, DEVNULL output handling, consume-before-start, exact executor validation, redacted results, matching timeout tree stop, and L1 `best_effort` terminology.

## Required Changes

None. The direct bad-digest, zero-Popen test required by the previous review is present in `bd152e0`.

No other acceptance failure was found. The runner uses standard-library `subprocess` only; the default `Popen` seam is constrained to the production wrapper path and every test injects a fake. It uses `shell=False`, explicit child environment, fixed PowerShell flags, `DEVNULL` streams, consumes the run before spawn, returns only the executor's safe result projection, and sends timeout stopping only to the launched child PID through the fixed task-tree command. The protocol correctly preserves L1 `best_effort` terminology and keeps real launch gated.

## Validation Check

- `py_compile scripts/local_opencode_live_runner.py` — passed.
- Focused runner plus affected Phase B.1--H fixture suite — **78 passed** with an isolated pytest base temp. The tests use fake Popen only.
- `git diff bb2e67d bd152e0 --check` — passed.
- Final follow-up scope contains three files, all within the task card's `allowed_scope`; no forbidden `services/`, `src/`, `database/`, `cloud/`, or `profiles/` path changed.
- Read-only review performed: no OpenCode execution, provider/configuration/environment/credential inspection, network request, Git worktree action, merge, push, or implementation/lifecycle/history mutation.

## Scope Compliance

The seven-file original delivery, five-file provenance correction, and three-file final test correction are each contained by the task card's `allowed_scope`. No forbidden path changed.

## Accepted Artifacts

- `scripts/local_opencode_live_runner.py`
- `tests/scripts/test_local_opencode_live_runner.py`
- `docs/operations/phase14.5-local-opencode-executor-contract.md`
- `docs/operations/phase14.5-six-agent-pilot-protocol.md`
- `coordination/delivery/phase14.5-local-opencode-live-runner-15-delivery-report.md`

## Residual Risks

Even after correction, this is an L1 `best_effort` boundary, not a sandbox or a claim of enforced host isolation. A future six-worker pilot must use current non-fixture approval and provenance records, maintain redaction, and remain separately supervised.
