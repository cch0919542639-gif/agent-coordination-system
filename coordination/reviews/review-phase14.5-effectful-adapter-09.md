# Independent Review: phase14.5-effectful-adapter-09

- Review ID: `review-phase14.5-effectful-adapter-09`
- Task ID: `phase14.5-effectful-adapter-09`
- Phase: `phase14.5-effectful-adapter`
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_05`
- Reviewed commit: `0cbefb1`
- Reviewed At: 2026-09-17
- Decision: needs_fix

## Summary

The submitted adapter has the intended injected-only boundary and its normal
success, binding-denial, attestation, timeout, termination-failure, and
duplicate-run fixture paths pass.  It is not acceptable yet because denial
results copy unvalidated request values into the returned evidence, violating
the required no-raw-data fail-closed boundary.

## Findings

- **P1 — unvalidated values leak on denial:** `_result()` copies every
  string/integer in `SAFE_RESULT_FIELDS` whenever `request` is a mapping,
  including after `_request()` has rejected it.  An independent probe with a
  malformed `task_id` carrying `secret-prompt-value` returned that exact value
  in `deny_invalid_grant` evidence.  A hostile caller can similarly place
  arbitrary raw values in `run_id`, `approval_id`, `grant_id`, or `agent_id`.
  This conflicts with the task acceptance requirement to never return raw or
  sensitive data and the established launcher contract rule that unverified
  fields are never echoed.  Denied/unvalidated input must return only the
  denial category and `dry_run`; allowlisted identifiers may be projected only
  after complete request validation.
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

1. Change result construction so a request that fails validation never
   contributes any values to the result.  Preserve useful allowlisted IDs only
   on paths where the request has already passed the exact validation boundary.
2. Add a deterministic regression test that supplies a malformed request with
   a distinctive sensitive/raw marker and asserts the marker and all
   unvalidated fields are absent from the denial result.  Re-run the focused
   and combined suites after the fix.

## Validation Check

- `python -m py_compile scripts/effectful_adapter.py` — passed.
- Focused adapter tests — 8 passed.
- Combined Phase B.1–H fixture suite — 88 passed.
- `python scripts/orchestrate.py validate` — passed.
- `git diff 09f39e2..0cbefb1 --check` — passed.
- Independent denial probe reproduced the raw-value leak above; no factory was
  called.

## Scope Compliance

- The six changed files are within the task card's permitted `scripts/**`,
  `tests/scripts/**`, `docs/operations/**`, and `coordination/**` scope.  No
  forbidden `services/`, `src/`, `database/`, `cloud/`, `profiles/`, or
  `.github/` path changed.
- The task card remains `REVIEW`.  This reviewer added only this review record;
  no implementation, lifecycle, runtime-state, credential, network, Git, or
  worktree action was performed.

## Residual Risks

- After the required correction, this remains only a caller-supplied,
  in-memory process boundary.  It does not establish or independently verify
  Windows enforcement, and it must not be treated as authorization to launch a
  connector or the Phase H pilot.
