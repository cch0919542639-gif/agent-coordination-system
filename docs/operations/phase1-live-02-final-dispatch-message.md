# Phase1 Live 02 Final Dispatch Message

Copy and send this message to the second external agent:

```text
You are assigned task phase1-live-02.

Please pull the latest repo state and read:
- coordination/task-board/ready/2026-06-29_phase1-live-02_validator-enhancement.md
- docs/operations/agent-task-execution-protocol.md

Your goal is to improve the coordination validator with one or two small, useful checks while staying strictly inside the allowed scope.

When you start:
- move the task card to coordination/task-board/in_progress/
- update coordination/progress/external-agent-tools-01.md

Allowed scope:
- scripts/**
- docs/**
- coordination/**

If blocked:
- create an incident in coordination/incidents/
- stop rather than guessing outside the assigned scope

When finished:
- move the task card to coordination/task-board/review/
- include repo-based delivery evidence and validation notes

Validation command:
- python scripts/validate_coordination_files.py
```

