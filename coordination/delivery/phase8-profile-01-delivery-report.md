- Task ID: phase8-profile-01
- Agent: external-agent-architecture-01
- Phase: phase8-profile-layer
- Status: REVIEW (needs_fix applied)
- Delivery Date: 2026-07-08

## Changed Files

| File | Type | Description |
|------|------|-------------|
| `profiles/README.md` | docs | Profile layer overview, directory structure, and usage rules |
| `profiles/schema-profile-v1.md` | docs | Complete profile schema definition with all blocks and field-level docs |
| `profiles/global-defaults-profile.md` | docs | Explicit representation of today's global defaults as a profile |
| `docs/operations/profile-schema-and-boundary.md` | docs | Core-vs-profile boundary analysis table, design rules, and dimension mappings |
| `coordination/task-board/in_progress/2026-07-08_phase8-profile-01_profile-schema-and-boundary.md` | task-card | Updated status to IN_PROGRESS and owner to external-agent-architecture-01 |
| `coordination/progress/external-agent-architecture-01.md` | progress | Updated with current task and completed changes |

## Validation Steps Performed

1. Ran `python scripts/orchestrate.py validate` — passed cleanly (zero errors)
2. Manual review of all profile files for schema consistency
3. Confirmed no existing coordination artifacts were modified (additive-only change)
4. Cross-referenced schema fields against existing validator constants and templates

## Known Residual Risks

1. **No profile-aware validator** — The validator does not yet enforce profile schema rules. A profile file with invalid front matter would not be caught. This is a deliberate deferral per task constraints ("documentation-first").
2. **No activation mechanism** — The profile layer defines the schema but does not yet integrate with dispatch or orchestrate commands. Profiles are documented, not loaded.
3. **Schema version 1.0 is frozen** — Breaking changes (e.g., adding inheritance) would require a version bump and migration.

## Acceptance Criteria Coverage

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Define a first profile schema for project-specific coordination behavior | ✅ | `profiles/schema-profile-v1.md` defines a complete YAML-front-matter schema with 6 top-level blocks |
| Clearly separate core engine rules from project-specific policy | ✅ | `docs/operations/profile-schema-and-boundary.md` has a 26-row table explicitly classifying each behavior as Core, Default, or Profile-overridable |
| Identify which current behaviors remain global defaults versus profile overrides | ✅ | `profiles/global-defaults-profile.md` documents every current default; `profile-schema-and-boundary.md` lists 26 behaviors with classifications |
| Document how task format, role mapping, artifact mapping, and branch/PR policy fit into the schema | ✅ | Four dedicated mapping sections in `profile-schema-and-boundary.md` with table-based field-to-schema-block mappings |
| Validator passes cleanly after the change | ✅ | `python scripts/orchestrate.py validate` passes with zero errors |

## Fix Round (2026-07-08)

Review returned `needs_fix`. Two issues fixed:

1. **Core-defined set semantics**: Revised `allowed_statuses` and `allowed_execution_modes` in schema (`schema-profile-v1.md`), boundary table (`profile-schema-and-boundary.md` rows 1-2), and global defaults profile. No longer documented as arbitrarily extensible. Profiles may narrow, configure defaults, or express opt-in policy, but must not add values the engine does not recognize. Added validation rule #8 confirming this constraint.

2. **YAML list syntax**: Fixed all list fields in the complete example (`schema-profile-v1.md`) and the global-defaults profile (`global-defaults-profile.md`) to use proper YAML syntax — one item per `- <value>` line instead of comma-joined scalars.

## Recommended Next Steps

1. **Profile-aware validator** — Extend `validate_coordination_files.py` to detect and validate profile files:
   - Check that `profiles/*-profile.md` files have valid front matter matching the schema
   - Validate uniqueness of `profile_name` across the directory
   - Add `--profile` flag to validation mode
2. **Dispatch integration** — Add `--profile` flag to `dispatch_task.py` to reference an active profile in the dispatch message
3. **Rental-rebuild profile** — Create `profiles/rental-rebuild-profile.md` using the v1 schema as the first real project profile
4. **Template overrides** — Support profile-scoped template overrides in a future version
