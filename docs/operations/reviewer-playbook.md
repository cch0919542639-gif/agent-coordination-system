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
| Agent knowingly edited forbidden files | `rejected` |
| Agent needed a file outside scope but did not escalate | `needs_fix` + require an incident |
| Scope was genuinely unclear in the task packet | `needs_fix` + patch the scope or reassign |

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
- no residual risks block merging or continuation

### `needs_fix`

Return `needs_fix` when the submission is on the right track but has correctable gaps:

- missing or incomplete progress update
- one or more acceptance criteria not fully met
- validator errors that the agent can fix
- scope compliance is borderline but fixable (e.g. an incident was missing)
- delivery evidence is present but incomplete

Always list exactly what must be fixed. The original agent should continue.

### `reassign`

Return `reassign` when the work should continue with a different agent or the orchestrator:

- the task requires a capability the current agent does not have
- the task packet needs re-scoping before work can continue
- the agent raised an incident that changes the task direction

Preserve the task ID, add review notes explaining why reassignment is needed, and reference any incident reports.

### `rejected`

Return `rejected` when the submission cannot be salvaged:

- scope is clearly violated with forbidden files modified
- agent repeatedly ignored escalation rules
- delivery evidence is fabricated or misleading
- the submission does not address the task objective

A rejected task must not continue in its current form. If the work is still needed, create a new task packet with adjusted scope.

## Decision Triage Flow

```
Does the submission have the required infrastructure?
  (task card in review/, progress updated, validator passes)
  NO  -> needs_fix
  YES -> check scope compliance

Is every changed file within allowed_scope?
  NO -> were forbidden files touched?
    YES -> rejected
    NO  -> needs_fix + incident
  YES -> check delivery evidence

Does the evidence cover all acceptance criteria?
  NO -> needs_fix
  YES -> check residual risks

Are there blocking risks?
  YES -> needs_fix or reassign depending on severity
  NO  -> accepted
```

## Writing the Review Report

Use the template at `coordination/templates/review-report.md`. Include these details in each section:

- **Summary**: one-sentence verdict (e.g. "Task meets all acceptance criteria and stays within scope.")
- **Findings**: list what was done well and what gaps were found
- **Scope Compliance**: state PASS or FAIL with the evaluation basis
- **Validation Check**: note whether the validator passed and what manual checks were done
- **Required Changes**: if `needs_fix` or `reassign`, list each required change
- **Accepted Artifacts**: list every file or artifact accepted as delivery evidence

## Key References

| Resource | Path |
|---|---|
| Review template | `coordination/templates/review-report.md` |
| Execution protocol | `docs/operations/agent-task-execution-protocol.md` |
| Rollout guide | `docs/operations/first-live-phase-rollout-guide.md` |
| Validator | `scripts/validate_coordination_files.py` |
| Task board | `coordination/task-board/` |
