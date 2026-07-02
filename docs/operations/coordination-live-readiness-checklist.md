# Coordination API — Live Readiness Checklist

## Live-Readiness Checks

Before the first internal live trial, confirm each of these:

### Repo Infrastructure

- [ ] `services/coordination_api/main.py` exists and starts without import errors
- [ ] `services/coordination_api/config.py` exposes `host`, `port`, `db_path`, `api_keys`, `base_url`
- [ ] `services/coordination_api/auth.py` middleware returns `JSONResponse` (not `HTTPException`)
- [ ] All 234+ coordination + billing tests pass (`python -m pytest tests/ -q`)
- [ ] Validator passes (`python scripts/orchestrate.py validate`)
- [ ] Database initialises automatically on first run (`run_migrations()`)
- [ ] Agent CLI exists at `clients/coordination_agent/` and can be invoked
- [ ] Startup guide exists at `docs/operations/coordination-api-startup-guide.md`
- [ ] API spec is committed at `docs/specs/coordination-api-v1.md`
- [ ] Task-board directory structure is present with `ready/`, `in_progress/`, `review/`, `done/`, `blocked/`

### Configuration Surface

- [ ] `HOST` env var binds to the intended address (default `127.0.0.1`)
- [ ] `PORT` env var sets the listen port (default `8000`)
- [ ] `COORDINATION_DB_PATH` env var sets the SQLite file location (default `coordination.db`)
- [ ] `COORDINATION_API_KEYS` env var enables auth when populated
- [ ] `COORDINATION_BASE_URL` env var sets the self-referencing URL (informational)
- [ ] `COORDINATION_API_KEY` env var (client side, singular) matches a server key when auth is enabled
- [ ] `COORDINATION_API_BASE_URL` env var (client side) points to the running server

### Auth

- [ ] Auth-disabled mode works when `COORDINATION_API_KEYS` is empty
- [ ] Auth-required mode works when `COORDINATION_API_KEYS` is set
- [ ] `401` returned for missing / invalid keys in auth-required mode
- [ ] `200` returned for valid keys in auth-required mode
- [ ] All endpoints (including `/health`) require auth when enabled

---

## First-Run Operator Checklist

Use this checklist during the first internal trial launch.

### Step 1: Configure Environment

```bash
set HOST=127.0.0.1
set PORT=8000
set COORDINATION_DB_PATH=data/coordination.db
set COORDINATION_API_KEYS=sk-orchestrator,sk-agent-pilot
set COORDINATION_BASE_URL=http://127.0.0.1:8000
```

### Step 2: Verify Dependencies

```bash
pip install fastapi uvicorn httpx
python -c "import fastapi, uvicorn, httpx; print('dependencies ok')"
```

### Step 3: Start the Coordination API

```bash
python -m services.coordination_api.main
```

Expected output: Uvicorn listens on `http://127.0.0.1:8000`.

### Step 4: Run Smoke Tests

Use the automated smoke-test helper:

```bash
set COORDINATION_API_BASE_URL=http://localhost:8000
set COORDINATION_API_KEY=sk-orchestrator
python scripts/smoke_test_coordination.py --task-id <taskId> --agent-id agent-pilot
```

