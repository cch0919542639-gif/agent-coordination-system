- Task ID: `phase14.5-opencode-api-task-payload-adapter-47`
- Agent: `ORCHESTRATOR`
- Phase: `phase14.5-phase-h-live-pilot`
- Status: submitted for independent review
- Runtime/API activity: none; all transport remains injected and uncalled.

## Changed Files

- `scripts/opencode_live_api.py`
- `scripts/opencode_permission_controller.py`
- `scripts/opencode_loopback_permission_adapter.py`
- `tests/scripts/test_opencode_live_api.py`
- `tests/scripts/test_opencode_permission_controller.py`
- `tests/scripts/test_opencode_loopback_permission_adapter.py`
- Task 47 card and this delivery report.

## Acceptance Criteria Coverage

- Normalizes the observed OpenCode 1.18.32 PermissionRequest shape and returns
  only session/request IDs, permission name, and a canonical digest of patterns.
- Validates the `per` and `ses` prefixes and selects exactly one target from
  the `GET /permission` array, rejecting malformed neighbors and duplicates.
- Renders assigned task objective/context/constraints/scope/acceptance/validation
  from an exact allowlist with a 16 KiB ceiling and private-key/token rejection.
- Uses `/permission/{requestID}/reply` and exactly `{"reply":"once"}`; no
  deprecated `response` body or `remember` field.
- No network, process, environment, credential, or configuration integration
  was added or invoked.

## Validation Steps Performed

- Focused tests: 14 passed after review fixes.
- `python scripts/orchestrate.py validate`: passed.
- `git diff --check`: passed; only existing line-ending warnings were emitted.

## Known Residual Risks

This task only freezes a pure API/payload shape. It does not read task cards,
open an HTTP connection, create a session, send a prompt, or reply to a live
permission. The caller must still bind the normalized request to current
authority and durable one-shot consumption.
