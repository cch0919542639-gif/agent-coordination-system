# Independent Review: phase14.5-wrapper-repin-24

- Review ID: `review-phase14.5-wrapper-repin-24`
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_20`
- Task ID: `phase14.5-wrapper-repin-24`
- Phase: `phase14.5-phase-h-wrapper-recovery`
- Reviewed commits: `42ea059`, P1 follow-up `796f9a9`
- Decision: accepted
- Reviewed At: `2026-09-19`

## Summary

Accepted. The P1 follow-up repeats strict wrapper path and content-pin
validation at the injected spawn boundary and demonstrates that a
post-admission replacement produces no Popen or start evidence.

## Findings

- **P1 resolved.** `_spawn()` now repeats `_wrapper_path()` and
  `_wrapper_content_digest()` directly before injected Popen. The new fake
  regression copies the reviewed wrapper, replaces it after initial admission,
  and proves the redacted `stopped_safety_signal`, zero Popen calls, and no
  start/concurrency projection.

## Verified Evidence

- `scripts/opencode_pilot_wrapper.ps1` contains only forwarding to fixed
  `opencode.exe` and `exit $LASTEXITCODE`; its source digest is exactly
  `aa7ea288a6e44204dff64ddf90f9b1a4b8f55f9ae70837020644b7e6a000c0d5`.
- The launch mapping remains exact, absolute `.ps1` validation is strict,
  wrapper reads are bounded to 1024 bytes, and missing/changed inputs at the
  initial check deny before fake Popen.
- Existing result projection remains redacted; the constrained seam retains
  `shell=False`, output suppression, explicit environment, binding fences,
  lease-stop behavior, and start/concurrency evidence. The static scan finds
  only the reviewed Popen seam and matching task-tree stop; no network,
  credential, Git, shell, or persistence API was added.
- Task 23 remains `BLOCKED`; the reviewed diff does not run or retry it.

## Validation Check

- SHA-256 of `scripts/opencode_pilot_wrapper.ps1` equals the pinned digest.
- `py_compile scripts/local_opencode_live_runner.py` — passed.
- Focused live-runner/executor/provision/adapter suite with isolated basetemp
  — **40 passed**.
- Affected Phase B--H control-plane suite with isolated basetemp —
  **119 passed**.
- `scripts/orchestrate.py validate` — passed.
- `git diff 42ea059^..42ea059 --check` and
  `git diff 42ea059..796f9a9 --check` — passed.
- The combined reviewed delivery has eight changed files (the P1 follow-up
  changes six), all task-allowed; no `services/`,
  `src/`, `database/`, `cloud/`, or `profiles/` paths changed. The existing
  unrelated Phase 10 dirty task card was preserved.

## Required Changes

None.

## Scope Compliance

PASS for the combined reviewed delivery. Its eight changed files are within
the task's allowed scope; no forbidden product path changed. This review
record is the only reviewer-created evidence.

## Accepted Artifacts

- `scripts/opencode_pilot_wrapper.ps1`
- `scripts/local_opencode_live_runner.py`
- `tests/scripts/test_local_opencode_live_runner.py`
- `docs/operations/phase14.5-local-opencode-executor-contract.md`
- `docs/operations/phase14.5-six-agent-pilot-protocol.md`
- `coordination/delivery/phase14.5-wrapper-repin-24-delivery-report.md`

## Residual Risk

The eventual result remains L1 best-effort: a path-based PowerShell launch
cannot claim platform-enforced filesystem integrity, including a residual
check-to-exec filesystem race. No PowerShell, OpenCode, real Popen,
provider/credential access, network request, or worktree action occurred
during this review.
