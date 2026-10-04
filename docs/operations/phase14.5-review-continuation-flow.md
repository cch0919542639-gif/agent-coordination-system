# Phase 14.5 Local Report and Continuation Flow

This document describes the lead-agent-controlled loop from a completed worker
run through review and the next assignment. The lead agent makes the routine
review decision from repository evidence; human attention is required only
when the delivery needs a human decision or the lead agent identifies risk.

## Flow

1. With the session, heartbeat, abort, create, and prompt callbacks bound to
   the same transport, the runner resolves the pinned worktree and captures a
   bounded in-memory snapshot of files matching the task card's `allowed_scope`
   before the worker session starts. The worker does not have to write a report
   or return a report manifest.
2. Only after exact-session supervision reports completion does the runner
   capture the same scoped files again. It compares per-file hashes in memory
   and generates a report containing controller-observed added, modified, and
   deleted paths. It stores neither file contents nor hashes. Validation output
   and risk assessment are explicitly marked as not captured by the runner.
   The callback then calls the strict submission lifecycle; the task moves from
   `in_progress/` to `review/` without a separate report-writing or submit step.
   Each run gets an immutable report path keyed by a digest of its run ID, so a
   `needs_fix` rerun can submit new evidence while preserving the prior attempt.
3. The lead agent inspects the task card, actual diff, changed paths, required
   validation evidence, and residual risk. A worker's completion or an idle
   session is not a review decision.
4. If the task meets its acceptance criteria and the lead agent identifies no
   risk and needs no human decision, it records `accepted` with explicit triage
   answers. The task moves to `done/`, and the command assigns at most one
   dependency-ready task whose card explicitly depends on the accepted task,
   preserving the same owner when assigned. Unrelated review tasks do not block
   this delivery's safe continuation, and unrelated ready tasks are never
   selected as continuations.
5. If the lead agent finds a bounded, in-scope correction and no risk or human
   decision is needed, it records `needs_fix`, adds the findings to the task
   card, and dispatches the correction to the same owner immediately.
6. If another existing owner is a clearly better fit and no risk or human
   decision is involved, the lead agent records `reassign` with an explicit
   `--reassign-owner`, returns the task to `ready/`, and dispatches to that
   owner immediately.
7. If a human decision is needed or any risk is identified, the lead agent
   records `paused`, states which condition triggered the pause, and notifies
   the user. The card stays in `review/`; no continuation is assigned.

Each review outcome is retained as a separate review file after the first
attempt. Correction feedback on the task card links to the latest review; older
run reports and review outcomes remain available for audit.

Use the controller-triage mode for the lead-agent workflow:

```powershell
python scripts/review_task.py --task-id <TASK_ID> --reviewer ORCHESTRATOR `
  --decision accepted --summary "Acceptance criteria and checks are satisfied." `
  --controller-triage --human-decision not-needed --risk none
```

Reassign a low-risk task when a different existing agent is a clear fit:

```powershell
python scripts/review_task.py --task-id <TASK_ID> --reviewer ORCHESTRATOR `
  --decision reassign --summary "A different agent type is needed." `
  --required-change "Continue from the review findings." --reassign-owner <AGENT_ID> `
  --controller-triage --human-decision not-needed --risk none
```

Pause when either escalation condition applies:

```powershell
python scripts/review_task.py --task-id <TASK_ID> --reviewer ORCHESTRATOR `
  --decision paused --summary "Explain the unresolved decision or risk." `
  --controller-triage --human-decision required --risk identified
```

Return safe, bounded corrections to the same owner:

```powershell
python scripts/review_task.py --task-id <TASK_ID> --reviewer ORCHESTRATOR `
  --decision needs_fix --summary "One in-scope correction is needed." `
  --required-change "Describe the exact correction." `
  --controller-triage --human-decision not-needed --risk none
```

## Boundaries and Remaining Gates

- A review decision is made by the lead agent from evidence; it does not require
  a separate human acceptance. The lead agent must not record `accepted` when a
  human decision is needed or risk is identified. Scope violations and unclear
  scope are treated as risk/decision pauses. The lifecycle CLI rejects review
  decisions that omit explicit controller triage.
- Controller continuation assigns work and prints a dispatch message. It does
  not start a worker process. A real task-bound OpenCode run still requires a
  fresh exact user authorization and a current accepted launch packet.
- Malformed scope, symlinked paths, unreadable files, or snapshot resource
  limits fail closed. Before the session starts, the runner stops without
  launching it. If the post-run snapshot fails, no report is submitted.
- Task assignment remains dependency-gated. An existing different owner is
  preserved; missing, unfinished, duplicate, and malformed dependencies block
  dispatch.
- The Task 51 HTTP adapter and Task 54 delivery path were verified with fake
  connections and temporary worktrees only. This flow's controller policy does
  not itself prove live OpenCode/API behavior.
- The other five workers require their separate computers and remain outside
  this local implementation. Cross-machine transport and credentials are not
  provided here.
