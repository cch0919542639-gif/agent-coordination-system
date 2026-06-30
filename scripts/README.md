# Scripts

## `validate_coordination_files.py`

Validates the repo-backed coordination markdown files.

Checks:

- task packet front matter keys
- required markdown sections
- progress report labels
- incident report labels
- review report labels
- task card status versus task-board folder state
- valid task status values (READY, IN_PROGRESS, REVIEW, DONE, BLOCKED, NEEDS_FIX, REASSIGNED, CANCELLED)
- valid review decision values (accepted, needs_fix, reassign, rejected)
- delivery report labels
- delivery report existence when task packet lists `delivery_report` in expected_artifacts

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
