# Incident: OpenCode bootstrap runtime is not ready

- Incident ID: 20260903-01-opencode-bootstrap-probe-failed
- Task ID: phase14.5-bootstrap-01
- Phase: phase14.5-bootstrap-connector
- Agent: ORCHESTRATOR
- Severity: high
- Category: environment_failure
- Status: open
- Created At: 2026-09-03

## Summary

The local OpenCode candidate cannot yet receive the requested bootstrap task.

## Exact Blocker

The requested manual OpenCode bootstrap cannot start: its bounded runtime probe
returned the sanitized status `probe_failed`, and the task's assigned worktree
reference `worktrees/external-agent-platform-33/phase14.5-bootstrap-01` does
not exist.

## Scope / Risk Impact

No OpenCode session, handoff activation, worktree creation, task-card
lifecycle transition, credential read, or network task execution was started.
Treating the generated dispatch text as delivered work would misrepresent the
task state.

## What Was Attempted

- Ran `python scripts/orchestrate.py runtime-preflight --runtime opencode --probe --json`.
- Verified the assigned task worktree reference is absent.

## Recommended Next Action

The operator must repair or select an approved OpenCode runtime, then rerun the
bounded preflight successfully. After the bootstrap task is integrated and the
specified worktree is provisioned, record the exact one-shot manual launch
approval before starting the external worker.
