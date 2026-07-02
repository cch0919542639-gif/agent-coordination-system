# Coordination API Startup Guide

## Prerequisites

- Python 3.13+
- Required packages: `fastapi`, `uvicorn`, `httpx`

## Quick Start

Run with default settings (auth disabled, port 8000, SQLite at `coordination.db`):

```bash
python -m services.coordination_api.main
```

Verify:

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}
```

## Configuration (Server)

All settings are controlled via environment variables:

| Variable | Default | Description |
|---|---|---|
| `HOST` | `127.0.0.1` | Bind address |
| `PORT` | `8000` | Listen port |
| `LOG_LEVEL` | `info` | Uvicorn log level |
| `COORDINATION_DB_PATH` | `coordination.db` | SQLite database file path |
| `COORDINATION_API_KEYS` | *(empty)* | Comma-separated API keys; **auth is disabled when empty** |
| `COORDINATION_BASE_URL` | `http://127.0.0.1:8000` | Self-referencing base URL (informational) |

### Example: custom port and DB path

```bash
set PORT=9000
set COORDINATION_DB_PATH=data/my-coordination.db
python -m services.coordination_api.main
```

### Example: enabling API key auth

```bash
set COORDINATION_API_KEYS=sk-agent-1,sk-agent-2,sk-orchestrator
python -m services.coordination_api.main
```

With auth enabled, every request must include the header `X-API-Key` with one of the configured keys:

```bash
curl -H "X-API-Key: sk-agent-1" http://localhost:8000/health
# {"status":"ok","version":"0.1.0"}

curl http://localhost:8000/health
# {"detail":"Invalid or missing API key"}  # 401
```

## Configuration (Agent CLI)

The agent client at `clients/coordination_agent/` uses separate environment variables:

| Variable | Default | Description |
|---|---|---|
| `COORDINATION_API_BASE_URL` | `http://localhost:8000` | Server base URL |
| `COORDINATION_API_KEY` | *(empty)* | Single API key sent as `X-API-Key` header |

Run:

```bash
set COORDINATION_API_BASE_URL=http://localhost:8000
set COORDINATION_API_KEY=sk-agent-1
python -m clients.coordination_agent poll --agent-id agent-01
```

## Environment Variable Summary

| Scope | Variable | Server Setting | Default |
|---|---|---|---|
| Server | `HOST` | `settings.host` | `127.0.0.1` |
| Server | `PORT` | `settings.port` | `8000` |
| Server | `LOG_LEVEL` | `settings.log_level` | `info` |
| Server | `COORDINATION_DB_PATH` | `settings.db_path` | `coordination.db` |
| Server | `COORDINATION_API_KEYS` | `settings.api_keys` | *(empty, auth disabled)* |
| Server | `COORDINATION_BASE_URL` | `settings.base_url` | `http://127.0.0.1:8000` |
| Client | `COORDINATION_API_BASE_URL` | `client.base_url` | `http://localhost:8000` |
| Client | `COORDINATION_API_KEY` | `client.api_key` | *(empty)* |

## Validation

After startup, verify:

1. Health endpoint responds: `GET /health` → `200 {"status":"ok","version":"0.1.0"}`
2. Auth enforcement (when `COORDINATION_API_KEYS` is set):
   - Without `X-API-Key` header → `401`
   - With valid `X-API-Key` → `200`
   - With invalid `X-API-Key` → `401`
3. Auth bypass (when `COORDINATION_API_KEYS` is empty):
   - All requests succeed without `X-API-Key`
4. Database initializes automatically: the SQLite file is created on first run
