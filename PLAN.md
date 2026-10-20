# Plan

## Angeline implementation completed (2026-10-21)

Current Codex session executed phase15-github-validation-01 on angeline;
102tests pass (88baseline+14new),independent review accepted14checks. A is DONE.
Initial collection failure retained;2/3 allowed pytest invocations used.
Five source pins unchanged. B durability remains READY/unclaimed;no B result
or combined A/B completion is claimed. See validation execution/review evidence.


## GitHub release published (2026-10-21)

User-approved codex/phase15-github-handoff-01 was published; remote SHA verified
against first published commit bf5a3e177b4d9dd30b77c24f488888000a36ce27.
Fixed worker base:910cb9175870fd6f3df6e699b632f85cb0a97bf4. See
coordination/evidence/phase15-github-01/dispatch-pack.md and publication receipt.
Two assigned cards are READY:angeline validation and second-machine durability.
Neither worker has claimed/executed; independent results and integration remain
pending. Older BLOCKED/publication-pending passages below are preparation history.
No peer/service/provider activation. Receipt-only commits do not change worker base.

## Current direction: GitHub-only parallel collaboration (2026-10-20)

GitHub-only packet preparation and independent review are accepted DONE; two
disjoint test tasks are prepared for angeline and 技嘉202509. See
coordination/evidence/phase15-github-01/completion-summary.md for five unchanged
input pins, the local 88-pass baseline, preserved first 88 setup errors and 15
independent checks. StateController is a restricted test fixture subset.
Direct-host TLS/SSH/remote-launch work is superseded; TLS is not a GitHub gate.
Do not run earlier Downloads diagnostics or start services. Publication, explicit
assignment, actual worker execution, worker reviews and integration remain pending;
worker cards remain BLOCKED. No dual-host completion or repaired TLS is claimed.

## Objective

Provide a safe, repo-first multi-agent coordination system that supports
repeatable planning, scoped delivery, independent review, and recoverable
automation.

## Current Milestone

The provider-tested local OpenCode/Hermes completion loop is integrated on
main, preserving the Phase14.5 safety foundation and current task boundaries.
Integrated validation, independent review and fresh main download checks passed;
cross-machine transport remains deferred.

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
