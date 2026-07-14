# Dispatch Notes: Profile-Driven Mode

> **Runtime Status**: `--profile` on `dispatch_task.py` IS supported. The profile is loaded and parsed, and its context is included in the dispatch message. However, `--profile` does NOT perform schema validation — that requires a separate step (`validate.ps1` or `orchestrate validate`). Profile-aware path remapping, auto-field-population, and auto-activation are NOT implemented — those remain manual operator steps.

## Pre-Dispatch Checklist

- [ ] Task card is in `coordination/task-board/ready/` (default path — NOT remapped)
- [ ] Profile file exists at `profiles/<project>-profile.md` and passes validation (run `validate.ps1` separately)
- [ ] Profile loaded via `--profile <name>` (script-supported) or read manually
- [ ] Worktree availability confirmed (if WORKTREE mode)
- [ ] Machine affinity checked (if required)
- [ ] allowed_scope and forbidden_scope clear

## Dispatch Steps

### Script-supported steps:

1. **Dispatch with profile context** — use `--profile <name>` to load profile data into the dispatch message:
   ```
   python scripts/dispatch_task.py --task-id rental-rebuild-backend-03 --owner backend-engineer-01 --profile rental-rebuild --execution-mode WORKTREE --branch feat/rental-rebuild/rental-rebuild-backend-03-tenant-search --worktree-path worktrees/rental-rebuild/rental-rebuild-backend-03 --machine-id dev-machine-01
   ```
2. `dispatch_task.py` loads the profile by parsing its YAML front matter and includes context in the dispatch message. It does NOT validate the profile against schema rules.
3. The dispatch message includes a **profile context block** showing name, description, defaults, naming conventions, artifact paths, and worktree policy — plus explicit "Supported by scripts" / "Manual follow-up" sections

### Manual/operator steps:

4. **Validate the profile separately** — run `powershell -ExecutionPolicy Bypass -File scripts\validate.ps1` to check all profile schema rules (name uniqueness, version check, subset enforcement, path safety). This is NOT done by `--profile`.
5. **Read the task packet** — verify required front matter; check acceptance criteria
6. **Check worktree availability** — verify worktree_path doesn't conflict; create worktree if needed
7. **Assign with explicit flags** — `--profile` does NOT auto-set owner, reviewer, execution_mode, branch, worktree_path, or machine_id. All of these must be passed explicitly or set on the task card manually
8. **Move to in_progress** — card stays in `coordination/task-board/in_progress/` (NOT remapped)
9. **Notify the worker** — provide task card path, worktree path, branch, scope, and profile reference

## Worker Handoff Template

```
Task assigned: [TASK_ID]
Profile: [profile_name] (context loaded via --profile; schema validation done separately via validate.ps1)
Location: coordination/task-board/in_progress/[TASK_ID].md
Worktree: [worktree_path] (set manually by operator)
Branch: [branch] (set manually by operator)
Scope: [list allowed paths]
Forbidden: [list forbidden paths]
Validation: powershell -ExecutionPolicy Bypass -File scripts\validate.ps1
Review: Submit to coordination/task-board/review/ (default path — NOT remapped)
Reviewer: [reviewer name] (set explicitly, not from profile)
```

## Post-Dispatch Monitoring

- Check progress file updates
- Watch for worktree conflicts or machine affinity issues
- Verify branch naming compliance (manual — not script-enforced)
- Monitor test results

## What `--profile` Does and Doesn't Do

| Behaviour | Supported | Notes |
|-----------|-----------|-------|
| Load profile by name/path | ✅ Yes | `--profile rental-rebuild` or `--profile profiles/rental-rebuild-profile.md` |
| Parse YAML front matter | ✅ Yes | Returns parsed dict if file exists and has valid YAML front matter |
| Include profile context in dispatch message | ✅ Yes | Name, description, defaults, naming, paths, worktree policy |
| Separate script-supported vs manual follow-up | ✅ Yes | Explicit sections in dispatch message |
| Validate profile against schema rules | ❌ No | Run `validate.ps1` or `orchestrate validate` separately |
| Auto-set owner from profile naming convention | ❌ No | Owner must be passed via `--owner` |
| Auto-set reviewer from profile | ❌ No | Reviewer must be passed via `--reviewer` |
| Auto-remap artifact paths | ❌ No | All paths stay under `coordination/` |
| Auto-set execution_mode from profile default | ❌ No | Must pass `--execution-mode WORKTREE` explicitly |
| Auto-populate branch/worktree_path/machine_id | ❌ No | All must be passed explicitly |
