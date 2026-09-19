# Independent Review: phase14.5-runtime-binding-repin-25

- Task ID: `phase14.5-runtime-binding-repin-25`
- Agent: `CODEX_INDEPENDENT_REVIEWER_22`
- Phase: `phase14.5-phase-h-runtime-recovery`
- Status: accepted
- Reviewer: `CODEX_INDEPENDENT_REVIEWER_22`
- Outcome: `accepted`

## Changed Files

- Review evidence only; no implementation files changed by this review.

## Acceptance Criteria Coverage

- Requires the original worker to close the pre-Popen runtime revalidation gap
  before this task can be accepted.

## Finding

### Resolved: Revalidate the runtime binding immediately before Popen

`run_live_opencode_once()` checks the runtime binding only in `_launcher()`.
The later `_spawn()` closure rechecks the wrapper content, but not the runtime
binding.  Therefore a runtime replacement after admission and before the
injected Popen still creates the PowerShell wrapper child; only the wrapper
then detects the changed binding.  This violates the task packet requirement
that a changed binding fails closed before Popen.

The implementation now repeats the opaque runtime-content validation in
`_spawn()` immediately before Popen.  Its fake-Popen regression changes the
binding after admission and proves a safe denial with no Popen calls.

### Resolved: Supply the already-validated binding to the wrapper without PATH lookup

The live runner deliberately creates its PowerShell child with an empty
environment except the approved project-context key.  The wrapper nevertheless
uses `Get-Command` to resolve the runtime.  Command resolution depends on the
child environment's search path, so the wrapper cannot reliably find the same
binding that the runner already verified.  The attempted one-shot can therefore
exit from the wrapper even though the runner admitted the binding.

The runner now passes its just-revalidated location only as an internal wrapper
parameter.  The wrapper hash-checks that supplied value immediately before
invocation, has no command search, and has no fallback route.  The fake-Popen
test verifies the internal parameter while the child environment remains only
the approved project-context mapping.  Safe results and repository evidence
remain location-free.

## Validation Steps Performed

- Focused executor and live-runner tests: 28 passed.
- `py_compile` for both modified Python modules: passed.
- `python scripts/orchestrate.py validate`: passed.
- `git diff --check`: passed.

## Scope and Privacy Review

The reviewed changes remain within the task packet scope.  The source,
contracts, and delivery evidence expose no discovered runtime identity,
provider configuration, credential, endpoint, or captured child output.  The
runner remains no-shell with the project-context-only child environment; it
preserves exact request/approval/run fencing, one-shot consumption, wrapper
content pinning, lease stops, and L1 `best_effort` wording.  The unrelated
Phase 10 task-card modification was preserved and not included in this review.

## Known Residual Risks

The runtime identity was not revalidated immediately before Popen at the time
of this review. The original worker must provide a fake-Popen regression before
independent re-review.
