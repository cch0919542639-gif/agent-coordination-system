# Delivery Report

- Task ID: phase12-events-03
- Agent: external-agent-platform-28
- Phase: phase12-event-driven-orchestration
- Status: DELIVERED

## Changed Files

- `scripts/worker_poller.py` — new file: opt-in worker-side polling command with register, poll, acknowledge subcommands
- `scripts/event_routing.py` — extended `DeliveryRecord` dataclass with routing-safe fields (ref, commit, owner, reviewer, artifact_paths)
- `scripts/orchestrate.py` — added `worker` passthrough subcommand
- `tests/scripts/test_worker_poller.py` — new file: 43 focused tests covering registration, project isolation, polling, acknowledgement, payload safety, malformed state, no subprocess/HTTP, no lifecycle mutation, CLI parsing

## Artifact Paths

- `scripts/worker_poller.py` — the worker poller implementation
- `tests/scripts/test_worker_poller.py` — focused tests
- `coordination/progress/external-agent-platform-28.md` — progress tracking
- `coordination/delivery/phase12-events-03-delivery-report.md` — this report
- `coordination/task-board/review/2026-07-17_phase12-events-03_registered-worker-poller.md` — task card (in review)

## Validation Steps Performed

1. `python -m pytest tests/scripts/ -q` — **278 passed, 2 skipped, 0 failed**
   - All 43 new worker-poller tests pass
   - All existing 235+ tests pass with no regressions (2 pre-existing skips for Git-dependent tests)
2. `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1` — **Coordination validation passed**
3. All 43 worker-poller specific tests verify:
   - Worker registration (add, update, remove, list, malformed file)
   - Worker/project isolation (worker sees only its project's notifications)
   - Polling behavior (empty, pending ready, ignores non-ready events, ignores non-pending records, ignores other destinations, JSON output, empty JSON, duplicate poll idempotent)
   - Acknowledgement (pending, nonexistent, idempotent, no lifecycle change)
   - Payload safety (no raw content, required fields present, artifact paths included)
   - Malformed delivery state (corrupt JSONL line skipped, empty file)
   - No subprocess/HTTP invoked (verified via `unittest.mock.patch`)
   - No task-card or lifecycle mutation (verified via filesystem checks)
   - CLI parser (all subcommands and flags parse correctly)

## Known Residual Risks

1. **Worker registration JSON mutability** — The `coordination/monitor/workers.json` file is plain JSON and can be manually edited or corrupted. Mitigation: `list_workers()` returns `[]` on malformed data; CLI validation is enforced on `register`/`unregister`.
2. **Delivery state path coupling** — `poll` reads delivery state via `event_routing.DELIVERY_FILE`. If the monitor directory layout changes, the poller breaks. Mitigation: the path is a single import away and would be caught by the validator.
3. **No authentication on acknowledge** — Anyone with local filesystem write access to the delivery state JSONL can acknowledge a notification. Mitigation: acknowledge is purely informational — it does not claim a task, launch an agent, or change lifecycle state.
4. **Poll scope limited to `ready_assigned`** — Other event types (`review_submitted`, `incident_opened`) are intentionally ignored. Mitigation: the filter is a simple list check and trivially extendable by a future task.
5. **Interval/jitter are documentation-only** — The `--interval` and `--jitter` flags are accepted for scheduler documentation but not enforced in a continuous daemon loop. Mitigation: documented clearly in `--help` and operator guides.

## Recommended Handoff

The ORCHESTRATOR (or next reviewer) should:

1. Verify the delivery report now conforms to `coordination/templates/delivery-report.md` with all required metadata and sections.
2. Confirm the task card is in `review/` with `status: REVIEW` and progress is at `WAITING_FOR_REVIEW`.
3. Review the 43 worker-poller tests for adequacy and the implementation for correctness.
4. If accepted, move the task card to `done/`, update progress to `DONE`, and merge the branch.

## Acceptance Criteria Coverage

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Opt-in worker-side polling command that reads only the registered worker's project-scoped pending ready-assignment notification payloads | **Met** | `worker_poller.py poll <worker_id>` reads `delivery_state.jsonl`, filters by `worker.project_id`, `event_type=ready_assigned`, `destination=registered_worker`, `status=pending` |
| 2 | Render a standard safe dispatch payload with task ID, relative task-card path, project/ref/commit identity, protocol references, and required start/block/finish rules | **Met** | `_render_notification()` outputs structured message with all required fields; JSON mode via `--json` |
| 3 | Require explicit worker registration and explicit acknowledgement; never automatically claim a task, launch an agent, pull code, create a worktree, or mutate task lifecycle | **Met** | Registration via `register` subcommand; acknowledgement via `acknowledge` subcommand calls `event_routing.acknowledge()` which only sets `status=acknowledged` — never claims, launches, pulls, or creates worktrees |
| 4 | Provide bounded polling configuration with a safe minimum interval, jitter guidance, and an idle/no-work exit that consumes negligible resources | **Met** | Single poll by default; `--interval` minimum enforced at 60s; `--jitter` documented (default 0.1); exits cleanly with "No pending work" |
| 5 | Add focused tests for registration, worker/project isolation, duplicate/no-work polling, acknowledgement, malformed payloads, no subprocess/network invocation, and no lifecycle mutation | **Met** | 43 tests across 9 test classes covering all required scenarios; verified via `unittest.mock.patch` for subprocess/HTTP; filesystem checks for lifecycle mutation |
