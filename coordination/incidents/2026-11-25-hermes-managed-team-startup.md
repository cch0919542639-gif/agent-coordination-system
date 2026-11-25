# Hermes managed team startup

- Incident ID: hermes-managed-team-startup-01
- Task ID: team-agent-workspaces-01
- Phase: agent-control-center
- Agent: ORCHESTRATOR
- Category: runtime compatibility
- Severity: medium
- Status: open
- Created At: 2026-11-25

## Summary

The installed Hermes v0.23.3 routes its standard ACP through a shared gateway.
Existing console safety checks govern an owned process and cannot establish
control over that gateway. The adjacent legacy Python launcher is absent, so
the existing integration rejects this runtime before launching it.

## What Was Attempted

A temporary experiment instantiated the in-process ACP with an owned session
manager and retained tool, route and approval guards. A disposable empty-profile
handshake succeeded after avoiding an inherited-stdin Git probe. On the real
installation the protected session did not become ready within 90 seconds;
the owned process was confirmed stopped. A separate attempt also exposed the
absence of the optional background process tool. The experimental adapter was
removed rather than enabling an unverified path. No private credentials or
transcripts were inspected, and no shared gateway session was attached.

## Exact Blocker

Protected session creation timed out on the installed runtime.

## Scope / Risk Impact

Current Hermes is unavailable in the console; OpenCode remains independently testable.

## Recommended Next Action

Next: diagnose protected session creation in an isolated fixture, establish
route and approval invariants for this Hermes version, then run a real controlled
file-operation test before enabling the adapter. Do not bypass the guard.
