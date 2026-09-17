# Independent Review: phase14.5-connector-provision-10

- Review ID: `review-phase14.5-connector-provision-10`
- Task ID: `phase14.5-connector-provision-10`
- Phase: `phase14.5-connector-provision`
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_06`
- Reviewed commit: `fe079a8`
- Reviewed At: 2026-09-17
- Decision: accepted

## Summary

The provisioner is a deterministic, in-memory six-record validation boundary.
It accepts only a current, exact Phase H one-shot approval, a current accepted
adapter evidence projection, six separately valid grants, and six exact current
enforcement attestations. It creates no connector or runtime.

## Findings

- `provision_connectors()` first rejects malformed, stale, disabled, non-one-shot,
  wrong-task, unsafe, duplicate, or out-of-window approvals. The exact approval
  schema binds each of the six identity, grant, worktree, enforcement-evidence,
  manifest, and allocation values, requires `network_policy: deny`, an ordered
  prohibited-action set, and a bounded stop authority and timeout.
- The adapter projection has an exact schema and must be current, independently
  accepted for `phase14.5-effectful-adapter-09`, `sandboxed_one_shot`, and bound
  to the approved adapter ID/version. Review and implementation references are
  component-safe relative references and the reviewed commit is a SHA-256 digest.
- Each grant is revalidated through the accepted admission validator, then bound
  to its approved agent, adapter/version, task class, deny-network policy,
  worktree root, and component-safe approved child worktree. Set checks reject
  missing, duplicate, and cross-wired grant/evidence inputs.
- Every evidence wrapper has an exact two-field schema and a unique safe
  reference. Its attestation is task/run/grant/agent/worktree bound, current,
  enabled, and explicitly asserts restricted writes, process identity, and
  `network_egress: deny`. Missing, malformed, stale, duplicate, or insufficient
  attestation yields precisely one privacy-bounded capability-mismatch incident
  projection and no connector record.
- Successful records contain only allowlisted safe IDs, relative references,
  approved digests, and boolean status. Invalid approval/binding paths return
  decision-only results; the enforcement incident contains only task/run/approval
  IDs. No prompt, source body, credential, raw log, transcript, or absolute path
  is echoed or persisted.
- The module imports only `datetime` and typing plus the existing in-memory grant
  validator. Source inspection and the negative API test found no runtime,
  process, network, credential, Git, worktree, persistence, or CLI operation.

## Validation Check

- `python -m py_compile scripts/connector_provision.py` — passed.
- Focused provision suite with isolated pytest base temp — 5 passed.
- Combined B.1–H affected fixture suite (launcher, admission, worktree context,
  durable scheduler, lease recovery, evidence review, operator surface, Phase H
  preflight, effectful adapter, and provisioner) — 103 passed.
- `python scripts/orchestrate.py validate` — passed.
- `git diff fe079a8^..fe079a8 --check` — passed.
- Negative source scan found only the explicit `credential_access` prohibited
  action literal; no operational runtime or sensitive-data API was found.

## Scope Compliance

- The six files changed by `fe079a8` are all in the task card's allowed
  `scripts/`, `tests/scripts/`, `docs/operations/`, or `coordination/` scope.
  No `services/`, `src/`, `database/`, `cloud/`, `profiles/`, or `.github/`
  path changed.
- The task card remains `REVIEW`. This review adds only this evidence record;
  it did not change implementation, lifecycle state, runtime, credentials,
  network, Git state, or worktrees.

## Accepted Artifacts

- `scripts/connector_provision.py`
- `tests/scripts/test_connector_provision.py`
- `docs/operations/phase14.5-connector-provision-runbook.md`
- `coordination/delivery/phase14.5-connector-provision-10-delivery-report.md`

## Residual Risks

- All inputs remain caller-supplied, in-memory evidence. This does not create
  or independently establish a sandbox, connector, credential binding,
  worktree, process, or network enforcement.
- A live Phase H pilot still requires concrete current operator bindings and
  separately authorized effectful execution; this accepted provision boundary
  is not launch authority.
