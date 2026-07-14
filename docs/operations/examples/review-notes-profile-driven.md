# Review Notes: Profile-Driven Mode

> **Runtime Status**: Profile-aware review routing is NOT implemented. `review_task.py` applies standard decisions (accepted → done/, others → stays in review/). Profile-specific checks (worktree isolation, branch naming, project-specific tests) remain manual reviewer steps.

## Pre-Review Checklist

- [ ] Task card is in `coordination/task-board/review/` (default path — NOT remapped)
- [ ] Profile referenced during dispatch (logged in progress — manual check)
- [ ] Progress file exists
- [ ] PR opened with project-formatted title (if applicable — manual check)
- [ ] Delivery report attached (if expected_artifacts includes it)

## Review Steps

1. **Read the task packet**
   - Verify all required front matter fields
   - If the task used `--profile`, confirm profile-specific fields were set correctly (manual check)
   - Check acceptance criteria against project standards
   - Confirm allowed_scope compliance

2. **Check worktree isolation** (if WORKTREE mode — manual check)
   - Verify worktree_path was used correctly
   - Confirm no cross-worktree contamination
   - Check branch follows project naming convention

3. **Check repo evidence**
   - Changed files list is complete
   - Code changes are within scope
   - No edits in forbidden_scope
   - PR title follows project format (if applicable)

4. **Validate execution**
   - Run validation: `python scripts/orchestrate.py validate`
   - Run project-specific tests (if applicable — manual step)
   - Check artifact paths

5. **Review quality**
   - Code meets project standards
   - Documentation follows project conventions
   - Tests pass

6. **Make decision using `review_task.py`**
   ```bash
   python scripts/review_task.py --task-id rental-rebuild-backend-03 --reviewer orchestrator --decision accepted --summary "Task meets all criteria."
   ```
   - `accepted`: script moves card to `done/`
   - `needs_fix`: script updates status to `NEEDS_FIX`, card stays in `review/`
   - `reassign`: script updates status to `REASSIGNED`, card stays in `review/`
   - `rejected`: script updates status to `REJECTED`, card stays in `review/`

## Reviewer Checklist

- [ ] Profile context reviewed (manual — not script-driven)
- [ ] Task card completeness verified
- [ ] Worktree isolation confirmed (if applicable — manual check)
- [ ] Branch naming follows project convention (if applicable — manual check)
- [ ] Scope compliance confirmed
- [ ] Validation passed
- [ ] Progress file updated
- [ ] PR format matches project standard (if applicable — manual check)
- [ ] Delivery report reviewed (if present)
- [ ] Quality meets standards
- [ ] Decision documented via `review_task.py`

## Review Report Template

```markdown
# Review Report

- Task: [TASK_ID]
- Profile: [profile_name] (if applicable — note this is for reference only)
- Reviewer: [reviewer name]
- Date: [YYYY-MM-DD]
- Decision: [accepted/needs_fix/reassign/rejected]

## Summary

[Brief summary of review findings]

## Profile Compliance (if profile-driven — manual check)

- [ ] Profile loaded and understood
- [ ] Task format matches profile requirements
- [ ] Branch naming follows project convention (if applicable)
- [ ] Worktree isolation confirmed (if applicable)

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

The `review_task.py` script handles the following automatically (no profile-aware routing):

### On Accept (`accepted`)
- Script moves task card from `review/` to `done/`
- Script updates progress status to DONE
- Worker notified via progress file
- Merge PR if project workflow requires (manual step)

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
- Close PR if opened (manual step)
- Notify worker and orchestrator
