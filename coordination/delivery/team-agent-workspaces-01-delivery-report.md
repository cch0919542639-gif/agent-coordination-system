# Team agent workspaces: partial delivery evidence

Task: team-agent-workspaces-01. Status: in progress; independent review pending.

The candidate adds native workers to the existing direct-model planner, one Git
worktree per native worker, per-worker status and bound permission responses.
Worktrees start at committed HEAD, remain for human inspection, share the user's
OS account and Git storage, and do not automatically merge results. The current
installed console was not modified.

Live OpenCode: an owned OpenCode process in a disposable Git project created
the requested synthetic marker in its own worktree. The source checkout remained
unchanged and cleanup was confirmed. The opt-in integration test passed once:
1 passed, 5 deselected. This is evidence for that call, not a service guarantee.

The direct, web-console and monitoring regression suites passed 98 tests. The
team/Agent suites passed 82 tests with two skips after disabling the experimental
Hermes adapter. The browser UI was exercised with
mocked workers and permission requests, not against the installed console.

Hermes support uses the pre-existing guarded legacy adapter where available.
This machine's newer Hermes remains blocked; see
`coordination/incidents/2026-11-25-hermes-managed-team-startup.md`. Independent
review, current-Hermes live workspace work and publication are not complete.
