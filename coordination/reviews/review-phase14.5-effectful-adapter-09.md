# Independent Review: phase14.5-effectful-adapter-09

- Review ID: `review-phase14.5-effectful-adapter-09`
- Task ID: `phase14.5-effectful-adapter-09`
- Phase: `phase14.5-effectful-adapter`
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_05`
- Reviewed commits: `0cbefb1`, `668a289`
- Reviewed At: 2026-09-17
- Decision: accepted

## Summary

The submitted adapter has the intended injected-only boundary and its normal
success, binding-denial, attestation, timeout, termination-failure, and
duplicate-run fixture paths pass.  The P1 denial-redaction finding from the
first review was fixed in `668a289` and independently revalidated.

## Findings

- **Resolved P1 — unvalidated values leaked on denial:** Before `668a289`,
  `_result()` copied fields from a request even after `_request()` had denied
  it.  The correction derives `safe_request` only after exact request
  validation and passes `None` to result construction for malformed input.
  The new regression test and an independent malformed `prompt: private
  source` probe both return exactly `deny_invalid_request` and `dry_run`, with
  no factory call and no echoed marker.  Safe IDs remain allowlisted only for
  otherwise valid request records.
- The exact schema and binding checks are otherwise present: request,
  approval, grant, and enforcement attestation require exact field sets;
  grant/request/approval/attestation bind task, run, grant, agent, and
  worktree before the injected factory.  Attestation independently requires
  current restricted-write, process-identity, and deny-network assertions.
- `run_id` is consumed before the factory, timeout targets only the process
  returned by that factory, and factory/wait/terminate failures produce a
  redacted terminal safety category.  No production process, connector,
  network, credential, Git, worktree, persistence, CLI, prompt, command,
  argv, output, or transcript handling was found.

## Required Changes

none

## Validation Check

- `python -m py_compile scripts/effectful_adapter.py` — passed.
- Focused adapter tests — 9 passed.
- Combined Phase B.1–H fixture suite — 89 passed.
- `python scripts/orchestrate.py validate` — passed.
- `git diff 0cbefb1..668a289 --check` — passed.
- Independent malformed-request probe passed: only
  `deny_invalid_request`/`dry_run` returned and the injected factory was not
  called.

## Scope Compliance

- The six changed files are within the task card's permitted `scripts/**`,
  `tests/scripts/**`, `docs/operations/**`, and `coordination/**` scope.  No
  forbidden `services/`, `src/`, `database/`, `cloud/`, `profiles/`, or
  `.github/` path changed.
- The task card remains `REVIEW`.  This reviewer updated only this review record;
  no implementation, lifecycle, runtime-state, credential, network, Git, or
  worktree action was performed.

## Residual Risks

- After the required correction, this remains only a caller-supplied,
  in-memory process boundary.  It does not establish or independently verify
  Windows enforcement, and it must not be treated as authorization to launch a
  connector or the Phase H pilot.

## Accepted Artifacts

- `scripts/effectful_adapter.py`
- `tests/scripts/test_effectful_adapter.py`
- `docs/operations/phase14.5-effectful-adapter-contract.md`
- `coordination/delivery/phase14.5-effectful-adapter-09-delivery-report.md`
