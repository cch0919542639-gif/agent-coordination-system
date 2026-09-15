# Phase 14.5 Lease Recovery Contract

`scripts/lease_recovery.py` is an in-memory, fake-clock fixture for Phase E.
It does not persist state, call the scheduler, launch a worker, contact a
network, read credentials, invoke Git, or use a real timer.

`LeaseRecovery.dispatch()` creates epoch 1 with an acknowledgement deadline
and lease expiry. `acknowledge()`, `heartbeat()`, `submit()`, and `cancel()`
accept only the active epoch. A heartbeat extends only an acknowledged active
lease. Invalid, stale, terminal, and expired evidence becomes a safe forensic
projection and cannot mutate the current lease.

`recover_expired()` is explicit and one-shot: it deterministically creates at
most one next epoch for a due lease when the retry budget permits. Exhaustion
creates one `lease_retry_exhausted` incident projection and one
`operator_decision_required` approval-queue projection; it never retries in a
loop. A later scheduler integration must consume these safe projections and
remain the sole lifecycle writer.
