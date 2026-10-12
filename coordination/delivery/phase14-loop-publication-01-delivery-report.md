# Delivery Report

- Task ID: phase14-loop-publication-01
- Agent: codex
- Phase: phase14-local-agent-loop
- Status: DELIVERED

## Changed Files

- Scoped local-loop controller, handoff, activation, submit and worker adapters
- scripts/run_python.ps1 and scripts/resolve-python.ps1 (portable Python discovery)
- scripts/prepare_local_loop.py (fresh local registrations and scoped demo packets)
- Focused controller, worker, bootstrap and runtime-wrapper tests
- docs/operations/local-agent-completion-loop.md and github-download-verification.md
- Publication README, scripts index, PLAN, PROGRESS, TASKS and DECISIONS
- Local-loop task cards/reports/reviews and filtered historical/current evidence
- coordination/reviews/review-phase14.5-05-external.md: missing schema labels only; original review body preserved

The isolated publication checkout started clean on the earlier Hermes branch.
74 explicit files were staged for the source commit. Original unrelated dirty
working-tree changes were not staged, reset or published.

## Artifact Paths

- GitHub branch: https://github.com/cch0919542639-gif/agent-coordination-system/tree/codex/local-agent-completion-loop
- Remote source commit: ca7cdf175272a9442c68a5b597bbffde5ebf66d4
- docs/operations/github-download-verification.md
- coordination/evidence/github-download-check-01/verification.json
- coordination/evidence/github-download-check-01/run-events.jsonl and run-summary.md
- coordination/evidence/github-download-check-01/opencode-attempt-1-needs-fix.md
- Fresh stage1.json, stage2.json and final.json in that evidence directory
- DONE cards, worker delivery/review reports and pinned plan for github-download-check-01-01/02/03

## Validation Steps Performed

1. Publication checkout:97 focused tests passed in64.72s; full coordination
   validation and Git diff checks passed. This includes the prior90 tests plus
   six fresh-bootstrap conflict/receipt-preservation tests and one portable
   runtime/quoted-argv test. No provider call was used by those tests.
2. Pushed source commit ca7cdf1, then cloned the actual GitHub branch into a
   new directory. Remote HEAD and clone HEAD matched. The initial clone was
   clean and contained no coordination/monitor machine state. All12 runtime
   source files matched local publication/original source by LF-normalized
   SHA256 and Git blob content.
3. Ran the downloaded preparation tool, creating a new exact-checkout registry,
   workers/routes and three new scoped READY cards. No old registry, inbox,
   ACK, attempt counter or private transcript was copied. Preparation launched
   zero models. Full coordination validation passed.
4. Fresh GitHub clone:97 focused tests passed in97.31s. An initial test-harness
   invocation had an uncreated basetemp parent; the corrected independent
   ignored temporary directory passed. No source change was needed.
5. Actual newly downloaded workers executed github-download-check-01. OpenCode
   submitted6, received needs_fix and automatically repaired to7 under the same
   ACK. Hermes attempt1 stopped on provider HTTP400 tool generation; no delivery
   was accepted and dependent work was not launched. Explicit same-ACK attempt2
   produced21 and used structured submission, with bounded minute-rate waits.
   After receipt/scope/JSON checks, the controller accepted Hermes and
   automatically dispatched OpenCode to write the final completed artifact.
   All three cards were accepted DONE; worker scope violations were empty.
6. Run completed2026-10-12 03:10:40 UTC. Replay completed03:11:51 UTC and
   launched zero workers. Source/integration/test Git diff remained empty;
   full coordination validation passed after the final worker delivery.

## Known Residual Risks

This was a clean GitHub download on the same physical Windows computer using
existing installed OpenCode/Hermes and existing providers. A second physical
computer or different OS was not tested. Python3.11+, Git, PowerShell, the agent
installations and valid local provider configuration are prerequisites; a clone
does not install them or transfer credentials. Hermes SDKv0.19.1 and native
OpenCode1.18.35 were the existing verified installations.

Provider tool generation and rate limits remain real failure conditions; this
was completion after bounded same-ACK recovery, not an uninterrupted first
attempt. Historical DONE plans cannot replay on a new machine without their
original local receipts; the documented path creates fresh IDs instead.
Git-visible scope checking is not an OS sandbox; reserve the checkout during a
run. General qualitative acceptance, cross-machine task transport and continuous
worker scheduling remain outside this finite deterministic contract.

Publication is on codex/local-agent-completion-loop, stacked on the earlier
Hermes branch; main has not been merged. No force push, credential change,
production action or recurring worker activation was performed.

## Recommended Handoff

Clone the explicitly named branch and follow github-download-verification.md.
Use prepare_local_loop.py --run-id FRESH-ID, validate, preview the plan, then
execute local-loop --plan PATH --run. Preserve its plan/ACK on --resume.
For general tasks, Codex supplies their own scoped packets and independent
checks. The exported verification.json records the tested remote source commit;
follow-up publication changes add evidence/docs without changing tested runtime
source. The draft PR is for review; merge is a separate decision.

## Acceptance Criteria Coverage

- Scoped publication: source commit pushed on the correct repository/branch; original dirty work and prior PR preserved.
- Fresh-download isolation: actual remote clone started without local runtime data;12 runtime files matched source; new registrations/tasks/receipts created locally.
- Real execution: accepted OpenCode repair -> Hermes21 -> OpenCode completion, with truthful retained HTTP400 stop and bounded same-ACK resume.
- Evidence and validation:97 tests in both checkouts, full validators, exact source identity, actual DONE/report/review artifacts and zero-launch replay recorded.
