# Phase 14.5 Connector Provision Runbook

`scripts/connector_provision.py` is an in-memory validation boundary. It does
not start a connector, a process, a network request, a worktree, or a CLI.
It never reads credentials or writes runtime state.

## Preconditions

Supply only caller-held records for one current Phase H approval:

1. An exact enabled, one-shot approval for `phase14.5-six-agent-pilot-08`,
   its run ID, six distinct identities/grants/worktrees/evidence references,
   deny-network policy, bounded window, stop authority, and manifest/allocation
   digests.
2. Six valid, current connector grants. Each must be for its approved identity,
   `external-runtime-pilot`, the approved adapter/version, the exact worktree
   root, and `network_policy: deny`.
3. Six exact enforcement-evidence wrappers. Each wrapper holds only its safe
   relative evidence reference and a current adapter attestation asserting
   restricted writes, process identity, and denied network egress.
4. Current independently accepted effectful-adapter evidence for the same
   adapter/version and the `sandboxed_one_shot` capability.

Do not supply credentials, prompts, source bodies, commands, raw logs,
transcripts, or absolute paths. All references are component-safe relative
references; `.` and `..` are rejected.

## Decision handling

`provisioned_no_runtime` returns exactly six safe records. It means only that
the supplied in-memory records are internally bound; it is not a launched or
live connector claim.

`deny_invalid_approval`, `deny_effectful_adapter_evidence`, and
`deny_connector_bindings` create no records. `deny_platform_enforcement`
returns a privacy-bounded `capability_mismatch` incident projection containing
only task, run, and approval IDs. The operator must record that projection in
the active Phase H incident and stop; do not substitute fixtures for platform
evidence or retry through another route.

## Handoff

This boundary is a prerequisite, not a pilot launcher. A separately accepted
Phase H task still needs the concrete operator approval and explicit authority
before a reviewed effectful adapter can start any connector. Merge, push,
credential access, and cleanup remain prohibited.
