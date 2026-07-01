# Phase4 Coordination API 04 Final Dispatch Message

Copy and send this message to the progress-endpoint agent:

```text
You are assigned task phase4-coordination-api-04.

Please pull the latest repo state and read:
- coordination/task-board/ready/2026-07-01_phase4-coordination-api-04_progress-api.md
- coordination/completed/2026-07-01_phase4-coordination-api-wave2-intake.md
- coordination/task-board/done/2026-07-01_phase4-coordination-api-03_assignment-claim-api.md
- coordination/delivery/phase4-coordination-api-03-delivery-report.md
- docs/specs/coordination-api-v1.md
- docs/operations/agent-task-execution-protocol.md

Your goal is to add structured progress reporting to the coordination API so an assigned agent can checkpoint execution without manual chat relay.

When you start:
- run `python scripts/orchestrate.py assigned --owner external-agent-platform-04`
- claim the task with `python scripts/orchestrate.py claim --task-id phase4-coordination-api-04 --agent external-agent-platform-04`

Allowed scope:
- services/coordination_api/**
- tests/coordination_api/**
- docs/specs/coordination-api-v1.md
- coordination/**

Do not work in:
- dashboard UI
- repo-sync worker
- unrelated application domains

If blocked:
- run `python scripts/orchestrate.py incident --task-id phase4-coordination-api-04 --agent external-agent-platform-04 --category spec_ambiguity --summary "<short blocker summary>"`
- stop rather than guessing outside the assigned scope

Before submission:
- create or update `coordination/delivery/phase4-coordination-api-04-delivery-report.md`
- run `python scripts/orchestrate.py validate`

When finished:
- submit with `python scripts/orchestrate.py submit --task-id phase4-coordination-api-04 --agent external-agent-platform-04`
- include repo-based delivery evidence and validation notes
```
