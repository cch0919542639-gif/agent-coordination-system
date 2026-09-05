# Delivery Report: phase14.5-launcher-09

- Task ID: phase14.5-launcher-09
- Agent: ORCHESTRATOR
- Phase: phase14.5-supervised-launcher
- Status: REVIEW

## Summary

Implements a bounded, one-shot OpenCode launcher boundary for the accepted
Phase 14.5 B admission contract. The implementation is in-memory and has no
CLI, file loading, executable resolution, network, credential, Git, or task
lifecycle behavior. It can reach an injected process factory only after exact
manifest, operator approval, connector grant, and admission validation.

## Changed Files

- `scripts/supervised_opencode_launcher.py`
- `tests/scripts/test_supervised_opencode_launcher.py`
- `docs/operations/phase14.5-supervised-opencode-launcher-contract.md`
- `coordination/task-board/review/2026-09-05_phase14.5-launcher-09_supervised-local-opencode-launcher.md`
- `coordination/progress/orchestrator.md`

## Validation Steps Performed

- `D:\codex work\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\scripts\test_supervised_opencode_launcher.py tests\scripts\test_controlplane_admission.py tests\scripts\test_supervised_launch_validation.py tests\scripts\test_launcher_dry_run.py tests\scripts\test_bootstrap_handoff.py -q` — 53 passed.
- `D:\codex work\.venv\Scripts\python.exe scripts\validate_coordination_files.py` — passed.
- `git diff --check` — passed.
- Source-level coverage rejects filesystem, network, shell, and direct process
  factory APIs from the launcher. All process behavior in tests uses fakes.

## Acceptance Criteria Coverage

| Requirement | Evidence |
| --- | --- |
| Immutable manifest, exact approval, grant, and admission before process creation | `prepare()` validates canonical manifest/grant digests, pilot binding, five-minute approval freshness, one-shot grant, and B admission result. |
| Allowlisted, no-shell argv boundary | Manifest accepts only safe-token argv with `opencode` as its allowlisted first token; `run_once()` passes an already constructed tuple to an injected factory. |
| Safe terminal outcomes | `run_once()` emits only safe projections for completion, timeout, and nonzero exit; timeout terminates only the injected matching process. |
| Deterministic no-process denials | Focused fake-process tests prove altered, expired, revoked, duplicate, mismatched, disabled, stopped, capacity, and allowlist inputs do not call the factory. |
| Separate pilot approval | The implementation has no CLI or real factory; the contract requires exact operator approval immediately before any production caller supplies one. |

## Known Residual Risks

- This is not a Windows filesystem/process/network enforcement adapter. That
  enforcement gap is explicit and deferred.
- No real OpenCode process, manifest file, credential, prompt, argv value, or
  runtime output was used or retained during implementation.

## Recommended Handoff

- Independent review must validate the fail-closed boundary before the planning
  branch integrates this delivery. A real pilot then needs a new exact operator
  approval for its immutable manifest and grant.
