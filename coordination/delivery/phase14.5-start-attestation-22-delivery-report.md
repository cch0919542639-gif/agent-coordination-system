# Delivery Report: phase14.5-start-attestation-22

- Task ID: `phase14.5-start-attestation-22`
- Agent: `CODEX_PLATFORM_WORKER_12`
- Phase: `phase14.5-phase-h-attestation`
- Status: submitted for independent review

## Changed Files

- `scripts/local_opencode_live_runner.py`
- `tests/scripts/test_local_opencode_live_runner.py`
- `docs/operations/phase14.5-local-opencode-executor-contract.md`
- `docs/operations/phase14.5-six-agent-pilot-protocol.md`
- task and progress evidence for this task

## Acceptance Criteria Coverage

- The injected runner records a safe start attestation only after constrained
  Popen returns a live child with a valid internal identity. The evidence is
  only a deterministic binding digest and a monotonic launch order.
- The paired concurrency projection contains only exact-binding digests,
  order, overlap count, and prior active binding digests. It exposes no PID,
  path, command, output, environment value, endpoint, or credential.
- Pre-spawn denials, Popen errors, and a returned non-live child result in no
  attestation or concurrency projection.
- The existing six-token fences, lease handling, wrapper provenance,
  `shell=False`, project-context validation, matching task-tree stop, and
  no-retry behavior are unchanged.
- Fake-Popen tests cover failed pre-spawn/Popen paths, started child,
  overlapping started children, timeout stop, and evidence redaction.
- P1 follow-up: if a caller-owned attestation state rejects registration after
  Popen returned a live child, the runner invokes the existing exact task-tree
  stop for that child before returning its redacted safety terminal result.
  The matching fake regression proves no attestation is emitted and no live
  child remains.

## Validation Steps Performed

- `python -m pytest -p no:cacheprovider --basetemp ...` for provision,
  adapter, executor, and live-runner suites — 36 passed.
- `py_compile scripts/local_opencode_live_runner.py` — passed.
- `scripts/orchestrate.py validate` — passed.
- `git diff --check` — passed.

## Known Residual Risks

All evidence is fake-Popen-only. This task did not execute OpenCode, real
Popen, a network/model request, provider configuration or credentials, or a
worktree action. Attestation remains L1 best-effort evidence and is not a
sandbox or host-enforcement claim.
