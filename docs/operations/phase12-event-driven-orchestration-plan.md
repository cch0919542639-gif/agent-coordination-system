# Phase 12 Event-Driven Orchestration Plan

## Purpose

Phase 12 removes the need for a human to copy an external worker's completion
report into the orchestrator chat. A low-frequency monitor observes GitHub
branch and task-card evidence, writes idempotent local events, and routes only
safe wake-up requests to the appropriate handler.

## Event Boundary

```text
external worker pushes branch and review task card
                    |
                    v
local monitor fetches remote refs at a bounded interval
                    |
                    v
deduplicated event ledger
   | review_submitted -> wake orchestrator review handler
   | ready_assigned  -> notify registered worker runner
   | incident_opened -> wake orchestrator triage handler
                    |
                    v
human decision only for acceptance, reassign, scope, or safety escalation
```

## Runtime Contract

1. GitHub branches and task cards in each registered project repository are the
   authoritative input; chat text is never an event source.
2. The monitor uses `git fetch` and local Git object inspection, not repeated
   API polling or LLM calls. Default cadence is 10 minutes with jitter.
3. Every event has a deterministic ID based on project identifier, repository,
   branch/ref, commit, task ID, and event type. Repeated polls emit no duplicate
   wake-up.
4. The monitor writes only its ignored runtime state/ledger. It never moves a
   task card, accepts a review, creates a branch, or pushes changes.
5. A wake-up adapter can request Codex heartbeat/automation for this thread,
   but it cannot impersonate or force-start an arbitrary external agent.
6. Worker wake-up is opt-in: an external agent runs a registered poller/runner
   that reads its own assignments. Without that runner, the event is recorded
   and remains pending rather than claimed as delivered.
7. Network or Git failures produce a retryable health event with exponential
   backoff; they do not erase prior event state.

## Delivery Sequence

1. Build remote-ref monitor and idempotent event ledger.
2. Add routing policy and safe notification payloads for review, ready, and
   incident events.
3. Add registered worker poller protocol and operator setup documentation.
4. Connect the orchestrator notifier to a Codex heartbeat/automation and run a
   full end-to-end regression with simulated remote branches.

## Deliberately Deferred

- direct control of third-party agent processes or paid provider APIs
- automatic review acceptance, merge, reassign, claim, or deployment
- webhooks requiring a public server
- credentials stored in task cards, event state, or repository files

## Acceptance Gate

The phase is complete only when a worker's pushed review card becomes one
deduplicated review event, a local orchestrator wake-up can be requested from
that event, registered workers can see ready work without human copy/paste, and
all unregistered/failed destinations remain visibly pending for operator action.
