# Delivery Report: phase14.5-opencode-network-credential-exception-14

- Task ID: `phase14.5-opencode-network-credential-exception-14`
- Agent: `CODEX_PLATFORM_WORKER_08`
- Phase: `phase14.5-opencode-network-exception`
- Status: submitted for independent review

## Changed Files

- `DECISIONS.md`
- `scripts/local_control_provision.py`
- `scripts/local_opencode_executor.py`
- `tests/scripts/test_local_control_provision.py`
- `tests/scripts/test_local_opencode_executor.py`
- `docs/operations/phase14.5-local-control-adapter-contract.md`
- `docs/operations/phase14.5-local-opencode-executor-contract.md`
- `docs/operations/phase14.5-six-agent-pilot-protocol.md`
- `coordination/task-board/review/2026-09-18_phase14.5-opencode-network-credential-exception-14.md`
- `coordination/progress/CODEX_PLATFORM_WORKER_08.md`

## Acceptance Criteria Coverage

Implemented the default-deny, exact one-shot L1 OpenCode network/provider
exception boundary. It is preparation only: no real environment was read, no
provider configuration or credential was accessed, and no process, network,
worktree, Git, merge, push, or cleanup action occurred.

### Delivered Artifacts

- `scripts/local_control_provision.py`: validates either the existing
  default-deny projection or the exact enabled exception. The enabled form is
  bound to the existing task, run, window, six bindings, and one sorted subset
  of named configuration-root variables.
- `scripts/local_opencode_executor.py`: accepts an injected caller-supplied
  mapping only when its keys exactly match that approved subset. It rejects
  unknown or credential-like content before fake spawn and never returns,
  serializes, logs, or persists values.
- Focused tests and L1 contracts document the exception without a credential,
  endpoint, absolute path, prompt, source, output, or transcript.

## Validation Steps Performed

- `py_compile scripts/local_control_provision.py scripts/local_opencode_executor.py` — passed.
- Affected Phase B.1--H fixture suite — 117 passed.
- `scripts/orchestrate.py validate` — passed.
- `git diff --check` — passed.

### Safety Properties

- The legacy no-exception approval remains network/provider deny with an empty
  child environment; supplying a mapping to it denies.
- An enabled exception requires one exact task/run approval, current window,
  all six validated records, exact allowlisted keys, `shell=False`, fixed
  `opencode.exe`, and consume-before-fake-spawn behavior.
- Result records keep only existing safe IDs and terminal category; provider
  environment values do not enter the result or delivery evidence.
- L1 remains `best_effort`; this is not a sandbox or a claim of enforced
  network, filesystem, or process isolation.

## Known Residual Risks

This boundary cannot validate a live provider, endpoint behavior, OpenCode
behavior, or host-level isolation. A real process start still requires an
independently accepted review and a current concrete one-shot approval.
