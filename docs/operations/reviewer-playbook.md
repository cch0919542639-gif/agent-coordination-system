# Reviewer Playbook

## Purpose

This playbook helps the orchestrator or reviewer apply consistent review logic to every submission during the first live GitHub collaboration phase. It complements the review report template at `coordination/templates/review-report.md`.

## Minimum Review Checks

Before reading the submission details, confirm the repo infrastructure is intact:

1. **Task card is in `review/`** -- the file must be under `coordination/task-board/review/` with front matter status set to `REVIEW`.
2. **Progress report is updated** -- `coordination/progress/<agent>.md` must exist and show the task as `WAITING_FOR_REVIEW`.
3. **Validator passes** -- run `python scripts/validate_coordination_files.py` and confirm zero errors.
4. **Changed files are listed** -- the agent must provide a changed-files list in the delivery evidence.

If any of these are missing, the submission is incomplete. Return `needs_fix` with the specific gap.

## Scope Compliance Check

Compare every changed file against the task packet's `allowed_scope` and `forbidden_scope` fields.

- All modified files must match at least one pattern in `allowed_scope`.
- No modified file may match a pattern in `forbidden_scope`.
- If the task packet scope is ambiguous, check the escalation rules in the packet and the coordination protocol at `docs/operations/agent-task-execution-protocol.md`.

Pass `scope_compliance` in the review report as either `PASS` or `FAIL`. If scope is violated:

| Situation | Decision |
|---|---|
| Agent knowingly edited forbidden files | `paused` + notify; record the scope risk |
| Agent needed a file outside scope but did not escalate | `paused` + notify; record the scope risk |
| Scope was genuinely unclear in the task packet | `paused` + notify; ask the user to resolve the scope decision |

## Delivery Evidence Check

The submission must contain repo-based evidence for every acceptance criterion in the task packet.

- For each `acceptance` line in the front matter, verify there is a matching artifact, file change, or documented result.
- Chat-only explanations do not count as evidence.

## Token And Resource Check

Apply this check only when the task changes agent count, model selection,
polling cadence, long-running commands, always-loaded context, or output
handling.

- Confirm the change has a bounded operational purpose and a measurement basis.
- Confirm summaries retain failures, warnings, validation results, and paths to
  recoverable original evidence.
- Confirm transcript or usage collection follows the privacy boundary in
  `docs/operations/token-efficiency-policy.md`.
- Require a disable or rollback path for a runtime behavior change.

## Outcome Decision Guide

### `accepted`

Return `accepted` only when **all** of the following are true:

- scope compliance passes (every change is within `allowed_scope`)
- delivery evidence covers every acceptance criterion
- validation notes exist and the validator passes
- progress report is accurate and up to date
- no residual risks remain and no human decision is needed

In the Phase 14.5 controller-triage flow, a clear `accepted` decision records
both triage results and automatically assigns at most one dependency-ready task
whose card explicitly depends on the accepted task. The lead agent preserves
that task's owner when assigning the continuation.
This continuation is per-delivery; unrelated review cards do not block it.

### `needs_fix`

Return `needs_fix` when the submission is on the right track but has correctable gaps:

- missing or incomplete progress update
- one or more acceptance criteria not fully met
- validator errors that the agent can fix
- scope compliance is borderline but fixable (e.g. an incident was missing)
- delivery evidence is present but incomplete

Always list exactly what must be fixed. In controller-triage mode, bounded
corrections are added to the task card and immediately returned to the same
owner.

### `reassign`

Return `reassign` when the work should continue with a different agent or the orchestrator:

- the task requires a capability the current agent does not have
- the task packet needs re-scoping before work can continue
- the agent raised an incident that changes the task direction

Preserve the task ID, add review notes explaining why reassignment is needed, and reference any incident reports.
In controller-triage mode, the lead agent may select a suitable existing
owner and return the task to `ready/` when the routing choice is clear and no
risk or human decision remains.

### `rejected`

Return `rejected` when the submission cannot be salvaged:

- scope is clearly violated with forbidden files modified
- agent repeatedly ignored escalation rules
- delivery evidence is fabricated or misleading
- the submission does not address the task objective

A rejected task must not continue in its current form. The repo-first lifecycle
CLI does not apply `rejected`; if the work cannot be salvaged, record `paused`
with `--human-decision required` so the user can decide whether to cancel or
replace the task. Do not create a replacement packet until that decision is
clear.

### `paused`

Use `paused` when the delivery needs a human decision or the lead agent
identifies risk. Keep the task in `review/`, record which condition triggered
the pause, notify the user, and do not dispatch more work.

## Decision Triage Flow

```
Does the submission have the required infrastructure?
  (task card in review/, progress updated, validator passes)
  NO  -> needs_fix
  YES -> check scope compliance

Is every changed file within allowed_scope?
  NO -> were forbidden files touched?
    YES -> paused + notify; scope risk
    NO  -> paused + notify; scope risk
  YES -> check delivery evidence

Does the evidence cover all acceptance criteria?
  NO -> needs_fix
  YES -> check residual risks

Does the lead agent need a human decision, or is any risk identified?
  YES -> paused; notify the user and stop dispatch
  NO  -> acceptance criteria met?
    YES -> accepted; continue dispatch
    NO  -> needs_fix; return bounded corrections to the same owner
```

## Writing the Review Report

Use the template at `coordination/templates/review-report.md`. Include these details in each section:

- **Summary**: one-sentence verdict (e.g. "Task meets all acceptance criteria and stays within scope.")
- **Findings**: list what was done well and what gaps were found
- **Scope Compliance**: state PASS or FAIL with the evaluation basis
- **Validation Check**: note whether the validator passed and what manual checks were done
- **Required Changes**: if `needs_fix` or `reassign`, list each required change
- **Reviewed Artifacts**: list every file or artifact considered as delivery evidence

## Key References

| Resource | Path |
|---|---|
| Review template | `coordination/templates/review-report.md` |
| Execution protocol | `docs/operations/agent-task-execution-protocol.md` |
| Rollout guide | `docs/operations/first-live-phase-rollout-guide.md` |
| Validator | `scripts/validate_coordination_files.py` |
| Task board | `coordination/task-board/` |
