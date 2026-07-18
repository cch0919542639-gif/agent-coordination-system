---
- Task ID: phase14-branch-01
- Agent: external-agent-platform-31
- Phase: phase14-branch-aware-monitoring
- Status: WAITING_FOR_REVIEW
- Last Updated: 2026-07-19
---

## Changed Files

- `scripts/project_registry.py` — validated and de-duplicated optional
  `monitor_branches` local-registry field
- `scripts/remote_ref_monitor.py` — bounded default-plus-allowlist fetch/ref
  inspection, worker review filtering, and retained per-ref monitor cursors
- `tests/scripts/test_remote_ref_monitor.py` — temporary-remote coverage for
  allowlist detection, exclusion, duplicate polls, independent cursors, and
  no mutation
- `docs/operations/phase12-monitor-operator-guide.md` — registration,
  bounded-resource, recovery/disable, and `usage-mvp-01` procedures
- `coordination/progress/external-agent-platform-31.md` — task progress
- `coordination/task-board/review/2026-07-19_phase14-branch-01_branch-aware-review-monitor.md`
  — submitted task card

## Validation Steps Performed

1. `python -m py_compile scripts/project_registry.py scripts/remote_ref_monitor.py tests/scripts/test_remote_ref_monitor.py` — passed.
2. Isolated temporary-remote compatibility runner — 6/6 passed: default-only
   compatibility, allowed worker review detection, unconfigured exclusion,
   duplicate polling/per-ref state, task-card immutability, and no commit
   creation.
3. Isolated temporary-remote `usage-mvp-01` monitor plus route demonstration
   — one matching sanitized event was detected and routed to `orchestrator`:
   `project_id=agent-usage-collector`,
   `ref=agent/external-agent-research-01/usage-mvp-01`,
   `task_id=usage-mvp-01`, `event_type=review_submitted`,
   `owner=worker-agent`, `reviewer=ORCHESTRATOR`. The temporary runtime state
   was removed after the demonstration; no real registry, task card, or
   delivery record was changed.
4. `python scripts/orchestrate.py validate` — passed.
5. `git diff --check` — passed.
6. `python -m pytest tests/scripts/test_remote_ref_monitor.py -q` and the
   required full `python -m pytest tests/scripts/ -q` are blocked in this
   active interpreter because `pytest` is not installed (`No module named
   pytest`). No pytest pass claim is made.

## Known Residual Risks

- Reviewer must run the focused and full pytest suites in a provisioned Python
  environment.
- The branch allowlist remains intentionally local ignored configuration; an
  operator must add the exact worker ref before it can be monitored.
- The monitor remains evidence-only and does not create worker worktrees,
  perform lifecycle actions, launch agents, or merge changes.

## Acceptance Criteria Coverage

- [x] Explicit validated branch allowlist with default-only compatibility
- [x] Bounded configured-ref fetch and no broad remote-head enumeration
- [x] Worker `REVIEW` evidence emits routed `review_submitted` with actual ref
  and commit metadata
- [x] Per-project/per-ref idempotent state preservation
- [x] Isolated no-mutation and branch-awareness validation
- [x] Operator registration, cadence/resource, recovery/disable, and
  `usage-mvp-01` recipe
