# Delivery Report: phase14.5-pilot-approval-fanout-20

- Task ID: `phase14.5-pilot-approval-fanout-20`
- Agent: `CODEX_PLATFORM_WORKER_11`
- Phase: `phase14.5-phase-h-pilot-fix`
- Status: submitted for independent review

## Changed Files

- `scripts/local_opencode_executor.py`
- `scripts/local_opencode_live_runner.py`
- `tests/scripts/test_local_opencode_executor.py`
- `tests/scripts/test_local_opencode_live_runner.py`
- `docs/operations/phase14.5-local-opencode-executor-contract.md`
- `docs/operations/phase14.5-six-agent-pilot-protocol.md`
- task, progress, and delivery evidence for this task

## Acceptance Criteria Coverage

- One approval produces one exact admission marker, preserving the same
  admitted pilot across its six approved binding launches.
- Each launch receives a separate token composed only after exact approval,
  request, record, lease, and project-context validation; duplicate and
  cross-wired requests deny before spawn.
- A populated admission state rejects a different second pilot. Expired,
  foreign, malformed, or missing-state inputs deny without a child boundary.
- The live seam forwards the same fenced state to the executor. Fixed wrapper
  provenance, `shell=False`, output suppression, redaction, matching stop,
  no retry/fallback, and L1 `best_effort` terminology remain unchanged.
- Task 19's pre-launch cardinality incident is resolved in fake-child tests:
  all six exact bindings can launch once under one admission instead of only
  the first binding.

## Validation Steps Performed

- `py_compile scripts/local_control_provision.py scripts/local_opencode_executor.py scripts/local_opencode_live_runner.py` — passed.
- Focused provision/executor/live-runner tests with isolated basetemp — 26 passed.
- Affected Phase B.1--H fixture suite with isolated basetemp — 131 passed.
- `scripts/orchestrate.py validate` — passed.
- `git diff --check` — passed.

## Known Residual Risks

This is fake-child-only correction evidence. It did not materialize an
approval or execute OpenCode, Popen, network/provider/credential access, or
worktree action. A future real attempt requires a fresh exact approval and
independent acceptance of this fix.
