# Phase 12 Monitor — Operator Guide

## Purpose

The `orchestrate monitor` command polls registered project repositories for
task-card evidence on remote branches. It detects review-submitted,
ready-assigned, and incident-opened events without modifying any task cards,
branches, or lifecycle state.

## Quick Start

```bash
# 1. Register a project
python scripts/orchestrate.py monitor --add-project \
  --project-id my-project \
  --local-path /path/to/clone \
  --default-branch main

# 2. Run a single poll
python scripts/orchestrate.py monitor --once

# 3. Run with JSON output
python scripts/orchestrate.py monitor --once --json
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

### Event Ledger

Events are appended to `coordination/monitor/events.jsonl` (Git-ignored).
Each event has a deterministic ID and is deduplicated automatically.

### State File

Monitor state (last-seen commits per project/branch) is stored in
`coordination/monitor/state.json` (Git-ignored).

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
  "delivery_state": "pending"
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

## Cadence and Resources

- Default poll interval: 600 seconds (10 minutes)
- Minimum interval: 60 seconds
- One bounded Git fetch per project per poll
- No busy loops, file watchers, or network polling
