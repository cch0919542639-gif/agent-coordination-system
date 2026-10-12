# Plan

## Objective

Provide a safe, repo-first multi-agent coordination system that supports
repeatable planning, scoped delivery, independent review, and recoverable
automation.

## Current Milestone

Integrate the accepted, provider-tested local OpenCode/Hermes completion loop
while preserving the Phase14.5 safety foundation and current task boundaries.
Integrated validation and independent review have passed; cross-machine
transport remains deferred.

## Milestones

| Milestone | Outcome | Exit Criteria |
| --- | --- | --- |
| Phase 12-13 | Monitor, event ledger, owner-strict local routing. | Accepted on `main`. |
| Phase 14 local | Same-machine worker activation with durable, safe handoff. | Activation task accepted and first local project loop verified. |
| Phase 14 branch-aware | Detect review evidence on worker branches or PR refs. | Product worker review triggers one orchestrator event. |
| Phase 14.5 | Safe external-runtime progression. | Contract and dry-run preflight accepted; supervised-launch design remains documentation-only until separately approved. |
| Phase 14 controlled workers | Owner-strict Hermes/OpenCode controlled launchers. | Local execution/reporting pilots accepted; schedules disabled. |
| Phase 14 local loop | Codex controls a finite task chain. | Real repair, checked delivery, continued dispatch and zero-launch replay accepted; integrated validation and review passed. |
| Phase 15 | Cross-machine worker delivery. | Designed only after local loop is stable. |

## Non-Goals For Current Milestone

- review acceptance outside explicitly pinned LOCAL_LOOP checks, unbounded
  launches, or automatic merge by execution workers
- supervised runtime invocation or mutable launch artifacts outside the
  separately approved controlled-worker/local-loop tasks
- cross-machine transport or credentials
- replacing repository task cards with a chat-only system
