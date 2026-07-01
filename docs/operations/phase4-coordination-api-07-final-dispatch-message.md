# Phase4 Coordination API 07 Final Dispatch Message

Copy and send this message to the review-endpoint agent only after task `phase4-coordination-api-06` is in `review/` or `done/`:

```text
You are assigned task phase4-coordination-api-07.

Please pull the latest repo state and read:
- coordination/task-board/ready/2026-07-01_phase4-coordination-api-07_review-api.md
- coordination/completed/2026-07-01_phase4-coordination-api-wave2-intake.md
- coordination/task-board/review/2026-07-01_phase4-coordination-api-06_artifact-and-submit-api.md if it exists, otherwise its done/ version
- coordination/delivery/phase4-coordination-api-06-delivery-report.md
- docs/specs/coordination-api-v1.md
- docs/operations/agent-task-execution-protocol.md

Your goal is to add structured review decisions so submitted API work can be accepted or returned for fixes through the control plane.

When you start:
- run `python scripts/orchestrate.py assigned --owner external-agent-platform-07`
- claim the task with `python scripts/orchestrate.py claim --task-id phase4-coordination-api-07 --agent external-agent-platform-07`

Allowed scope:
- services/coordination_api/**
- tests/coordination_api/**
- docs/specs/coordination-api-v1.md
- docs/operations/**
- coordination/**

Do not work in:
- reassignment API
- heartbeat recovery
- dashboard UI

If blocked:
- run `python scripts/orchestrate.py incident --task-id phase4-coordination-api-07 --agent external-agent-platform-07 --category spec_ambiguity --summary "<short blocker summary>"`
- stop rather than guessing outside the assigned scope

Before submission:
- create or update `coordination/delivery/phase4-coordination-api-07-delivery-report.md`
- run `python scripts/orchestrate.py validate`

When finished:
- submit with `python scripts/orchestrate.py submit --task-id phase4-coordination-api-07 --agent external-agent-platform-07`
- include repo-based delivery evidence and validation notes
```
