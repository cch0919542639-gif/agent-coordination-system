# Codex Heartbeat Operator Guide

## Purpose

This guide documents how the orchestrator enables a bounded Codex heartbeat
that periodically checks for new monitor events and wakes the orchestrator
for evidence inspection.  It separates what the automation checks from what
still requires reviewer or worker decisions.

## What the Heartbeat Does

The heartbeat is a **local, bounded check** that:

1. Runs `python scripts/orchestrate.py monitor --once` to poll registered
   project repositories for task-card evidence on remote branches.
2. Inspects the event ledger for new `review_submitted`, `ready_assigned`,
   or `incident_opened` events.
3. If new events exist, prints a wake-up summary for the operator to act on.
4. If no events exist, returns an idle result with no further action.

The heartbeat **never**:

- Claims, dispatches, reviews, merges, or pushes tasks.
- Modifies task-card lifecycle or assignments.
- Creates branches, commits, or worktrees.
- Calls LLMs, GitHub APIs, or external services.
- Stores credentials, prompts, or source code.
- Launches agents or invokes subprocesses beyond the bounded Git checks.

## What Still Requires Human Decisions

The heartbeat surfaces evidence; it does not decide:

| Action | Who Decides |
|---|---|
| Review acceptance | Reviewer (ORCHESTRATOR) |
| Scope changes | Operator |
| Task reassignment | Operator |
| Safety escalation | Operator |
| External agent execution | Worker (via registered poller) |

## Cadence

### Default: 10 Minutes

```bash
# Recommended cron entry (every 10 minutes)
*/10 * * * * cd /path/to/agent-coordination-system && python scripts/orchestrate.py monitor --once
```

**Why 10 minutes is sufficient:**

- The heartbeat runs bounded local/Git checks only: one `git fetch` per
  registered project, then local object inspection.
- When no event is pending, it returns an idle result without broad repo
  reading or LLM calls.
- LLM/token cost is negligible: no prompts are sent, no models are invoked.
- GitHub API rate limits are not approached with this cadence.

### Minimum: 1 Minute (Supervised Debugging Only)

```bash
# Only for short supervised debugging sessions
*/1 * * * * cd /path/to/agent-coordination-system && python scripts/orchestrate.py monitor --once
```

**Use 1-minute cadence ONLY when:**

- Actively debugging a specific event detection or routing issue.
- Verifying that a recent push is detected correctly.
- Supervised by an operator who will revert to 10-minute cadence after
  the issue is resolved.

**Never use 1-minute cadence as the normal operating mode.**  It provides no
meaningful benefit for routine monitoring and wastes Git fetch resources.

## Setup Sequence

### 1. Register Projects

```bash
python scripts/orchestrate.py monitor --add-project \
  --project-id agent-usage-collector \
  --local-path /path/to/agent-usage-collector \
  --default-branch main
```

Replace `agent-usage-collector` with your project's identifier and
`/path/to/agent-usage-collector` with the local clone path.

**Do not commit local paths to Git.**  The project registry
(`coordination/monitor/projects.json`) is Git-ignored because it contains
machine-specific paths.

### 2. Configure Routing Policy

Create `coordination/monitor/routing_policy.json`:

```json
[
  {
    "project_id": "agent-usage-collector",
    "routes": [
      {"event_type": "review_submitted", "destination": "orchestrator"},
      {"event_type": "ready_assigned", "destination": "registered_worker"},
      {"event_type": "incident_opened", "destination": "orchestrator"}
    ],
    "enabled": true
  }
]
```

### 3. Register Workers (Optional)

If external workers will poll for ready-assigned tasks:

```bash
python scripts/orchestrate.py worker register <worker-id> <project-id>
```

### 4. Run a Test Poll

```bash
python scripts/orchestrate.py monitor --once
python scripts/orchestrate.py monitor --once --json
```

### 5. Set Up Cron

Add to crontab:

```bash
crontab -e
```

```cron
*/10 * * * * cd /path/to/agent-coordination-system && python scripts/orchestrate.py monitor --once >> coordination/monitor/heartbeat.log 2>&1
```

## First-Project Onboarding (Example)

Using `agent-usage-collector` as a generic example:

```bash
# 1. Register the project
python scripts/orchestrate.py monitor --add-project \
  --project-id agent-usage-collector \
  --local-path /path/to/agent-usage-collector \
  --default-branch main

# 2. Verify registration
python scripts/orchestrate.py monitor --once --json

# 3. Set up routing policy (see above)

# 4. Register a worker for this project
python scripts/orchestrate.py worker register worker-collector agent-usage-collector

# 5. Enable cron at 10-minute cadence
```

## Stop Conditions

Stop the heartbeat and investigate if:

- `monitor --once` returns exit code 1 (fetch failures).
- The event ledger shows repeated `fetch_failed` events for a project.
- Routing policy validation errors appear in output.
- A worker reports unexpected notifications.

## Recovery Actions

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

### Routing Policy Errors

```
Symptom: events detected but no delivery records created
Fix: Validate routing_policy.json — check project_id, event_type, destination
```

### Worker Not Seeing Notifications

```
Symptom: worker poll returns "No pending work" despite ready tasks
Fix: Verify worker registration and project_id match the routing policy
```

## Monitoring the Monitor

To check heartbeat health:

```bash
# View recent heartbeat log
tail -20 coordination/monitor/heartbeat.log

# Check event ledger
cat coordination/monitor/events.jsonl | python -m json.tool

# Check delivery state
cat coordination/monitor/delivery/delivery_state.jsonl | python -m json.tool

# List registered workers
python scripts/orchestrate.py worker list
```

## Resource Usage

| Resource | 10-min Cadence | 1-min Cadence |
|---|---|---|
| Git fetches per hour | 6 per project | 60 per project |
| LLM tokens | 0 | 0 |
| API calls | 0 | 0 |
| Disk I/O | Negligible (one JSONL append) | Negligible |
| CPU | Bounded (one subprocess per project) | Bounded |

## What This Guide Does NOT Cover

- Automatic review acceptance or merge decisions.
- Direct control of third-party agent processes.
- Webhook-based event notification.
- Credentials management.
- Dashboard or hosted monitoring services.

These remain operator-governed through existing Phase 11 and Phase 12
protocols.
