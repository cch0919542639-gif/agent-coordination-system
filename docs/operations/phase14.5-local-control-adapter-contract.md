# Phase 14.5 L1 Local-Control Adapter Contract

`local_control_provision.py` and `local_control_adapter.py` are pure,
in-memory L1 boundaries. They are for `best_effort` local controlled
collaboration, not a sandbox or an enforced isolation boundary.

## Required approval

One exact, enabled, unexpired, one-shot approval must bind
`phase14.5-six-agent-pilot-08`, one run, a component-safe worktree root, and
exactly six distinct bindings. Each binding contains one agent and grant, a
component-safe child worktree, a fixed safe runtime and argv allowlist, bounded
timeout, stop authority, and scheduler, lease, review, manifest, and allocation
references. By default, the approval's prohibited actions are exactly
credential access, merge, push, cleanup, and network activation. A separate
exact `network_provider_exception` may instead be enabled for one approved
run. It allows only existing local provider configuration and the configured
model service, binds an explicit sorted subset of `APPDATA`, `LOCALAPPDATA`,
`PATH`, `SYSTEMROOT`, `USERPROFILE`, and `WINDIR`, and leaves cleanup, merge,
and push prohibited. It does not contain a credential or endpoint.

Unknown fields, expiry, unsafe references, duplicate identities/grants/worktrees,
cross-root worktrees, malformed fixed arguments, or consumed runs deny before
the injected factory is called.

## Evidence and process boundary

Provisioning returns six safe binding records marked `best_effort`; it does not
create a worker. The adapter checks a request against one of those records,
consumes the bound run, then makes at most one injected fake-process call. A
timeout calls only that fake process's `terminate_tree` method and returns
privacy-bounded evidence.

The output records separate worktree provenance, fixed runtime identity,
timeout/stop handling, and durable scheduler/lease/review references. They do
not assert enforced restricted writes, independent OS process identity, or
denied network egress. No runtime, connector, network, credential, Git
worktree, merge, push, or cleanup operation is implemented by either module.

## L2 separation

The L2-only `effectful_adapter.py` and `connector_provision.py` remain
unchanged. L1 records are not enforcement attestations and cannot be used to
make an L2 isolation claim.
