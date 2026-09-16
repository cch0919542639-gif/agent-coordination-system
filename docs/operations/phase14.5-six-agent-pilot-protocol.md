# Phase 14.5 Supervised Six-Agent Pilot Protocol

## Purpose and boundary

This protocol is the Phase H acceptance procedure for the architecture's Six-Agent Acceptance Scenario. It is a preflight and evidence procedure, not a runtime launcher. It does not authorize or perform connector launch, credential access, network transport, Git worktree provisioning, merge, push, or cleanup.

The live pilot is fail-closed. It may begin only when every preflight input below is recorded, current, and independently checkable. Missing or unverifiable evidence produces an incident and ends the attempt; it is never replaced by a mock, a second route, or an interactive fallback.

## Exact approval preflight

The operator must record one enabled, unexpired, one-shot approval bound to `phase14.5-six-agent-pilot-08`. It must name six connector grants and six distinct admitted agent identities; the exact project-relative worktree root and six allocated worktree references; network policy, adapter/version, sandbox-enforcement evidence, run-window start/end, timeout, and stop authority; plus expected manifest/allocation digests.

The approval must state that merge, push, credential access, and cleanup are not approved by this pilot. Each connector needs independently verifiable grant admission and enforcement-capability evidence. A `network_policy: deny` grant is not proof of enforced sandbox policy. The preflight rejects unless it has exactly six distinct admitted identities, six enforcement records, a current exact approval, and all run-bound provenance.

## Supervised acceptance procedure

1. Freeze reviewed allocations, context snapshots, grants, manifests, approval, and review targets; verify hashes and expiry immediately before each launch boundary.
2. Run deterministic fake-clock evidence first: six lease identities, acknowledgement and heartbeat evidence, a fenced lease-expiry retry, and retry exhaustion that routes exactly one incident and approval-queue projection.
3. Only after preflight passes, a separately approved effectful adapter may start at most the six approved connectors in allocated worktrees. It must reject any request not exactly bound to grant, manifest, approval, worktree, network policy, and run window.
4. Collect safe references only: dispatch, acknowledgement, lease, review-queue, incident, validation, and delivery. Never record prompts, source bodies, credentials, raw logs, transcripts, or absolute paths.
5. Verify all seven architecture conditions: eight-task mixed graph; worker context/acknowledgement/lease/review evidence; one dependency unlock; bounded restart and expiry recovery; review queued with merge/push blocked; restart-safe non-duplicate dispatch; and six actual admitted enforcement-capable connectors.
6. Send evidence to an independent reviewer. Review submission is not acceptance and cannot merge or push.

## Current gate

No real pilot has run. The repository has deterministic fixtures and an operator approval validator, but no recorded Phase H approval and no six actual admitted enforcement-capable connector instances. Phase H remains at the preflight gate. A future effectful adapter requires a separately reviewed implementation task and the exact operator record above.
