# Coordination Workspace

This directory contains the repo-backed coordination layer for multi-agent collaboration.

## Directory Map

- `task-board/`
  - Task state folders used to track where each task currently sits.
- `progress/`
  - Rolling agent progress files.
- `incidents/`
  - Blockers and escalation reports.
- `completed/`
  - Agent delivery reports after task submission.
- `reviews/`
  - Reviewer decisions and review findings.
- `templates/`
  - Standard markdown templates for coordination files.

## Task Board States

- `ready/`
  - Task is prepared and can be assigned by the orchestrator.
- `in_progress/`
  - Task is currently being executed by the assigned agent.
- `review/`
  - Task has been submitted and is waiting for review.
- `done/`
  - Task was accepted and is complete.
- `blocked/`
  - Task is paused pending incident resolution or reassignment.

## Rules

1. A task is not complete unless the repo includes task movement plus delivery evidence.
2. Agents should only work on explicitly assigned task packets.
3. If blocked, write an incident instead of improvising around unclear scope.
4. Review is required before a task moves to `done/`.

