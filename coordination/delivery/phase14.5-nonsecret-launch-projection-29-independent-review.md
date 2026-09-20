# Independent Review: phase14.5-nonsecret-launch-projection-29

- Task ID: `phase14.5-nonsecret-launch-projection-29`
- Agent: `CODEX_INDEPENDENT_REVIEWER_26`
- Phase: `phase14.5-phase-h-launch-projection`
- Status: needs_fix
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_26`
- Reviewed implementation: `bf40c3f`
- Decision: `needs_fix`

## Changed Files

- No implementation files changed; reviewed `bf40c3f`.

## Acceptance Criteria Coverage

- The pure no-process boundary and privacy scope were retained.
- P1 requires provenance validation before acceptance.

## Known Residual Risks

Projection validation remains insufficient until the P1 provenance fix is
independently re-reviewed.

## Finding

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

## Validation Steps Performed

- 32 focused projection, executor, and live-runner tests: passed.
- `py_compile` for the three relevant modules: passed.
- `python scripts/orchestrate.py validate`: passed.
- `git diff --check`: passed.

## Scope And Privacy

The submitted implementation itself remains a pure module with no process,
CLI, network, provider, credential, or worktree access.  The required fix can
remain within its existing minimal projection/validation seam.
