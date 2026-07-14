- Task ID: phase8-profile-02
- Agent: external-agent-docs-02
- Phase: phase8-profile-layer
- Status: REVIEW
- Delivery Date: 2026-07-08

## Changed Files

| File | Type | Description |
|------|------|-------------|
| `profiles/rental-rebuild-profile.md` | profile | Full rental-rebuild project profile using schema v1 |
| `profiles/README.md` | docs | Added rental-rebuild-profile.md to directory listing |
| `coordination/task-board/in_progress/2026-07-08_phase8-profile-02_rental-rebuild-profile-instance.md` | task-card | Updated status to IN_PROGRESS and owner to external-agent-docs-02 |
| `coordination/progress/external-agent-docs-02.md` | progress | Updated with current task and completed changes |

## Validation Steps Performed

1. Ran `python scripts/orchestrate.py validate` — passed cleanly (zero errors)
2. Manually verified the profile uses only schema v1 fields (no schema redefinition)
3. Confirmed no global coordination defaults were modified (additive-only change)
4. Cross-referenced profile values against the boundary doc's comparison table

## Known Residual Risks

1. **No profile-aware validator** — The validator does not enforce that task cards in `rental-rebuild/coordination/` match the profile. This is a documented future hook.
2. **`completed/` and `handoffs/` directories** — These rental-rebuild-specific artifact directories are not representable in the current schema's `artifact_mapping.coordination_structure` block. Documented as an unresolved gap in the profile.
3. **No activation mechanism** — The profile is declared but not consumed by any script (`--profile` flag does not exist yet).

## Acceptance Criteria Coverage

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Create the first rental-rebuild profile instance using the approved schema | ✅ | `profiles/rental-rebuild-profile.md` with all 6 schema blocks |
| Express rental-rebuild-specific task format and artifact conventions without changing global defaults | ✅ | Profile overrides task_format, role_mapping, artifact_mapping; no global files changed |
| Make role mapping and branch/PR expectations explicit and reviewable | ✅ | role_mapping block with 3 project-specific categories; branch_pr_policy block with rental-rebuild prefix and PR format |
| Document any unresolved gaps that still require core-engine support | ✅ | Three gaps documented in profile: additional artifact dirs, dispatch flag, profile-aware validation |
| Validator passes cleanly after the change | ✅ | `python scripts/orchestrate.py validate` passes with zero errors |

## Recommended Next Steps

1. **Schema extension** — Add `completed/` and `handoffs/` to the artifact mapping schema if multiple projects need them.
2. **`--profile` flag** — Add to `dispatch_task.py` so the orchestrator can activate the rental-rebuild profile during dispatch.
3. **Profile-aware validation** — Extend validator to check profile conformance for task cards under the profile's coordination paths.
