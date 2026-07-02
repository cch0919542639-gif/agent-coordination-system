# Coordination Agent CLI

A command-line client for the Coordination API control plane.

## Usage

Run via `python -m clients.coordination_agent <command> [options]`.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `COORDINATION_API_BASE_URL` | `http://localhost:8000` | API server base URL |
| `COORDINATION_API_KEY` | *(none)* | API key for authenticated requests |

### Commands

| Command | Description |
|---|---|
| `poll` | List assigned tasks |
| `claim` | Claim a task |
| `heartbeat` | Send a heartbeat to extend the claim lease |
| `progress` | Report progress on a task |
| `incident` | Open an incident / report a blocker |
| `artifact` | Attach a delivery artifact to a task |
| `submit` | Submit a task for review |

### Examples

```bash
# Poll for assigned tasks
python -m clients.coordination_agent poll --agent-id agent-backend-01

# Claim a task
python -m clients.coordination_agent claim task-123 --agent-id agent-backend-01

# Report progress
python -m clients.coordination_agent progress task-123 --agent-id agent-backend-01 --step "Implementing batch retry" --files "src/billing/generate.ts,tests/billing/generate.test.ts"

# Raise an incident
python -m clients.coordination_agent incident task-123 --agent-id agent-backend-01 --severity high --summary "Migration outside allowed scope" --category scope_conflict --details "Schema change required but forbidden by task packet"

# Attach an artifact
python -m clients.coordination_agent artifact task-123 --type repo_file --path coordination/completed/delivery-report.md --repo-ref feature/my-task

# Submit for review
python -m clients.coordination_agent submit task-123 --agent-id agent-backend-01 --summary "Implementation complete" --validation-notes "tests pass, manual review done"

# Send a heartbeat
python -m clients.coordination_agent heartbeat task-123 --agent-id agent-backend-01

# Use a custom API server
python -m clients.coordination_agent --base-url http://localhost:8080 poll --agent-id my-agent
```
