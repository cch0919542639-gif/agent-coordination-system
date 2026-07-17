# Phase 14 Same-Machine Worker Automation Plan

## Goal

Complete automatic task handoff for workers running on the same Windows
machine as the coordination host. This phase uses the existing local,
Git-ignored monitor runtime in `D:\codex work\coordination\monitor\` and
does not attempt cross-machine delivery.

## Boundary

Phase 14 automates evidence discovery and worker wake-up preparation. It does
not grant a process the authority to claim, implement, review, merge, or push
a task without that worker agent following the existing protocol.

An LLM agent cannot be universally launched by a Python script: Codex,
MiMo, and other runtimes own their own sessions. The supported contract is a
per-worker heartbeat or scheduler that runs a bounded local poll command, then
lets the already-running agent session decide whether to claim its own task.

## Target Loop

```text
lead writes and pushes ready task card
        |
        v
central heartbeat: monitor --route
        |
        v
shared local delivery state (owner-strict)
        |
        v
each local worker heartbeat: worker poll <worker-id>
        |
        v
worker claims only its matching task and executes in its worktree
        |
        v
worker pushes review evidence; central heartbeat wakes orchestrator
```

## Rules

1. All local worker polling reads the shared coordination checkout at
   `D:\codex work`; task implementation may occur in a separate worktree.
2. Delivery is fail-closed. A missing, empty, or mismatched owner reaches no
   worker.
3. A worker heartbeat must use a bounded single poll, not a busy loop.
4. A notification acknowledgement confirms receipt only. It never claims or
   starts a task by itself.
5. The worker's agent runtime is the only component allowed to claim its
   matching task after it reads the task card and protocol.
6. All monitor, worker, inbox, and scheduler state remains Git-ignored local
   runtime data. No machine path, credential, or live delivery record is
   committed.

## Delivery Steps

1. Implement a local worker activation command that reads an owner-strict
   notification once, acknowledges only after durable handoff preparation, and
   emits a compact, safe action payload for the local agent heartbeat.
2. Add a worker bootstrap guide for Codex and generic local runtimes, including
   one-time registration, bounded cadence, stop conditions, and recovery.
3. Add two-worker same-machine end-to-end tests proving no cross-owner handoff,
   no duplicate activation, no lifecycle mutation before the worker claims, and
   no subprocess/HTTP/agent launch.
4. Install one real worker heartbeat after the test gate is accepted, then run
   `agent-usage-collector` as the first live local-worker project.
5. Only after this loop is stable, design Phase 15 cross-machine delivery.

## Success Criteria

- A ready task assigned to local worker A appears only in A's bounded poll.
- A's local agent heartbeat can receive a safe action payload without manual
  copy/paste of the task details.
- Worker B cannot see or acknowledge A's delivery.
- Review evidence wakes the central orchestrator heartbeat.
- The loop uses no GitHub API polling, webhook, credential, public service,
  process launch, or automatic review/merge decision.
