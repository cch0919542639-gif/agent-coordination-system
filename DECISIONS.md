# Decisions

| Date | Decision | Rationale | Consequence |
| --- | --- | --- | --- |
| 2026-07 | Keep task lifecycle in repository files. | Git provides recoverable, reviewable evidence. | Chat is notification only. |
| 2026-07 | Route local worker deliveries owner-strict and fail-closed. | A missing owner must not leak work to another worker. | Ownerless delivery requires orchestration attention. |
| 2026-07 | Complete same-machine automation before cross-machine transport. | Shared local runtime lowers risk and validates the loop first. | Cross-machine support is deliberately deferred. |
| 2026-07 | Use progressive context files as entry points. | New threads need stable orientation without loading all documents. | Detailed specs remain the source for scoped work. |
| 2026-07 | Adopt a platform-neutral token and resource policy. | Cost control must preserve evidence and privacy across agent providers. | Provider-specific transcript tools remain opt-in and separately reviewed. |
| 2026-07 | Require explicit approval for local shared-resource Junction changes. | A Junction can affect multiple agent runtimes on one machine. | Agents must validate and plan first; only the approved plan may be applied. |
| 2026-08-09 | Integrate the accepted `phase14-local-03` status projector into the dedicated integration branch. | The worker snapshot has unrelated Git history, so only the reviewed task artifacts can be safely imported instead of merging the entire snapshot. | `codex/phase14-runtime-adapter-01-integration` contains the projector, focused tests, and operator guide; promotion to `main` requires a separate decision. |
| 2026-07-19 | Require a docs-agent phase summary after every evidence-backed phase or material segment acceptance. | Durable project memory must be updated from repository evidence rather than chat recollection. | The orchestrator opens a bounded summary task after acceptance; it updates the designated Master Plan with completion, integration state, residual risks, and next action. |
| 2026-07-20 | Use OpenCode for the first Phase 14.5 supervised-pilot candidate, with `external-agent-platform-33`, `ORCHESTRATOR` reviewer and rollback owner, and dedicated pilot provenance. | The bounded OpenCode availability probe returned `available`; the operator authorized the recommended configuration while preserving one-shot launch approval for a later task. | The launcher contract must bind only this selected provenance, default to dry run, and reject all other runtime, worker, project, branch, worktree, or run values. |
| 2026-07-21 | After clean validation and accepted review, commit, merge, and push without an additional confirmation. | The operator authorized a streamlined completion path while retaining exceptions for unresolved concerns, failed validation, conflicts, or unclear safety scope. | The orchestrator proceeds through normal integration automatically when those gates are clean; otherwise it pauses with evidence for a decision. |
| 2026-07-21 | Codex owns planning and task decomposition; other assigned agents own implementation, independent verification/review, and push execution. | The operator wants a clear separation between orchestration and delivery execution. | Planning tasks may be assigned to Codex; implementation, checking, and push tasks must name an external owner, while the existing clean-gate policy still governs whether that owner may integrate and push. |
| 2026-07-21 | Until the external GitHub export policy is resolved, the operator performs the final `git push` manually. | Codex's managed environment currently denies pushes to the configured GitHub remote as an untrusted external destination. | Codex may prepare and verify local commits, but reports the exact pending push to the operator instead of retrying or bypassing the restriction. |
| 2026-07-22 | Use the configured Hermes, OpenCall, or MemoCall external runtimes for delegated implementation and verification; do not treat internal subagents as their substitute. | The operator wants external-agent automation to reduce Codex token use while Codex retains planning and high-risk decisions. | Codex writes repo task cards and paste-ready dispatch payloads for external runtimes; it keeps planning, task decomposition, safety gates, and escalation decisions. |
| 2026-08-01 | Hermes pilot reuses the existing owner-strict `worker activate --json` durable inbox instead of Hermes Kanban. | The repository task board remains the single lifecycle authority; Hermes Kanban would create a second dispatcher and state store. | Hermes may handle only a matching assigned task and submit it to review; it must not auto-accept, merge, push, or select unassigned work. |
| 2026-08-04 | OpenCode polling uses the Windows Task Scheduler task `OpenCode Controlled Worker` at a 10-minute cadence. | It directly wakes the accepted OpenCode launcher; Codex app automation did not trigger reliably. | The task is disabled by default; when enabled, each turn handles at most one owner-matching delivery with no retry, auto-approval, or lifecycle authority. |
| 2026-07-19 | Require a docs-agent phase summary after every evidence-backed phase or material segment acceptance. | Durable project memory must be updated from repository evidence rather than chat recollection. | The orchestrator opens a bounded summary task after acceptance; it updates the designated Master Plan with completion, integration state, residual risks, and next action. |
| 2026-10-11 | Run the Hermes controlled worker through a bounded installed AIAgent session and the same native ten-minute wake-up mechanism as OpenCode. | The interactive CLI context exceeded Groq capacity; pilot-04 verified a fresh owner-strict dispatch with Qwen 3.8 27B, fixed request/output limits and immediate REVIEW receipt stop. | Worker model selection is local to the invocation; Desktop keeps GPT-OSS 120B. The native task stays disabled, both legacy cron jobs stay paused, and only the orchestrator accepts deliveries. |

## Finite deterministic local completion loop

Codex may control only an explicit finite plan whose cards name LOCAL_LOOP and
pin independent machine checks. Workers may submit but never accept or dispatch.
Repair preserves the same task and ACK within bounded attempts; failure stops
continuation. Qualitative review, merging and continuous scheduling retain
their original gates. Fresh clones create new local registrations/tasks/receipts
instead of importing runtime state.

## GitHub-mediated two-machine work (2026-10-20)

User explicitly selects GitHub task/branch/PR handoff over direct control of B.
This wave needs no mutual TLS, SSH, shared runtime DB or remote launcher/custody.
Retain those requirements only for separately scoped future remote execution.
Use one lead, frozen source/release commits, disjoint branches, host-local
evidence and independent review. No push or service activation authority is
implied. Historical TLS failures remain evidence, not GitHub blockers.
