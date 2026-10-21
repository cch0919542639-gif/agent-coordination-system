# Tasks

## First GitHub two-machine wave complete (2026-10-21)

A and B deliveries accepted;both tasks DONE. PR5 merged56575a8 into handoff.
108combined tests passed;all seven merged source/test pins match that candidate.
Main unchanged;no peer control or provider/service activation. This closes only
the first GitHub-mediated wave,not full remote-runtime/production qualification.
Durable completion summary and fresh-clone verification follow. Older pending
statements below are dated history.


## B delivery independently verified (2026-10-21)

Technically complete B delivery is verified from PR5/head2a76667:94passed
(88baseline+6new),15 independent checks passed,five source pins unchanged.
Local isolated A+B candidate9114fe6 passed108tests (88+14+6). B board state
is REVIEW pending formal PR integration,not READY/unclaimed. No B test/source
code was merged into this published branch by this review-only update.
See durability/lead-verification-summary.md under phase15-github-01 evidence.
Older B-pending statements below are dated history;do not redispatch B work.


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

User selects independent tasks on angeline and the second named computer via
GitHub branches/PRs. Direct-host TLS/SSH/remote-launch pilot is superseded; it
is not a GitHub readiness gate. Do not run earlier Downloads diagnostics or
start services. See coordination/plans/phase15-github-01.md and
docs/operations/phase15-github-handoff-guide.md. Two disjoint test packets are
prepared; publication, actual worker execution and integration remain pending.
No additional peer connections, model jobs or two-host completion claimed.

## Authoritative System

Task lifecycle lives in `coordination/task-board/`:

- `ready/`: assigned work awaiting worker claim
- `in_progress/`: active worker execution
- `review/`: submitted delivery awaiting orchestrator decision
- `done/`: accepted work
- `blocked/`: incident or dependency requires resolution

## Current Groups

- Phase 14 same-machine automation is accepted in `coordination/task-board/done/`.
- The Hermes controlled-worker parent and original supervised pilot are accepted.
- Hermes launcher parity is accepted on `phase14-hermes-pilot-04` (2026-10-11).
  Its fresh normal invocation exited zero on a verified REVIEW receipt;
  interrupted pilots 02 and 03 are in `cancelled/`, superseded by this run.
- Product project work: each registered project owns its own `coordination/`
  directory and task board; `usage-mvp-01` is awaiting orchestrator review on
  its configured worker branch.

Use `python scripts/orchestrate.py next` for a suggestion, then confirm status
from the actual task card before dispatching.

- Local-loop implementation and independent review are accepted; GitHub publication
  and fresh-download verification are accepted on phase14-loop-publication-01.

- phase14-main-integration-01 prepares verified local-loop promotion to main
  under the existing clean-validation/accepted-review completion policy.

- phase14-main-integration-01 and independent phase14-main-review-01 are
  accepted DONE; PR3 merged the verified local loop into main.
