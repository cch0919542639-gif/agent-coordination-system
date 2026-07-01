# Phase4 Coordination API Wave 2 Dispatch Pack

## Purpose

This document is the ready-to-send dispatch pack for the next coordination API build wave.

Wave 2 is the minimum loop-closing wave:

- progress reporting
- blocker reporting
- artifact registration
- submit for review
- structured review decision

Once this wave is accepted, the coordination API will support the first full assigned-task lifecycle without requiring you to relay each step manually.

## Wave 2 Owner Map

- `phase4-coordination-api-04`
  - owner: `external-agent-platform-04`
  - task file: `coordination/task-board/ready/2026-07-01_phase4-coordination-api-04_progress-api.md`
- `phase4-coordination-api-05`
  - owner: `external-agent-platform-05`
  - task file: `coordination/task-board/ready/2026-07-01_phase4-coordination-api-05_incident-api.md`
- `phase4-coordination-api-06`
  - owner: `external-agent-platform-06`
  - task file: `coordination/task-board/ready/2026-07-01_phase4-coordination-api-06_artifact-and-submit-api.md`
- `phase4-coordination-api-07`
  - owner: `external-agent-platform-07`
  - task file: `coordination/task-board/ready/2026-07-01_phase4-coordination-api-07_review-api.md`

## Recommended Launch Order

For the safest rollout:

1. dispatch `phase4-coordination-api-04`
2. dispatch `phase4-coordination-api-05`
3. dispatch `phase4-coordination-api-06`
4. hold `phase4-coordination-api-07` until `phase4-coordination-api-06` is in review or done

Practical note:

- `phase4-coordination-api-04` and `phase4-coordination-api-05` can run in parallel
- `phase4-coordination-api-06` can also run after Wave 1 is pulled, but it is cleaner if the progress and incident endpoints already set the event-handling pattern
- `phase4-coordination-api-07` should not start until the submission flow behavior is visible

## Shared Instruction Block

Include this context in every dispatch:

```text
Please pull the latest repo state before starting.

Required reading:
- docs/operations/agent-task-execution-protocol.md
- your assigned task packet
- coordination/completed/2026-07-01_phase4-coordination-api-wave2-intake.md

When you start:
- run `python scripts/orchestrate.py assigned --owner <your-agent-name>`
- claim the task with `python scripts/orchestrate.py claim --task-id <task-id> --agent <your-agent-name>`

If blocked:
- run `python scripts/orchestrate.py incident --task-id <task-id> --agent <your-agent-name> --category <category> --summary "<short blocker summary>"`
- stop rather than guessing outside task scope

Before submission:
- create or update `coordination/delivery/<task-id>-delivery-report.md`
- run `python scripts/orchestrate.py validate`

When finished:
- run `python scripts/orchestrate.py submit --task-id <task-id> --agent <your-agent-name>`
- include repo-based delivery evidence and validation notes
```

## Dispatch 1

Target owner:

- `external-agent-platform-04`

Paste this:

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

## Dispatch 2

Target owner:

- `external-agent-platform-05`

Paste this:

```text
You are assigned task phase4-coordination-api-05.

Please pull the latest repo state and read:
- coordination/task-board/ready/2026-07-01_phase4-coordination-api-05_incident-api.md
- coordination/completed/2026-07-01_phase4-coordination-api-wave2-intake.md
- coordination/task-board/done/2026-07-01_phase4-coordination-api-03_assignment-claim-api.md
- coordination/delivery/phase4-coordination-api-03-delivery-report.md
- docs/specs/coordination-api-v1.md
- docs/operations/agent-task-execution-protocol.md

Your goal is to add structured incident reporting to the coordination API so blocked agents can stop safely and raise first-class blockers through the service.

When you start:
- run `python scripts/orchestrate.py assigned --owner external-agent-platform-05`
- claim the task with `python scripts/orchestrate.py claim --task-id phase4-coordination-api-05 --agent external-agent-platform-05`

Allowed scope:
- services/coordination_api/**
- tests/coordination_api/**
- docs/specs/coordination-api-v1.md
- coordination/**

Do not work in:
- heartbeat workers
- dashboard UI
- unrelated application domains

If blocked:
- run `python scripts/orchestrate.py incident --task-id phase4-coordination-api-05 --agent external-agent-platform-05 --category spec_ambiguity --summary "<short blocker summary>"`
- stop rather than guessing outside the assigned scope

Before submission:
- create or update `coordination/delivery/phase4-coordination-api-05-delivery-report.md`
- run `python scripts/orchestrate.py validate`

When finished:
- submit with `python scripts/orchestrate.py submit --task-id phase4-coordination-api-05 --agent external-agent-platform-05`
- include repo-based delivery evidence and validation notes
```

## Dispatch 3

Target owner:

- `external-agent-platform-06`

Paste this:

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

## Dispatch 4

Target owner:

- `external-agent-platform-07`

Paste this only after `phase4-coordination-api-06` is in review or done:

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
