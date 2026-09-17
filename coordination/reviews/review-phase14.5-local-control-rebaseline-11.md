# Independent Review: phase14.5-local-control-rebaseline-11

- Reviewer: `CODEX_INDEPENDENT_REVIEWER_07`
- Reviewed commit: `f0709a1`
- Decision: `needs_fix`

## Required Change

### P1 — L1 is documented as launchable, but the reviewed Phase H gate still requires L2 enforcement

The rebaseline correctly says that L2 is optional, but the only reviewed
Phase H preflight remains L2-only:

- `tests/scripts/test_six_agent_pilot_preflight.py` requires six records with
  `enforcement_verified is True` and accepts an adapter only when its
  `enforcement_capability` is `sandboxed_one_shot`.
- The accepted implementation that this fixture mirrors,
  `scripts/connector_provision.py`, requires six attestations asserting
  restricted writes, process identity, and denied network egress; its
  `scripts/effectful_adapter.py` requires the same attestation before invoking
  the injected process factory.
- Yet the revised pilot protocol says that, after preflight, a local-control
  adapter may start six L1 workers, while also saying L2 is not an L1
  prerequisite.

This leaves no reviewed or executable L1 path and can mislead an operator into
believing an L1 one-shot approval is sufficient. The task forbids changing
`scripts/**`, so do not weaken the existing L2 gate here. Instead, make the
architecture, task map, pilot protocol, and Phase H card explicit that the
current adapter/provisioner are L2-only and cannot start an L1 pilot. Add a
dependency-gated, separately reviewed L1 local-control adapter/provisioner
implementation task before the live pilot, or otherwise remove the claim that
the present preflight can launch L1 workers. Its eventual contract must retain
the exact one-shot approval and all critical-action prohibitions while emitting
only `best_effort` evidence.

The new static test checks terminology only; add a deterministic documentation
contract that prevents the L1 protocol/card/task map from presenting the
existing enforced preflight as an L1 launch path.

## Validation

- `pytest -p no:cacheprovider --basetemp D:\\codex work\\Temp\\local-control-review` over local-control, Phase B.1--H affected suites: **95 passed**.
- `D:\\codex work\\.venv\\Scripts\\python.exe scripts/orchestrate.py validate`: passed.
- `git diff --check f0709a1^ f0709a1`: passed.
- Scope check: all 13 changed files are within the task card's `allowed_scope`;
  no forbidden implementation, service, database, cloud, or profile path was
  changed.

## Verified Strengths

- The durable `2026-09-18` decision accurately defines L1 as `best_effort`
  local controlled collaboration and reserves enforced restricted writes,
  process identity, and network-egress denial for L2.
- Architecture, protocol, Phase H card, task map, incident, and progress record
  consistently retain exact one-shot approval and prohibit credential access,
  merge, push, destructive cleanup, and unapproved network/runtime activation.
- The added contract test correctly guards the principal anti-claim wording;
  it is insufficient only for the implementation-path mismatch above.

## Residual Risk

Until the P1 correction is made, the documents' L1 default and the available
reviewed runtime boundary disagree. No live pilot should be dispatched or
approved from this submission; the existing fail-closed L2 implementation
continues to deny rather than create an unsafe launch.
