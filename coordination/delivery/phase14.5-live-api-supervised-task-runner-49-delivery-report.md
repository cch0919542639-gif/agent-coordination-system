# Task 49 Delivery Report — Live API Supervised Task Runner

- Task ID: `phase14.5-live-api-supervised-task-runner-49`
- Agent: `ORCHESTRATOR`
- Phase: `phase14.5-phase-h-live-pilot`
- Status: independently accepted after needs-fix re-review
- Date: 2026-09-27
- Runtime/API activity: none; request builders and transport callbacks were not invoked against a live service.

## Changed Files

- `scripts/local_opencode_live_runner.py`
- `scripts/local_opencode_executor.py`
- `scripts/one_shot_consumption.py`
- `tests/scripts/test_local_opencode_live_runner.py`
- `tests/scripts/test_local_opencode_executor.py`
- `tests/scripts/test_one_shot_consumption.py`
- Task 49 card, Task 48 review evidence, and this delivery report.

## Acceptance Criteria Coverage

- `scripts/local_opencode_live_runner.py` now builds version-pinned OpenCode
  session requests and orchestrates assigned task delivery to an exact session.
  It reloads a strict allowlist of task-card fields, requires current
  `IN_PROGRESS` ownership, checks the assigned worktree resolver's agent/grant/
  worktree identity, bounds and filters the prompt, and verifies the created
  session's returned directory before sending it.
- The v1.18.32 request map is `POST /session?directory=...`,
  `POST /session/{sessionID}/prompt_async`, `GET /session/status`, and
  `POST /session/{sessionID}/abort`. Session creation, prompt delivery, status,
  heartbeat, abort, and clocks remain injected. The pinned route and schema
  definitions are documented in the [OpenCode session API source](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.32/packages/opencode/src/server/routes/instance/httpapi/groups/session.ts), [session schema](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.32/packages/opencode/src/session/session.ts), and [prompt schema](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.32/packages/opencode/src/session/prompt.ts).
- Approval and exact binding identities are durably claimed before session
  creation. Permission handling checks the current approval, exact local-control
  record, a session claim persisted from the exact API-created session, and the
  current GET `/permission` item. It compares the request action and resource
  digest to the current assigned task card's explicit `permission_policy`,
  whose digest is included in the durable session claim. Missing or mismatched
  policy, foreign sessions, and unapproved actions/resources fail closed before
  permission consumption. The exact session/permission identity is then
  durably claimed before the injected one-time `reply` callback.
  No raw permission patterns or metadata enter the ledger or result.
- `scripts/local_opencode_executor.py` replaces caller-provided fake check
  timestamps and in-memory replay state with required durable state and an
  injected monotonic loop. It polls the exact child, checks heartbeat deadlines,
  respects the lesser of request timeout and hard ceiling, and terminates only
  the bound process tree.

## Validation Steps Performed

- Focused regression modules: 52 passed, 1 skipped. The skip is explicit where
  Windows account policy prevents creation of a symlink fixture.
- Command: `python -m pytest -p no:cacheprovider --basetemp _pytest_tmp_task49fix tests/scripts/test_local_opencode_live_runner.py tests/scripts/test_local_opencode_executor.py tests/scripts/test_one_shot_consumption.py tests/scripts/test_opencode_live_api.py tests/scripts/test_opencode_loopback_permission_adapter.py tests/scripts/test_opencode_permission_controller.py -q`.
- `py_compile` on the changed runner/executor and their API/store dependencies:
  passed.
- `python scripts/orchestrate.py validate`: passed.
- `git diff --check`: passed; Git printed only its existing LF/CRLF conversion
  warnings.

## Known Residual Risks

- Tests use fake session transports, fake clocks, and fake child processes. No
  server, HTTP call, model/provider request, runtime, or worker was started.
- The caller-supplied session-state callback must map observed session evidence
  to `running`, `completed`, or `failed`; unknown states abort only that session.
  The injected callbacks are the transport boundary for this repository task.
- The permission caller must reload the current task card and pass its exact
  `permission_policy` together with the runner-returned session binding. Cards
  without an explicit policy cannot approve a permission request.
- This review submission is not permission for a live pilot. Any pilot needs a
  separate fresh user authorization. No commit or push was performed.
