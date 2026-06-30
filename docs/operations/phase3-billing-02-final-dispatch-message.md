# Phase3 Billing 02 Final Dispatch Message

Copy and send this message to the next backend agent:

```text
You are assigned task phase3-billing-02.

Please pull the latest repo state and read:
- coordination/task-board/ready/2026-06-30_phase3-billing-02_invoice-generation-service.md
- coordination/completed/2026-06-30_phase3-billing-intake.md
- coordination/task-board/done/2026-06-30_phase3-billing-01_invoice-model-and-persistence.md
- coordination/delivery/phase3-billing-01-delivery-report.md
- docs/operations/agent-task-execution-protocol.md

Your goal is to implement invoice generation using the billing model and persistence layer created in phase3-billing-01.

When you start:
- run `python scripts/orchestrate.py assigned --owner external-agent-backend-02`
- claim the task with `python scripts/orchestrate.py claim --task-id phase3-billing-02 --agent external-agent-backend-02`

Allowed scope:
- src/billing/**
- tests/billing/**
- docs/api/billing.md
- coordination/**

Do not work in:
- src/payments/**
- infra/**
- unrelated domains outside billing

If blocked:
- run `python scripts/orchestrate.py incident --task-id phase3-billing-02 --agent external-agent-backend-02 --category scope_conflict --summary "<short blocker summary>"`
- stop rather than guessing outside the assigned scope

Before submission:
- create or update `coordination/delivery/phase3-billing-02-delivery-report.md`
- run `python scripts/orchestrate.py validate`

When finished:
- submit with `python scripts/orchestrate.py submit --task-id phase3-billing-02 --agent external-agent-backend-02`
- include repo-based delivery evidence and validation notes
```

