# Independent Review: phase14.5-nonsecret-launch-projection-29

- Task ID: `phase14.5-nonsecret-launch-projection-29`
- Agent: `CODEX_INDEPENDENT_REVIEWER_26`
- Phase: `phase14.5-phase-h-launch-projection`
- Status: accepted
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_26`
- Reviewed implementation: `1cd117f`
- Decision: `accepted`

## Changed Files

- No implementation files changed; reviewed `bf40c3f`.

## Acceptance Criteria Coverage

- The pure no-process boundary and privacy scope were retained.
- P1 requires provenance validation before acceptance.

## Known Residual Risks

Projection validation remains insufficient until the P1 provenance fix is
independently re-reviewed.

## Prior Findings

### P1 — Projection validation accepts recomputed cross-wired bindings

`validate_nonsecret_launch_projection()` validates each projected binding in
isolation, but does not require its `worktree_ref` to be unique, within the
declared `worktree_root`, or equal to the reviewed agent-to-worktree identity
represented by the projection.  A modified artifact can therefore replace
`agent-01`'s reference with another component-safe child, recompute its
`binding_id` and matching request, and still validate.  This defeats the
required pre-spawn rejection of stale/cross-wired worktree provenance.

Reproduction (pure local validation, no runner or process invoked): replacing
the first binding reference with `worktrees/pilot/agent-99`, recomputing that
binding's identity and its matching request made the validator return `True`.

Require the validator to reject duplicate and cross-root references and to
bind every projected record to the reviewed identity mapping.  Add a regression
that recomputes the dependent identity/request values, so it proves the
provenance guard rather than only detecting an inconsistent digest.

## Re-review of `be560dd`

The fix adds duplicate and root-child checks and makes the immediate record /
draft copies agree.  It does not bind the projection to an independently
expected reviewed mapping, so the P1 remains.

The added regression changes only `binding_records[0]`.  A mutation that also
updates the matching `approval_draft.bindings[0]`, recomputes its `binding_id`,
and updates the matching request still returns `True` for
`worktrees/pilot/agent-99`.  All six references remain unique and within the
root, but the artifact no longer represents the reviewed agent-to-worktree
mapping.  The validator needs an independently supplied/revalidated reviewed
identity mapping (or an equivalently verifiable current mapping) at the point
the projection is accepted; a self-consistency check cannot prove provenance.

Add this complete recomputation case as the regression before resubmitting.

## Validation Steps Performed

- 33 focused projection, executor, and live-runner tests: passed.
- `py_compile` for the three relevant modules: passed.
- `python scripts/orchestrate.py validate`: passed.
- `git diff --check`: passed.

## Scope And Privacy

The submitted implementation itself remains a pure module with no process,
CLI, network, provider, credential, or worktree access.  The required fix can
remain within its existing minimal projection/validation seam.

## Final Re-review of `1cd117f`

Accepted. The validator now requires a caller-supplied independently reviewed
identity map and compares every projected agent/worktree/manifest/allocation
tuple against it. The complete-recomputation regression changes both artifact
copies, its identity, and its request, then correctly denies against the
unchanged reviewed map. Unique root-child worktree references and the
request/draft/record consistency checks also hold.

The module remains pure: no runner, process, CLI, provider, credential,
network, or worktree access was added. It contains only non-secret projection
identities; it neither materializes approval nor invokes a pilot.

Final checks: 34 focused tests, `py_compile`, coordination validation, and
`git diff --check` all passed.
