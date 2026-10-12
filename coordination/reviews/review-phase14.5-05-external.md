# Review Report

- Review ID: review-phase14.5-05-external
- Reviewer: EXTERNAL_RUNTIME_REVIEWER
- Task ID: phase14.5-05-external-review-01
- Phase: phase14.5-external-runtime-launcher
- Decision: accepted
- Reviewed At: 2026-07-22

## Summary

External independent verification accepted. Commit `fd122d1` is reachable on `main`. The supervised-launch validation module is pure in-memory, fail-closed, and covers every contract-defined reject-path category without any process, shell, network, or mutable-artifact API. The operator-supplied external review result is consistent with independent verification.

## Findings

- `scripts/supervised_launch_validation.py` imports only `datetime`, `hashlib.sha256`, `json`, `re`, and `typing`. No `subprocess`, `os.system`, `Popen`, `shell=True`, `Path(`, `open(`, or any process/network/filesystem API is present. Source-level scan confirmed zero matches.
- The single pilot bindings (`opencode` runtime, `external-agent-platform-33` worker, `ORCHESTRATOR` reviewer, frozen branch and worktree) match the frozen contract and accepted Phase 14.5-04 design exactly.
- The manifest `argv` field accepts only a single-item opaque SHA-256 digest (64 hex chars). Multi-item, shell-like, or otherwise unsupported structures return `deny_invalid_manifest` before the future-executor gate.
- Non-allowlisted runtime or executable identity returns `deny_allowlist` before provenance comparison.
- All 11 contract reject categories have deterministic implementation paths and test coverage: missing manifest, invalid manifest, disabled state, inbox mismatch, provenance mismatch, worktree mismatch, allowlist denial, approval denial, timeout, unsafe audit fields, and the no-execution boundary.
- A schema-valid `supervised_one_shot` request returns `supervised_launch_requires_future_executor`; execution is deliberately unavailable in this module.
- The boundary document explicitly states that any future launch-executor task requires separate one-shot operator approval, independently reviewed audit/incident/stop/rollback plans, and explicit acceptance of external-runtime risk.

## Scope Compliance

PASS — changed files are limited to `scripts/supervised_launch_validation.py`, `tests/scripts/test_supervised_launch_validation.py`, `docs/operations/phase14.5-supervised-validation-boundary.md`, and coordination artifacts, all within the original task card's `allowed_scope`. No files in the `forbidden_scope` were modified.

## Validation Check

Independent verification performed:

- Commit `fd122d1` confirmed reachable on `main` (`git log fd122d1 -1` — `feat: add supervised launch validation foundation`).
- `python -m py_compile scripts/supervised_launch_validation.py` — passed.
- `python -m py_compile scripts/launcher_dry_run.py` — passed.
- `python scripts/validate_coordination_files.py` — passed (task card template-section gaps are pre-existing, not introduced by this delivery).
- Source-level forbidden-API scan of `supervised_launch_validation.py` — no matches for `subprocess`, `os.system`, `Popen`, `shell=True`, `Path(`, `open(`, `os.popen`, `multiprocessing`, `asyncio.create_subprocess`, or `os.exec`.
- All 12 focused test functions (7 new + 5 existing dry-run safety tests) passed via standard-library harness.
- Operator-supplied external review result (12 passed, py_compile passed, coordination validation passed, git diff check passed, source-level scan passed) is consistent with independent verification.

## Required Changes

- None.

## Accepted Artifacts

- scripts/supervised_launch_validation.py
- tests/scripts/test_supervised_launch_validation.py
- docs/operations/phase14.5-supervised-validation-boundary.md
- docs/operations/phase14.5-launcher-safety-contract.md
- docs/operations/phase14.5-supervised-launch-design.md
- coordination/delivery/phase14.5-05-delivery-report.md
- coordination/reviews/review-phase14.5-05.md

## Preserved Original External Evidence

The original external report is retained below; its metadata normalization is
superseded by main's authoritative review header above. Neither historical
review is rerun or replaced by this integration.

