# Scripts

## `orchestrate.py`

Single entrypoint that wraps the most common coordination scripts as subcommands.

Available subcommands:

- `validate`
- `summary`
- `next`
- `intake`
- `assigned`
- `claim`
- `submit`
- `incident`
- `review-queue`
- `dispatch`
- `review`
- `complete`

Usage:

```bash
python scripts/orchestrate.py summary
python scripts/orchestrate.py next
python scripts/orchestrate.py intake --phase-id phase7-example --objective "..." --in-scope "src/**"
python scripts/orchestrate.py validate --templates-only
python scripts/orchestrate.py assigned --owner external-agent-docs-01
python scripts/orchestrate.py dispatch --task-id phase2-03 --owner external-agent-docs-04
python scripts/orchestrate.py dispatch --task-id phase2-03 --owner external-agent-docs-04 --profile rental-rebuild
python scripts/orchestrate.py review --task-id phase2-03 --reviewer orchestrator --decision accepted --summary "Task meets acceptance criteria."
```

## `validate_coordination_files.py`

Validates the repo-backed coordination markdown files.

Checks:

- task packet front matter keys
- required markdown sections
- optional worktree provenance keys (`execution_mode`, `branch`, `worktree_path`, `machine_id`)
- progress report labels
- incident report labels
- review report labels
- task card status versus task-board folder state
- valid task status values (READY, IN_PROGRESS, REVIEW, DONE, BLOCKED, NEEDS_FIX, REASSIGNED, CANCELLED)
- valid review decision values (accepted, needs_fix, reassign, rejected)
- valid execution mode values (`REPO_FIRST`, `WORKTREE`)
- required `branch` and `worktree_path` when `execution_mode: WORKTREE`
- delivery report labels
- delivery report existence when task packet lists `delivery_report` in expected_artifacts

Profile checks:

- profile file discovery under `profiles/` (excludes README.md and schema-profile-v1.md)
- required top-level keys (`profile_name`, `schema_version`, `description`)
- `profile_name` must be non-empty and unique across all profiles
- `schema_version` must be `"1.0"`
- `description` must be non-empty
- `extends` must be null in schema v1
- `allowed_statuses` must be a subset of the engine's valid statuses
- `allowed_execution_modes` must be a subset of the engine's valid execution modes
- `artifact_mapping.coordination_structure` paths must not escape the repo root (no `../` or absolute paths)

Usage:

```bash
python scripts/validate_coordination_files.py
```

Templates only:

```bash
python scripts/validate_coordination_files.py --templates-only
```

Recommended use:

- run before opening a phase to external agents
- run before review on a batch of newly added task cards
- later wire into CI or pre-commit hooks

## `list_assigned_tasks.py`

Lists active tasks assigned to a specific owner.

Usage:

```bash
python scripts/list_assigned_tasks.py --owner external-agent-docs-01
```

Optional states:

```bash
python scripts/list_assigned_tasks.py --owner external-agent-docs-01 --states ready in_progress review
```

## `claim_task.py`

Claims a task from `ready/`, moves it to `in_progress/`, updates the owner, and creates a basic progress file if one does not exist.

Usage:

```bash
python scripts/claim_task.py --task-id phase2-03 --agent external-agent-docs-04
```

Override owner:

```bash
python scripts/claim_task.py --task-id phase2-03 --agent external-agent-docs-04 --force-owner
```

## `submit_task.py`

Submits a task from `in_progress/` to `review/`. By default it checks for a delivery report when the task packet requires one.

Usage:

```bash
python scripts/submit_task.py --task-id phase2-03 --agent external-agent-docs-04
```

Bypass delivery report check:

```bash
python scripts/submit_task.py --task-id phase2-03 --agent external-agent-docs-04 --skip-delivery-check
```

## `list_review_queue.py`

Lists all tasks currently waiting in `review/`.

Usage:

```bash
python scripts/list_review_queue.py
```

## `complete_task.py`

Moves a task from `review/` to `done/` after acceptance.

Usage:

```bash
python scripts/complete_task.py --task-id phase2-03
```

Optional source state:

```bash
python scripts/complete_task.py --task-id phase2-03 --from-state review
```

## `open_incident.py`

