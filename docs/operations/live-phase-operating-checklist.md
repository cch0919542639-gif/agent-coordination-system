# Live Phase Operating Checklist

## Purpose

This checklist is the practical runbook for operating the first live GitHub collaboration phase.

Use it before, during, and immediately after the first pilot wave.

## Before Launch

- [ ] Confirm the phase objective is frozen enough for delegation.
- [ ] Confirm the backbone or spec is committed.
- [ ] Confirm the task packets for the first wave are in `coordination/task-board/ready/`.
- [ ] Confirm each task packet has `allowed_scope`, `forbidden_scope`, and `acceptance`.
- [ ] Confirm the assigned reviewer is ready to inspect submissions promptly.
- [ ] Run `python scripts/validate_coordination_files.py`.
- [ ] Confirm external agents know which repo and branch to pull from.
- [ ] Confirm external agents have the dispatch message template they will receive.

## First Wave Selection

- [ ] Start with only one or two tasks.
- [ ] Choose low-risk, low-coupling tasks.
- [ ] Avoid tasks that require architecture-level decisions.
- [ ] Avoid tasks likely to spill outside allowed scope.
- [ ] Avoid assigning too many tasks to one agent in the first wave.

## Assignment

- [ ] Assign a named owner to each task.
- [ ] Send the standard dispatch message.
- [ ] Confirm the agent knows where to update progress.
- [ ] Confirm the agent knows how to raise an incident.

## Early Execution Check

- [ ] Confirm the agent pulled the latest repo state.
- [ ] Confirm the task card moved from `ready/` to `in_progress/` when work started.
- [ ] Confirm `coordination/progress/<agent>.md` was updated.
- [ ] Confirm the agent is working inside allowed scope.

## Blocker Handling

- [ ] If blocked, confirm an incident file was created.
- [ ] Confirm the agent paused instead of widening scope by guesswork.
- [ ] Decide whether to clarify, split, reassign, or take back the task.
- [ ] Record the decision in repo artifacts where relevant.

## Submission Check

- [ ] Confirm the task card moved to `review/`.
- [ ] Confirm delivery evidence exists in the repo.
- [ ] Confirm validation notes are present.
- [ ] Confirm residual risks are stated if relevant.

## Review Check

- [ ] Confirm the review is based on acceptance criteria, not memory alone.
- [ ] Confirm scope compliance was checked.
- [ ] Confirm review outcome is written explicitly.
- [ ] Confirm `accepted`, `needs_fix`, `reassign`, or `rejected` is recorded clearly.

## Completion Check

- [ ] Move the task to `done/` only after review acceptance.
- [ ] Confirm the task history is reconstructable from repo files.
- [ ] Confirm the result is good enough to be used as reference for future agents.

## Scale Decision

After the first wave, ask:

- [ ] Did task packets hold up without heavy chat explanation?
- [ ] Did agents update progress in the expected format?
- [ ] Did incidents appear early enough?
- [ ] Was review fast enough to avoid bottlenecks?
- [ ] Can another person recover the context from repo state alone?

If most answers are yes:

- [ ] expand carefully to another task or another agent

If several answers are no:

- [ ] patch the protocol before expanding

## Stop Conditions

Pause expansion if any of the following happens:

- [ ] agents repeatedly ask for hidden context not present in the repo
- [ ] progress updates are too vague to review
- [ ] tasks drift across forbidden scope
- [ ] delivery is declared complete without repo evidence
- [ ] review requires manual reconstruction from chat

## End Of First Pilot

- [ ] Write at least one review report for the finished wave.
- [ ] Note any protocol gaps or confusing steps.
- [ ] Update docs or templates before opening the next wave.
- [ ] Decide whether the workflow is ready for broader GitHub collaboration.

