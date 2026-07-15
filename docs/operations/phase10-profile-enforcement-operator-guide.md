# Phase 10 Profile Enforcement — Operator Guide

## Purpose

This guide tells operators exactly what Phase 10 does today and what it does
not do.  Every claim below has been verified by the end-to-end regression
matrix in `tests/scripts/test_profile_e2e_regression.py`.

## Quick-Start Command Sequence

```
1.  python scripts/validate_coordination_files.py          # validate profile files + task cards

2.  python scripts/dispatch_task.py \
      --task-id <TASK-ID> \
      --owner <AGENT> \
      --profile <NAME-OR-PATH>                             # optional: record profile on task card

3.  python scripts/validate_coordination_files.py          # re-validate before submission
```

Step 2 records the canonical `profile_name` on the task card.  It does
**not** apply profile defaults, remap artifact paths, or auto-create
worktrees.  The operator must still set `--execution-mode`, `--owner`,
`--reviewer`, `--branch`, `--worktree-path`, and `--machine-id` explicitly
when needed.

## What Phase 10 Does (Current Capabilities)

| Capability | How | Scope |
|---|---|---|
| **Profile resolution by name** | `--profile rental-rebuild` looks up `profiles/rental-rebuild-profile.md` | dispatch |
| **Profile resolution by path** | `--profile /path/to/profile.md` resolves the exact file | dispatch |
| **Schema preflight** | Loaded profile is validated against profile schema before any task-card mutation | dispatch |
| **Canonical profile recording** | `profile: rental-rebuild` written to task card on successful mutating dispatch | dispatch |
| **Profile-aware task validation** | Validator checks `allowed_statuses`, `allowed_execution_modes`, `required_front_matter`, `required_sections` declared by a task's profile | validator |
| **Profile field type enforcement** | `profile` must be a scalar string, not a YAML list | validator |
| **Non-mutating dispatch** | `--message-only` shows profile context in dispatch message without writing to task card | dispatch |
| **Unprofiled task compatibility** | Tasks without `profile` field pass all existing validation unchanged | validator |

## What Phase 10 Does NOT Do (Deferred Capabilities)

These are **explicitly deferred** to a future migration phase.  Do not
assume they work:

| Deferred capability | Why it is deferred |
|---|---|
| Automatic profile selection from `active: true` | Requires migration of existing unprofiled tasks |
| Automatic owner / reviewer / branch / worktree population from profile | Alters assignment semantics; needs its own phase |
| Artifact path remapping (`rental-rebuild/coordination/`) | All coordination files still live under `coordination/` |
| Automatic worktree creation | Requires provisioning infrastructure |
| Profile inheritance (`extends`) | Schema v1 forbids `extends`; future schema versions may support it |
| Profile-specific review routing | Review assignment remains explicit |
| Lifecycle state auto-population | Status remains an explicit operator choice |

## Profiles Directory

Profile files live at `profiles/<name>-profile.md`.  The resolver searches
this directory by name:

```
--profile rental-rebuild  →  profiles/rental-rebuild-profile.md
--profile /abs/path.md    →  exact file
```

## Validator

Run `python scripts/validate_coordination_files.py` (or
`powershell -ExecutionPolicy Bypass -File scripts\validate.ps1`) to check:

- All profile files pass schema validation
- Task cards reference resolvable profiles
- Task card `status` is in the profile's `allowed_statuses` (if declared)
- Task card `execution_mode` is in the profile's `allowed_execution_modes` (if declared)
- Profile-declared `required_front_matter` and `required_sections` are present

## Dispatch Flags Reference

| Flag | Effect on profile |
|---|---|
| `--profile <name>` | Loads, prefights, and records canonical `profile_name` on task card |
| `--profile <path>` | Same, but resolves an explicit file path |
| `--message-only` | Shows profile context in dispatch message; never writes to task card |
| *(omitted)* | No profile loaded; existing `profile` field preserved unchanged |

## Safety Guarantees

1. **Preflight before mutation.**  A profile that fails resolution or schema
   validation causes the dispatch to exit with an error.  No task-card
   fields are modified.

2. **No automatic defaults.**  Profile `default_status`,
   `default_execution_mode`, `role_mapping`, `artifact_mapping`, and
   `worktree_policy` are shown in the dispatch message for informational
   purposes only.  They are never applied to task cards automatically.

3. **`active` is not a selector.**  A profile with `active: true` is not
   auto-selected.  The operator must pass `--profile` explicitly.

4. **Unprofiled tasks remain valid.**  Existing tasks without a `profile`
   field pass all validation unchanged.
