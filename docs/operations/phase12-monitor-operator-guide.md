# Phase 12 Monitor — Operator Guide

## Purpose

The `orchestrate monitor` command polls registered project repositories for
task-card evidence on remote branches. It detects review-submitted,
ready-assigned, and incident-opened events without modifying any task cards,
branches, or lifecycle state.

## Quick Start

```bash
# 1. Register a project (edit the registry file directly)
# coordination/monitor/projects.json (Git-ignored)
```

```json
[
  {
    "project_id": "my-project",
    "local_path": "/path/to/local/clone",
    "remote_name": "origin",
    "default_branch": "main",
    "monitor_branches": ["agent/worker-01/task-123"]
  }
]
```

```bash
# 2. Configure routing policy
# coordination/monitor/routing_policy.json (Git-ignored)
```

```json
[
  {
    "project_id": "my-project",
    "routes": [
      {"event_type": "review_submitted", "destination": "orchestrator"},
      {"event_type": "ready_assigned", "destination": "registered_worker"},
      {"event_type": "incident_opened", "destination": "orchestrator"}
    ],
    "enabled": true
  }
]
```

```bash
# 3. Run monitor + route in one pass
python scripts/orchestrate.py monitor --route

# 4. Or run separately
python scripts/orchestrate.py monitor --once
python scripts/orchestrate.py route-events
```

## Configuration

### Project Registry

Projects are registered in `coordination/monitor/projects.json` (Git-ignored).

```json
[
  {
    "project_id": "my-project",
    "local_path": "/path/to/local/clone",
    "remote_name": "origin",
    "default_branch": "main"
  }
]
```

**Do not commit local paths to Git.**  The project registry is Git-ignored
because it contains machine-specific paths.

`monitor_branches` is optional. When omitted or empty, the monitor retains
default-branch-only behavior. When present, it is an explicit per-project
allowlist: the monitor checks the default branch and only the listed worker
branches. It does not infer eligible branches from their names or enumerate
all remote heads. Branch names must be normal Git branch names (for example,
no `refs/` prefix, whitespace, or ref-control characters); invalid registry
entries fail closed rather than widening collection.

Worker branches are review-evidence only: a `REVIEW` task card on an allowed
worker branch creates `review_submitted`; ready and blocked cards continue to
be detected on the default branch only.

### Routing Policy

Routing policy is configured in `coordination/monitor/routing_policy.json`
(Git-ignored).

```json
[
  {
    "project_id": "my-project",
    "routes": [
      {"event_type": "review_submitted", "destination": "orchestrator"},
      {"event_type": "ready_assigned", "destination": "registered_worker"},
      {"event_type": "incident_opened", "destination": "orchestrator"}
    ],
    "enabled": true
  }
]
```

### Event Ledger

Events are appended to `coordination/monitor/events.jsonl` (Git-ignored).
Each event has a deterministic ID and is deduplicated automatically.

### State File

Monitor state (last-seen commits per project/branch) is stored in
`coordination/monitor/state.json` (Git-ignored).

### Delivery State

Delivery records are stored in `coordination/monitor/delivery/delivery_state.jsonl`
(Git-ignored). Records include acknowledgement, retry, and failure state.

## Event Types

| Event | Trigger | Description |
|---|---|---|
| `review_submitted` | Task card in `review/` | Worker submitted for review |
| `ready_assigned` | Task card in `ready/` with owner | Task ready and assigned |
| `incident_opened` | Task card in `blocked/` | Task blocked, incident needed |
| `fetch_failed` | Git fetch error | Network or remote issue |

## Event Schema

```json
{
  "event_id": "<deterministic-hash>",
  "project_id": "my-project",
  "repository": "/path/to/clone",
  "ref": "main",
  "commit": "<sha>",
  "task_id": "phase12-events-01",
  "event_type": "review_submitted",
  "detected_at": "2026-07-17T12:00:00Z",
  "delivery_state": "pending",
  "owner": "agent-name",
  "reviewer": "ORCHESTRATOR"
}
```

## What It Does NOT Do

- Does **not** claim, dispatch, review, merge, or push
- Does **not** change task-card lifecycle or assignments
- Does **not** create branches, commits, or worktrees
- Does **not** call LLMs, GitHub APIs, or external services
- Does **not** store credentials, prompts, or source code

## Exit Codes

- **0**: all projects scanned successfully
- **1**: one or more health issues (fetch failures)

## Recovery

### Fetch Failed

```
Symptom: fetch_failed health event
Fix: Check network connectivity and remote URL in projects.json
```

### No Events Detected

```
Symptom: monitor runs but finds no events
Fix: Verify project has task cards in coordination/task-board/{review,ready,blocked}/
```

### Stale State

```
Symptom: events not updating after pushes
Fix: Delete coordination/monitor/state.json to reset cursors
```

### Disable Worker-Branch Monitoring

```
Symptom: a worker branch should no longer be monitored
Fix: Remove that exact name from monitor_branches in projects.json, then run one normal poll.
```

The saved cursor is intentionally retained for a removed branch. Re-adding it
later does not lose other branch cursors; delete `state.json` only when an
operator intentionally wants every configured ref to be re-evaluated.

### Routing Policy Errors

```
Symptom: events detected but no delivery records created
Fix: Validate routing_policy.json — check project_id, event_type, destination
```

## Cadence and Resources

- Default poll interval: 600 seconds (10 minutes)
- Minimum interval: 60 seconds
- One bounded, depth-one Git fetch per project per poll, limited to the
  configured default branch plus the explicit worker-branch allowlist
- No busy loops, file watchers, or network polling

Each additional configured worker branch adds only one refspec and one local
object inspection pass. Keep the normal 10-minute cadence; use the 1-minute
minimum only for supervised diagnosis.

## usage-mvp-01 Verification Recipe

For the first local-loop verification, register the existing worker branch
alongside the default branch in the ignored local registry:

```json
[
  {
    "project_id": "agent-usage-collector",
    "local_path": "/path/to/agent-usage-collector",
    "remote_name": "origin",
    "default_branch": "main",
    "monitor_branches": [
      "agent/external-agent-research-01/usage-mvp-01"
    ]
  }
]
```

With the existing routing policy mapping `review_submitted` to
`orchestrator`, run:

```bash
python scripts/orchestrate.py monitor --json
python scripts/orchestrate.py route-events --json
```

Confirm one sanitized event for task `usage-mvp-01` with event type
`review_submitted`, ref
`agent/external-agent-research-01/usage-mvp-01`, its commit SHA, owner, and
reviewer; then confirm one orchestrator delivery record. Do not copy task-card
body content, absolute local paths, or live delivery records into reports.