Creates a standard incident file and, if the agent already has a progress file, updates it to `BLOCKED`.

Usage:

```bash
python scripts/open_incident.py --task-id phase2-03 --agent external-agent-docs-04 --category scope_conflict --summary "Required file is outside allowed scope."
```

## `intake_phase.py`

Generates a draft phase-intake markdown file from CLI input.

Usage:

```bash
python scripts/orchestrate.py intake --phase-id phase7-example --objective "Implement feature X"
```

See `docs/operations/intake-command-usage.md` for the full reference with all flags and task JSON format.

## `dispatch_task.py`

Assigns or reassigns a task owner by updating the task card in place and generates a ready-to-send dispatch message.

Usage:

```bash
python scripts/dispatch_task.py --task-id phase2-03 --owner external-agent-docs-04
```

Optional reviewer override:

```bash
python scripts/dispatch_task.py --task-id phase2-03 --owner external-agent-docs-04 --reviewer ORCHESTRATOR
```

Worktree-aware dispatch:

```bash
python scripts/dispatch_task.py --task-id phase7-worktree-02 --owner external-agent-platform-16 --execution-mode WORKTREE --branch agent/external-agent-platform-16-phase7-worktree-02-r1 --worktree-path worktrees/external-agent-platform-16/phase7-worktree-02 --machine-id workstation-a
```

Profile-aware dispatch:

```bash
python scripts/dispatch_task.py --task-id phase2-03 --owner external-agent-docs-04 --profile rental-rebuild
```

The `--profile` flag accepts a profile name (e.g. `rental-rebuild`) or a path to a profile file. When provided, the dispatch message includes a profile context section showing the profile's declared defaults, role naming conventions, artifact paths, and worktree policy. It also explicitly states what is script-supported versus what requires manual operator follow-up. Path remapping and artifact placement are NOT automated — the profile context is informational.

Pipe the raw dispatch message without decoration:

```bash
python scripts/dispatch_task.py --task-id phase2-03 --owner external-agent-docs-04 --output -
```

Write the dispatch message to a file:

```bash
python scripts/dispatch_task.py --task-id phase2-03 --owner external-agent-docs-04 --output dispatch-msg.md
```

Preview the message without modifying the task card:

```bash
python scripts/dispatch_task.py --task-id phase2-03 --owner external-agent-docs-04 --message-only
```

## `review_task.py`

Writes a review report and applies a review decision. By default, `accepted` moves the task to `done/`; other decisions keep it in `review/` and update the task status.

Usage:

```bash
python scripts/review_task.py --task-id phase2-03 --reviewer orchestrator --decision accepted --summary "Task meets acceptance criteria."
```

Add findings and artifacts:

```bash
python scripts/review_task.py --task-id phase2-03 --reviewer orchestrator --decision needs_fix --summary "Delivery report is missing." --finding "Expected delivery report was not present." --required-change "Add the missing delivery report." --artifact coordination/task-board/review/2026-06-29_phase2-03_real-project-intake-packet.md
```

## `daily_orchestration_summary.py`

Prints a daily snapshot of the coordination queues and current owner load.

Usage:

```bash
python scripts/daily_orchestration_summary.py
```

Highlight specific owners:

```bash
python scripts/daily_orchestration_summary.py --owners external-agent-tools-02 external-agent-docs-04
```

## `orchestrate.py next`

Recommends the next orchestrator action using a simple priority rule:

1. `review`
2. `blocked`
3. `ready`
4. `idle`

Usage:

```bash
python scripts/orchestrate.py next
```

Optional owner hint:

```bash
python scripts/orchestrate.py next --owner external-agent-docs-04
```

## PowerShell wrappers

For Windows environments where `python` or `py` is not reliably available in `PATH`, use these wrappers:

### `run_python.ps1`

Runs a repository Python script using the fixed local runtime path documented in `docs/operations/local-python-runtime.md`.

Usage:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_python.ps1 scripts\orchestrate.py validate
```

Pass extra arguments through to the target Python script:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_python.ps1 scripts\orchestrate.py next --owner external-agent-docs-04
```

### `validate.ps1`

Runs the coordination validator through the fixed Python runtime wrapper.

Usage:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate.ps1
```