# External Review Report for phase14.5-05

**Task ID**: phase14.5-05-external-review-01
**Reviewer**: External Independent Verifier
**Date**: 2026-07-22
**Decision**: accepted

## Commands and Results Checked

1. **Dependency Check**: Verified that commit `fd122d1` is present in `main`.
   - Command: `git show fd122d1 --quiet && echo "Commit exists" || echo "Commit does not exist"` → Commit exists.
   - Command: `git branch --contains fd122d1` → `* main`

2. **Focused Tests**: Executed the test suite via standard library harness (since pytest not available).
   - Command: `cd /d/codex\ work/worktrees/phase14-runtime-adapter-01-main && python tests/scripts/test_supervised_launch_validation.py`
   - Result: No output, exit code 0 → all 12 test functions passed.

3. **Python Compilation**:
   - Command: `python -m py_compile scripts/supervised_launch_validation.py scripts/launcher_dry_run.py` (as per delivery report)
   - Result: Passed.

4. **Coordination Validation**:
   - Command: `python scripts/validate_coordination_files.py`
   - Result: Passed.

5. **Git Diff Check**:
   - Command: `git diff --check`
   - Result: Passed.

6. **Source-Level Scan for Forbidden APIs**:
   - Verified absence of `subprocess`, `os.system`, `Popen`, `shell=True`, `Path(`, `open(` in `scripts/supervised_launch_validation.py`.
   - Command: `grep -E "subprocess|os\.system|Popen|shell\s*\(|\" scripts/supervised_launch_validation.py` (or we trust delivery report.
   - The test file scan for these tokens.

## Findings

- The implementation `scripts/supervised_launch_validation.py` is a pure, in-memory validation module with no file, environment, network, or runtime execution behavior.
- All decisions are deterministic and fail‑closed. The module returns only safe decision categories and safe audit fields.
- The module correctly validates:
  - Single pilot binding (`runtime_id: opencode`, `worker_id: external-agent-platform-33`, etc.)
  - Allowlisted executable ID (`opencode`)
  - Timeout bounds (1‑900 seconds)
  - Opaque SHA‑256 digest `argv` (exactly one 64‑hex character string)
  - Manifest integrity (digest match)
  - Inbox provenance
  - Approval reference (non‑expired, exact match, enabled, approver role ORCHESTRATOR, mode supervised_one_shot)
  - Safe audit schema
- For a valid supervised request (with correct approval) the module returns the decision `supervised_launch_requires_future_executor` and does **not** trigger any process creation. This satisfies the requirement that supervised requests cannot launch a runtime without a future executor implementation.
- All reject‑path categories from the contract are covered: missing manifest, invalid manifest, disabled, missing/malformed inbox, wrong worker/project/task, wrong branch/worktree, unallowlisted runtime/executable, missing/expired/mismatched approval, timeout, non‑zero exit, credential prompt/monitor anomaly (via audit validation).
- The module does not emit any unsafe fields (paths, argv, task content, prompts, credentials, runtime output, error output).

## Scope Compliance

- Changed files are within the allowed scope: `scripts/**`, `tests/scripts/**`, `docs/operations/**`, `coordination/task-board/**`, `coordination/progress/**`, `coordination/delivery/**`.
- No changes were made to forbidden scopes: `services/**`, `src/**`, `database/**`, `cloud/**`, `profiles/**`, or any runtime‑launching code.

## Residual Risk

- The module validates only in‑memory JSON‑shaped values; it does not enforce real manifest immutability, signature custody, operator authority, or runtime safety. These are out of scope for this task and must be addressed in a later, separately approved implementation.
- A supervised request that passes validation still yields `supervised_launch_requires_future_executor` and cannot proceed to launch without a future executor component. This is by design and matches the contract boundary.

## Required Changes

None. The implementation satisfies all acceptance criteria and the contract.

## Conclusion

The implementation of phase14.5-05 meets the Phase 14.5 supervised launch safety contract, passes all focused tests, and respects the mandated scope. The external reviewer recommends **acceptance**.
