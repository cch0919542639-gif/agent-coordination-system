# Independent Review: phase14.5-start-attestation-22

- Review ID: review-phase14.5-start-attestation-22
- Reviewer: CODEX_INDEPENDENT_REVIEWER_18
- Task ID: phase14.5-start-attestation-22
- Phase: phase14.5-phase-h-attestation
- Decision: accepted
- Reviewed At: 2026-09-19 15:10 Asia/Taipei
- Reviewed commits: `27466b4cc01f5a0aa0a869945171636414d7fe8b`, P1 follow-up `7c1ed745c909a8bfebf2ad72554492034a16b195`.

## Summary

Accepted. The submitted P1 follow-up safely stops the matching returned child
when state registration rejects, without emitting unsafe or false evidence.

## Findings

- Attestation is captured only after constrained Popen returns a live child
  with a positive private PID and `poll() is None`. Popen failure and non-live
  returns produce no attestation or concurrency projection.
- Records contain only schema version, deterministic exact-binding digest,
  monotonic order, overlap count, and prior binding digests; no PID, path,
  command, output, environment value, endpoint, or credential is returned.
- P1 follow-up separates child construction from `register_start()`. If the
  caller-owned state rejects registration after Popen returns a live child, it
  invokes the existing matching task-tree stop and returns only the redacted
  safety result. The regression proves exactly two fake calls (start then stop),
  no attestation/projection, and a non-live child afterward.
- Shared-state fake coverage proves distinct live starts receive monotonic
  launch orders and records the exact active predecessor as overlap evidence.
- The Phase H protocol accurately calls the earlier attempt
  attempted-but-unattested and requires a fresh approval for a later pilot.

## Scope Compliance

PASS. The implementation, fake test, executor contract, pilot protocol,
delivery/progress evidence, and task-card state are all allowed. No
`services/`, `src/`, `database/`, `cloud/`, or `profiles/` path changed. The
pre-existing Phase 10 modified card and unrelated Task 21 review note remain
untouched.

## Validation Check

- Focused live-runner, executor, adapter, and provision suites: 36 passed.
- `py_compile scripts/local_opencode_live_runner.py`: passed.
- `scripts/orchestrate.py validate`: passed after this report's required
  metadata and headings were added.
- `git diff 27466b4..7c1ed745 --check`: passed.
- Static scan found only the reviewed constrained OpenCode Popen seam and
  matching taskkill stop; no network, credential, Git, shell, or persistence
  API was added.

## Required Changes

- None.

## Accepted Artifacts

- `scripts/local_opencode_live_runner.py`
- `tests/scripts/test_local_opencode_live_runner.py`
- `docs/operations/phase14.5-local-opencode-executor-contract.md`
- `docs/operations/phase14.5-six-agent-pilot-protocol.md`
- `coordination/delivery/phase14.5-start-attestation-22-delivery-report.md`

## Residual Risk

All evidence is fake-Popen-only. This acceptance is L1 best-effort, not a
sandbox claim. No OpenCode, real Popen, network/model request, provider
configuration, credential, or worktree action was performed during review.
