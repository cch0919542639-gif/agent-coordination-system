# Offline follow-up self-check, 2026-10-27

Reviewed publication baseline: `7d3076f02b02caaa959289697e2ebc8dc66cc195`,
Draft PR #11. This is author self-check and regression repair, not independent
review, source-card approval, task acceptance or permission to merge.

## Findings and repair

1. Reconciliation accepted matching content without checking the conversation
   role; a non-object row raised AttributeError. The added assistant-role and
   null-row regressions both failed before repair. Reconcile now requires one
   object with role `user`, integer total 1 and the exact submitted content.
   Refused rows leave the durable receipt `uncertain`; they cause no retry.
2. A Git subprocess timeout during an MCP request escaped the request handler
   and ended the session. The added timeout regression failed before repair.
   The handler now returns the existing safe error; a subsequent ping succeeds.

All three new cases initially failed (native exit 1); all 54 focused cases now
pass (native exit 0, 24.58 seconds). The unchanged publication baseline also
passed its original 51 cases during this self-check (24.17 seconds).

The HTTP fixture's add-response fields now match `accepted_ids`,
`accepted_versions`, and `total_count` in the pinned upstream handler. Response
envelope and query field names were checked against source, not a live service:
[AgentMemory memory.rs at reviewed commit](https://github.com/hsuanshao/AgentMemory/blob/9d2ee0de1497634e20cefa56bb5c0f951f7ab584/crates/memory-gateway/src/handlers/memory.rs).

## Evidence and remaining gates

`review-junit.xml` is sanitized passing evidence; `verification.json` records
the latest run and committed-blob hashes. The original publication JUnit remains
unchanged. No real model/provider, memory service, key or NAS was used.

The PR remains Draft and task remains REVIEW. Candidate summaries are pending
human review; the active ten-question benchmark is still unfrozen. Actual
AgentMemory extraction/source correlation, upstream cleanup, protected persistent
NAS deployment, two-device handoff and endurance have not been qualified.
