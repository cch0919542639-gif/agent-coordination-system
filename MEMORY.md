# Memory

## Durable Facts

- The coordination system is repo-first; task card, review report, delivery
  report, and validation evidence outrank chat summaries.
- Runtime monitor registry, ledger, routing policy, worker registrations, and
  delivery state are local Git-ignored data and must not be committed.
- A heartbeat can wake this orchestrator thread but cannot universally launch a
  third-party agent process.
- Product repositories own their own task evidence; this repository owns the
  coordination engine and its own development tasks.

## References

- `docs/operations/universal-work-context-workflow.md`
- `docs/operations/project-repository-boundary.md`
- `docs/operations/phase12-event-driven-orchestration-plan.md`
- `docs/operations/phase14-same-machine-worker-automation-plan.md`
