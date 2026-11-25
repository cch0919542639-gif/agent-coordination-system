# Team agent workspaces: reduced-scope delivery evidence

- Task ID: team-agent-workspaces-01
- Phase: agent-control-center
- Agent: ORCHESTRATOR
- Status: independently reviewed; ready for merge preparation

## Changed Files

Team API, workspace provisioning, Agent control, console UI, tests, and task documentation.

## Acceptance Criteria Coverage

The candidate adds native workers to the existing direct-model planner, one Git
worktree per native worker, per-worker status and bound permission responses.
Before native work, an administrator verifies the Git root and pinned revision;
the system rejects an outdated confirmation.
Worktrees start at committed HEAD, remain for human inspection, share the user's
OS account and Git storage, and do not automatically merge results. The current
installed console was not modified.

## Validation Steps Performed

Live OpenCode: an owned OpenCode process in a disposable Git project created
the requested synthetic marker in its own worktree. The source checkout remained
unchanged and cleanup was confirmed. The opt-in integration test passed once:
1 passed, 5 deselected. This is evidence for that call, not a service guarantee.

The final focused team, API and mocked UI suites passed 21 tests with one
explicitly skipped opt-in live probe. Earlier team/Agent suites passed 82 tests
with two skips and direct, web-console and monitoring suites passed 98 tests.
The browser UI was exercised with mocked workers and permission requests, not
against the installed console. Final Agent, provider, console and monitor
regression passed 165 tests with one skip.

## Known Residual Risks

Hermes support uses the pre-existing guarded legacy adapter where available.
This machine's newer Hermes remains blocked and the user deferred repair; see
`coordination/incidents/2026-11-25-hermes-managed-team-startup.md`. The candidate
has not been merged, published or installed; actual console visual verification
and live multi-provider team execution remain pending.
