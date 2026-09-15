# Independent Review Request: phase14.5-worktree-context-04

- Task ID: phase14.5-worktree-context-04
- Agent: ORCHESTRATOR
- Phase: phase14.5-worktree-context
- Status: REVIEW_REQUEST

## Changed Files

- No implementation files. This is the durable, copy-paste review packet for
  commit `93544ac`.

## Reviewer Mandate

You are `INDEPENDENT_PLATFORM_REVIEWER`. Review commit `93544ac` on branch
`agent/orchestrator/phase14.5-controlplane-02`. You are independent of the
implementation owner (`ORCHESTRATOR`). Do not modify implementation files,
task lifecycle state, Git history, runtime state, or credentials. Add only
`coordination/reviews/review-phase14.5-worktree-context-04.md` with your
evidence and decision.

## Purpose

Determine whether Phase D provides a deterministic fixture-only planner for
six isolated worktree identities and a safe immutable context projection,
without crossing the no-provision/no-runtime/no-network boundary.

## Required Files

1. `coordination/task-board/review/2026-09-03_phase14.5-worktree-context-04_isolated-worktrees-and-context.md`
2. `coordination/delivery/phase14.5-worktree-context-04-delivery-report.md`
3. `docs/architecture/controlled-orchestration-architecture.md` — sections “Dependency and Context Contracts” and “Run Manifest Contract”.
4. `docs/operations/phase14.5-durable-scheduler-contract.md`
5. `docs/operations/phase14.5-worktree-context-contract.md`
6. `scripts/worktree_context.py`
7. `tests/scripts/test_worktree_context.py`
8. `tests/scripts/test_durable_scheduler.py`, `tests/scripts/test_controlplane_admission.py`, and `tests/scripts/test_supervised_opencode_launcher.py` for regression boundaries.

## Acceptance Criteria Coverage

Mark `accepted` only if all items hold:

1. `plan_worktree_allocations()` is deterministic and collision-free for six
   identities; it creates no filesystem or Git worktree.
2. Identity input is exact and fail-closed. Branch/worktree values are safe
   project-relative references and bound to the owning agent’s approved
   `agent/<owner>/` and `worktrees/<owner>/` prefixes.
3. The allocation ID is canonical SHA-256-derived and is revalidated before a
   snapshot trusts it; forged/mutated provenance fails closed.
4. `build_bounded_context_snapshot()` includes only the documented task-card
   allowlist, dependency evidence references, validated allocation bindings,
   schema version, hash, byte limit, sensitivity label, and future expiry.
5. Extra task body-style data is not interpreted as configuration; forbidden
   material (credential, prompt, transcript, source body, command, etc.),
   absolute paths, unsafe refs, expired snapshots, and over-limit payloads are
   rejected without a partial success result.
6. Success records contain only project-relative references and no credentials,
   prompts, source bodies, transcripts, or absolute paths.
7. Scope is restricted to the six delivered files; no `services/**`, `src/**`,
   `database/**`, `cloud/**`, or `profiles/**` changes exist in the reviewed
   diff.
8. The implementation imports no runtime-launch, network, credential-store,
   filesystem-persistence, or Git-worktree API, and no such action is executed.

## Validation Steps Performed

Run from the worktree root. A local `--basetemp` is permitted only if the
machine’s default pytest temporary directory is inaccessible.

```powershell
$py = 'D:\\codex work\\.venv\\Scripts\\python.exe'
& $py -m py_compile scripts/worktree_context.py
& $py -m pytest -p no:cacheprovider tests/scripts/test_worktree_context.py -q
& $py -m pytest -p no:cacheprovider tests/scripts/test_worktree_context.py tests/scripts/test_durable_scheduler.py tests/scripts/test_controlplane_admission.py tests/scripts/test_supervised_opencode_launcher.py -q
& $py scripts/orchestrate.py validate
git diff 6321d66..93544ac --check
git diff --name-only 6321d66..93544ac
rg -n "subprocess|socket|requests|urllib|Popen|os\.system|git worktree|open\(" scripts/worktree_context.py
```

If a command fails because of an environment permission issue, distinguish it
from a product failure and report the exact workaround and result. Do not use
network access, an external runtime, Git provisioning, or credentials to make
the check pass.

## Known Residual Risks

- The requested review is static and fixture-only. It must not turn into
  worktree provisioning, runtime launch, network use, or credential access.

## Required Report Format

Create `coordination/reviews/review-phase14.5-worktree-context-04.md` exactly
with these sections, filling every placeholder:

```markdown
# Independent Review: phase14.5-worktree-context-04

- Reviewer: INDEPENDENT_PLATFORM_REVIEWER
- Reviewed commit: 93544ac
- Decision: accepted | needs_fix | rejected

## Findings

- [P0-P3 or `none`] <file:line> — <evidence-backed finding and impact>

## Validation Check

- `<command>` — <result>

## Scope Compliance

- <reviewed diff paths and forbidden-scope result>
- <no-runtime/no-network/no-credential/no-Git-worktree evidence>

## Accepted Artifacts

- `scripts/worktree_context.py` — <accepted only when decision is accepted>
- `tests/scripts/test_worktree_context.py` — <accepted only when decision is accepted>
- `docs/operations/phase14.5-worktree-context-contract.md` — <accepted only when decision is accepted>
- `coordination/delivery/phase14.5-worktree-context-04-delivery-report.md` — <accepted only when decision is accepted>

## Residual Risks

- <fixture-only limits and any remaining concern>
```

Do not transition the task card. The orchestrator moves it to `DONE` only
after an evidence-backed `accepted` decision.
