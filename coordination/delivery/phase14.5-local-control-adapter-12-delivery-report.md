# Delivery Report: phase14.5-local-control-adapter-12

- Task ID: `phase14.5-local-control-adapter-12`
- Phase: `phase14.5-local-control`
- Worker: `CODEX_PLATFORM_WORKER_06`
- Agent: `CODEX_PLATFORM_WORKER_06`
- Status: submitted for independent review

## Changed Files

- `scripts/local_control_adapter.py`
- `scripts/local_control_provision.py`
- `tests/scripts/test_local_control_adapter.py`
- `tests/scripts/test_local_control_provision.py`
- `docs/operations/phase14.5-local-control-adapter-contract.md`
- `coordination/task-board/review/2026-09-18_phase14.5-local-control-adapter-12.md`
- `coordination/progress/CODEX_PLATFORM_WORKER_06.md`

## Acceptance Criteria Coverage

`provision_local_workers()` accepts only an exact current one-shot Phase H L1
approval with six unique agent, grant, and component-safe worktree bindings.
Each binding carries fixed safe runtime/argument tokens, bounded timeout, stop
authority, and scheduler, lease, review, manifest, and allocation references.
It returns six privacy-bounded `best_effort` records and creates no worker.

`run_local_once()` rechecks the exact approval and request-to-binding record,
consumes the run before at most one injected process-factory call, and uses only
the injected fake process's tree-stop method on timeout. Invalid, expired,
duplicate, unsafe, malformed, or cross-wired inputs return before that call.
Results omit the argument allowlist and never call L1 a sandbox or claim
enforced filesystem, process-identity, or network isolation.

The L2-only adapter and provisioner were not changed. No runtime, connector,
network, credential, Git worktree, merge, push, or cleanup operation was made.

## Validation Steps Performed

- `py_compile scripts/local_control_adapter.py scripts/local_control_provision.py` — passed.
- Focused L1 tests plus L1 contract — 10 passed.
- Affected Phase B.1–H fixture regression suite — 118 passed.
- Negative API/anti-claim source scan — no matches.
- `python scripts/orchestrate.py validate` — passed.
- `git diff --check` — passed.

## Known Residual Risks

This is L1 `best_effort` local controlled collaboration only. Caller-held
in-memory records do not enforce write scope, OS process identity, or network
egress, and fake process factories are not a live process start. A separately
recorded one-shot operator approval and the later Phase H protocol remain
required before any real process start.
