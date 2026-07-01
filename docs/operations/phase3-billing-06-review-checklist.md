# Phase 3 Billing 06 Review Checklist

## Purpose

This checklist is for reviewing `phase3-billing-06` after the external backend agent submits the durable persistence work for billing.

## Task Reference

- Task card: `coordination/task-board/review/2026-07-01_phase3-billing-06_sqlite-persistence-adapter.md`
- Expected delivery report: `coordination/delivery/phase3-billing-06-delivery-report.md`
- Expected owner: `external-agent-backend-05`
- Phase: `phase3-billing-wave2`

## Review Goal

Confirm that billing now has a durable persistence option that stays inside billing scope, preserves first-wave behavior, and survives reopen or reinitialization scenarios.

## Review Sequence

### 1. Coordination File Checks

- Task card is in `coordination/task-board/review/`
- Task card front matter status is `REVIEW`
- Progress file exists and shows `WAITING_FOR_REVIEW`
- Delivery report exists at the expected path
- `python scripts/orchestrate.py validate` passes

### 2. Scope Checks

Allowed:

- `src/billing/**`
- `tests/billing/**`
- `docs/api/billing.md`
- `coordination/**`

Forbidden:

- `src/payments/**`
- `infra/**`
- unrelated app domains

Decision rule:

- If all changes stay within allowed scope, continue
- If forbidden files were touched, reject or return `needs_fix` depending on severity and intent

### 3. Core Acceptance Checks

Confirm the submission provides all of the following:

- A durable billing persistence implementation exists
- The durable store supports `save`
- The durable store supports `load`
- The durable store supports `delete`
- The durable store supports `list_by_customer`
- The durable store supports `count`
- The normal invoice lifecycle still works with the new persistence path
- Stored invoices survive reopening or reinitializing the store
- A delivery report is included

### 4. Behavioral Parity Checks

Look for evidence that the durable store preserves the important first-wave behaviors:

- Invoice data remains intact after save/load
- Line items remain intact after reload
- `paid_amount` remains intact after reload
- Invoice status remains intact after reload
- Customer-based listing still behaves correctly
- Delete behavior still removes the invoice cleanly

### 5. Test Coverage Checks

Look for targeted tests that cover:

- happy-path persistence
- reopen or reinitialize behavior
- customer listing behavior
- delete behavior
- at least one lifecycle flow using stored invoices

Preferred command evidence:

- `python -m pytest tests/billing -q`
- any focused persistence test command the agent reports

### 6. Documentation Checks

Confirm `docs/api/billing.md` explains:

- what durable store was introduced
- whether the in-memory store still exists
- any local-environment assumptions
- any known residual limitations that remain after this task

### 7. Residual Risk Checks

The delivery report should clearly state any remaining gaps such as:

- local-file locking limitations
- concurrency assumptions
- migration or schema evolution limits
- storage-path assumptions

Residual risks are acceptable if they are explicit and do not block the task acceptance criteria.

## Acceptance Decision Guide

Return `accepted` when:

- validator passes
- scope is clean
- durable persistence exists
- reopen behavior is proven
- first-wave behavior remains intact
- tests and docs support the claimed result

Return `needs_fix` when:

- durable persistence mostly works but one acceptance criterion is not proven
- reopen behavior is claimed but not actually tested
- docs do not explain the new storage behavior
- coordination artifacts are incomplete

Return `reassign` when:

- the task reveals a broader architecture issue that cannot be solved safely within billing scope

Return `rejected` when:

- the submission violates forbidden scope in a material way
- the durable implementation is misleading or unsupported by repo evidence

## Suggested Reviewer Commands

```text
python scripts/orchestrate.py validate
python -m pytest tests/billing -q
```

## Expected Output Of A Good Submission

A good submission should leave the repo with:

- a durable billing store under `src/billing/**`
- matching tests under `tests/billing/**`
- updated storage documentation in `docs/api/billing.md`
- a delivery report with validation notes and residual risks
