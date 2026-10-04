# Phase 14.5 Local OpenCode Transport

`scripts/opencode_loopback_transport.py` supplies Python standard-library
callbacks to Task 49's `run_assigned_task` and
`reply_assigned_permission`. It binds to one exact `http://127.0.0.1:<port>`
origin and uses direct `HTTPConnection`; it does not consult proxy settings,
follow redirects, retry a request, launch a server, or inspect OpenCode
configuration or credentials.

The transport is only an adapter. It does not read or approve a launch grant.
The caller must first pass Task 49's current-approval, exact-binding, durable
one-shot, task-card ownership, and worktree checks. Permission replies must go
through `reply_assigned_permission`; `transport.send` only implements the
modern `{"reply":"once"}` wire shape and must not be used as a permission
decision.

Session completion is deliberately conservative. OpenCode omits idle sessions
from `GET /session/status`, so absence is initially treated as running. The
adapter reports completion only after it has observed `busy` or `retry` for
that exact newly-created session and later observes idle. Unknown/malformed
status is unavailable and the supervised runner stops the exact session. If a
very short task finishes before the first busy sample, this may time out and
stop rather than infer success. An accepted review of the task card remains a
separate human decision.

The API contract is pinned to OpenCode v1.18.32:

- [Session routes](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.32/packages/opencode/src/server/routes/instance/httpapi/groups/session.ts) define creation, async prompt, session status, message reads, and exact-session abort.
- [Session status schema](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.32/packages/schema/src/session-status-event.ts) contains `idle`, `retry`, and `busy`; idle is also the default when a session is absent from the in-memory status map.
- [Permission routes](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.32/packages/opencode/src/server/routes/instance/httpapi/groups/permission.ts) define the current pending-permission list and one-time `reply` endpoint.

Validation uses injected fake HTTP connections only. This adapter has not been
connected to a running OpenCode server, used to submit a task, or used to reply
to a permission. Any live task run still requires a fresh exact user approval
and independent review of its current launch packet.
