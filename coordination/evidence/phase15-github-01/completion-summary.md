# Phase15 GitHub-only wave preparation: accepted local scope

Source `phase15-github-handoff-01` and independent review `phase15-github-review-01`
are accepted DONE. This records local packet preparation, not publication or
completion of either worker task. The user chose two machines working locally
and exchanging tasks/results through GitHub branches and PRs. Direct-host control
is superseded; 8443, mTLS, SSH and the old TLS error are not readiness gates for
this workflow. Historical failures remain evidence, not repaired-TLS claims.

## Accepted artifacts and division of work

The [plan](../../plans/phase15-github-01.md) and
[operator guide](../../../docs/operations/phase15-github-handoff-guide.md)
prepare two disjoint packets against frozen inputs:

| Machine / owner | Packet | Exclusive new test file |
| --- | --- | --- |
| angeline / phase15-angeline-worker | [validation](../../task-board/ready/2026-10-20_phase15-github-validation-01_validation-tests.md) | tests/scripts/test_phase15_github_validation.py |
| 技嘉202509 / phase15-gigabyte-worker | [durability](../../task-board/ready/2026-10-20_phase15-github-durability-01_durability-tests.md) | tests/scripts/test_phase15_github_durability.py |

A adds at least six distinct validation/rejection cases; B adds at least five
persistence/fault cases. Both read existing coverage and must add distinct
observations. Production source stays fixed; a production defect stops the worker
for lead resolution. Each worker owns separate progress/delivery/evidence files.
B's actual hostname, OS and tool versions require B-local evidence.

The selective publication candidate is `codex/phase15-github-handoff-01`, based
on remote main `bfc5163af6dca4b9b7dec6b599563e3cbf984cac`. It does not export the
integration branch's unrelated history or full Master Plan. See the dated
[scope inventory](publication-scope.json); lead must verify final lifecycle/docs
metadata and final release SHA before dispatch. Shared task roots are lead-owned.

## Five unchanged input pins

[Source pins](source-pins.json) bind source commit
`501da4e5d6fb209a27a8fb8d54811f574d008e72`; all five are byte-identical in both
trees. Narrow Git attributes disable EOL conversion for these inputs.

| File | SHA256 |
| --- | --- |
| `coordination_runtime/__init__.py` | `7b004d7a4de1a58463c2061fad6c3840dbf59629fd96d2f84d748486a73b30d4` |
| `coordination_runtime/offline_inbox.py` | `850c790244045f64bfdc7ed106afe82180ebda9a4d5bba40239ffcdfdbbe5d16` |
| `tests/scripts/test_offline_inbox.py` | `e5b3f7e24a74e120e59a0fb417b8679cabe679ee86bd1b379d5d0d0cce516ef8` |
| `docs/operations/phase15-offline-inbox-contract.md` | `e0667ed495f42e76f65b5b7bc135ae6d5030e93caaa29bbcd52f49cd0c4fa632` |
| `coordination_runtime/state_controller.py` | `a6b2a776337b10f239cce9a5fb02e03294acdaa04b40f8baeab91e4db5da412e` |

StateController is supplied unchanged only for baseline initialize and
monkeypatch(apply). Its lazy parallel/resource dependencies are not bundled;
other Controller APIs, CLI and runtime integration are unsupported here. This
is a fixture subset, not a complete runtime distribution or production verifier.

## Validation and preserved failures

- [Baseline attempt 2](local-checks.json): exit 0, 88 passed, zero errors,
  failures or skips; [JUnit](publication-baseline-attempt-2.xml) contains 88
  testcases. Outer elapsed time is 24.016 seconds. This was a local publication
  baseline, not worker A/B task execution.
- [Attempt 1 history](attempt-1-history.json) and
  [compact JUnit](publication-baseline-attempt-1.xml) retain 88 setup errors and
  zero executed test bodies: default temp PermissionError plus wrapper capture
  decoding failure. Fresh task-specific temp and UTF-8 capture corrected the
  harness without permissions changes. The oversized raw XML remains in local
  scratch with its hash/size recorded; no failure was replaced by a success.
- [Independent review](independent-review.md) and
  [checks](independent-checks.json): 15 checks passed, five preparation findings
  fixed (fixture dependency, EOL bytes, allowlist, subprocess budget and evidence
  size). Reviewer verified pins/JUnit consistency and fixture initialization;
  the 88-test run was not repeated independently.

## Remaining gates and operating limits

Publication, PR creation, READY-card release, explicit worker assignment,
actual A/B execution, independent worker reviews and combined integration
validation remain pending. Both worker cards stay BLOCKED. No push, merge,
new peer connection, worker dispatch or new model/provider job is claimed.
The old direct-control pilot is CANCELLED by supersession, not completed.

Each machine permits one concurrent top-level pytest invocation, at most three
attempts of 180 seconds within a 30-minute active-work window. The fixed baseline
may create six concurrent/twelve total synthetic child processes per invocation
(thirty-six across three attempts); new tests must not spawn processes. No new
model/API work or paid service is authorized. Evidence is capped at 256 KiB/file
and 1 MiB/host. The plan remains authoritative for all detailed budgets.

Wrong release/pin/assignment, scope conflict, missing dependency, failure, timeout
or exhausted budget stops work and preserves failed evidence. A local operator
stops that machine's process; closing a PR is not process-stop proof. Recovery
preserves branches and uses reviewed withdrawal/revert PRs, never force-push or
shared-history reset. GitHub outage preserves local commits without unbounded
retry. Final dispatch must pin the released commit, then collect host-local
results, distinct review and combined baseline plus new-test validation before
claiming dual-host completion.

This docs submission awaits lead review; it does not accept itself or grant
publication authority. Next action is lead verification of this summary and the
final publication candidate, followed by an exact-target publication decision.

Lead acceptance: phase15-github-docs-01 is now accepted DONE; see
coordination/reviews/review-phase15-github-docs-01.md (repository-relative).
The preceding submission wording is retained history. Publication remains pending.

## Approved release update (2026-10-21)

User approved the scoped GitHub publication and both READY cards. The preceding
BLOCKED/pending passages describe preparation history. Worker execution and
integration remain unperformed. Final dispatch pins the published worker base.
