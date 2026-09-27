# Task 46 — installed runtime schema diagnostic

- Task ID: `phase14.5-opencode-live-integration-46`
- Agent: `ORCHESTRATOR`
- Phase: `phase14.5-phase-h-live-pilot`
- Status: independently accepted diagnostic result; DONE
- Observed date: `2026-09-27`

## Changed Files

Probe script/tests, Task 46 card/review/report, PROGRESS.md, handoff.md,
orchestrator progress and incident 20260925-12 corrections.
Also backfilled missing headings in Task 39–45 cards/reports/reviews and
Task 42's coordinator worktree provenance, without changing historical review
decisions or granting retries/launches.

## Acceptance Criteria Coverage

Independent safety review accepted script SHA256
`c2a02ad16c0939c595d3bc771d32d49cbaab92c0ff42d3cc7d7273e134db0fe9`
before one execution. Runtime SHA256:
`cf664aa1da32b788f9b2699b84a9bb9be30b7e025693b90f9b85829d5fe4e252`.

Observed `schema_observed`, version `1.18.32`, exit code 0,
`server_stopped: true`; command duration approximately 4.73 seconds.
One server spawn, no model prompt, permission reply or pilot attempt.
Helper requests were only GET `/global/health` and `/doc`; no session data,
provider configuration or credential query. Runtime logs were discarded.
This does not establish enforced isolation or absence of every internal
OpenCode startup side effect.

### Observed public API shape

| Endpoint | Observed shape |
| --- | --- |
| GET `/permission` | array of PermissionRequest references |
| POST `/permission/{requestID}/reply` | required reply string; optional message; boolean 200 |
| POST `/session/{sessionID}/permissions/{permissionID}` | required response string; remember not declared; boolean 200 |
| POST `/session` | optional parent/title/agent/model/metadata/permission/workspace fields |
| POST `/session/{sessionID}/prompt_async` | required parts; optional model/agent/tools/system/format/variant fields; 204 |
| POST `/session/{sessionID}/abort` | boolean 200 |
| GET `/session/status` | object with SessionStatus values |

Task 44's response/remember body is not the modern reply endpoint's body.
A legacy response endpoint exists; this does NOT prove prior worker nonzero
exits were caused by the mismatch. Task 45's injected raw request shape is
not yet verified against concrete PermissionRequest fields. Component refs
were retained but not expanded, and enums were not retained; do not invent them.

## Validation Steps Performed

- Independent reviewer: 9 probe tests passed after timeout/schema/lifecycle fixes.
- Coordinator combined Task 44/45/probe regression: 17 passed.
- Compilation and diff whitespace checks: passed (line-ending warnings).
- Single reviewed live diagnostic: passed; owned server stopped.
- Global coordination validation: initially failed on historical Task 39–45
  metadata/report gaps; passed after scoped heading/provenance backfills.

## Known Residual Risks

L1 best-effort only. No successful six-worker pilot, actual task/context delivery,
provider/model success, current approval lifecycle, durable permission consumption
or live heartbeat proven here. Future launch must pin native binary, not only
shim, and cannot reuse expired Task 43. Next: verify referenced request schemas,
map actual API and bounded task payload, wire current authority and supervision,
and review before fresh pilot. No additional probe spawn is allowed by Task 46.
