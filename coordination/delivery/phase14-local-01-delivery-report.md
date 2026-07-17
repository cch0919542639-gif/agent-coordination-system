---
- Task ID: phase14-local-01
- Agent: external-agent-platform-30
- Phase: phase14-same-machine-worker-automation
- Status: WAITING_FOR_REVIEW
- Last Updated: 2026-07-18
---

## Changed Files

- `scripts/worker_poller.py` — added `activate` subcommand and supporting functions
- `tests/scripts/test_worker_activation.py` — 16 focused tests
- `docs/operations/phase14-worker-bootstrap-guide.md` — operator bootstrap guide
- `coordination/progress/external-agent-platform-30.md` — progress update
- `coordination/task-board/review/2026-07-18_phase14-local-01_worker-activation-command.md` — task card moved to review

## Validation Steps Performed

1. `python -m pytest tests/scripts/test_worker_activation.py -v` — 16/16 passed
2. `python -m pytest tests/scripts/ -q` — 342 passed, 2 skipped (7 pre-existing profile validator failures unrelated to this task)
3. `python scripts/orchestrate.py validate` — passed (progress file labels correct)

## Known Residual Risks

- The 7 profile validator test failures are pre-existing and unrelated to this task. They relate to the progress file format validation for profile-aware tests.
- No cross-machine delivery is implemented; this phase is same-machine only.

## Acceptance Criteria Coverage

- [x] Bounded same-machine worker activation command consuming owner-matching pending delivery
- [x] Emits safe local action payload (no raw task body, prompts, credentials, paths)
- [x] Acknowledgement separate from task claim; no lifecycle mutation before worker acts
- [x] Duplicate activation is idempotent (no duplicate payload)
- [x] Fail-closed for missing, empty, mismatched, malformed, acknowledged, retry-pending, or failed records
- [x] Two-worker same-machine tests proving isolation, no duplicate, no task-card mutation, no subprocess/HTTP/agent launch
- [x] Bootstrap guide for worker registration and heartbeat configuration
