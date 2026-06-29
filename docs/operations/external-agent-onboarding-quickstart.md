# External Agent Onboarding Quickstart

## Purpose

This quickstart gives a new external agent everything needed to begin repo-first work with minimal human explanation. Follow these steps in order after receiving a task assignment.

## Repo Structure Overview

```
coordination/
  task-board/           # Task lifecycle: ready -> in_progress -> review -> done
    ready/              # Tasks available for assignment
    in_progress/        # Tasks currently being worked
    review/             # Tasks submitted for review
    done/               # Completed tasks
    blocked/            # Tasks that cannot proceed
  progress/             # Per-agent progress reports
  incidents/            # Blocker and issue reports
  reviews/              # Review outcomes
  templates/            # Reusable file templates
  completed/            # Phase completion summaries
docs/
  operations/           # Operational guides and protocols
  architecture/         # System architecture documents
  specs/                # API and interface specifications
scripts/                # Utility scripts
```

## Required Reading

Before touching any files, read:

- `docs/operations/agent-task-execution-protocol.md` -- operating rules, lifecycle, escalation
- `coordination/task-board/ready/<your-task-file>` -- the assigned task packet

Both contain the rules and scope boundaries you must follow.

## First Five Actions After Pulling the Repo

### 1. Locate Your Assigned Task

Your assignment message will include a task ID (e.g. `phase1-live-01`). Find the matching file in:

```
coordination/task-board/ready/<task-id>_<description>.md
```

If no matching file exists, stop and raise an incident.

### 2. Read the Task Packet and Execution Protocol

Read both files before making any changes:

- `coordination/task-board/ready/<task-file>` -- the task packet with objective, scope, acceptance criteria, and escalation rules
- `docs/operations/agent-task-execution-protocol.md` -- defines how to claim work, report progress, escalate blockers, and submit for review

The task packet's `allowed_scope` and `forbidden_scope` fields define exactly which files you may modify.

### 3. Claim the Task

Move the task card from `ready/` to `in_progress/`:

```
coordination/task-board/ready/<task-file>  -->  coordination/task-board/in_progress/<task-file>
```

Update the front matter `status` field from `READY` to `IN_PROGRESS`. Create or update your progress file at `coordination/progress/<agent-name>.md` using the template at `coordination/templates/progress-report.md`.

### 4. Execute Within the Allowed Scope

Follow the task packet's implementation notes. You may only modify files under `allowed_scope`. If the required change falls outside this scope, stop and raise an incident. Update your progress file at meaningful checkpoints to show current step, changed files, and blocker status.

### 5. Submit for Review

When your implementation is complete:

1. Move the task card to `coordination/task-board/review/`
2. Update progress status to `waiting_for_review`
3. Verify your delivery against the acceptance criteria
4. Run the coordination validator: `python scripts/validate_coordination_files.py`
5. Include changed files list, validation notes, and any residual risks

Only the orchestrator or reviewer may mark the task as accepted and move it to `done/`.

## If You Get Blocked

Blocked means any of: missing spec, scope conflict, environment failure, dependency missing, merge conflict, capability mismatch, or regression risk.

When blocked:

1. Stop implementation
2. Create an incident report in `coordination/incidents/` using the template at `coordination/templates/incident-report.md`
3. Update progress with a blocked summary
4. Wait for orchestrator direction -- do not continue by guessing

## Key References

| Resource | Path |
|---|---|
| Task board | `coordination/task-board/` |
| Progress template | `coordination/templates/progress-report.md` |
| Incident template | `coordination/templates/incident-report.md` |
| Review template | `coordination/templates/review-report.md` |
| Execution protocol | `docs/operations/agent-task-execution-protocol.md` |
| Validator script | `scripts/validate_coordination_files.py` |
| Dispatch message templates | `docs/operations/external-agent-dispatch-message-templates.md` |

## Validation Checklist

Before submitting, confirm you can answer yes to each:

- [ ] I found my assigned task in the task board
- [ ] I moved the task card to `in_progress/` when I started
- [ ] I updated my progress file at meaningful checkpoints
- [ ] I raised an incident if blocked instead of guessing
- [ ] I moved the task card to `review/` and included delivery evidence
- [ ] The coordination validator passes on my changed files
