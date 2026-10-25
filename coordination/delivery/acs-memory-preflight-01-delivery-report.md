# Delivery Report

- Task ID: acs-memory-preflight-01
- Agent: codex-memory-implementation
- Phase: acs-memory-pilot
- Status: DELIVERED FOR REVIEW

## Changed Files

- `scripts/curated_memory.py`: one optional stdlib CLI plus stdio query tool.
- `tests/scripts/test_curated_memory.py`: source, approval, delivery, activation,
  scope, HTTP, MCP and isolated Windows transport regression coverage.
- `docs/operations/curated-memory-guide.md`: actual commands and limits.
- `docs/specs/acs-agentmemory-integration.md`, `acs-agentmemory-plan.md`,
  `acs-agentmemory-context.md`: implemented slice and approved planning snapshot.
- This task's packet, progress, evidence and root progress update only.

## Artifact Paths

`coordination/evidence/acs-memory-preflight-01/` contains unapproved ten-card
candidate batch/questions, offline preview, final JUnit, sanitized earlier failed
JUnit and verification summary. Original local test artifacts remain outside Git.

## Validation Steps Performed

- Python3.13.15 focused pytest: **51passed,0failed,0skipped, native exit0**,
  21.60seconds. Runs in temporary synthetic Git repositories and a loopback HTTP
  contract fixture; no AgentMemory instance or model is called.
- The end-to-end isolated CLI test exercises import/verify/query/MCP across
  separate processes and persistent receipt SQLite, with Chinese/emoji cards and
  ordinary Windows output encoding; JSON stdout is ASCII transport.
- Real candidate preview verifies10pinned Git source blobs and origin without
  network or receipt writes. Candidate references remain pending-human-review
  and cannot import even with a copied digest.
- Coordination validator passed before final delivery metadata; final validation
  and diff check are recorded in the verification artifact.
- The first37 and44case runs passed; a later50case run had49pass/1fail because
  the environment parsed2000nested JSON levels without raising RecursionError.
  The code now enforces64levels explicitly. The repaired50case run passed before
  the final51case run added bounded Git blob loading coverage. Failure evidence
  was retained, not hidden or called an upstream defect.

## Acceptance Criteria Coverage

| Task criterion | Evidence / boundary |
| --- | --- |
| Git provenance before side effects | Exact origin, commit object type, regular blob, source size/hash and line anchors validated before network or ledger initialization |
| Exact approval and processing reference | Offline digest preview; pending card/processing references refused; exact manifest and connection stored privately in receipts with approval time |
| Durable import and ambiguity | Deterministic sessions, unique per-scope/card receipts reserved before HTTP; lost reply held, exact read reconciliation, no blind resend |
| Active curated recall | Atomic activation; verified atom IDs and source markers required; superseded/withdrawn/stale/foreign candidates and shared persona are excluded at adapter output |
| Meaningful negative verification | Tampering, secrets, redirect, malformed/oversized/deep JSON, uncertain delivery, source marker loss, scope mismatch, mid-query activation, outage and isolated CP950-safe JSON transport |
| Reviewable sources | Ten real public Git document candidates and question expectations prepared without claiming their content or processing is approved |

## Known Residual Risks

The local adapter slice is implemented. P0content approval and the full P1/P2
upstream deployment gates are **not complete**: no model endpoint or cost/source
authorization was chosen, and no actual upstream extraction or8/10benchmark was
run. Synthetic extraction preserves a marker by construction; it cannot prove a
real model will do so. Marker omission refuses activation.

Withdrawal filters this adapter only; upstream L1/L2/L3 may retain history. Do not
give raw upstream recall the same provenance/withdrawal claims. No attempt to
repair/delete an upstream scope is made. More than100atoms refuses verification.

Operator digest/reference is local attestation, not reviewer authentication or a
cryptographic signature. Runtime receipt/connection files must be protected by
the operator. Ordinary keys are not server-enforced read-only. Only a single-user,
single-project pilot over a numeric loopback SSH tunnel is supported.

No NAS service, model, credentials, hooks, schedule, worker, production database or
formal acceptance logic was changed. No independent reviewer or full-repository
regression is claimed. On2026-10-26 the user explicitly authorized publication
to the original GitHub repository with a Draft PR, without merge. Publication
sanitizes the non-loopback endpoint test to a documentation-reserved address;
the final publication check is recorded separately in the verification artifact.

## Recommended Handoff

Reviewer/user should inspect the adapter and candidate summaries, freeze an active
ten-question benchmark, and decide model endpoint, processing scope and spend.
Next perform actual0.4.3 ingestion/source-correlation and withdrawal qualification.
If official extraction cannot preserve trustworthy correlation, hold deployment
and compare the existing Markdown search before adding another subsystem.
