# Phase 14.5 Controlled-Orchestration Task Map

## Purpose

This map converts the accepted controlled-orchestration architecture into the
smallest ordered delivery sequence. It is a dispatch aid only: task cards,
reviews, and delivery reports remain the authoritative lifecycle evidence.

## Delivery Order

| Order | Task | Architecture phase | Depends on | Owner profile | Exit evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | `phase14.5-bootstrap-02` | B0.1. Least-privilege permission profile | `phase14.5-architecture-01` | orchestrator/platform | Reviewed B0-scoped OpenCode allow/deny profile. |
| 2 | `phase14.5-bootstrap-01` | B0. Manual bootstrap handoff | `phase14.5-bootstrap-02` | platform / OpenCode candidate | One-shot, approval-bound handoff and no-launch proof. |
| 3 | `phase14.5-controlplane-02` | B. Connector grants + admission | `phase14.5-bootstrap-01` | platform | Accepted/rejected admission fixtures; no-launch proof. |
| 4 | `phase14.5-launcher-09` | B.1 Supervised local launcher | `phase14.5-controlplane-02` | orchestrator/platform | One explicitly approved OpenCode process produces acknowledgement or terminal incident. |
| 5 | `phase14.5-scheduler-03` | C. Durable scheduler | `phase14.5-launcher-09` | platform | Restart, duplicate, stale-epoch, and atomic-transition tests. |
| 6 | `phase14.5-worktree-context-04` | D. Worktree and context lifecycle | `phase14.5-scheduler-03` | platform | Six dry-run allocations; bounded, hashed context-packet tests. |
| 7 | `phase14.5-lease-recovery-05` | E. Lease and recovery | `phase14.5-worktree-context-04` | platform | Fake-clock expiry, retry-budget, fencing, and incident-routing tests. |
| 8 | `phase14.5-evidence-review-06` | F. Evidence and review queue | `phase14.5-lease-recovery-05` | platform | Read-only review bundle and DONE-only unlock end-to-end tests. |
| 9 | `phase14.5-operator-surface-07` | G. Operator surface | `phase14.5-evidence-review-06` | platform/docs | JSON projections and approval-queue contract tests. |
| 10 | `phase14.5-local-control-rebaseline-11` | H. L1 local-control rebaseline | `phase14.5-connector-provision-10` | architecture/docs | Reviewed L1/L2 terminology and anti-claim contract. |
| 11 | `phase14.5-six-agent-pilot-08` | H. Six-agent pilot | `phase14.5-local-control-rebaseline-11` | test/operations | Independently reviewed supervised L1 acceptance run for six real registered local workers, labelled `best_effort`. |

## Dispatch Boundaries

- Dispatch only the first unresolved dependency in this sequence. A later
  card being `READY` does not waive its listed hard dependency.
- Every implementation task has independent review because it changes the
  shared scheduler/control-plane backbone.
- Tasks other than `phase14.5-launcher-09` are implementation and deterministic-test work only. They must
  not launch a runtime, use credentials, merge, push, or alter another task's
  lifecycle outside the scheduler contract.
- `phase14.5-launcher-09` may start one runtime only with the separate recorded
  approval required by its task card and the supervised-launch design.
- The six-agent pilot is a supervised test protocol, not authorization to launch.
  Its L1 execution needs a separately recorded one-shot operator approval and
  six registered local workers. L1 is `best_effort`, not a sandbox or a claim
  of enforced filesystem/network isolation. L2 platform enforcement remains
  optional hardening with separate evidence requirements.
- Phase I cross-machine expansion is deliberately unscheduled. It requires a
  separate design approval and security review after Phase H is accepted.

## Current Dispatch Decision

`phase14.5-bootstrap-02` is the sole current implementation candidate.
All other cards are sequenced follow-up work and remain blocked by their hard
dependencies until the task-card `DONE` evidence exists.
