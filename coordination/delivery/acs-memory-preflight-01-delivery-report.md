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

## Follow-up self-check (2026-10-27)

At the user's next-step request, checked Draft PR11 (no reviews, threads or CI
records at inspection), reviewed the adapter and pinned upstream response fields,
and repaired reconciliation role/row validation and MCP Git-timeout handling.
Three added regressions failed before repair; final54tests passed/native0 in
24.58seconds. Author self-check does not replace independent acceptance.
See `coordination/evidence/acs-memory-preflight-01/followup-self-check.md` and
`review-junit.xml`. The original publication evidence remains intact. Publication
continues on the same authorized Draft PR; no merge or real processing.

## Authorized branch integration (2026-10-28)

Integrated main d6c4578 into the PR11 branch at fixed merge
`3a8dfb5a80e7fd53fc525683ec954e4dfabc6258`. The sole PROGRESS.md conflict preserves both new
prefixes and one shared history. Exact parent proof retains763main files,
17feature-only files and117product/test paths, without new product logic.

One combined11file pytest invocation passed343tests/native0 in
223.281seconds (memory54 + core241 + handoff48). Encoding
overrides were unset. Fresh local Windows autocrlf clone passed73raw/blob pins,
threeCLIhelp calls, imports, validator, ten-card offline preview and clean status.
Candidate summaries remain unapproved. This is local deterministic integration
proof, not independent acceptance, a new second-device test or NAS qualification.

The ordinary diff check against the feature parent reports inherited CRLF line
endings from main's pinned snapshots. The CR-at-EOL-aware check and ordinary
PR delta check against main both pass. Pinned bytes were preserved, not rewritten.
Raw local logs remain outside Git. No real provider, real document import,
persistent NAS service, hook, worker or schedule was activated.

See coordination/evidence/acs-memory-preflight-01/integration-20261028/. PR remains Draft; no merge to main or task acceptance.

## Synthetic upstream qualification (2026-10-29)

Two real0.4.3 core/local-3B-model runs extracted one synthetic atom each; both omitted the exact source marker and the adapter refused activation. Direct upstream recall worked in the second run. Deployment remains HOLD; see coordination/evidence/acs-memory-preflight-01/upstream-synthetic-20261029/report.md for limits and the preliminary startup incident. No real documents or remote model calls.
