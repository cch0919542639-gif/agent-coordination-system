# ACS curated memory: implementation boundary

User approved the integration plan on2026-10-26. Git remains formal authority;
the memory service is an optional derived search aid. This first implemented
slice is the offline/source/approval and scoped HTTP adapter, not NAS deployment.
The [approved planning snapshot](acs-agentmemory-plan.md) and
[domain glossary](acs-agentmemory-context.md) preserve the larger gated scope.

## Domain and inputs

A source card is selected reviewed technical history. A batch fixes1..10cards
to the ACS repository, exact commit/blob hashes, source line ranges, applicability,
review references and explicit active/superseded/withdrawn state. Runtime receipts
are outside the repository. Operator approval binds the exact JSON batch digest;
it is attestation, not cryptographic reviewer identity.

## Implemented seam

One CLI and optional stdio MCP transport: preview → explicit approved conversation
submission → atom/source-marker verification → active curated recall. It uses
AgentMemory0.4.3 official endpoints and no provider SDK or new package dependency.
Lost delivery is held/reconciled, never blindly retried. Only approved card prose
is returned after verifying both source marker and remote atom ID. Shared model
persona/navigation cannot become an unchecked second answer path.

Batch activation/withdrawal applies to this adapter's output, not deletion from
upstream shared memory. Do not claim raw upstream layer cleanup. Query error is
unavailable/refused, not zero history; formal Git work can continue without memory.

## Before subsequent phases

1. Reviewer selects/approves the candidate source summaries and fixes an active
   ten-question benchmark; the shipped candidate set includes a historical-only
   question and is not a measured benchmark.
2. User chooses model endpoint, processing boundaries and spend limit. Synthetic
   HTTP tests establish adapter behavior only; no upstream LLM/source-preservation
   or recall-quality claim follows from them.
3. Run the actual0.4.3 ingestion/extraction/recall gate and measure top3quality.
   If source markers disappear or correlation is ambiguous, hold deployment.
4. Verify upstream withdrawal/rebuild if native access will be offered. Prove
   ordinary-user isolation, protected keys, backup/restore and bounded NAS load.
5. Then qualify persistent NAS service, two-device handoff and24hour operation.

No hook, webhook, scheduler, formal task-state write, worker launch, live provider,
key creation, NAS installation or external publication is part of this slice.
See [operator guide](../operations/curated-memory-guide.md) for exact supported
commands and constraints; unrelated product repositories and rental/financial
documents are outside the ACS source allowlist.
