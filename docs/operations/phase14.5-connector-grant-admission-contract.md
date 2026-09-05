# Connector Grant and Admission Contract

## Boundary

`scripts/controlplane_admission.py` is a pure in-memory planner. It does not
read files, start processes, access credentials, write task cards, invoke Git,
or perform network operations.

## Connector Grant

A grant binds one `agent_id` to one `project_id`, adapter identity and version,
allowed task classes, maximum concurrent runs, a project-relative worktree
root, deny-by-default network policy, expiry, enabled state, revocation state,
and canonical digest. Credential material is forbidden; a later runtime layer
may hold only an opaque local reference outside this contract.

Missing, altered, disabled, revoked, expired, malformed, unsafe, or
credential-bearing grants are terminal denials.

## Admission

Admission requires a valid grant plus one task owned by the grant agent. The
planner rejects identity/capability mismatches, unsafe branch or worktree
references, worktree roots outside the grant, unfinished dependencies,
duplicate task ownership, and exhausted capacity.

On success it emits a safe `admitted_no_launch` projection with stable
idempotency key. It emits no branch, credentials, prompt, source body,
absolute path, process command, or runtime output.
