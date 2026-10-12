# Independent Review: main-local-agent-loop-integration

- Task: phase14-main-review-01
- Reviewer: opencode-coordination-pilot (independent, not the integrator)
- Integrator under review: codex (`phase14-main-integration-01`)
- Baseline A: `origin/main` = 7b0a22e
- Baseline B: provider-tested publication = `c04bad5`
- Reviewed state: branch `codex/main-local-agent-loop-integration`, local prepared
  merge (staged index), no commit, no remote `main` change

## Review Scope

Inspect whether the prepared main merge introduced a regression versus either
parent, using actual source. No implementation change, no test-suite rerun, no
acceptance decision. This document is assessment only.

## Findings

### 1. Provider-tested loop source is byte-identical (no regression)

`git diff c04bad5 -- scripts/` yields exactly one file, 5 additive lines in
`scripts/orchestrate.py` (COMMAND_MAP entries `status`, `launcher-dry-run`, plus
their `build_parser` help branches). All loop/adapters are unchanged:

- `scripts/local_agent_loop.py`, `scripts/prepare_local_loop.py`,
  `scripts/verify_worker_handoff.py`, `scripts/submit_task.py`,
  `scripts/resolve-python.ps1`, `scripts/run_python.ps1` — identical to c04bad5.
- `git diff c04bad5 -- tests/` adds only main-side tests
  (`test_launcher_dry_run.py`, `test_status_projector.py`,
  `test_supervised_launch_validation.py`); provider-tested loop tests unchanged.

### 2. Main's accepted safety foundation is intact

Blob hashes compared between `origin/main` and the merged tree are identical for
`scripts/launcher_dry_run.py` (ec9a0d9), `scripts/status_projector.py` (ac8f8ad),
`scripts/runtime_adapter_preflight.py` (63f1fe2),
`scripts/supervised_launch_validation.py` (495d3f2) and `scripts/review_task.py`
(a89bf53). `git diff origin/main -- scripts/orchestrate.py` is a single added
line (`local-loop`), so main's `status` and `launcher-dry-run` commands survive.

Runtime check in the merged tree: `orchestrate status` executes the read-only
projector; `orchestrate launcher-dry-run` remains fail-closed, exiting 2 with a
usage error when `--manifest-json`/`--inbox-json` are absent. No runtime was
started.

### 3. Conflict resolutions preserve both sides' intent

- `PLAN.md`: milestone table rows and both non-goal blocks preserved; the
  "Current Milestone" line now names the local loop instead of the Phase 14.5
  external-runtime design. This is an editorial judgement by the integrator, not
  a loss — the Phase 14.5 milestone row and `PROGRESS.md` Active Work/Next
  Action are intact.
- `DECISIONS.md`: all 2026-07-21/22 main rows preserved; loop and pilot rows plus
  a finite-loop section appended.
- `PROGRESS.md`: main's accepted Phase 14/14.5 state and Active Work kept;
  publication and main-integration sections appended.
- `coordination/reviews/review-phase14.5-05-external.md`: main's authoritative
  header kept and the original external report text (reviewer "External
  Independent Verifier", decision `accepted`, task
  `phase14.5-05-external-review-01`) retained verbatim underneath. No review was
  rerun or relabelled.
- `coordination/progress/codex.md`: rolled to the new active task, which matches
  the protocol's single rolling progress file.
- `coordination/task-board/`: no existing main card was modified or deleted —
  `git diff --cached --name-status origin/main -- coordination/task-board/`
  reports only additions.

### 4. Worker/LOCAL_LOOP boundary is not widened

`LOCAL_LOOP` appears only in `local_agent_loop.py` and `prepare_local_loop.py`,
both unchanged from c04bad5. The pinned-reviewer/owner/digest gate
(`local_agent_loop.py:145`, `local_agent_loop.py:509`) and general review
(`review_task.py`, byte-identical to main) remain separate paths.

## Concrete Blockers

None found. No regression in the merge result was reproducible from source.

## Validation Performed

- `scripts/validate_coordination_files.py` — passed.
- `pytest tests/scripts/test_local_agent_loop.py tests/scripts/test_prepare_local_loop.py`
  — 29 passed in 28s. (Required `--basetemp`: the default
  `%LOCALAPPDATA%\Temp\pytest-of-angel` path is permission-denied on this
  machine; an environment condition, not a code defect.)
- Static comparison above; no provider call, no runtime launch, no branch switch.

## Residual Risks

1. `phase14-main-integration-01` is still IN_PROGRESS with no delivery report or
   `coordination/evidence/main-loop-integration-01/` test evidence. The combined
   scripts suite, PR head/base and real-run evidence remain the lead's to supply.
2. `orchestrate status` reports 56 `task_progress_mismatch` alerts. 54 concern
   legacy main tasks; 2 (`phase14-opencode-pilot-02`, `phase14-hermes-pilot-04`)
   are merge-added pilot cards. `status_projector.py:131-137` fires this alert for
   any non-`in_progress` card that still has a progress report, so DONE/CANCELLED
   pilot cards always raise it. Advisory noise, not integration damage.
3. A baseline `origin/main` projector run is not reproducible from a clean export
   (project registry is local/Git-ignored), so alert parity could not be proven
   by execution; it was proven by blob identity plus alert semantics instead.
4. `PLAN.md` "Current Milestone" no longer names the Phase 14.5 design; the
   reviewer may want that wording reconciled before merge.

## Verdict

No actionable blocker identified from actual source. Acceptance remains the
orchestrator's decision; this review neither accepts nor merges.