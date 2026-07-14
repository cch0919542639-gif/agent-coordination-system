# External Agent Dispatch Message Templates

## Purpose

These message templates are intended for assigning repo-first work to external agents during the first live GitHub collaboration phase.

Use them as short, repeatable dispatch messages. The task card remains the source of truth. The message should only direct the agent to the right repo state and expected workflow.

> **Automated alternative:** The `dispatch_task.py` script (via `python scripts/orchestrate.py dispatch`) generates dispatch messages automatically from the task card. It produces the same structure as Template 1 below, including the task ID, packet path, protocol references, and start/blocked/finish instructions. Use `--output -` to pipe the raw message body into a chat message or notification.

## General Rules

- Keep the dispatch message short.
- Do not restate the entire task card in chat.
- Always point the agent back to the repo files.
- Always include what to do when blocked.

## Template 1: Standard Task Assignment

```text
You are assigned task {TASK_ID}.

Please pull the latest repo state, read:
- coordination/task-board/ready/{TASK_FILE}
- docs/operations/agent-task-execution-protocol.md

When you start:
- move the task card to coordination/task-board/in_progress/
- update coordination/progress/{AGENT_NAME}.md

If blocked:
- create an incident in coordination/incidents/
- do not continue by guessing outside the task scope

When finished:
- move the task card to coordination/task-board/review/
- submit repo-based delivery evidence and validation notes
```

## Template 2: Follow-Up After Assignment

```text
Quick check for task {TASK_ID}:

Please confirm you have:
- pulled latest repo state
- read the assigned task packet
- updated the task to in_progress when starting
- written your current progress in coordination/progress/{AGENT_NAME}.md
```

## Template 2A: Worktree-Aware Assignment

```text
You are assigned task {TASK_ID}.

Please pull the latest repo state, then read:
- {TASK_FILE}
- docs/operations/agent-task-execution-protocol.md

Execution mode:
- WORKTREE
- branch: {BRANCH}
- worktree_path: {WORKTREE_PATH}
- machine_id: {MACHINE_ID}

Before implementation:
- confirm the assigned branch and worktree are the ones you are using
- if the worktree is missing locally, stop and report it instead of improvising another checkout

When you start:
- move the task card to coordination/task-board/in_progress/
- update coordination/progress/{AGENT_NAME}.md

If blocked:
- create an incident in coordination/incidents/
- do not continue by guessing outside the task scope

When finished:
- move the task card to coordination/task-board/review/
- include repo-based delivery evidence and validation notes
```

## Template 3: Blocker Response

```text
For task {TASK_ID}, please stop implementation at the current safe point and write an incident report in coordination/incidents/.

Do not widen scope or bypass the blocker until the incident is reviewed.

After the incident is written, update coordination/progress/{AGENT_NAME}.md with a blocked summary.
```

## Template 4: Review Submission Reminder

```text
Before submitting task {TASK_ID} for review, please confirm the repo contains:
- the updated task card in coordination/task-board/review/
- your latest progress update
- delivery evidence
- validation notes
- residual risks if any
```

## Template 5: Needs-Fix Return

```text
Task {TASK_ID} requires follow-up changes.

Please read the review notes, continue only within the original allowed scope unless explicitly expanded, update your progress file, and return the task to review after the requested fixes are complete.
```

## Recommended First Live Message

For the first pilot, this is the best default dispatch:

```text
You are assigned task {TASK_ID}. Pull the latest repo state and read the assigned task packet plus docs/operations/agent-task-execution-protocol.md.

Start by moving the task card into coordination/task-board/in_progress/ and updating coordination/progress/{AGENT_NAME}.md.

If blocked, write an incident in coordination/incidents/ and stop rather than guessing.

When finished, move the task to coordination/task-board/review/ and include repo-based delivery evidence and validation notes.
```
