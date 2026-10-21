# Delivery Report

- Task ID: phase15-github-durability-01
- Agent: phase15-gigabyte-worker
- Phase: phase15-github-01
- Status: DELIVERED, awaiting independent review
- Observed hostname: 技嘉202509
- OS: Windows-11-10.0.26300-SP0
- Python: 3.13.15
- pytest: 9.1.1; PyYAML: 6.0.3
- Branch: codex/phase15-github-durability-01
- Worker base: 910cb9175870fd6f3df6e699b632f85cb0a97bf4
- Dispatch commit: 7e2d2fc492f023fc6e6b30f0147be4d0ed20a7f6
- Tested candidate: 79ea5112a6e56956bf980ed1f4c43e09894807cf

## Changed Files And Artifacts

- tests/scripts/test_phase15_github_durability.py
- Own task card moved ready -> in_progress -> review.
- coordination/progress/phase15-gigabyte-worker.md
- This delivery report and own fixture-import incident (resolved).
- coordination/evidence/phase15-github-01/durability/: work-start.json,
  findings.md, execution.json, attempt-1.execution.json, both JUnit reports,
  both concise pytest outputs, coordination-validation.json, its preserved initial template-label failure,
  and final-checks.json.

## Validation Steps Performed

Verified the fetched handoff branch contains the full worker base; started a
clean clone and exact assigned branch. All five pinned inputs match SHA256.
Existing dirty D:/acs and unrelated workspace files were preserved.

Combined command: python -m pytest tests/scripts/test_offline_inbox.py
tests/scripts/test_phase15_github_durability.py -q --junitxml=.../attempt-2.junit.xml.
Result: 94 passed, 0 failures/errors/skips, 8.83 seconds pytest runtime.
Attempt 1 collection failure and one-line import repair are preserved, not erased.
Exact command, UTC times, versions, hashes and candidate are in execution.json.
Coordination validator passed after restoring two required incident headings;
its original failure is retained. Command/result are in coordination-validation.json.
Diff whitespace, allowlist, evidence size and tested Python bytes also passed.

## Acceptance Criteria Coverage

Six additional observations exceed the five-case requirement: populated journal
reinitialization and ACK isolation; reopened conflict without sequence reservation;
maximum sequence persistence; real write-lock timeout/recovery; receipt INSERT
abort/recovery; commit-exception rollback/recovery. findings.md maps each to the
baseline coverage gap. Existing 88 tests pass alongside all six new tests.
Five source pins remain byte-identical. Only the assigned allowlist is changed.

## Known Residual Risks

The new tests reuse existing synthetic fixture helpers and have no subprocesses.
They prove local SQLite behavior, not production crypto, peer transport,
power-loss behavior or hostile-host identity. Write-lock timing uses a 4..15s
tolerance around the configured 5s timeout. No production source changed.

## Recommended Handoff

On 2026-10-21 Asia/Taipei the local operator explicitly requested publishing
the completion to GitHub for review from the other computer. This authorizes
pushing codex/phase15-github-durability-01 and creating its review PR targeting
codex/phase15-github-handoff-01. Route an independent reviewer; do not accept
or merge this worker delivery.
Lead must integrate both reviewed worker candidates and run combined validation
before declaring the two-host wave complete. Later report commits do not change
the tested Python bytes; execution.json identifies the tested code candidate.
