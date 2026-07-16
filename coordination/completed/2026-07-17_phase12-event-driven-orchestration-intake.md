# Phase Intake: phase12-event-driven-orchestration

## Objective

Turn Git-backed task-state changes into safe, idempotent orchestration events so
external worker delivery and ready-work notification no longer depend on a
human manually relaying chat summaries.

## Entry Criteria

- Phase 11 runtime safety is accepted.
- Task-card lifecycle, review reports, and `orchestrate` commands remain the
  repository source of truth.
- Git credentials are available only through normal Git transport; no secret is
  recorded in repository files.

## Exit Criteria

- A remote branch with a review task yields exactly one durable review event.
- The event can create a bounded orchestration wake-up request.
- Registered workers can poll their own ready assignments and receive a
  standard dispatch payload.
- Failures and unregistered destinations remain visible and retryable.

## Task Decomposition

### phase12-events-01: Remote Ref Monitor And Event Ledger

- **Owner**: external-agent-platform-26
- **Dependencies**: Phase 11 accepted
- **Scope**: `scripts/**`, `tests/scripts/**`, `docs/operations/**`, `coordination/**`
- **Goal**: monitor remote Git refs/task cards and emit idempotent review, ready,
  and incident events without lifecycle mutation.

### phase12-events-02: Routing Policy And Notification Payloads

- **Owner**: external-agent-platform-27
- **Dependencies**: `phase12-events-01`
- **Scope**: `scripts/**`, `tests/scripts/**`, `docs/operations/**`, `coordination/**`
- **Goal**: route events to safe orchestrator/worker destinations and retain
  pending/retry state without invoking arbitrary processes.

### phase12-events-03: Registered Worker Poller

- **Owner**: external-agent-platform-28
- **Dependencies**: `phase12-events-01`, `phase12-events-02`
- **Scope**: `scripts/**`, `tests/scripts/**`, `docs/operations/**`, `coordination/**`
- **Goal**: provide an opt-in worker-side polling command and scheduling guide.

### phase12-events-04: Codex Wake-Up Integration And E2E Gate

- **Owner**: external-agent-quality-03
- **Dependencies**: `phase12-events-01`, `phase12-events-02`, `phase12-events-03`
- **Scope**: `tests/**`, `docs/operations/**`, `coordination/**`
- **Goal**: verify the full event loop and document Codex heartbeat setup,
  failure recovery, and manual decision boundaries.

## Review Rule

Accept each task only after focused tests, full script tests, and coordination
validation pass. Review acceptance remains an orchestrator decision.
