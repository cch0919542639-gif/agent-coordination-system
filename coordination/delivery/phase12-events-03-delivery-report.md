---
task_id: phase12-events-03
phase: phase12-event-driven-orchestration
status: DELIVERED
owner: external-agent-platform-28
reviewer: ORCHESTRATOR
delivered_at: 2026-07-17
---

# Delivery Report: phase12-events-03 — Registered Worker Poller

## Summary

Built the opt-in worker-side polling command (`scripts/worker_poller.py`)
that reads a registered worker's project-scoped pending ready-assignment
notification payloads and renders a safe dispatch message without
auto-claiming, auto-executing, or invoking external processes.

## Artifacts

| Artifact | Path |
|---|---|
| Worker poller script | `scripts/worker_poller.py` |
| Extended delivery record | `scripts/event_routing.py` (`DeliveryRecord`) |
| Orchestrate integration | `scripts/orchestrate.py` (added `worker` subcommand) |
| Focused tests | `tests/scripts/test_worker_poller.py` |
| Progress | `coordination/progress/external-agent-platform-28.md` |
| Operator docs | `docs/operations/phase12-monitor-operator-guide.md` (referenced for worker setup) |

## Delivery Paths

### 1. Worker Registration
- `python scripts/worker_poller.py register <worker_id> <project_id>`
- `python scripts/worker_poller.py unregister <worker_id>`
- `python scripts/worker_poller.py list`
- State stored in `coordination/monitor/workers.json` (Git-ignored)

### 2. Polling
- `python scripts/worker_poller.py poll <worker_id>`
- `python scripts/worker_poller.py poll <worker_id> --json`
- Single poll by default; exits cleanly with "No pending work" when idle
- Minimum interval: 60s (enforced), default: 600s with 0.1 jitter (documented for scheduler)

### 3. Acknowledgement
- `python scripts/worker_poller.py acknowledge <payload_id>`
- Idempotent; marks delivery as acknowledged (not claimed/executed)
- Uses existing `event_routing.acknowledge()` — no new state

### 4. Orchestrate Integration
- `python scripts/orchestrate.py worker ...` (passthrough to worker_poller.py)

## Safe Payload Schema

Rendered fields (both human-readable and JSON):
- `payload_id` — deterministic routing hash
- `project_id` — originating project
- `task_id` — task identifier
- `event_type` — always `ready_assigned`
- `ref` — Git branch/ref
- `commit` — commit SHA
- `owner` — assigned agent
- `reviewer` — designated reviewer
- `artifact_paths` — pre-routed artifact paths
- `task_card_path` — conventional `coordination/task-board/ready/{task_id}.md`

Explicitly excluded: raw task body, prompts, credentials, absolute paths.

## Constraints Verification

| Constraint | Status |
|---|---|
| Explicit local worker registration | ✅ `workers.json` (Git-ignored) |
| Read only registered worker's project-scoped payloads | ✅ Filters by `worker.project_id` |
| Render only safe fields from routing | ✅ Uses `DeliveryRecord` safe fields |
| Acknowledge delivery only, never auto-claim | ✅ `acknowledge()` sets status to `acknowledged` |
| No subprocess/Git/HTTP/GitHub/Codex API calls | ✅ Verified by test + code audit |
| No task-card mutation | ✅ Verified by test |
| No lifecycle mutation | ✅ Verified by test |
| Bounded poll, idle exit | ✅ Single poll by default, 0 exit code |
| Minimum interval enforcement | ✅ 60s minimum with error message |

## Tests

- **43 focused tests** in `tests/scripts/test_worker_poller.py`
  - 8 registration tests
  - 4 worker/project isolation tests
  - 9 polling tests (including JSON, empty, duplicate)
  - 4 acknowledgement tests
  - 3 payload safety tests
  - 2 malformed state tests
  - 6 no-subprocess/no-HTTP tests
  - 2 no-lifecycle-mutation tests
  - 7 CLI parser tests
- **Full suite:** 278 passed, 2 skipped (pre-existing)
- **Validator:** `scripts/validate.ps1` passes

## Branch & SHA

- Branch: `phase12-events-03-worker-poller`
- SHA: _(to be determined after commit)_

## Residual Risks

| Risk | Mitigation |
|---|---|
| Worker registration file is JSON — manual edit could cause parse errors | `list_workers` returns `[]` on malformed JSON; CLI validation enforced |
| Delivery state is read by path — if directory structure changes, poll breaks | Paths are resolved through `event_routing.DELIVERY_FILE` |
| No authentication on acknowledge — anyone who can write the delivery state file can acknowledge | Acknowledge is informational only; does not grant task claim or execution |
| Polling assumes `ready_assigned` event type — other events ignored | By design per task spec; extendable via protocol constants |
| Interval and jitter are documentation-only — not enforced in continuous mode | Documented for external scheduler configuration |
