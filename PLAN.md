# Plan

## Objective

Provide a safe, repo-first multi-agent coordination system that supports
repeatable planning, scoped delivery, independent review, and recoverable
automation.

## Current Milestone

Phase 14.5: external-runtime launcher safety design.

## Milestones

| Milestone | Outcome | Exit Criteria |
| --- | --- | --- |
| Phase 12-13 | Monitor, event ledger, owner-strict local routing. | Accepted on `main`. |
| Phase 14 local | Same-machine worker activation with durable, safe handoff. | Activation task accepted and first local project loop verified. |
| Phase 14 branch-aware | Detect review evidence on worker branches or PR refs. | Product worker review triggers one orchestrator event. |
| Phase 14.5 | Safe external-runtime progression. | Contract and dry-run preflight accepted; supervised-launch design remains documentation-only until separately approved. |
| Phase 15 | Cross-machine worker delivery. | Designed only after local loop is stable. |

## Non-Goals For Current Milestone

- automatic review acceptance, merge, or external agent launch
- supervised runtime invocation or mutable launch artifacts without a separate
  one-shot approval and accepted implementation task
- cross-machine transport or credentials
- replacing repository task cards with a chat-only system
