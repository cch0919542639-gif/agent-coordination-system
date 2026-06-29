# Real Project Intake Guide

## Purpose

This guide explains how the orchestrator uses the phase intake template at `coordination/templates/phase-intake.md` to convert a real engineering initiative into the next clean execution phase.

## When To Use This Guide

Use this guide when:

- Phase 2 exit criteria are met and the repo-first workflow is ready for real project work
- The orchestrator has identified a concrete engineering initiative that can be decomposed into task packets
- The initiative is well-defined enough to freeze scope boundaries and dependencies

## How The Intake Path Works

The intake path has three layers:

```
Phase Intake (coordination/templates/phase-intake.md)
  └── Task Packets (coordination/templates/task-packet.md)
        └── Delivery Reports (coordination/templates/delivery-report.md)
```

1. **Phase intake** defines the overall engineering initiative — its objective, scope boundaries, dependencies, and the list of task packets that decompose it
2. **Task packets** are created from the decomposition list and placed in `coordination/task-board/ready/` — each packet follows the standard template
3. **Delivery reports** are produced by each agent after task completion, as enforced by the validator

## Step-by-Step Orchestrator Workflow

### Step 1: Define the Phase

Open a new intake document using `coordination/templates/phase-intake.md`. Fill in:

- **Phase ID** — use a short kebab-case identifier (e.g. `phase3-billing`)
- **Objective** — one or two sentences describing what the phase achieves
- **Entry criteria** — what must be true before starting
- **Exit criteria** — how you know the phase is done
- **Scope** — explicit in-scope and out-of-scope boundaries
- **Dependencies** — backbone specs, API docs, or prerequisite phases

### Step 2: Decompose Into Task Packets

List 3-8 candidate task packets that decompose the phase. Each packet should:

- have a unique `task_id`
- fit within the phase's overall scope
- be independent enough that agents can work in parallel
- have measurable acceptance criteria

Create each task packet file in `coordination/task-board/ready/` using the standard template.

### Step 3: Set Artifact Expectations

Define what every task in this phase must produce. At minimum:

- A delivery report (`coordination/delivery/<task-id>-delivery-report.md`)
- The primary implementation artifacts (code, docs, config)

The validator enforces delivery report existence for any task packet that lists `delivery_report` in its `expected_artifacts`.

### Step 4: Commit and Validate

Before opening the phase to agents:

1. Commit the phase intake document to `coordination/completed/` (or another agreed location)
2. Commit all task packets to `coordination/task-board/ready/`
3. Run `python scripts/validate_coordination_files.py` and fix any errors
4. Confirm the intake document is referenced by the first wave of task packets

### Step 5: Dispatch the First Wave

Open 1-3 task packets in the first wave. Use the standard dispatch message template from `docs/operations/external-agent-dispatch-message-templates.md`.

Do not open all packets at once. Use the rollout strategy described in `docs/operations/first-live-phase-rollout-guide.md`.

## Illustrative Example

The following shows how a hypothetical "phase3-billing" initiative would be captured in the intake template.

```
Phase ID: phase3-billing

Objective: Implement the minimum billing feature set — invoice generation,
payment recording, and balance display — for internal alpha testing.

Entry Criteria:
- Billing API spec is frozen and committed
- Database schema for invoices and payments is reviewed
- Phase 2 delivery standard is in effect

Exit Criteria:
- Invoices can be generated for test accounts
- Payments can be recorded against invoices
- Balance display renders correctly for three test scenarios
- All task delivery reports are accepted and filed

In Scope:
- src/billing/**
- database/migrations/billing/**
- docs/api/billing.md

Out Of Scope:
- Payment gateway integration (third-party dependency not yet scoped)
- Billing admin UI (separate phase)
- Recurring billing and subscriptions

Task Packet Decomposition:
- phase3-billing-01: Invoice data model and migration
- phase3-billing-02: Invoice generation service
- phase3-billing-03: Payment recording endpoint
- phase3-billing-04: Balance query API
- phase3-billing-05: Billing integration smoke tests
```

This example is illustrative only. Replace with the actual project initiative when ready.

## Validator Integration

The validator at `scripts/validate_coordination_files.py` supports the intake path in two ways:

1. **Task packet validation** — every task card must have valid front matter, required sections, and a status that matches its board folder
2. **Delivery report enforcement** — if a task packet lists `delivery_report` in expected artifacts, the validator checks that a matching file exists in `coordination/delivery/` when the task reaches `review/` or `done/`

Run the validator before opening a phase and before each review pass.

## Key References

| Resource | Path |
|---|---|
| Phase intake template | `coordination/templates/phase-intake.md` |
| Task packet template | `coordination/templates/task-packet.md` |
| Delivery report template | `coordination/templates/delivery-report.md` |
| Validator script | `scripts/validate_coordination_files.py` |
| Rollout guide | `docs/operations/first-live-phase-rollout-guide.md` |
| Dispatch templates | `docs/operations/external-agent-dispatch-message-templates.md` |
| Phase 2 productionization plan | `docs/operations/phase2-productionization-plan.md` |
