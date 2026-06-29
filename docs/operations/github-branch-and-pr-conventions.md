# GitHub Branch and PR Conventions

## Purpose

This document defines the naming and usage conventions for branches and pull requests in the repo-first multi-agent workflow.

The goal is to make it easy to answer:

- which task a branch belongs to
- which phase it supports
- who is working on it
- whether a PR is ready for review

## Core Rule

Every task that produces repo changes should be traceable across:

- task card
- branch name
- PR title
- completion report

The `task_id` is the anchor across all of them.

## Branch Naming Convention

Recommended format:

```text
{type}/{task_id}-{short-slug}
```

Examples:

```text
docs/phase1-live-01-onboarding-quickstart
chore/phase1-live-02-validator-enhancement
docs/phase1-live-03-reviewer-playbook
feat/phase2-billing-generate-01-generate-endpoint
fix/phase2-billing-batch-02-retry-logic
```

## Allowed Branch Types

Use these prefixes:

- `docs`
- `feat`
- `fix`
- `chore`
- `test`
- `refactor`

Guidance:

- use `docs` for documentation and coordination file work
- use `chore` for workflow, validator, or non-product support tooling
- use `feat` for new product behavior
- use `fix` for defect correction
- use `test` for test-only work
- use `refactor` only when the task explicitly allows structural cleanup

## Branch Naming Rules

- always include the `task_id`
- keep the trailing slug short and descriptive
- use lowercase letters, numbers, and hyphens only
- do not create vague names like `update-stuff` or `agent-work`

## PR Title Convention

Recommended format:

```text
[{TASK_ID}] Short outcome statement
```

Examples:

```text
[phase1-live-01] Add external agent onboarding quickstart
[phase1-live-02] Add extra coordination validator checks
[phase1-live-03] Add reviewer playbook for live pilot
```

## PR Description Convention

Suggested structure:

```text
Task ID:
- {TASK_ID}

Phase:
- {PHASE_ID}

Summary:
- What was changed

Validation:
- Commands run
- Manual checks completed

Artifacts:
- Paths to key files

Risks:
- Known limitations or follow-up needs
```

## Commit Message Guidance

Recommended format:

```text
[{TASK_ID}] Short change summary
```

Examples:

```text
[phase1-live-01] Add onboarding quickstart draft
[phase1-live-02] Validate review decision values
```

## PR Readiness States

Use simple, explicit meanings:

- Draft PR
  - work in progress, not ready for final review
- Ready for review
  - task submission is complete enough for reviewer inspection
- Needs fix
  - reviewer found required changes
- Accepted
  - reviewer approved and task may move toward done

## Mapping To Repo Workflow

The expected mapping is:

- branch created when the agent starts execution
- task card moved to `in_progress/`
- progress file updated during work
- PR opened as draft if using PR workflow
- task card moved to `review/` when submission is ready
- review report written after inspection
- task card moved to `done/` only after acceptance

## First Live Phase Recommendation

For the first pilot:

- prefer one branch per task
- prefer one PR per task if PRs are being used
- avoid mixing multiple task IDs into the same branch
- avoid broad cleanup commits unrelated to the assigned task

## Anti-Patterns

Avoid:

- one branch covering multiple unrelated task packets
- PR titles that omit task ID
- commits that hide which task they belong to
- "drive-by" unrelated file edits during assigned work

## Short Version

If someone sees only the branch name and PR title, they should still be able to identify the task packet quickly.

