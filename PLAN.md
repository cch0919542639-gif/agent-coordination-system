# Plan

## Objective

Provide a safe, repo-first multi-agent coordination system that supports
repeatable planning, scoped delivery, independent review, and recoverable
automation.

## Current Milestone

Phase 14.5: six-agent controlled orchestration plane.

## Milestones

| Milestone | Outcome | Exit Criteria |
| --- | --- | --- |
| Phase 12-13 | Monitor, event ledger, owner-strict local routing. | Accepted on `main`. |
| Phase 14 local | Same-machine worker activation with durable, safe handoff. | Activation task accepted and first local project loop verified. |
| Phase 14 branch-aware | Detect review evidence on worker branches or PR refs. | Product worker review triggers one orchestrator event. |
| Phase 14.5 | Safe local controlled-runtime progression. | L1 local controlled collaboration is separately approved and still requires one-shot approval for a real process start; L2 enforced isolation is optional hardening. |
| Phase 15 | Cross-machine worker delivery. | Designed only after local loop is stable. |

## Non-Goals For Current Milestone

- automatic review acceptance, merge, push, or external agent launch outside a
  pre-approved, sandboxed connector grant
- supervised runtime invocation or mutable launch artifacts without a separate
  one-shot approval and accepted implementation task
- cross-machine transport or credentials
- replacing repository task cards with a chat-only system
