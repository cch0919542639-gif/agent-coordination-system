# Review Report

- Review ID: review-phase14.5-05
- Reviewer: external-agent-test-01
- Task ID: phase14.5-05
- Phase: phase14.5-external-runtime-launcher
- Decision: accepted
- Reviewed At: 2026-07-22

## Summary

Accepted after correction. The implementation preserves the no-execution
boundary and now fails closed for the manifest `argv` restrictions and runtime
allowlist category required by the frozen contract and accepted Phase 14.5-04
design.

## Findings

The two earlier reject-path findings are resolved.

## Required Changes

1. `_valid_manifest_shape` now permits only a one-item, lower-case 64-hex
   opaque SHA-256 digest. Multi-item, shell-like, or otherwise unsupported
   forms return `deny_invalid_manifest` before the future-executor gate. This
   validates a non-command reference only; it introduces no real argv or
   executable path.
2. Runtime allowlist validation now precedes provenance comparison, so a
   non-`opencode` `runtime_id` returns `deny_allowlist`. Focused tests cover
   both the runtime and executable rejection paths.

## Validation Check

- Manual cross-check against
  `docs/operations/phase14.5-launcher-safety-contract.md` and
  `docs/operations/phase14.5-supervised-launch-design.md` — identified the
  two reject-path gaps above.
- Source-level scan of `scripts/supervised_launch_validation.py` for process,
  shell, and operational-artifact APIs (`subprocess`, `os.system`, `Popen`,
  `shell=True`, `Path(`, `open(`, `os.popen`, `multiprocessing`,
  `asyncio.create_subprocess`, and `os.exec`) — no matches.
- `python -m py_compile scripts/supervised_launch_validation.py
  scripts/launcher_dry_run.py` — passed.
- `python scripts/validate_coordination_files.py` — passed.
- `git diff --check` — passed.
- `python -m pytest tests/scripts/test_supervised_launch_validation.py
  tests/scripts/test_launcher_dry_run.py` — unavailable because the
  configured interpreter has no `pytest` module; no dependency was installed.
  A standard-library import-and-call harness executed all 12 focused test
  functions successfully after the corrections.
- Independent corrected-path assertions confirmed: one opaque SHA-256 digest
  returns `supervised_launch_requires_future_executor`; multi-item and
  shell-like forms return `deny_invalid_manifest`; a non-allowlisted runtime
  returns `deny_allowlist`.

## Scope Compliance

The submitted files are within the task's allowed scope, and no process,
filesystem-artifact, runtime, or task-lifecycle execution path was found.
`DECISIONS.md` is unrelated and remains excluded. The task may move to `done`
and be committed locally; no push is authorized.

## Accepted Artifacts

- `scripts/supervised_launch_validation.py`
- `tests/scripts/test_supervised_launch_validation.py`
- `docs/operations/phase14.5-supervised-validation-boundary.md`
- `coordination/delivery/phase14.5-05-delivery-report.md`
