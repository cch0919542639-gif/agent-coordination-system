# Project Profiles

## Purpose

This directory defines project-specific coordination profiles. Each profile expresses how a project customizes the core coordination engine — task format, role names, artifact locations, branch/PR conventions, and worktree policies — without modifying the global defaults or the engine's validation logic.

## How It Works

The coordination engine ships with a built-in set of global defaults. These defaults are the implicit behavior when no profile is active. A project profile sits on top of the defaults and selectively overrides specific dimensions:

```
Global Defaults (core engine)
       |
Project Profile (overrides)
       |
Active Coordination Behavior
```

Profiles are additive. Every field that a profile does not specify falls back to the global default. There is no cascade — a profile cannot chain to another profile in the current design.

## Directory Structure

```
profiles/
  README.md                  This file
  schema-profile-v1.md       The profile schema definition
  global-defaults-profile.md  Explicit representation of today's global defaults
  rental-rebuild-profile.md  Rental-rebuild project profile
  <project-name>-profile.md  Future project-specific profiles
```

## When To Create A Profile

Create a profile when a project needs to diverge from the global defaults in any of these dimensions:

- task card format (different required fields or sections)
- role naming conventions (different owner/reviewer patterns)
- artifact locations (different coordination directory paths)
- branch or PR conventions (different naming or workflow)
- worktree policies (different execution model expectations)

## When Not To Create A Profile

Do not create a profile for:

- one-off task variations — use the task packet's own fields instead
- temporary experiments — use an inline dev note instead
- changes that belong in the core engine — if every project would need the same override, the engine should be updated instead

## Profile Activation

Profile activation is not yet automated. The `--profile` flag on `dispatch_task.py` loads profile context into the dispatch message, but does not auto-activate the profile for task card validation, path remapping, or field auto-population. For the current version, activation means:

1. The profile YAML front matter documents which project it describes.
2. The orchestrator or agent uses `--profile <name>` during dispatch to include profile context in the dispatch message.
3. The profile context is informational — the operator must still set all task fields explicitly via CLI flags.
4. Future automation may add profile-aware validation, path remapping, and field auto-population.

## Validation

Profile files are validated by `scripts/validate_coordination_files.py` (run via `python scripts/orchestrate.py validate`). The validator checks:

- required top-level keys: `profile_name`, `schema_version`, `description`
- `profile_name` is non-empty and unique across all profiles
- `schema_version` is `"1.0"`
- `description` is non-empty
- `extends` is null (reserved for future use in v1)
- `allowed_statuses` is a subset of the engine's valid statuses
- `allowed_execution_modes` is a subset of the engine's valid execution modes
- `artifact_mapping.coordination_structure` paths do not escape the repo root

The `schema-profile-v1.md` file is excluded from validation since it defines the schema rather than being a profile instance.

## Scope

Profiles are operated scoped. They can define:

- task format policy
- role mapping
- artifact mapping (path overrides and naming conventions)
- branch/PR policy
- worktree policy (optional)

Profiles cannot redefine:

- the validation engine's core data structures
- the dispatch, review, or incident protocols
- the agent execution loop (agent-task-execution-protocol.md)
- the orchestrator's role or authority

## Related References

- `profiles/schema-profile-v1.md` — full schema definition
- `profiles/global-defaults-profile.md` — global defaults as a profile
- `docs/operations/profile-schema-and-boundary.md` — core-vs-profile boundary analysis
