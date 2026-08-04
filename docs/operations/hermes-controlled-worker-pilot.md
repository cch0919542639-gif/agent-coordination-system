# Hermes Controlled-Worker Pilot

## Scope

This pilot uses the repository task board and existing owner-strict activation
contract. Hermes is only a scheduled worker runtime; Hermes Kanban is not used.

## Skill Source

The reviewed source is
`integrations/hermes-coordination-worker/SKILL.md`. Link it to the local
Hermes skill target only through the approved global-resource-link plan. The
target name is `coordination-worker`.

## Worker Registration

Register the pilot only for the central project:

```powershell
python scripts/orchestrate.py worker register hermes-coordination-pilot agent-coordination-system
```

## Cron Job

Create exactly one 10-minute job, rooted at this repository, with the local
skill attached:

```powershell
hermes cron create "every 10m" "Run the coordination-worker skill exactly once. If no eligible delivery exists, stop without changes. If one matching delivery exists, process only that task and stop after submitting it to review. Never use Kanban, accept, review, merge, commit, push, select unassigned work, or launch another agent." --name coordination-worker-pilot --skill coordination-worker --workdir "D:\codex work"
```

The configured job is `d215f82b3e50`. It is currently **paused** after its
single supervised run `a5bffadecd284679968eac30f8248536` completed on
2026-08-02. That run consumed one owner-matching delivery, claimed
`phase14-hermes-pilot-01`, wrote its repository delivery report, and submitted
the task card to `review/`. The local Gateway was healthy for the run.

Before any further supervised run, an operator must explicitly resume this
job. A new no-side-effect task also needs an independent authorization for the
model data transfer; resuming the job alone must not be used to dispatch work.

## Safety And Recovery

- `worker activate` writes a durable inbox payload before acknowledging the
  delivery; it does not itself claim or execute a task.
- A task remains subject to the repository task packet and `allowed_scope`.
- Review acceptance remains an orchestrator decision.
- Pause a job with `hermes cron pause <job-id>`.
- Resume only for a supervised test with `hermes cron resume <job-id>`.
- Remove it with `hermes cron remove <job-id>`.
- Remove only the Hermes skill junction after verifying its target. Do not
  delete the source skill or alter task cards as part of rollback.
