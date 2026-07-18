# Global Skill Connection Policy

## Purpose

This policy provides a safe single-source-of-truth pattern for skills, design
references, and other shared local knowledge across compatible agent runtimes.
It avoids copying the same resource into several runtime directories, while
keeping project-specific rules and permissions explicit.

## Rules

1. Keep each shared resource in one owned source directory under a user-managed
   root. Do not make the agent runtime directory the editable source of truth.
2. Register every shared resource in a reviewed registry before linking it.
   Unregistered resources are not assumed available to agents.
3. Use a directory junction only after `validate` and `plan` succeed. The
   linking tool defaults to read-only planning; `apply` is explicit.
4. Never delete files through a junction. Remove only the junction itself after
   verifying its target. Do not overwrite an existing ordinary directory.
5. A global resource is discoverable, not automatically applicable. A project
   still explicitly selects a skill or design reference in its task packet,
   `AGENTS.md`, or project skill routing.

## Resource Types

| Type | Minimum contents | Intended use |
| --- | --- | --- |
| `skill` | `SKILL.md` plus optional references/scripts | Executable or procedural capability loaded on demand. |
| `knowledge` | Markdown index and references | Stable facts, runbooks, or domain guidance. |
| `design` | `DESIGN.md` or equivalent index | Visual system reference selected by a UI task. |

## Local Registry And Tool

Start from `coordination/templates/global-resource-registry.example.json` and
save a machine-local copy outside version control, for example under
`coordination/monitor/`. The registry uses `%USERPROFILE%` placeholders, so it
does not store an individual's absolute path in the repository.

Use the tool in this order:

```powershell
python scripts/global_resource_links.py validate <registry.json>
python scripts/global_resource_links.py plan <registry.json>
python scripts/global_resource_links.py apply <registry.json>
```

`validate` checks the registry shape and path safety. `plan` also verifies each
source and reports create, already-linked, or blocked actions. `apply` creates
only planned Windows directory junctions; it refuses an existing non-junction
path or a junction targeting a different source. It never deletes or replaces
paths.

## Runtime Path Discovery

The source document's path table is a useful starting point, not a guarantee.
Installations differ by runtime and version. Before registering a target,
confirm that runtime's documented skills or knowledge directory. Common
examples include `%USERPROFILE%\\.codex\\skills`,
`%USERPROFILE%\\.claude\\skills`, and `%USERPROFILE%\\.hermes\\skills`.
Only add verified targets to the local registry.

## Operating Procedure

1. Clone or create the resource once in the owned source directory.
2. Review its contents, source URL, privacy classification, and invocation
   instructions.
3. Add it to the local registry with only verified runtime targets.
4. Run `validate`, then `plan`; inspect all reported source and link paths.
5. Run `apply` only after explicit user or local-owner approval of the exact
   plan.
6. Add the resource to the project task or skill routing when it is actually
   needed. Do not globally inject a large reference into every agent prompt.
7. Update the source repository in place, then rerun `validate` and `plan` to
   confirm links remain healthy.

## Security And Maintenance

- Shared resources must not contain secrets, credentials, private transcripts,
  or unreviewed executable code.
- Treat a skill update as code: inspect its diff and document incompatible
  changes before shared use.
- Keep the local registry machine-specific and out of Git when it contains
  local paths. Commit only the example schema and policy.
- If a runtime cannot use directory junctions, use its supported discovery
  mechanism rather than copying the resource blindly.
