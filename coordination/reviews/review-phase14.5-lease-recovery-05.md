# Independent Review: phase14.5-lease-recovery-05

- Review ID: review-phase14.5-lease-recovery-05
- Task ID: phase14.5-lease-recovery-05
- Phase: phase14.5-lease-recovery
- Reviewer: CODEX_INDEPENDENT_REVIEWER_01
- Reviewed commit: 5e10b38
- Reviewed At: 2026-09-16
- Decision: accepted

## Summary

The resubmission resolves both prior P1 findings. The in-memory Phase E fixture
now has deterministic fake-clock acknowledgement, heartbeat, expiry, terminal
submission, fencing, bounded retry, incident, and approval-projection behavior
without introducing an effectful runtime boundary.

## Findings

- The prior terminal-submission defect is resolved. `submit()` changes the
  active lease state to `submitted` before returning
  `accepted_submission` (`scripts/lease_recovery.py:108-116`).
  `recover_expired()` processes only `active` leases (`126-129`), while
  subsequent heartbeat, submission, and cancellation evidence is captured as
  `deny_terminal_lease` forensic data via `_active()` (`189-199`).
  `test_submission_is_terminal_and_never_recovers_or_accepts_later_evidence`
  covers no retry, incident, or approval projection after a submitted lease.
- The heartbeat interval is now enforced with an explicit fake-clock deadline.
  Acknowledgement sets `heartbeat_deadline`; a heartbeat at or after that
  boundary returns `deny_missed_heartbeat`; a timely heartbeat renews both the
  heartbeat and lease deadlines (`scripts/lease_recovery.py:91-108`).
  `recover_expired()` routes a missed heartbeat to a fenced retry with
  `heartbeat_missed` reason (`133-145`).
  `test_missed_heartbeat_is_denied_then_recovered_with_new_epoch` covers the
  exact 20-second boundary and epoch 2 recovery; the renewal test covers an
  in-window 19-second heartbeat.
- Independent boundary probes confirm: a heartbeat at 19 seconds is accepted;
  at its exact 20-second deadline it is denied and recovery creates epoch 2;
  submitted leases reject later heartbeat/cancel evidence and remain absent
  from recovery after 60 seconds.
- Acknowledgement deadline, lease expiry, stale-epoch fencing, retry-budget
  exhaustion, one-time incident/approval routing, deterministic iteration, and
  forensic evidence remain covered. Retry exhaustion still stops rather than
  looping.
- No forbidden capability was introduced. `scripts/lease_recovery.py` imports
  only `dataclasses`, `datetime`, and `typing`; source scan finds no runtime,
  network, credential, filesystem-persistence, Git-worktree, or real-sleep API.

## Required Changes

- none

## Validation Check

- `python -m py_compile scripts/lease_recovery.py` — passed.
- `python -m pytest -p no:cacheprovider --basetemp <Temp>/codex-phasee-rereview tests/scripts/test_lease_recovery.py -q` — 9 passed.
- Combined Phase B.1–E suite (`lease_recovery`, `durable_scheduler`,
  `controlplane_admission`, `supervised_opencode_launcher`, and
  `worktree_context`) — 67 passed.
- `python scripts/orchestrate.py validate` — passed.
- `git diff 9a9dfb4..5e10b38 --check` — passed.
- The default pytest basetemp is permission-denied in this local environment;
  passing runs used a unique writable temporary basetemp. This is unrelated to
  the reviewed diff.

## Scope Compliance

- `git diff --name-only 9a9dfb4..5e10b38` changes only allowed paths:
  `scripts/**`, `tests/scripts/**`, `docs/operations/**`,
  `coordination/task-board/**`, `coordination/progress/**`, and
  `coordination/delivery/**`.
- No `services/`, `src/`, `database/`, `cloud/`, or `profiles/` path is
  changed. The task card remains `REVIEW`.
- This reviewer changed only this review record; no implementation, lifecycle,
  Git-history, runtime-state, credential, or network operation occurred.

## Accepted Artifacts

- `scripts/lease_recovery.py`
- `tests/scripts/test_lease_recovery.py`
- `docs/operations/phase14.5-lease-recovery-contract.md`
- `coordination/delivery/phase14.5-lease-recovery-05-delivery-report.md`

## Residual Risks

- This deliberately remains an in-memory fake-clock fixture. It does not
  persist leases, update task cards, launch or contact a worker, use a real
  timer, read credentials, invoke Git, or access a network.
- A later integration must carry these safe projections through authenticated
  scheduler envelopes while preserving the scheduler as the sole task-card
  lifecycle writer.
- Approval records remain in-memory projections until the later operator
  surface supplies a separately reviewed durable queue.