Or run the manual [Smoke-Test Sequence](#smoke-test-sequence) below.

### Step 5: Configure Agent CLI

```bash
set COORDINATION_API_BASE_URL=http://127.0.0.1:8000
set COORDINATION_API_KEY=sk-agent-pilot
python -m clients.coordination_agent --help
```

### Step 6: Ready a Pilot Task

- [ ] Place a task packet in `coordination/task-board/ready/`
- [ ] Assign it via the API: `POST /tasks/{taskId}/assign`
- [ ] Confirm the agent can poll and claim it

---

## Required Environment Variables

### Startup Order

1. Set server env vars
2. Start `services/coordination_api.main`
3. Verify `/health` responds
4. Set client env vars
5. Run smoke tests
6. Dispatch pilot task

### Quick-Reference Table

| Order | Variable | Scope | Default | Required For |
|---|---|---|---|---|
| 1 | `HOST` | Server | `127.0.0.1` | Binding address |
| 2 | `PORT` | Server | `8000` | Listen port |
| 3 | `COORDINATION_DB_PATH` | Server | `coordination.db` | Database file |
| 4 | `COORDINATION_API_KEYS` | Server | *(empty)* | API key auth |
| 5 | `COORDINATION_BASE_URL` | Server | `http://127.0.0.1:8000` | Self-reference |
| 6 | `COORDINATION_API_BASE_URL` | Client | `http://localhost:8000` | Server address |
| 7 | `COORDINATION_API_KEY` | Client | *(empty)* | Auth token |

### Full Reference

See `docs/operations/coordination-api-startup-guide.md` for detailed descriptions and examples.

---

## Smoke-Test Sequence

Run this sequence on launch day to confirm the system is operational.

### 1. Health Check

```bash
curl http://localhost:8000/health
# Expected: 200 {"status":"ok","version":"0.1.0"}
```

### 2. Auth Enforcement (when enabled)

```bash
# Without key — should fail
curl http://localhost:8000/health
# Expected: 401 {"detail":"Invalid or missing API key"}

# With valid key — should succeed
curl -H "X-API-Key: sk-orchestrator" http://localhost:8000/health
# Expected: 200 {"status":"ok","version":"0.1.0"}

# With invalid key — should fail
curl -H "X-API-Key: wrong-key" http://localhost:8000/health
# Expected: 401 {"detail":"Invalid or missing API key"}
```

### 3. Agent Lifecycle (end-to-end)

Prerequisites: a phase and task must exist in the database. Use the repo-sync script if needed to verify initial state.

```bash
# 3a. Create an agent (if not present via seed)
# 3b. Assign a task
curl -X POST http://localhost:8000/tasks/<taskId>/assign \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-orchestrator" \
  -d '{"agent_id": "agent-pilot", "assignment_reason": "Live trial"}'
# Expected: 200 {"ok":true,"status":"assigned",...}

# 3c. Poll assigned work
curl "http://localhost:8000/tasks?agent_id=agent-pilot&status=assigned" \
  -H "X-API-Key: sk-agent-pilot"
# Expected: 200 {"ok":true,"tasks":[...]}

# 3d. Claim the task
curl -X POST http://localhost:8000/tasks/<taskId>/claim \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-agent-pilot" \
  -d '{"agent_id": "agent-pilot"}'
# Expected: 200 {"ok":true,"status":"in_progress",...}

# 3e. Report progress
curl -X POST http://localhost:8000/tasks/<taskId>/progress \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-agent-pilot" \
  -d '{"agent_id":"agent-pilot","current_step":"Smoke test","blocker_status":"none"}'
# Expected: 200 {"ok":true,"status":"in_progress",...}

# 3f. Submit for review
curl -X POST http://localhost:8000/tasks/<taskId>/submit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-agent-pilot" \
  -d '{"agent_id":"agent-pilot","summary":"Smoke test complete"}'
# Expected: 200 {"ok":true,"status":"review",...}

# 3g. Review and accept
curl -X POST http://localhost:8000/tasks/<taskId>/review \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-orchestrator" \
  -d '{"reviewer_id":"orchestrator","decision":"accepted","summary":"Pilot accepted"}'
# Expected: 200 {"ok":true,"status":"accepted",...}
```

### 4. Incident Path

```bash
# Open incident
curl -X POST http://localhost:8000/tasks/<taskId>/incidents \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-agent-pilot" \
  -d '{"agent_id":"agent-pilot","severity":"low","summary":"Test incident","category":"environment_failure"}'
# Expected: 200 {"ok":true,"status":"blocked","incident_id":"...",...}
```

### 5. Heartbeat + Lease Recovery

```bash
# Heartbeat
curl -X POST http://localhost:8000/tasks/<taskId>/heartbeat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk-agent-pilot" \
  -d '{"agent_id":"agent-pilot","status":"in_progress"}'
# Expected: 200 {"ok":true,...}

# List expired leases (expect empty unless leases have timed out)
curl http://localhost:8000/heartbeat/expired \
  -H "X-API-Key: sk-orchestrator"
# Expected: 200 {"ok":true,"expired_assignments":[]}
```

### 6. Repo-Sync Projection

```bash
python scripts/repo_sync.py --db-path data/coordination.db
# Expected: writes coordination/sync/state-snapshot.md
```

### 7. Agent CLI

```bash
python -m clients.coordination_agent poll --agent-id agent-pilot
# Expected: lists assigned tasks or empty list
```

### 8. Automated Smoke-Test Helper

```bash
python scripts/smoke_test_coordination.py --task-id <taskId> --agent-id agent-pilot
# Expected: all checks PASS, summary shows N/N passed
```

---

## Rollback / Stop Conditions

### Immediate Stop

Stop the server and pause the trial if any of these occur:

| Condition | Action |
|---|---|
| `/health` returns non-200 | Stop. Check process, port, dependencies. |
| Auth bypass: request succeeds without key when auth is enabled | Stop. Auth middleware is broken. Do not proceed. |
| Auth false-positive: valid key returns 401 | Stop. Check `COORDINATION_API_KEYS` format. |
| Database fails to initialise | Stop. Check `COORDINATION_DB_PATH` is writable. |
| API returns 5xx on standard workflows (assign, claim, submit) | Stop. Check logs and test isolation. |

### Pause / Do Not Expand

Pause the trial and do not add more agents or tasks if:

- Agent cannot poll tasks assigned to it
- Claim fails despite valid assignment
- Progress reported but task status does not update
- Incident creation does not move task to `blocked`
- Submit does not move task to `review`
- Review decision does not change task status correctly
- Lease expiry or heartbeat behaves unexpectedly
- Agent CLI returns unhandled errors on any standard command
- Repo-sync script fails when pointed at the live database
- Test suite regresses after deployment
- Operator cannot reconstruct trial state from repo files alone

### Rollback Procedure

1. Stop the coordination API process (`Ctrl+C` or `kill`).
2. Keep the database file for post-mortem analysis.
3. Revert any env var changes applied for the trial.
4. Restore the previous database if one was backed up.
5. File an incident in `coordination/incidents/` describing what went wrong.
6. Update `coordination/reviews/` with the trial outcome and findings.
7. Do not restart the trial until the root cause is fixed and re-validated.

### Rollback Criteria Summary

| Severity | Criterion | Action |
|---|---|---|
| Critical | Auth broken (bypass or false-reject) | Immediate stop + rollback |
| Critical | Database corruption or write failure | Immediate stop + rollback |
| Critical | 5xx on any standard endpoint | Immediate stop + rollback |
| High | Any lifecycle endpoint fails (assign/claim/progress/submit/review) | Pause, investigate |
| High | Agent CLI fails on standard command | Pause, investigate |
| Medium | Smoke test sequence has gaps but core loop works | Document, continue cautiously |
| Low | Repo-sync projection is stale but API works | Document, fix in follow-up |
