# Independent Loop Review

- Task: phase14-local-loop-review-01
- Reviewer: opencode-coordination-pilot (independent of the code author)
- Date: 2026-10-12
- Scope: `scripts/local_agent_loop.py`, `scripts/verify_worker_handoff.py`,
  `scripts/submit_task.py` structured mode, `scripts/orchestrate.py`,
  `scripts/worker_poller.py`, both controlled-worker launchers,
  `integrations/hermes-coordination-worker/run_session.py`, focused tests,
  and the exported v5 evidence. Runtime `state.json`, transcripts and
  credentials were not read.

## Verdict

**No blocking defect.** Five findings below are actionable but each fails
closed; none invalidates the v5 completion evidence. This packet does not
accept, review or merge anything; ORCHESTRATOR retains that decision.

## Findings

### 1. Medium — `needs_fix` leaves a permanently pending orchestrator receipt
`scripts/local_agent_loop.py:625-629` emits the `review_submitted` delivery
first and acknowledges it only when `not failures`. Every automatic-repair
attempt therefore leaves a `pending` orchestrator notification. Verified
against the live delivery ledger: `local-loop-v3-02` is still
destination `orchestrator`, status `pending`, while that card sits in
`coordination/task-board/cancelled/`. Acceptance is unaffected — `accepted()`
(`local_agent_loop.py:85-99`) still requires a `done/` card plus an accepted
review file — so this is receipt/observability debt that can mislead
orchestrator polling, not an acceptance bypass. The v5 journal contains no
`needs_fix`, so the shipped v5 evidence is unaffected.

### 2. Medium — gitignored paths are outside scope enforcement
`local_agent_loop.py:238` builds the fingerprint set from
`git ls-files --cached --others --exclude-standard`, and `.gitignore`
excludes `coordination/monitor/`, `*.log`, `test-*/`, `.venv/`. A worker can
create or modify files under those paths without producing any
`scope_violations` entry (`local_agent_loop.py:256-259`), including extra
inbox payload files beside its own. Mitigations are real — controller state is
held in memory and rewritten by `atomic_json` after every `record()`
(line 494), and `handoff()`/`accepted()` re-derive identity from the ledger —
so this is an unenforced part of the declared boundary, not a bypass.

### 3. Medium — concurrent unrelated writes are charged to the worker, terminally
`local_agent_loop.py:582-589` diffs the whole working tree against the
pre-launch baseline. A change from any other process (monitor, another agent,
`.playwright-mcp/`, `_pytest_tmp_*/`) is attributed to the worker, sets
`terminal_failure = "scope_breach"`, and on resume lines 480-481 refuse to
continue pending operator investigation. Measured here: `fingerprints()` hashes
586 files in ~2.4 s and runs twice per attempt; several untracked, non-ignored
directories are routinely written. No occurrence is recorded — every
`worker_exited` in the v5 journal reports `scope_violations: []` — so this is
latent, not observed.

### 4. Low — one SDK backoff can consume the whole worker budget
`integrations/hermes-coordination-worker/run_session.py:167` adds the 5 s
minute-only margin and correctly declines to pad `TPD`; the SDK's own 600 s
wait is recorded at `run-events.jsonl:25`. `local_agent_loop.py:111` caps
`worker_timeout_seconds` at 900, so a late daily-quota retry would be killed
fail-closed by `taskkill /T /F` (`local_agent_loop.py:404-413`) instead of
reaching a review receipt. Attempt 1 escaped this by exiting at 341 s
(`run-events.jsonl:26`).

### 5. Low — an evidence filename asserts a v5-run event that did not occur
`coordination/evidence/local-loop-pilot-v5/opencode-automatic-repair-review.md:3-7`
is `review-local-loop-v2-01`, decision `needs_fix` — a v2-run repair record
filed under the v5 directory. The v5 journal has no needs_fix/repair event.
Content is truthful; the name is misleading.

## Verified

- **Ownership / ACK.** The payload `bbbafda0adf9880e` worker id matches the
  card owner. `handoff()` (`local_agent_loop.py:284-301`) re-verifies ledger
  status, project, owner, destination and durable inbox identity before every
  adopt; `verify_worker_handoff.py` re-runs the same check inside both
  launchers before a model call.
- **Immutable contracts.** `digest(checks)` reproduces `bef5f3a4…` and
  `5c3afcb7…`, exactly the `local_loop_checks_sha256` pins on the two DONE
  cards (enforced at lines 145 and 509). `accepted()` is True for
  `local-loop-v2-01`, and for v5-02/v5-03 under `LOCAL_LOOP`. Checker-source
  pinning is live at lines 477/513/602.
- **Scope.** The v5 tasks' `allowed_scope` cover only their evidence file,
  delivery report, progress file and own card; the pinned checks read exactly
  that evidence. Deletion and out-of-scope writes are covered by
  `test_failures_stop_before_dependent_dispatch_and_never_accept`.
- **Process termination.** `bounded_process` kills the owned tree on timeout
  (`local_agent_loop.py:404-413`), covered by
  `test_bounded_child_timeout_stops_the_owned_process`.
- **Durable resume / replay.** `run-events.jsonl:28-30` resumes attempt 2
  with no new `dispatch_prepared` and the same payload `08be7917219da139`;
  `run-events.jsonl:52-53` is a replay with zero launches, matching
  `run-summary.json:4`. Asserted at `test_local_agent_loop.py:136-137, 158-159`.
- **Bounded repair.** `max_attempts` 2 enforced at lines 566-567 and 640-641;
  same-ACK repair moves the card to `in_progress/` (line 638) and both
  launchers add the "do not claim again" override.
- **SDK receipt stop / restoration.** `run-events.jsonl:42` shows
  `completed: true` with `turn_exit_category: interrupted` — the receipt gate
  fired, not a model self-report. Compaction pinning and full `finally`
  restoration asserted at `test_hermes_controlled_worker.py:262-271, 300-303`.
- **Objective / template / minute margin preserved.** The Hermes prompt embeds
  Objective, allowed scope and the literal delivery template
  (`hermes/run-controlled-worker.ps1:81-87, 129-132`); the 5 s minute-only
  margin is asserted at `test_hermes_controlled_worker.py:275`.
- **Test-count claim.** `run-summary.json:12-14` "90 focused tests" is
  reproducible from the current tree: 23 + 43 + 18 + 5 + 1 = 90 collected
  across the five focused files. Not rerun, per the packet's instruction.

## Residual limits

The pinned checks assert artifact *content*, not provenance, so the loop
verifies declared JSON rather than semantics. That matches PLAN.md's stated
non-goal on acceptance outside a deterministic check contract. Findings 1-3
are the areas ORCHESTRATOR should weigh before the loop is used unattended.