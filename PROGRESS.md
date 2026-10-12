# Progress

## Current State

- Central monitor and owner-strict routing are active for the local
  `agent-usage-collector` project.
- Phase 14 local activation is accepted: a worker payload is durably written
  to a local inbox before acknowledgement and resolves the real task-card path.
- Phase 14 branch-aware monitoring is accepted: the configured worker branch
  for `usage-mvp-01` produced a `review_submitted` orchestrator delivery.
- `phase14-local-03` is accepted: the worker branch was pushed, the monitor
  detected `review_submitted`, 72 focused tests and coordination validation
  passed, and the status-projector delivery is recorded on the task board.

- Hermes/OpenCode launcher parity is accepted on 2026-10-11 through
  `phase14-hermes-pilot-04`: payload `a640283f6cd83672` completed a fresh
  owner-strict activation, claim, delivery, validation, REVIEW receipt and
  orchestrator acceptance. Hermes made eight main API calls and exited zero
  without operator recovery. The bounded SDK runner and activation contract
  pass 21 focused tests. Its worker-local model is Groq `qwen/qwen3.8-27b`;
  Desktop retains `openai/gpt-oss-120b`. The native ten-minute task is disabled,
  ignores overlap and has a fifteen-minute limit; both legacy cron jobs remain
  paused. Interrupted pilots 02 and 03 are cancelled, superseded by pilot-04.

- Hermes launcher artifacts and evidence are published on GitHub in
  [draft PR #1](https://github.com/cch0919542639-gif/agent-coordination-system/pull/1),
  from `codex/hermes-launcher-parity` into the existing controlled-worker source
  branch. The isolated publication suite passed all 21 tests. Full coordination
  validation retains nine pre-existing missing labels in the unchanged base
  external review report; Hermes artifacts pass. Integration review is pending.

## Active Work

- Integrate the accepted `phase14-local-03` worker branch only after an
  explicit review/merge decision; automatic merge remains prohibited.
- Review the `usage-mvp-01` worker-branch submission and record an evidence-
  backed decision.

## Blockers And Risks

- Hermes and OpenCode controlled workers have each completed supervised,
  owner-strict handoff pilots. OpenCode's Windows Task Scheduler wake-up path
  is verified and disabled by default.
- The focused branch-aware pytest suite exceeded the bounded local verification
  window; the accepted compatibility runner and real monitor demonstration are
  retained as evidence, with a provisioned full-suite rerun still desirable.
- Same-machine runtime state is Git-ignored by design; cross-machine delivery
  is deferred.
- The status-projector worker branch is accepted but intentionally not yet
  merged into `main`.

- Groq's observed 8K TPM allowance and GPT-OSS quota failures constrain larger
  tasks. The accepted Hermes SDK path is verified on the installed v0.19.1
  runtime; recurring polling and larger workloads still need explicit scope
  and capacity validation. This was a local working-tree event-routing test,
  not a pushed-commit or production-monitor test.

## Next Action

Record an evidence-backed phase summary, decide the `phase14-local-03`
integration path, then open the bounded OpenCode runtime-adapter preflight.

## Local Completion Loop Publication

The phase14-local-loop-01 implementation is accepted with real bounded recovery,
automatic reporting, follow-up dispatch and zero-launch replay. Failed historical
pilots remain cancelled with evidence. The earlier local suite passed90 tests.
The publication branch adds portable Python discovery and a fresh-download
preparation command. GitHub clone verification is governed by
phase14-loop-publication-01; exact results are in its delivery report.
No original registry, inbox, ACKs, credentials or private transcripts are shipped.
