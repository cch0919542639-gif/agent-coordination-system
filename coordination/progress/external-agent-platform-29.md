---
- Agent: external-agent-platform-29
- Active Task: phase13-events-01
- Phase: phase13-event-delivery-runtime
- Status: NEEDS_FIX
- Last Updated: 2026-07-17
---

# Progress: phase13-events-01

## Current Step
NEEDS_FIX — implementing fixes for owner-aware delivery, stale docs, and JSON output.

## Changes So Far
- Added `owner` and `reviewer` fields to Event dataclass in event_ledger.py
- Updated remote_ref_monitor.py to populate owner/reviewer from task card front matter
- Updated routing_runner.py to pass owner/reviewer from events to route_event()
- Updated worker_poller.py to filter ready_assigned notifications by owner matching worker_id
- Corrected phase12-monitor-operator-guide.md: removed unsupported --add-project, documented actual onboarding flow
- Rejected --route --json combination with clear error message and alternative
- Added 4 new tests: owner-aware delivery (2), owner field round-trip, JSON rejection
- Updated existing test helpers to set owner to match worker_id or empty

## Blocker Status
No blockers. All fixes implemented and tests passing.

## Next Step
Pushing updated branch for re-review.
