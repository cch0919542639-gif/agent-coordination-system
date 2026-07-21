# Delivery Report

- Task ID: phase14.5-05
- Agent: external-agent-platform-34
- Phase: phase14.5-external-runtime-launcher
- Status: REVIEW

## Changed Files

- `scripts/supervised_launch_validation.py`
- `tests/scripts/test_supervised_launch_validation.py`
- `docs/operations/phase14.5-supervised-validation-boundary.md`
- `coordination/progress/external-agent-platform-34.md`
- `coordination/task-board/review/2026-07-22_phase14.5-05_supervised-launch-safety-foundation.md`

## Validation Steps Performed

- Executed all seven new validation test functions and five existing dry-run
  safety test functions through a standard-library import-and-call harness:
  `12 focused test functions passed`.
- `python -m py_compile scripts/supervised_launch_validation.py
  scripts/launcher_dry_run.py` — passed.
- `python scripts/validate_coordination_files.py` — passed.
- `git diff --check` — passed.
- Source-level scan of the new module for `subprocess`, `os.system`, `Popen`,
  `shell=True`, `Path(`, and `open(` — passed with no matches.
- `python -m pytest ...` could not run because the provisioned interpreter has
  no `pytest` module. The focused test functions were therefore invoked using
  the standard library; no dependency was installed or changed.

## Known Residual Risks

- This validates in-memory JSON-shaped values only; it does not establish real
  manifest immutability, signature custody, operator authority, credentials,
  provider behavior, or runtime safety.
- A schema-valid supervised request deliberately yields
  `supervised_launch_requires_future_executor`; this task supplies no launch
  capability or authorization.

## Acceptance Criteria Coverage

- Deterministic canonical-digest, identity, provenance, inbox, timeout,
  executable-identity, approval-reference, enable-state, and safe-audit
  validation is implemented for the one frozen pilot.
- All decisions are safe in-memory records; branch and worktree are represented
  only by a digest in output. No paths, argument values, task bodies,
  credentials, runtime output, files, or external artifacts are read or
  written by the module.
- Focused tests cover successful dry-run validation, successful supervised
  validation remaining execution-ineligible, missing/malformed/altered and
  disabled manifests, malformed and mismatched inbox/provenance, runtime and
  executable allowlist, timeout, unsafe audit fields, and missing/mismatched/
  expired approval cases.
- The operator boundary document states the exact independent approvals and
  review gates required before any future executor task.

## Review Fixes Applied

- A manifest `argv` now accepts only a one-item opaque SHA-256 digest. It
  rejects arbitrary multi-item, shell-like, and other unsupported structures
  as `deny_invalid_manifest` before the supervised future-executor gate.
- A runtime ID outside the single `opencode` allowlist is now classified as
  `deny_allowlist` before provenance comparison. Focused deterministic tests
  cover both corrected paths.
