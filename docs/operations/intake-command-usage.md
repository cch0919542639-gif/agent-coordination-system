# Intake Command Usage

## Overview

`python scripts/orchestrate.py intake` generates a draft phase-intake markdown file from CLI input.

The output follows the structure of `coordination/templates/phase-intake.md` and is written to a stable location for review and editing before finalization.

## When To Use

Use this command when the orchestrator or lead agent needs to quickly produce a first draft of a phase intake document for a new engineering initiative.

The generated draft is a starting point — it should be reviewed, edited (if needed), and finalized before task packets are created from it.

## Command Syntax

```bash
python scripts/orchestrate.py intake \
  --phase-id PHASE_ID \
  --objective "OBJECTIVE" \
  [--in-scope "PATTERN"] \
  [--out-of-scope "PATTERN"] \
  [--dependency "DEPENDENCY"] \
  [--entry-criteria "CRITERION"] \
  [--exit-criteria "CRITERION"] \
  [--task 'TASK_JSON'] \
  [--dry-run]
```

## Arguments

| Argument | Required | Repeatable | Description |
|---|---|---|---|
| `--phase-id` | Yes | No | Short kebab-case phase identifier (e.g. `phase7-billing`) |
| `--objective` | Yes | No | One or two sentences describing the phase objective |
| `--in-scope` | No | Yes | In-scope path pattern or description |
| `--out-of-scope` | No | Yes | Out-of-scope path pattern or description |
| `--dependency` | No | Yes | Dependency description or reference |
| `--entry-criteria` | No | Yes | Precondition that must be true before the phase starts |
| `--exit-criteria` | No | Yes | Measurable condition that defines phase completion |
| `--task` | No | Yes | Task packet specification as JSON string (see below) |
| `--dry-run` | No | No | Print the generated content instead of writing to file |
| `--output` | No | No | Override the default output path |

## Task JSON Format

Each `--task` argument must be a valid JSON object with these fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | Yes | Unique task identifier (e.g. `phase7-01`) |
| `objective` | string | Yes | Short description of what the task achieves |
| `priority` | string | No | `high`, `medium`, or `low` (default: `medium`) |
| `deps` | array of strings | No | Task IDs this task depends on |
| `allowed_scope` | array of strings | No | Path patterns the task may modify |
| `forbidden_scope` | array of strings | No | Path patterns the task must not touch |
| `acceptance` | array of strings | No | Measurable acceptance criteria |

### Example Task JSON

```json
{
  "id": "phase7-01",
  "objective": "Create billing data model and migration",
  "priority": "high",
  "deps": [],
  "allowed_scope": ["src/billing/models/**", "database/migrations/billing/**"],
  "forbidden_scope": ["src/ui/**"],
  "acceptance": ["Invoice model exists", "Migration runs cleanly"]
}
```

## Output Location

By default, the generated draft is written to:

```
coordination/completed/{phase_id}-intake-draft.md
```

Example: `python scripts/orchestrate.py intake --phase-id phase7-billing ...` produces `coordination/completed/phase7-billing-intake-draft.md`.

Use `--output <path>` to override.

## Examples

### Minimal Intake

```bash
python scripts/orchestrate.py intake \
  --phase-id phase7-billing \
  --objective "Implement billing V2 for internal alpha"
```

Produces a skeleton draft with placeholder sections for entry criteria, scope, dependencies, and task decomposition.

### Full Intake With Tasks

```bash
python scripts/orchestrate.py intake \
  --phase-id phase7-billing \
  --objective "Implement billing V2 for internal alpha" \
  --in-scope "src/billing/**" \
  --in-scope "tests/billing/**" \
  --out-of-scope "Admin UI" \
  --out-of-scope "Payment gateway integration" \
  --dependency "Phase6 deployment infrastructure must be stable" \
  --entry-criteria "Billing API spec is frozen" \
  --exit-criteria "All billing V2 tests pass" \
  --exit-criteria "Delivery reports accepted for all tasks" \
  --task '{"id":"phase7-01","objective":"Data model","priority":"high","deps":[],"allowed_scope":["src/billing/models/**"],"forbidden_scope":[],"acceptance":["Model exists"]}' \
  --task '{"id":"phase7-02","objective":"API endpoint","priority":"high","deps":["phase7-01"],"allowed_scope":["src/billing/api/**"],"forbidden_scope":["src/ui/**"],"acceptance":["Endpoint returns 200"]}'
```

### Preview Without Writing

Add `--dry-run` to print the generated markdown to stdout instead of writing a file:

```bash
python scripts/orchestrate.py intake --phase-id phase7-billing --objective "..." --dry-run
```

## Limitations (First Version)

- No validation of task JSON fields beyond JSON parsing
- Task ordering follows the order `--task` arguments are provided
- No automatic dependency ordering or cycle detection
- No integration with the task-board (this is a draft generator only)
- All fields use simple text; no markdown rendering customization

## Post-Generation Workflow

1. Review the generated draft at `coordination/completed/{phase_id}-intake-draft.md`
2. Edit to fix missing details, add context, or adjust task decomposition
3. Create individual task packet files in `coordination/task-board/ready/`
4. Run `python scripts/orchestrate.py validate` to confirm the repo is consistent
5. Dispatch the first wave of tasks

## See Also

- [Phase Intake Template](../../coordination/templates/phase-intake.md)
- [Real Project Intake Guide](real-project-intake-guide.md)
- [Lead Agent Orchestration Protocol](lead-agent-orchestration-protocol.md)
