# Dispatch Notes: Default Mode

## Pre-Dispatch Checklist

- [ ] Task card is in `ready/` with complete front matter
- [ ] No active profile required for this task
- [ ] allowed_scope and forbidden_scope are clear
- [ ] Dependencies are resolved (or noted as blockers)
- [ ] Agent availability confirmed

## Dispatch Steps

1. **Read the task packet**
   - Verify all required front matter fields exist
   - Confirm acceptance criteria are measurable
   - Check expected_artifacts list

2. **Assign the task**
   - Select agent based on task type (docs, test, platform, etc.)
   - Use free-form agent naming: `external-agent-<category>-<number>`
   - Update owner field in task card

3. **Move to in_progress**
   - Move card from `ready/` to `in_progress/`
   - Update status to IN_PROGRESS
   - Create or update progress file

4. **Notify the worker**
   - Provide task card path
   - Confirm allowed_scope boundaries
   - Remind of validation steps

## Worker Handoff Template

```
Task assigned: [TASK_ID]
Location: coordination/task-board/in_progress/[TASK_ID].md
Scope: [list allowed paths]
Forbidden: [list forbidden paths]
Validation: Run python scripts/orchestrate.py validate
Review: Submit to coordination/task-board/review/
```

## Post-Dispatch Monitoring

- Check progress file updates at meaningful intervals
- Watch for blocker reports in coordination/incidents/
- Verify task doesn't stall in in_progress for too long
