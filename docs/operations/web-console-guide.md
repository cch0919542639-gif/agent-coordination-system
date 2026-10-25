# Local Web console operator guide

Phase5 is accepted locally in owned fixtures; this guide documents manual use.
It does not start a server, create accounts or authorize real runtime/provider/
publication activation. See the [accepted record](../../coordination/evidence/coordination-v2-01/web-phase-summary.md)
and [frozen contract](web-console-contract.md). Existing runtime/controllers and
legacy FastAPI service are unchanged; this console is `web.api`.

## Explicit finite launch

Use installed Python3.12 from the repository root only after the target and access
configuration have been deliberately supplied. Every value in angle brackets
below is a placeholder, not an existing account, private path or runnable setup.

```text
python -B -m web.api --repo "<ABSOLUTE_REPOSITORY>" --db "<ABSOLUTE_SCHEMA4_DB>" --workspaces "<ABSOLUTE_WORKSPACE_ROOT>" --project-id "<PROJECT_ID>" --auth-file "<EXTERNAL_AUTH_JSON>" --port 8765 --duration 300
```

All five named path/project arguments are required. The service binds IPv4
`127.0.0.1` only; CLI port1024..65535, duration10..1800seconds. Defaults are8765
and300seconds; no installation/autostart/daemon is supplied. Open the exact
`http://127.0.0.1:PORT` origin printed at startup on this host, without a reverse
proxy or `localhost` substitution. Host/Origin checks require that exact origin.
The finite server stops at its duration; logout ends only the browser session.
Starting it never creates/migrates a DB, enables mode or supplies default accounts.
A missing DB displays repository metadata with runtime unavailable. An existing
foreign/schema/binding conflict refuses; use the separately governed runtime
setup/migration procedure, not an invented UI initialization step.

## External authentication

The operator must deliberately supply an external canonical auth-file path outside
both repository and workspace root. Maximum16KiB, schema_version1,1..8 unique
usernames, exact fields shown below. All values in angle brackets are placeholders;
this template is intentionally incomplete and contains no usable credential.

```json
{
  "schema_version": 1,
  "users": [
    {"username": "<VIEWER_USERNAME>", "role": "viewer", "token_sha256": "<64_LOWERCASE_HEX_SHA256>"},
    {"username": "<OPERATOR_USERNAME>", "role": "operator", "token_sha256": "<64_LOWERCASE_HEX_SHA256>"},
    {"username": "<ADMIN_USERNAME>", "role": "administrator", "token_sha256": "<64_LOWERCASE_HEX_SHA256>"}
  ]
}
```

A login token is random32bytes encoded URL-safe without padding (43characters).
Store only the lowercase64-hex SHA256 digest of its UTF-8 token string in the
external file; enter the original token in the login form. Usernames must satisfy
the existing Controller identifier rules. File permissions remain the operator's
responsibility. Do not put tokens/configuration in repo, URL query, screenshots,
logs or browser storage. This docs task creates no credentials or permissions.

The server issues a port-specific HttpOnly/SameSite=Strict cookie and a separate
CSRF value in JS memory. Sessions expire after15minutes; maximum8 concurrent
sessions, failed login budget5/minute per server. Logout invalidates that session
and its preview plans. HTTP loopback provides no TLS; use a trusted local host and
browser. Public hosting and hostile OS/browser isolation are outside this contract.

| Role | Server-enforced capability |
| --- | --- |
| Viewer | Read seven views |
| Operator | Reads, live run inspection, Controller dry-run previews |
| Administrator | Same capabilities plus execute own session's valid preview |

Changing hidden controls cannot grant permission. An Operator's preview cannot be
transferred to an Administrator; that Administrator must create a fresh preview
in their own session. No account/permission editor is exposed.

## Read actual state

Overview, Task Board, Agent Monitor, Workspace Explorer, Review Center, Events
and Settings read bounded real repository/schema4 projections. Task cards and
canonical reviews remain formal lifecycle authority. Persisted PID/exit/check/
publication receipts are historical; a row is not fresh tree-stop, Git validation,
health or acceptance proof. Use the permitted live inspection when needed.
Missing runtime is unavailable, not zero/healthy. No task/review bodies, transcripts,
argv, arbitrary workspace files or absolute backend paths are exposed.

Only the current view polls:5seconds visible/60seconds hidden, one pending request.
The runtime SQL snapshot is fresh per request. Repository metadata may be10seconds
old, including after manual refresh; successful HTTP mutation invalidates its cache.
Preview leaves cache intact. Mutations independently recheck Controller state.
Page size is at most100; events default50/max100 by sequence cursor, retaining100
DOM rows. The board scan refuses beyond4096entries/2048cards/8MiB total/64KiB per
card rather than inventing a complete view. Updating errors retain the last data;
check the status/error and timestamp before treating it as current.

## Preview, check, confirm

1. Open Settings with Operator or Administrator and inspect a specific run if
   needed. Obtain current expected fields; do not infer them from stale receipts.
2. Select an allowed action and enter its exact arguments below. Generate a
   preview; inspect its result before proceeding. Preview does not grant authority.
3. Administrator confirms their own preview within60seconds. Its random plan is
   session-bound and one-use; execute accepts the plan, not replacement arguments.
4. Controller rechecks version/fence/resource sequence/intent preimage/quiescence.
   Expired/consumed/refused plans require refresh and a new preview. A Controller
   refusal consumes the plan; there is no automatic retry. Verify the returned
   result and fresh state after execution.

| Action | Required arguments |
| --- | --- |
| recovery.reconcile | run_id, request_id, expected_version, expected_fence, reason (`expired` or `interrupted`) |
| resource.probe | none; preview samples, execute can open the latch |
| resource.reset | expected_sequence; healthy/quiescent/known checker state required |
| board.reconcile / board.cancel | exact request_id |
| parallel.disable | none; quiescent checks still apply |

Version/sequence are nonnegative integers, fence at least1. Recovery does not
prove an unknown tree stopped or authorize relaunch/deletion; unknown slots and
dirty work remain held. Board compensation is the separate exact intent operation.
There is no worker start/kill, provider dispatch, Parallel enable, generic SQL/
command, formal acceptance or ref-publication endpoint. Web login roles do not add
actor attribution to historical Controller receipts.

## Refusals and measured limits

401 requires login again;403 indicates role/origin/CSRF refusal, not a request to
relax those gates.429 requires waiting/reducing requests or releasing sessions.
400/413/415 indicates malformed/oversize/non-JSON input.409 Controller refusal
requires fresh state and preview;503 means local service unavailable. Configuration
failure prints a private fixed message and exits2; invalid CLI range is refused.
Do not bypass a foreign DB, board conflict, resource latch or unknown process tree.

The accepted204-card warm API fixture measured1.978% of one CPU core and28.37MiB
working set over30.016s on this host; browser/provider/all-host costs are unmeasured.
Earlier5.31%/3.28% misses remain evidence. Hidden polling was tested with simulated
Visibility API in real Edge timers, not OS-native-hidden proof. Three minor paging/
session/enumeration findings were repaired and independently closed. See the
[phase record](../../coordination/evidence/coordination-v2-01/web-phase-summary.md)
for distinct runs and provenance. Actual Phase6 provider pilots and publication
require separate authorization and dedicated owner/scope/resource contracts.
