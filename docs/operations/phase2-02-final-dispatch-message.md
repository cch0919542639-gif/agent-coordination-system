# Phase2-02 Final Dispatch Message

Copy and send this message to the next Phase 2 agent:

```text
You are assigned task phase2-02.

Please pull the latest repo state and read:
- coordination/task-board/ready/2026-06-29_phase2-02_delivery-report-standardization.md
- docs/operations/agent-task-execution-protocol.md
- docs/operations/phase2-productionization-plan.md
- docs/operations/phase1-retrospective.md

Your goal is to standardize delivery-report expectations so future tasks have clearer, more enforceable delivery artifacts.

When you start:
- move the task card to coordination/task-board/in_progress/
- update coordination/progress/external-agent-tools-02.md

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

