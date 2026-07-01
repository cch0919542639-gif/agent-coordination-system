# Phase4 Coordination API 06 Final Dispatch Message

Copy and send this message to the artifact-and-submit agent:

```text
You are assigned task phase4-coordination-api-06.

Please pull the latest repo state and read:
- coordination/task-board/ready/2026-07-01_phase4-coordination-api-06_artifact-and-submit-api.md
- coordination/completed/2026-07-01_phase4-coordination-api-wave2-intake.md
- coordination/task-board/done/2026-07-01_phase4-coordination-api-03_assignment-claim-api.md
- coordination/delivery/phase4-coordination-api-03-delivery-report.md
- docs/specs/coordination-api-v1.md
- docs/operations/agent-task-execution-protocol.md

Your goal is to add artifact registration and submit-for-review behavior so repo-based delivery evidence can move cleanly into review through the control plane.

When you start:
- run `python scripts/orchestrate.py assigned --owner external-agent-platform-06`
- claim the task with `python scripts/orchestrate.py claim --task-id phase4-coordination-api-06 --agent external-agent-platform-06`

Allowed scope:
- services/coordination_api/**
- tests/coordination_api/**
- docs/specs/coordination-api-v1.md
- docs/operations/**
- coordination/**

Do not work in:
- dashboard UI
- repo-sync worker
- notification layer

If blocked:
- run `python scripts/orchestrate.py incident --task-id phase4-coordination-api-06 --agent external-agent-platform-06 --category spec_ambiguity --summary "<short blocker summary>"`
- stop rather than guessing outside the assigned scope

Before submission:
- create or update `coordination/delivery/phase4-coordination-api-06-delivery-report.md`
- run `python scripts/orchestrate.py validate`

When finished:
- submit with `python scripts/orchestrate.py submit --task-id phase4-coordination-api-06 --agent external-agent-platform-06`
- include repo-based delivery evidence and validation notes
```
