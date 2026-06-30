# Phase3 Billing 03 Final Dispatch Message

Copy and send this message to the next backend agent:

```text
You are assigned task phase3-billing-03.

Please pull the latest repo state and read:
- coordination/task-board/ready/2026-06-30_phase3-billing-03_payment-recording.md
- coordination/completed/2026-06-30_phase3-billing-intake.md
- coordination/task-board/done/2026-06-30_phase3-billing-01_invoice-model-and-persistence.md
- coordination/task-board/done/2026-06-30_phase3-billing-02_invoice-generation-service.md
- coordination/delivery/phase3-billing-01-delivery-report.md
- coordination/delivery/phase3-billing-02-delivery-report.md
- docs/operations/agent-task-execution-protocol.md

Your goal is to implement internal payment recording against an invoice using the billing model and generation flow already established.

When you start:
- run `python scripts/orchestrate.py assigned --owner external-agent-backend-03`
- claim the task with `python scripts/orchestrate.py claim --task-id phase3-billing-03 --agent external-agent-backend-03`

Allowed scope:
- src/billing/**
- tests/billing/**
- docs/api/billing.md
- coordination/**

Do not work in:
- src/gateway/**
- infra/**
- unrelated domains outside billing

If blocked:
- run `python scripts/orchestrate.py incident --task-id phase3-billing-03 --agent external-agent-backend-03 --category scope_conflict --summary "<short blocker summary>"`
- stop rather than guessing outside the assigned scope

Before submission:
- create or update `coordination/delivery/phase3-billing-03-delivery-report.md`
- run `python scripts/orchestrate.py validate`

When finished:
- submit with `python scripts/orchestrate.py submit --task-id phase3-billing-03 --agent external-agent-backend-03`
- include repo-based delivery evidence and validation notes
```

