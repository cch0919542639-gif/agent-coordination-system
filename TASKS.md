# Tasks

## Authoritative System

Task lifecycle lives in `coordination/task-board/`:

- `ready/`: assigned work awaiting worker claim
- `in_progress/`: active worker execution
- `review/`: submitted delivery awaiting orchestrator decision
- `done/`: accepted work
- `blocked/`: incident or dependency requires resolution

## Current Groups

- Phase 14 same-machine automation is accepted in `coordination/task-board/done/`.
- The Hermes controlled-worker parent and original supervised pilot are accepted.
- Hermes launcher parity is accepted on `phase14-hermes-pilot-04` (2026-10-11).
  Its fresh normal invocation exited zero on a verified REVIEW receipt;
  interrupted pilots 02 and 03 are in `cancelled/`, superseded by this run.
- Product project work: each registered project owns its own `coordination/`
  directory and task board; `usage-mvp-01` is awaiting orchestrator review on
  its configured worker branch.

Use `python scripts/orchestrate.py next` for a suggestion, then confirm status
from the actual task card before dispatching.

- Local-loop implementation and independent review are accepted; GitHub publication
  and fresh-download verification are tracked by phase14-loop-publication-01.
