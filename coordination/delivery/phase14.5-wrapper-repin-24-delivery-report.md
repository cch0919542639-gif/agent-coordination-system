# Delivery Report: phase14.5-wrapper-repin-24

- Task ID: `phase14.5-wrapper-repin-24`
- Agent: `CODEX_PLATFORM_WORKER_13`
- Phase: `phase14.5-phase-h-wrapper-recovery`
- Status: accepted after independent review

## Changed Files

- `scripts/opencode_pilot_wrapper.ps1`
- `scripts/local_opencode_live_runner.py`
- `tests/scripts/test_local_opencode_live_runner.py`
- `docs/operations/phase14.5-local-opencode-executor-contract.md`
- `docs/operations/phase14.5-six-agent-pilot-protocol.md`
- task and progress evidence

## Acceptance Criteria Coverage

- The project-owned wrapper forwards only argv to `opencode.exe` and returns its exit code.
- The runner accepts only a strict absolute `.ps1` input whose bounded source content matches the fixed SHA-256 pin, and rechecks it immediately before injected Popen; missing, changed, oversized, unsafe, or post-admission replacement content denies with zero Popen.
- Safe results remain redacted; wrapper paths, source, child identity, commands, argv, output, credentials, environment values, endpoints, and prompts are absent.
- Existing approval, one-shot, lease, project-context, start-attestation, concurrency, `shell=False`, and empty-environment boundaries remain covered by fake-Popen tests.

## Validation Steps Performed

- Focused live-runner, executor, provision, and adapter tests: 37 passed.
- `py_compile scripts/local_opencode_live_runner.py`: passed.
- Static forbidden-API scan: no matches.
- `git diff --check`: passed.

## Review Follow-up

- P1 closed: the spawn boundary rechecks the same path and content pin. A
  fake regression replaces the wrapper after initial admission and proves a
  redacted safety result, zero Popen calls, and no start evidence.

## Known Residual Risks

This is source-pin recovery only. No PowerShell, OpenCode, Popen, network,
provider configuration, credential, or worktree action occurred. It neither
retries Task 23 nor creates pilot authority.
