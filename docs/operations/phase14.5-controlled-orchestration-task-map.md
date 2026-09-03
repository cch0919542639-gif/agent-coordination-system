# Phase 14.5 Controlled-Orchestration Task Map

## Purpose

This map converts the accepted controlled-orchestration architecture into the
smallest ordered delivery sequence. It is a dispatch aid only: task cards,
reviews, and delivery reports remain the authoritative lifecycle evidence.

## Delivery Order

| Order | Task | Architecture phase | Depends on | Owner profile | Exit evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | `phase14.5-bootstrap-01` | B0. Manual bootstrap handoff | `phase14.5-architecture-01` | platform / OpenCode candidate | One-shot, approval-bound handoff and no-launch proof. |
| 2 | `phase14.5-controlplane-02` | B. Connector grants + admission | `phase14.5-bootstrap-01` | platform | Accepted/rejected admission fixtures; no-launch proof. |
| 3 | `phase14.5-scheduler-03` | C. Durable scheduler | `phase14.5-controlplane-02` | platform | Restart, duplicate, stale-epoch, and atomic-transition tests. |
| 4 | `phase14.5-worktree-context-04` | D. Worktree and context lifecycle | `phase14.5-scheduler-03` | platform | Six dry-run allocations; bounded, hashed context-packet tests. |
| 5 | `phase14.5-lease-recovery-05` | E. Lease and recovery | `phase14.5-worktree-context-04` | platform | Fake-clock expiry, retry-budget, fencing, and incident-routing tests. |
| 6 | `phase14.5-evidence-review-06` | F. Evidence and review queue | `phase14.5-lease-recovery-05` | platform | Read-only review bundle and DONE-only unlock end-to-end tests. |
| 7 | `phase14.5-operator-surface-07` | G. Operator surface | `phase14.5-evidence-review-06` | platform/docs | JSON projections and approval-queue contract tests. |
| 8 | `phase14.5-six-agent-pilot-08` | H. Six-agent pilot | `phase14.5-operator-surface-07` | test/operations | Independently reviewed supervised acceptance run for six admitted adapters. |

## Dispatch Boundaries

- Dispatch only the first unresolved dependency in this sequence. A later
  card being `READY` does not waive its listed hard dependency.
- Every implementation task has independent review because it changes the
  shared scheduler/control-plane backbone.
- Tasks 1–6 are implementation and deterministic-test work only. They must
  not launch a runtime, use credentials, merge, push, or alter another task's
  lifecycle outside the scheduler contract.
- Task 7 is a supervised test protocol, not authorization to launch. Its
  execution needs a separately recorded operator approval and an admitted,
  enforcement-capable connector grant.
- Phase I cross-machine expansion is deliberately unscheduled. It requires a
  separate design approval and security review after Phase H is accepted.

## Current Dispatch Decision

`phase14.5-bootstrap-01` is the sole current implementation candidate.
All other cards are sequenced follow-up work and remain blocked by their hard
dependencies until the task-card `DONE` evidence exists.
