---
- Task ID: phase14-local-01
- Agent: external-agent-platform-30
- Phase: phase14-same-machine-worker-automation
- Status: WAITING_FOR_REVIEW (correction iteration)
- Last Updated: 2026-07-18
---

## Changed Files

- `scripts/worker_poller.py` — added `activate` subcommand, atomic worker inbox handoff, and registered-product card-path resolution
- `tests/scripts/test_worker_activation.py` — 18 focused tests
- `docs/operations/phase14-worker-bootstrap-guide.md` — operator bootstrap guide
- `coordination/progress/external-agent-platform-30.md` — progress update
- `coordination/task-board/review/2026-07-18_phase14-local-01_worker-activation-command.md` — task card moved to review

## Validation Steps Performed

1. Focused activation test methods — 18/18 passed through an isolated compatibility runner because the active environment has no `pytest` module.
2. `python -m py_compile scripts/worker_poller.py tests/scripts/test_worker_activation.py` — passed.
3. `python scripts/orchestrate.py validate` — passed.
4. The full `tests/scripts/` pytest suite is not runnable in this environment because its active Python interpreter lacks `pytest`; this correction does not claim a full-suite result.

## Known Residual Risks

- The active local Python environment lacks `pytest`, so acceptance still requires the reviewer to run the focused and full pytest commands in a provisioned test runtime.
- No cross-machine delivery is implemented; this phase is same-machine only.

## Acceptance Criteria Coverage

- [x] Bounded same-machine worker activation command consuming owner-matching pending delivery
- [x] Persists a safe worker-specific local inbox payload atomically before acknowledgement; duplicate activation does not duplicate it
- [x] Emits a safe local action payload with an actual registered-product repository-relative task-card path (no raw task body, prompts, credentials, or absolute paths)
- [x] Acknowledgement separate from task claim; no lifecycle mutation before worker acts
- [x] Duplicate activation is idempotent (no duplicate payload)
- [x] Fail-closed for missing, empty, mismatched, malformed, acknowledged, retry-pending, or failed records
- [x] Two-worker same-machine tests proving isolation, no duplicate, no task-card mutation, no subprocess/HTTP/agent launch
- [x] Bootstrap guide for worker registration and heartbeat configuration
