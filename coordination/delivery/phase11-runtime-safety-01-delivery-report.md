# Delivery Report: phase11-runtime-safety-01

## Summary

Implemented the `orchestrate doctor` read-only preflight diagnostic command.
The command detects the wrong clone, unavailable runtime, incomplete
coordination structure, and invalid explicit task/profile references before a
lead agent dispatches work.

## Changed Files

| File | Change |
|------|--------|
| `scripts/doctor.py` | New — read-only preflight diagnostic script |
| `scripts/orchestrate.py` | Updated — registered `doctor` subcommand in COMMAND_MAP and parser |
| `tests/scripts/test_doctor.py` | New — 18 focused tests covering success, failure, and no-mutation paths |
| `docs/operations/lead-agent-orchestration-protocol.md` | Updated — added Doctor Command Details section |
| `coordination/progress/external-agent-platform-21.md` | Updated — progress tracking |
| `coordination/task-board/in_progress/2026-07-16_phase11-runtime-safety-01_orchestrate-doctor-preflight.md` | Updated — status changed to IN_PROGRESS |
| `coordination/delivery/phase11-runtime-safety-01-delivery-report.md` | New — this report |

## Acceptance Criteria Coverage

1. **Add orchestrate doctor subcommand** — implemented in `scripts/doctor.py`,
   registered in `scripts/orchestrate.py` via delegated subcommand pattern
   (COMMAND_MAP + subparser).

2. **Check repository identity, Git, Python, coordination dirs, optional
   task/profile** — all six check categories implemented in
   `scripts/doctor.py:_check_root()`, `_check_git()`, `_check_python()`,
   `_check_coordination_dirs()`, `_check_task()`, `_check_profile()`.

3. **Non-zero exit on failure, no mutation** — exit code is 0 when all checks
   PASS, 1 when any check FAILS. All test fixtures verify byte-for-byte
   identity after doctor runs (task cards, profiles remain unchanged).

4. **Focused tests** — 18 tests across 7 test classes:
   - Healthy repository (5 tests)
   - Missing repository root (2 tests)
   - Non-git directory (1 test)
   - Task reference success/failure/no-mutation (3 tests)
   - Profile reference success/failure/no-mutation (4 tests)
   - Combined task+profile (2 tests)
   - No-mutation across temp fixtures (1 test)

5. **Documentation** — added Doctor Command Details to
   `lead-agent-orchestration-protocol.md` with checks, exit behavior, usage
   examples, and key constraints.

## Validation Results

```text
python -m pytest tests/scripts/ -v
=> 84 passed, 2 skipped in 19.80s

powershell -ExecutionPolicy Bypass -File scripts\validate.ps1
=> Coordination validation passed.
```

## Residual Risks

- The Git remote check requires `origin` to be configured. Agents working
  with a different remote name will see a FAIL on `git-remote` but can still
  proceed with the other checks passing.
- The coordination directory check for `incidents/` is intentionally a WARN
  (not FAIL) since the directory may not exist until the first incident.

## Recommended Next Handoff

Transition to the next Phase 11 task (dependency-aware wave planner) once this
delivery is accepted. The wave planner can use `orchestrate doctor` as its
precondition check before planning.
