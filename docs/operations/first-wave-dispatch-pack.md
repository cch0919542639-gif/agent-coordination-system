# First Wave Dispatch Pack

## Purpose

This document is a ready-to-send dispatch pack for the first live GitHub collaboration wave.

It bundles:

- the three initial task assignments
- the recommended task owners
- the exact repo paths each agent should read
- short dispatch messages you can paste directly

## First Wave Owner Map

- `phase1-live-01`
  - owner: `external-agent-docs-01`
  - task file: `coordination/task-board/ready/2026-06-29_phase1-live-01_onboarding-quickstart.md`
- `phase1-live-02`
  - owner: `external-agent-tools-01`
  - task file: `coordination/task-board/ready/2026-06-29_phase1-live-02_validator-enhancement.md`
- `phase1-live-03`
  - owner: `external-agent-docs-02`
  - task file: `coordination/task-board/ready/2026-06-29_phase1-live-03_reviewer-playbook.md`

## Recommended Launch Order

For the safest first pilot:

1. send `phase1-live-01` first
2. wait until the first `in_progress` and progress update are correct
3. then send either `phase1-live-02` or `phase1-live-03`

If you want a two-agent first wave:

- start `phase1-live-01`
- start `phase1-live-02`
- hold `phase1-live-03` until one of the first two reaches review

## Shared Instruction Block

Include this context in every dispatch:

```text
Please pull the latest repo state before starting.

Required reading:
- docs/operations/agent-task-execution-protocol.md
- your assigned task packet

When you start:
- move your task card from coordination/task-board/ready/ to coordination/task-board/in_progress/
- update coordination/progress/<your-agent-name>.md

If blocked:
- write an incident in coordination/incidents/
- stop rather than guessing outside task scope

When finished:
- move the task card to coordination/task-board/review/
- include repo-based delivery evidence and validation notes
```

## Dispatch 1

Target owner:

- `external-agent-docs-01`

Paste this:

```text
You are assigned task phase1-live-01.

Please pull the latest repo state and read:
- coordination/task-board/ready/2026-06-29_phase1-live-01_onboarding-quickstart.md
- docs/operations/agent-task-execution-protocol.md

When you start:
- move the task card to coordination/task-board/in_progress/
- update coordination/progress/external-agent-docs-01.md

If blocked:
- create an incident in coordination/incidents/
- do not continue by guessing outside the task scope

When finished:
- move the task card to coordination/task-board/review/
- submit repo-based delivery evidence and validation notes
```

## Dispatch 2

Target owner:

- `external-agent-tools-01`

Paste this:

```text
You are assigned task phase1-live-02.

Please pull the latest repo state and read:
- coordination/task-board/ready/2026-06-29_phase1-live-02_validator-enhancement.md
- docs/operations/agent-task-execution-protocol.md

When you start:
- move the task card to coordination/task-board/in_progress/
- update coordination/progress/external-agent-tools-01.md

If blocked:
- create an incident in coordination/incidents/
- do not continue by guessing outside the task scope

When finished:
- move the task card to coordination/task-board/review/
- submit repo-based delivery evidence and validation notes
```

## Dispatch 3

Target owner:

- `external-agent-docs-02`

Paste this:

```text
You are assigned task phase1-live-03.

Please pull the latest repo state and read:
- coordination/task-board/ready/2026-06-29_phase1-live-03_reviewer-playbook.md
- docs/operations/agent-task-execution-protocol.md

When you start:
- move the task card to coordination/task-board/in_progress/
- update coordination/progress/external-agent-docs-02.md

If blocked:
- create an incident in coordination/incidents/
- do not continue by guessing outside the task scope

When finished:
- move the task card to coordination/task-board/review/
- submit repo-based delivery evidence and validation notes
```

## Orchestrator Notes

Before sending each dispatch, quickly confirm:

- the task card is still in `ready/`
- the owner value in the task card matches the intended agent
- the agent has repo access
- you are ready to review the first progress update

After sending each dispatch, check for:

- task moved to `in_progress/`
- progress file created or updated
- no immediate confusion about scope or process

## Optional Human-Friendly Mapping

If your actual external agents use different names, replace only the owner strings while keeping the task IDs and file paths stable.

Recommended mapping style:

- `external-agent-docs-01` -> actual docs-focused agent name
- `external-agent-tools-01` -> actual tooling-focused agent name
- `external-agent-docs-02` -> second docs/review-support agent name

