# Phase3 Billing 05 Final Dispatch Message

Copy and send this message to the integration/test agent:

```text
You are assigned task phase3-billing-05.

Please pull the latest repo state and read:
- coordination/task-board/ready/2026-06-30_phase3-billing-05_integration-smoke-tests.md
- coordination/completed/2026-06-30_phase3-billing-intake.md
- coordination/task-board/done/2026-06-30_phase3-billing-02_invoice-generation-service.md
- coordination/task-board/done/2026-06-30_phase3-billing-03_payment-recording.md
- coordination/task-board/done/2026-06-30_phase3-billing-04_balance-query.md
- coordination/delivery/phase3-billing-02-delivery-report.md
- coordination/delivery/phase3-billing-03-delivery-report.md
- coordination/delivery/phase3-billing-04-delivery-report.md
- docs/operations/agent-task-execution-protocol.md

Your goal is to create a billing integration smoke path that proves the minimal flow works end to end: generate invoice -> record payment -> query balance.

When you start:
- run `python scripts/orchestrate.py assigned --owner external-agent-test-01`
- claim the task with `python scripts/orchestrate.py claim --task-id phase3-billing-05 --agent external-agent-test-01`

Allowed scope:
- tests/billing/**
- docs/api/billing.md
- coordination/**

Do not work in:
- src/**
- infra/**
- unrelated test suites

If blocked:
- run `python scripts/orchestrate.py incident --task-id phase3-billing-05 --agent external-agent-test-01 --category scope_conflict --summary "<short blocker summary>"`
- stop rather than guessing outside the assigned scope

Before submission:
- create or update `coordination/delivery/phase3-billing-05-delivery-report.md`
- run `python scripts/orchestrate.py validate`

When finished:
- submit with `python scripts/orchestrate.py submit --task-id phase3-billing-05 --agent external-agent-test-01`
- include repo-based delivery evidence and validation notes
```

