---
name: coordination-worker
description: Run one bounded, owner-strict task handoff from the repository coordination system. Use only for a scheduled Hermes worker turn after the orchestrator has assigned a task to this worker.
---

# Controlled Coordination Worker

Run exactly one cycle from the configured coordination repository root.

1. Run `python scripts/orchestrate.py worker activate hermes-coordination-pilot --json`.
2. If it reports no eligible delivery, stop without changing files.
3. If it emits a payload, verify its `worker_id` is
   `hermes-coordination-pilot`, then read the named task card and
   `docs/operations/agent-task-execution-protocol.md`.
4. Confirm the task is in `coordination/task-board/ready/` and its owner
   matches `hermes-coordination-pilot`. Claim it, update progress, and work
   only inside its `allowed_scope`.
5. If blocked, create the required incident and stop. Do not guess or ask a
   headless user for clarification.
6. When finished, create repository delivery evidence and move the card to
   `review/`. Stop immediately.

Never run Hermes Kanban. Never select an unassigned task. Never process a
second payload in the same turn. Never auto-accept, review, merge, commit,
push, or launch another agent.
