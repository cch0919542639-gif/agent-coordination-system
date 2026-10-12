# Plan

## Objective

Provide a safe, repo-first multi-agent coordination system that supports
repeatable planning, scoped delivery, independent review, and recoverable
automation.

## Current Milestone

Phase 14 local completion loop accepted on 2026-10-12: actual OpenCode/Hermes
dispatch, execution, checked delivery, bounded repair, continuation and stop.
Cross-machine delivery remains the next deferred milestone.

## Milestones

| Milestone | Outcome | Exit Criteria |
| --- | --- | --- |
| Phase 12-13 | Monitor, event ledger, owner-strict local routing. | Accepted on `main`. |
| Phase 14 local | Same-machine worker activation with durable, safe handoff. | Activation task accepted and first local project loop verified. |
| Phase 14 branch-aware | Detect review evidence on worker branches or PR refs. | Product worker review triggers one orchestrator event. |
| Phase 14.5 | Hermes consumes one owner-strict local handoff per scheduled turn. | A supervised pilot submits exactly one assigned task for review without lifecycle overreach. |
| Phase 14 local loop | Codex controls a finite OpenCode/Hermes task chain. | Real workers automatically report, independently checked work advances dependencies, bounded repair succeeds, and completion stops the run. |
| Phase 15 | Cross-machine worker delivery. | Designed only after local loop is stable. |

## Non-Goals For Current Milestone

- review acceptance outside an explicitly authorized deterministic check contract
- automatic merge or unbounded agent launches
- cross-machine transport or credentials
- replacing repository task cards with a chat-only system
