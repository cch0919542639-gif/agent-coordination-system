# Tasks

## Authoritative System

Task lifecycle lives in `coordination/task-board/`:

- `ready/`: assigned work awaiting worker claim
- `in_progress/`: active worker execution
- `review/`: submitted delivery awaiting orchestrator decision
- `done/`: accepted work
- `blocked/`: incident or dependency requires resolution

## Current Groups

- Phase 14 local worker automation: `coordination/task-board/ready/`
- Product project work: each registered project owns its own `coordination/`
  directory and task board.

Use `python scripts/orchestrate.py next` for a suggestion, then confirm status
from the actual task card before dispatching.
