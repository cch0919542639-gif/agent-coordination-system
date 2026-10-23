# Phase2 parallel workspace/controller contract

2026-10-16. Extends accepted Phase1c; Git remains formal task/review/delivery
identity, SQLite owns runs/reservations/intents. Default Serial behavior remains
on boards without a parallel marker. Current project is not activated by this
implementation. Trusted local/cooperative filesystem/Git configuration, not an
OS security sandbox or authentication. Real provider adapters remain Phase6.

## Schema3 and explicit mode

Schema3 adds parallel_projects and parallel_runs, retaining schema1/2 data and
receipt digests. Normal old schemas refuse; migrate defaults read-only and must
make a verified new backup under writer gate before additive upgrade. No live
migration, counter reset, restore or Git history publication in this task.

ParallelController(controller,repo_root,workspace_root,project_id) requires a
workspace root outside the authoritative repository, normalized non-aliased
paths and one configured DB/project per board. enable(capacity=2, execute=False,
quiesced=False) defaults to preview. Execute requires explicit quiescence of
legacy writers, no active runs/intents/reservations, and capacity1..2. Persist
an exclusive, fsynced ignored mode marker BEFORE SQL mode becomes enabled. A
matching interrupted setup is resumable; unknown marker/config refuses. Shared
helper writes to task-board/delivery/reviews/progress and legacy activation/
Serial launch entry points refuse while any marker exists (including corrupt
markers). Participating parallel mutations use the controller route; unqualified
StateController/BoardProjector mutations refuse enabled projects. Private Python
controller methods are a cooperative boundary, not hostile-caller authorization.

Disable requires no active authority, unresolved intent or held reservations.
Commit disabled DB state while guard remains; a second writer transaction checks
it is still disabled before removing the matching marker. Interrupted/racing
mode changes remain fail-closed. Formal review/DONE stays with existing authorized
review workflow AFTER quiescent disable; no automated acceptance is introduced.

## Atomic admission and scope

prepare(request,filename,expected_sha256,resources,output,execute=False) derives
a claim from an exact request (project/task/run/owner/request/expected_version/
base_sha/lease_seconds). Contract digest binds current card digest, declared
worker scopes/dependencies, exclusive resource IDs and chosen mock output.
The source card must be unique READY and assigned to this owner; exact base40hex
must equal authoritative HEAD and resolve to a local commit. No implicit copy of
uncommitted authoritative changes into workspaces. Dependencies must be unique,
acyclic, bounded and already formal DONE in done/ with exact canonical accepted
review for that task; they stay unchanged during
Parallel Mode. Serial formal review can progress them between quiescent batches.

Supported scopes: literal relative file paths or directory/** prefixes, max64;
no traversal/absolute/backslash/ambiguous glob, max240 characters each. Normalize
case conservatively for Windows. Protected .git, controller metadata and shared
coordination task-board/delivery/reviews/progress cannot be worker scopes.
Parent/child prefixes conflict conservatively. Resources are sorted distinct
bounded IDs (max16), exclusive by exact key. Dependency count max32/graph128.
Atomic SQL admission checks capacity, scope/resource conflict and root binding,
then reserves workspace and commits claim/board intent/request/audit together.
Unreleased reservations remain held after expiry, failure or unknown process;
no blind slot reuse. Retrying same request/spec is historical, changed inputs
refuse. Capacity is deterministic configured slot count, not measured host load.

## Workspace lifecycle and writer routing

Workspace path is derived only as workspace_root/project_id/run_id, unique and
bound by project/task/run/owner/fence/base/path/policy digest. provision(run_id,
execute=False) explicitly creates a detached native Git worktree at exact base,
with bounded Git commands and hooks disabled for creation. The manifest is
exclusive metadata inside .coordination-runtime/binding.json. Validate registered
Git common directory, exact top-level, detached HEAD, base and metadata before
launch/collection. No arbitrary branch reuse, overwrite, checkout reset, worktree
remove/prune or automatic candidate cleanup. A reserved interrupted creation may
adopt ONLY matching registered, pristine pinned worktree; unknown/dirty paths
remain preserved. All candidates survive retirement and mode changes.

project(run_id,execute=False) routes pending claim through Phase1c projector
only after verified workspace readiness. No participating mock writes shared
cards/reports. Controller publishes its bounded deterministic delivery receipt
through a durable digest and exclusive complete-file publication before board
submit intent. Unknown delivery occupant refuses. submit(run_id,request_id,
execute=False) requires verified stopped successful mock, unchanged binding/HEAD,
exact scope inspection and new/known report publication; then projects review
through Phase1c. No formal DONE or test/review SHA acceptance is inferred.

## Bounded passive parallel proof

mocks(run_ids,execute=False) previews unless explicit, finite1..2 ready runs,
Windows JobProcess only. No arbitrary argv/provider/model/shell. Each fixed
Python mock writes one declared output in its own worktree, uses own bounded
metadata handshake and waits for controller's go barrier. Two mocks overlap in
real native processes; monotonic start/end receipts must overlap. Record launcher
PID/creation durably while suspended, numeric exit and verified empty Job tree. Commit launching state
BEFORE spawn; lost/ambiguous launch retains reservation and recovery_required,
never automatically reruns. If cleanup also fails, retain known PID/creation
identity with tree_stopped=false and keep the reservation. Cleanup owns only
these Jobs, not unrelated PIDs.

Inspect tracked/untracked/ignored Git changes, refuse unexpected HEAD/branch/
registration, aliases, protected paths, rename/deletion outside declared scope,
or unrecognized controller metadata. A scope breach preserves work and prevents
submission. This detects cooperative violations; it cannot prevent a malicious
OS process writing elsewhere. Output and input bounds apply (request16KiB,
changed paths2048, metadata64KiB, SQL queries max100). No transcript storage.

cancel(run_id,execute=False) explicitly compensates an unlaunched pending claim
through Phase1c; it cannot guess that an unknown process stopped.

retire(run_id,execute=False) needs known never-launched or verified stopped
process and no unresolved projection. Explicit fenced revoke retires runtime
and releases reservation atomically; it neither accepts task nor deletes work.
Unknown launches require later dedicated recovery, no force flag. No automatic
retry, restart reconciliation, performance guarantee or broad resource breaker
beyond Phase2 slots/resource keys; Phase4 retains those gates.

CLI: python -m coordination_runtime.parallel_runtime --db PATH --repo ROOT
--workspaces ROOT --project-id ID enable [--capacity N --quiesced --execute];
disable [--execute]; prepare --request-file FILE --filename NAME
--expected-sha256 SHA --output REL [--resource ID ... --execute];
provision|project|submit|retire|cancel --run-id ID [--request-id ID --execute];
mocks --run-id ID [--run-id ID --execute]; inspect --run-id ID.
No command commits/pushes/merges, enables provider schedules or changes global
permissions/settings. Production activation and Phase3+ remain separate gates.
