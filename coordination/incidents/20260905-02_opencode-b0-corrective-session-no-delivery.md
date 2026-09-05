# Incident: OpenCode B0 corrective session ended without delivery

- Incident ID: 20260905-02-opencode-b0-corrective-session-no-delivery
- Task ID: phase14.5-bootstrap-01
- Phase: phase14.5-bootstrap-connector
- Agent: external-agent-platform-33
- Severity: high
- Category: capability_mismatch
- Status: open
- Created At: 2026-09-05

## Summary

The explicitly approved corrective OpenCode session began reading the returned
B0 task and review report, then exited without repository changes, progress
updates, or a review submission.

## What Was Attempted

- The local OpenCode executable was restored by its package postinstall and
  responds with version `1.18.27`.
- The session used the reviewed B0 least-privilege profile and the isolated B0
  worktree.
- The session read the task card and review report. No credentials, raw logs,
  prompts, provider output, or transcript content were inspected or recorded.
- The worktree remained unchanged after the session exited.

## Exact Blocker

The current headless OpenCode invocation does not provide a reliable,
observable transition from assigned corrective handoff to repository delivery
under the reviewed least-privilege profile. A third attempt would be an
automatic retry, which the B0 task explicitly forbids.

## Scope / Risk Impact

No B0 implementation, task acceptance, commit, push, credential access, or
unapproved retry occurred. The restored OpenCode binary is a local runtime
repair only; it does not prove reliable delegated delivery.

## Recommended Next Action

Open a separately reviewed connector-observability and launcher task that can
prove acknowledgement, bounded execution outcome, and terminal status before
using OpenCode for further delegated implementation. Resolve or reassign B0
only through an explicit orchestrator decision.
