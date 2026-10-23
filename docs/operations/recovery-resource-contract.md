# Phase4 recovery, health and resource contract

Scoped extension of accepted schema4/Phase3. Local cooperative configuration,
SQLite writer and native Windows identity observations; no new daemon or schema.
The architecture PDF recovery matrix is evaluated here, not execution authority.

## Inventory and recovery

RecoveryManager takes an existing ParallelController. inspect(run_id) and bounded
scan(after_run_id='',limit=100) are read-only: current run/fence/lease/heartbeat,
numeric PID/creation and observed root state, workspace binding/scope, original
task card stage, intent stage, delivery hash and related checker/queue metadata.
Private absolute paths, command arguments, worker output and transcripts are
excluded. A clock below SQLite's high-water mark is unknown, never a valid lease.

An OS observation of a missing/exited/replaced root PID does not prove a stopped
descendant tree. Only the previously durable whole-Job stopped receipt (numeric
PID/creation/exit) proves that; otherwise preserve recovery_required and slot.
No launch identity is safe only for a claimed reservation with no process receipt
and no committed launch event. Existing dirty/foreign/unregistered workspaces are
preserved; invalid binding or unresolved board intent prevents slot release.

reconcile(run_id,request_id,expected_version,expected_fence,reason,execute=False)
defaults to preview. reason is expired or interrupted. Expired requires expired
lease; interrupted refuses a healthy running root with a valid lease. Explicit
execution compares version/fence, atomically revokes old authority and either
releases a provably safe reservation with resolved intents or keeps it held in
recovery_required. A previously retired exact generation (fence+1/no current run)
can settle later with a new request, never after a newer run is admitted.
Same request/identical input returns a historical receipt; changed input refuses.
Fencing, slot change, receipt and event share one SQLite transaction. There is
no inferred successful submission, tested SHA, task acceptance or automatic rerun.

Board intents remain independently recoverable via existing reconcile/cancel.
Pending/conflicting intent holds the reservation; recovery never overwrites a
card, rewrites delivery or deletes source/target. Related checking/unknown checker
records and queued/publishing receipts are inventoried; checker success is never
manufactured and publication uses only its separately authorized existing API.

## Resource breaker

Finite samples measure minimum free disk for configured DB/workspace roots (and
validation root for checking/publication), available physical memory and memory
load through Windows GlobalMemoryStatusEx. No CPU/child quotas or benchmark target
is claimed. Initial fixed policy: at least512MiB disk,256MiB available physical
memory, memory load below95%. Failure to sample is unknown and refuses new work.
Numeric samples only; no host identity, paths or transcripts in audit fields.

One project latch is the latest resource.breaker.open/closed event ordered by
SQLite sequence. Pressure/unknown sampling at explicit preflight commits an open
event before refusal, surviving caller exceptions and restarts. Healthy samples
never automatically close it. Open latch refuses new reservations, provisioning,
mock launch/resume, native checker launch and local publication CAS. Existing
workers may finish; renew/collect/submit/retire/reconcile/inspect remain available.
Critical writer transactions recheck latch and current resources; a newly failing
sample there refuses execution even if the preceding preflight was healthy.

reset(expected_sequence,execute=False) is explicit and compares the observed latch
sequence. It requires current canonical project binding, all reservations/owners/
intents quiescent, no checking or unknown checker tree, and a new healthy sample.
It appends a closed event and never clears historical events or changes mode.
Concurrent open/reset versus admission/launch is serialized by the existing writer.
Inspection/previews create no DB, event, directory, marker or worktree.

## Boundaries and verification

Recovery/resource CLI requires explicit --db --repo --workspaces --project-id;
inspect/scan/resources are read-only; reconcile/probe/reset mutate only with
--execute. JSON output is bounded and private; malformed input returns a fixed
refusal. No automatic initialize/migrate/default path or provider activation.

Crash testing uses owned hidden finite Windows Jobs in disposable repositories.
Root and descendants are observed after owning controller death, while recovery
continues to preserve an unknown tree reservation despite missing PID. Dirty
candidate, board conflict, concurrent recovery, exact retry, pressure gates and
reset conflicts are tested. Actual project remains inactive/uncommitted. Global
authentication, hostile direct SQLite/filesystem writes, arbitrary process control,
automatic cleanup, CPU limits and provider retry policy remain separate work.
