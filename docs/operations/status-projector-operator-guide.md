# Status Projector Operator Guide

`python scripts/orchestrate.py status` derives local operational status for
registered projects without changing lifecycle state, delivery records, Git
branches, worktrees, or remote services.

Use JSON for automation:

```text
python scripts/orchestrate.py status --json --stale-after-hours 24
```

The command reads registered-project task-card front matter, monitor events,
delivery records, progress reports, and incident-file presence. Output
contains only project IDs, task IDs, alert codes, and repository-relative task
paths. It excludes task bodies, source content, credentials, absolute paths,
and inbox payload contents.

Alerts are observational only:

- `pending_review_delivery`: a review-submitted delivery is still pending.
- `acknowledged_ready_nonready`: a ready delivery was acknowledged but its
  matching card has since left `ready/`.
- `task_progress_mismatch`: lifecycle or ownership evidence conflicts with a
  progress report, or progress names no current card.
- `worker_branch_unmonitored`: a WORKTREE task branch is absent from the
  registered project's `monitor_branches` allowlist.
- `stale_in_progress`: an in-progress task has no progress timestamp within
  the configured threshold.

Operating loop: every 10 minutes by default, run the bounded monitor and route
commands, let workers submit repository evidence, then use `status` to decide
whether an orchestrator should investigate. Resolve alerts through the task
lifecycle or incident protocol; the projector never performs corrections.
