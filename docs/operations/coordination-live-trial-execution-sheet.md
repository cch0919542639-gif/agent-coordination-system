# Coordination API — Live-Trial Execution Sheet

## Overview

Run one real task through the coordination system from dispatch to review.
Record timings, failures, manual interventions, and observations.
After the trial, complete the retrospective to capture lessons.

## Preconditions

Before starting, confirm:

- [ ] Coordination API is running (see [Startup Guide](coordination-api-startup-guide.md))
- [ ] All [Live-Readiness Checks](coordination-live-readiness-checklist.md#live-readiness-checks) pass
- [ ] Smoke tests pass (`python scripts/smoke_test_coordination.py --task-id trial-prep --agent-id agent-pilot`)
- [ ] Trial agents are configured: `orchestrator` (server key) and `agent-pilot` (client key)
- [ ] A real task packet is placed in `coordination/task-board/ready/` with a meaningful description
- [ ] A phase record exists in the database (e.g. `phase-live-trial-01`)
- [ ] The pilot agent record exists in the database (e.g. `agent-pilot`)
- [ ] `scripts/repo_sync.py` can reach the running database (`--db-path` matches server setting)
- [ ] Reporter is ready with a stopwatch or timestamp logger

### Quick Setup

```bash
# 1. Start the server
set COORDINATION_DB_PATH=data/live-trial.db
set COORDINATION_API_KEYS=sk-orchestrator,sk-agent-pilot
set COORDINATION_BASE_URL=http://127.0.0.1:8000
python -m services.coordination_api.main

# 2. In a second terminal, seed phase and agent
curl -X POST http://localhost:8000/tasks/phase-live-trial-01/assign ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: sk-orchestrator" ^
  -d "{\"agent_id\":\"agent-pilot\",\"assignment_reason\":\"Trial prep\"}"
# (This will fail — that's expected; the phase/agent must exist first.
#  Use the API docs to create them, or seed via the smoke-script.)

set COORDINATION_API_BASE_URL=http://127.0.0.1:8000
set COORDINATION_API_KEY=sk-orchestrator
```

---

## Pilot Sequence

Run each step in order. Record the data in the [Recording Log](#recording-log) below.

### Step 1 — Dispatch (Orchestrator)

Create the task assignment so the agent can find it.

```bash
# Replace <taskId> with the actual task ID from the packet in coordination/task-board/ready/
set taskId=<taskId>
set agentId=agent-pilot

curl -X POST http://localhost:8000/tasks/%taskId%/assign ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: sk-orchestrator" ^
  -d "{\"agent_id\":\"%agentId%\",\"assignment_reason\":\"Live trial\"}"
```

**Expected:** `200 {"ok":true,"status":"assigned",...}`
**Record:** response time, task_id, event_id, assignment timestamp.

### Step 2 — Poll (Agent)

Agent polls for work assigned to it.

```bash
set COORDINATION_API_KEY=sk-agent-pilot
curl "http://localhost:8000/tasks?agent_id=%agentId%&status=assigned" ^
  -H "X-API-Key: sk-agent-pilot"
```

**Expected:** `200 {"ok":true,"tasks":[...]}` with the assigned task in the list.
**Record:** number of tasks returned, response time, any polling latency.

### Step 3 — Claim (Agent)

Agent accepts the task and begins working (lease starts).

```bash
curl -X POST http://localhost:8000/tasks/%taskId%/claim ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: sk-agent-pilot" ^
  -d "{\"agent_id\":\"%agentId%\"}"
```

**Expected:** `200 {"ok":true,"status":"in_progress","lease_expires_at":"...",...}`
**Record:** claim timestamp, lease_expires_at, response time.

### Step 4 — Progress (Agent)

Agent reports work progress.

```bash
curl -X POST http://localhost:8000/tasks/%taskId%/progress ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: sk-agent-pilot" ^
  -d "{\"agent_id\":\"%agentId%\",\"current_step\":\"Working on task\",\"blocker_status\":\"none\"}"
```

**Expected:** `200 {"ok":true,"status":"in_progress",...}`
**Record:** number of progress reports sent, response time per report.

#### Progress Options

| Field | Value | Notes |
|---|---|---|
| `current_step` | Any description | e.g. "Implementing feature X" |
| `blocker_status` | `none`, `blocked`, `needs_input` | Use `blocked` to indicate a problem |
| `completion_pct` | 0–100 | Optional, if the API supports it |

#### Optional: Send Multiple Progress Reports

Send 2–3 progress updates to exercise the progression:

```bash
curl -X POST http://localhost:8000/tasks/%taskId%/progress ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: sk-agent-pilot" ^
  -d "{\"agent_id\":\"%agentId%\",\"current_step\":\"Step 2 of 3\",\"blocker_status\":\"none\",\"completion_pct\":50}"

curl -X POST http://localhost:8000/tasks/%taskId%/progress ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: sk-agent-pilot" ^
  -d "{\"agent_id\":\"%agentId%\",\"current_step\":\"Step 3 of 3\",\"blocker_status\":\"none\",\"completion_pct\":90}"
```

### Step 5 — Heartbeat (Agent)

Agent sends a heartbeat to keep the lease alive.

```bash
curl -X POST http://localhost:8000/tasks/%taskId%/heartbeat ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: sk-agent-pilot" ^
  -d "{\"agent_id\":\"%agentId%\",\"status\":\"in_progress\"}"
```

**Expected:** `200 {"ok":true,...}`
**Record:** response time, new lease_expires_at.

### Step 6 — Submit (Agent)

Agent submits the completed task for review.

```bash
curl -X POST http://localhost:8000/tasks/%taskId%/submit ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: sk-agent-pilot" ^
  -d "{\"agent_id\":\"%agentId%\",\"summary\":\"Task completed during live trial\"}"
```

**Expected:** `200 {"ok":true,"status":"review",...}`
**Record:** submit timestamp, response time.

### Step 7 — Review (Orchestrator)

Orchestrator reviews and accepts the submitted task.

```bash
set COORDINATION_API_KEY=sk-orchestrator
curl -X POST http://localhost:8000/tasks/%taskId%/review ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: sk-orchestrator" ^
  -d "{\"reviewer_id\":\"orchestrator\",\"decision\":\"accepted\",\"summary\":\"Pilot accepted\"}"
```

**Expected:** `200 {"ok":true,"status":"accepted",...}`
**Record:** review timestamp, decision, review latency (from submit → review).

### Step 8 — Repo-Sync

Project the trial state into the repo.

```bash
python scripts/repo_sync.py --db-path data/live-trial.db
```

**Expected:** Writes `coordination/sync/state-snapshot.md` with the final trial state.
**Record:** command output, any warnings, snapshot file size.

### Step 9 — Final State Check

Confirm the task card is in the correct state.

```bash
curl "http://localhost:8000/tasks/%taskId%" ^
  -H "X-API-Key: sk-orchestrator"
```

**Expected:** `200` with `"status":"accepted"` or the final status.
**Record:** final status, updated_at timestamp.

---

## Incident Path (Optional)

If the task encounters a problem during the trial, exercise the incident path:

```bash
# Open an incident (while task is in_progress)
curl -X POST http://localhost:8000/tasks/%taskId%/incidents ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: sk-agent-pilot" ^
  -d "{\"agent_id\":\"%agentId%\",\"severity\":\"low\",\"summary\":\"Discovered minor issue during trial\",\"category\":\"environment_failure\"}"
```

**Expected:** `200 {"ok":true,"status":"blocked","incident_id":"...",...}`
**Record:** incident_id, status change, response time.

To resume after resolving:

```bash
curl -X POST http://localhost:8000/tasks/%taskId%/resolve ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: sk-agent-pilot" ^
  -d "{\"agent_id\":\"%agentId%\"}"
```

**Expected:** `200 {"ok":true,"status":"in_progress",...}`

---

## Recording Log

For each step, record the following data in this table.

| Step # | Step Name | Timestamp (UTC) | Response Code | Response Time (ms) | Failure? Y/N | Manual Intervention? | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Dispatch | | | | | | |
| 2 | Poll | | | | | | task count, polling latency |
| 3 | Claim | | | | | | lease_expires_at |
| 4 | Progress (×N) | | | | | | N = number of reports |
| 5 | Heartbeat | | | | | | new lease_expires_at |
| 6 | Submit | | | | | | |
| 7 | Review | | | | | | review_latency = submit→review delta |
| 8 | Repo-Sync | | | | | | snapshot file size |
| 9 | Final State | | | | | | final status |

### Aggregate Metrics (fill after trial)

| Metric | Value |
|---|---|
| Total elapsed time (dispatch → accepted) | |
| Number of progress reports sent | |
| Number of heartbeats sent | |
| Number of incidents opened | |
| Review latency (submit → review) | |
| Total API calls made | |
| Any failures encountered? | |
| Any manual interventions? | |

---

## Post-Trial Retrospective

File this in `coordination/reviews/` after the trial completes.

```markdown
# Live Trial Retrospective — <Trial ID>

- Trial ID: <phase5-live-trial-XX>
- Date: <YYYY-MM-DD>
- Operator: <name or agent-id>
- Pilot Task: <taskId>

## Summary

<Brief one-paragraph summary of how the trial went.>

## Metrics

- Total elapsed time: <value>
- Review latency: <value>
- API success rate: <value>% (<passed>/<total>)
- Incidents opened: <count>
- Manual interventions: <count>

## What Worked

- <list what went well>

## What Did Not Work

- <list what went wrong or was harder than expected>

## Surprises / Observations

- <anything unexpected during the trial>

## Gaps Found

- <missing features, documentation gaps, confusing error messages, etc.>

## Recommendations

- <actionable changes for the next trial or live launch>

## Action Items

| # | Action | Owner | Priority |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
```

---

## Rollback / Stop

If any [Rollback / Stop Conditions](coordination-live-readiness-checklist.md#rollback--stop-conditions) are triggered during the trial, stop immediately, file an incident, and do not continue.

---

## Related Documents

- [Live Readiness Checklist](coordination-live-readiness-checklist.md)
- [Startup Guide](coordination-api-startup-guide.md)
- [API Spec](../specs/coordination-api-v1.md)
- [Agent Task Execution Protocol](agent-task-execution-protocol.md)
- [Reviewer Playbook](reviewer-playbook.md)
