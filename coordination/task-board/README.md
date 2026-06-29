# Task Board

This task board is the repo projection of task state.

## State Folders

- `ready/`
- `in_progress/`
- `review/`
- `done/`
- `blocked/`

## Operating Rule

Only move a task card when its actual state has changed.

Suggested flow:

`ready -> in_progress -> review -> done`

Exceptions:

- `in_progress -> blocked`
- `review -> in_progress` when `needs_fix`
- `blocked -> in_progress` after orchestrator resolution

