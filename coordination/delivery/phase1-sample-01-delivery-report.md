# Delivery Report

- Task ID: phase1-sample-01
- Agent: sample-agent
- Phase: phase1-foundation
- Status: DELIVERED

## Changed Files

- `coordination/task-board/ready/example_reference_task_card.md` — New sample task card created using the standard template (`coordination/templates/task-packet.md`). Demonstrates all required front matter fields (task_id, phase, status, owner, reviewer, priority, dependencies, allowed_scope, forbidden_scope, acceptance, expected_artifacts) and all body sections (Objective, Context, Constraints, Implementation Notes, Validation Steps, Escalation Rules) with realistic example content.

## Artifact Paths

- `coordination/task-board/ready/example_reference_task_card.md` — deliverable task card
- `coordination/delivery/phase1-sample-01-delivery-report.md` — this report

## Validation Steps Performed

1. **Template compliance:** Verified the new task card matches the structure in `coordination/templates/task-packet.md` — all 11 front matter fields present, all 6 body sections present.
2. **Scope check:** All changes are within `docs/**` and `coordination/**`; no files touched in `src/**` or `database/**`.
3. **Markdown validity:** The task card is valid markdown with proper YAML front matter delimiters (`---`).
4. **Validator:** `python scripts/orchestrate.py validate` — passed.

## Known Residual Risks

- The example task card is a reference only; it is not an executable task and should not be dispatched unless a real task with matching spec exists.
- The example card uses placeholder acceptance criteria and should be replaced with real criteria before any real agent is assigned to it.

## Recommended Handoff

The sample task card is ready as a reference for future agents joining the project. When a new agent needs to understand the task packet format, point them to `coordination/task-board/ready/example_reference_task_card.md`.

## Acceptance Criteria Coverage

| Criterion | Status | Evidence |
|---|---|---|
| Create a sample task card using the standard template | Met | `coordination/task-board/ready/example_reference_task_card.md` follows `coordination/templates/task-packet.md` |
| Keep all changes inside documentation and coordination folders | Met | All changes in `coordination/` |
| Include validation notes in the final delivery report | Met | Validation Steps and Acceptance Criteria Coverage sections above |
