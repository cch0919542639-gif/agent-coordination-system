# Phase 14 Worker Bootstrap Guide

## Purpose

One-time setup and per-worker heartbeat configuration for same-machine
automatic worker handoff.  This guide configures an already-running agent
session to poll; it does not launch an agent.

## Prerequisites

- Python 3.12+ installed on the coordination host machine
- A local clone of the coordination repository
- A local clone of the project repository the worker will serve
- The central monitor heartbeat already running (`monitor --route`)

## One-Time Setup

### 1. Register the Worker

```bash
python scripts/orchestrate.py worker register <worker-id> <project-id>
```

Example:

```bash
python scripts/orchestrate.py worker register worker-collector agent-usage-collector
```

Verify:

```bash
python scripts/orchestrate.py worker list
```

### 2. Verify Routing Policy

Ensure the project's routing policy routes `ready_assigned` events to
`registered_worker`:

```json
[
  {
    "project_id": "agent-usage-collector",
    "routes": [
      {"event_type": "ready_assigned", "destination": "registered_worker"}
    ],
    "enabled": true
  }
]
```

### 3. Test Manual Activation

```bash
python scripts/orchestrate.py worker activate <worker-id>
```

If a pending delivery exists for this worker, the command first writes one
safe action payload to `coordination/monitor/inbox/<worker-id>/` and then
acknowledges the delivery. The payload's task-card path is resolved from the
registered product checkout and is always repository-root-relative. If not,
you will see "No eligible delivery."

## Per-Worker Heartbeat Configuration

### Codex Heartbeat

If the worker runs inside a Codex session, configure the session's periodic
check to run the activation command:

```bash
# In the Codex session, add to the periodic check:
python scripts/orchestrate.py worker activate <worker-id> --json
```

The `--json` flag produces a machine-readable payload that the agent session
can parse directly.

### Generic Local Runtime

For any local agent runtime (MiMo, custom scheduler, cron):

```bash
# Single-shot bounded activation (no busy loop)
python scripts/orchestrate.py worker activate <worker-id> --json
```

### Recommended Cadence

| Cadence | Use Case |
|---|---|
| 10 minutes | Normal production heartbeat |
| 1 minute | Supervised debugging only |
| Manual | Ad-hoc testing |

**Never use a busy loop.**  Each invocation is a single bounded poll.

## What Activation Does

1. Reads the shared delivery state (Git-ignored, local only).
2. Finds the first pending `ready_assigned` record matching this worker's
   project and owner.
3. Resolves the card in the registered product checkout and writes one safe,
   worker-specific inbox payload atomically.
4. Emits that payload with task ID, project, ref, and instructions.
5. Acknowledges the delivery only after the inbox file is durable.

## What Activation Does NOT Do

- Does **not** claim, move, or modify any task card.
- Does **not** launch an agent, process, shell, or subprocess.
- Does **not** call HTTP, webhooks, GitHub APIs, or external services.
- Does **not** store credentials, prompts, or source code.
- Does **not** make review or merge decisions.

## Failure Modes

| Condition | Result |
|---|---|
| Worker not registered | Exit code 1, error on stderr |
| Worker disabled | Exit code 1, error on stderr |
| No pending delivery | Exit code 0, "no eligible delivery" |
| Empty owner | Exit code 0, activation skipped |
| Owner mismatch | Exit code 0, activation skipped |
| Already acknowledged | Exit code 0, activation skipped |
| Retry-pending / failed | Exit code 0, activation skipped |
| Malformed record | Skipped silently, other records processed |
| Missing/ambiguous product task card | Exit code 1; delivery remains pending |
| Inbox write failure | Exit code 1; delivery remains pending |

## Recovery

### Worker Not Seeing Deliveries

```
Symptom: activate returns "no eligible delivery" despite ready tasks
Fix: Verify worker registration and project_id match the routing policy
```

### Activation Returns Error

```
Symptom: exit code 1 from activate
Fix: Check worker registration: python scripts/orchestrate.py worker list
```

### Stale Delivery State

```
Symptom: old acknowledged records blocking new deliveries
Fix: The system is idempotent; acknowledged records are skipped automatically
```

## Monitoring

```bash
# Check delivery state
cat coordination/monitor/delivery/delivery_state.jsonl | python -m json.tool

# Inspect a worker's durable handoff inbox
Get-ChildItem coordination/monitor/inbox/<worker-id>

# List registered workers
python scripts/orchestrate.py worker list

# Test activation
python scripts/orchestrate.py worker activate <worker-id> --json
```
