# Review Notes: Default Mode

## Pre-Review Checklist

- [ ] Task card is in `review/` with complete front matter
- [ ] No active profile required for this task
- [ ] Progress file exists and is updated
- [ ] Delivery report attached (if expected_artifacts includes it)

## Review Steps

1. **Read the task packet**
   - Verify acceptance criteria are addressed
   - Check allowed_scope compliance
   - Confirm forbidden_scope was respected

2. **Check repo evidence**
   - Changed files list is complete
   - Code changes are within scope
   - No unauthorized edits in forbidden areas

3. **Validate execution**
   - Run `python scripts/orchestrate.py validate`
   - Verify no validation errors
   - Check artifact paths are correct

4. **Review quality**
   - Code meets project standards
   - Documentation is clear
   - Tests pass (if applicable)

5. **Make decision**
   - `accepted`: Task meets all criteria
   - `needs_fix`: Specific issues to correct
   - `reassign`: Different agent should continue
   - `rejected`: Delivery not acceptable

## Reviewer Checklist

- [ ] Task card completeness verified
- [ ] Scope compliance confirmed
- [ ] Validation passed
- [ ] Progress file updated
- [ ] Delivery report reviewed (if present)
- [ ] Quality meets standards
- [ ] Decision documented

## Review Report Template

```markdown
# Review Report

- Task: [TASK_ID]
- Reviewer: ORCHESTRATOR
- Date: [YYYY-MM-DD]
- Decision: [accepted/needs_fix/reassign/rejected]

## Summary

[Brief summary of review findings]

## Acceptance Criteria Check

- [ ] Criterion 1: [status]
- [ ] Criterion 2: [status]

## Scope Compliance

- [ ] All changes within allowed_scope
- [ ] No changes in forbidden_scope

## Validation

- [ ] Validator passed
- [ ] Tests pass (if applicable)

## Issues Found

[List any issues, or "None"]

## Decision Rationale

[Why this decision was made]

## Next Steps

[What happens after this review]
```

## Post-Review Actions

The `review_task.py` script handles the following automatically:

### On Accept (`accepted`)
- Script moves task card from `review/` to `done/`
- Script updates progress status to DONE
- Worker notified via progress file

### On Needs Fix (`needs_fix`)
- Script updates task status to `NEEDS_FIX` in place (stays in `review/`)
- Orchestrator or worker must manually move card back to `in_progress/` when ready to fix
- Re-review after fixes are submitted

### On Reassign (`reassign`)
- Script updates task status to `REASSIGNED` in place (stays in `review/`)
- Orchestrator must manually move card to `ready/` and assign new owner
- Document why reassignment is needed

### On Reject (`rejected`)
- Script updates task status to `REJECTED` in place (stays in `review/`)
- Orchestrator decides whether to cancel, rework, or archive
- Notify worker and orchestrator
