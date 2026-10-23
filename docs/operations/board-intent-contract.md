# Phase1c durable board intent contract

2026-10-16. Extends the accepted Phase1b contract; its historical schema1/source
hashes remain prior evidence. Git is formal task/review/delivery authority;
SQLite governs runtime authority and intent receipts. No Git commit transaction
or authentication is claimed. Trusted local caller, one configured DB per board,
explicit project/repository root. No server, worker execution or implicit DONE.

## Schema and upgrade

New initialization creates schema2. Adds project_bindings(project_id,root_digest)
and board_intents, retaining v1 runtime tables/receipts/counters/events unchanged.
Normal APIs refuse v1/future/foreign schemas. Explicit migrate defaults to dry-run
(read-only/no files). Execute requires a new backup path, holds the SQLite writer
gate, verifies v1, makes consistent exclusive/non-overwriting backup, then adds
schema2 transactionally. DDL failure rolls back, retains backup. Existing schema2
is a no-op. Quiesce legacy v1 writers before upgrade; no live upgrade/restore is
performed by this task. No fence reset or automatic migration on query/import.
DB backup verifies actual source schema version. Event envelope stays version1.

## Prepare and identity

BoardProjector(controller, repo_root, project_id) is opt-in. First intent binds
project to a normalized resolved-root digest in the same SQL transaction; another
root refuses. One board uses one configured project/DB; legacy task helpers and
Serial must not concurrently write that board. SQLite's BEGIN IMMEDIATE gates
all participating runtime and filesystem writes. Existing helpers stay unchanged;
Phase2 must route board writes before any parallel activation. Trusted local
filesystem only, no guarantee against hostile noncooperating OS/path mutation.

prepare(command, filename, expected_sha256) reads one bounded UTF-8 card (64KiB),
checks unique task ID across lifecycle directories, matching assigned owner and
status/location, then enqueues intent in the SAME transaction as apply's runtime
changes, idempotency result and audit. It does not write the card. Exact supplied
preimage digest is mandatory. Filename is a bounded ASCII basename ending .md;
no path traversal, symbolic link/junction escapes or aliased child paths, arbitrary
body or paths are accepted. IDs/digests remain bounded; no card body/path stored
in SQLite. Bound root digest is local-path identity, not a portable repo ID.

Allowed operations: claim ready->in_progress; transition submitted
in_progress->review; transition failed/lost/recovery_required in_progress->blocked.
Other operations/targets, owner reassignment, dependencies, delivery verification,
formal review acceptance or DONE are not inferred. Caller must already have the
existing task assignment and required delivery evidence; prepare checks declared
report existence at prepare and again before review publication/removal. Body/header bytes are preserved except
one exact status-line replacement and appended comment with unique intent ID.
A duplicate prepare with the same command/spec uses the SQL receipt even if the
card has moved; changed arguments under the same request key refuse.

Unresolved pending/recovery_required intent blocks later task mutations except
same-authority renew or explicit revoke. Renew does not invalidate prepared
fence/phase; revoke invalidates future board writes and does not prove OS stop.
No blind launch or takeover. After a cancel/terminal receipt, runtime state still
requires its normal checks and any explicit retirement; no hidden compensation.

## Reconcile, interruption and conflict

reconcile(request_id) defaults to dry-run and creates no file. Execute starts a
writer transaction, checks bound root and exact intent, reads current runtime,
clock and board. A new mutation requires current run/owner/fence/phase and lease;
renewed version may differ, but phase and fence may not. Clock rollback refuses.

Known filesystem stages (B=original bytes; A=desired bytes with intent marker):
- only source B: prepare complete, no board mutation yet; build/fsync A draft,
  publish complete target with exclusive os.link, never overwrite an existing file.
- source B plus target A: publication happened; remove source only after exact
  B check and current authority. Source removed only when target still equals A.
- only target A: projection complete; record applied receipt/audit even if lease
  later expired/revoked, since no board write remains. Receipt is historical.
- any changed/missing/duplicate/unrecognized card: recovery_required; preserve
  files, no overwrite, silent deletion, new claim, runtime rollback or replay.

Each successful intent status has a deterministic deduplicated audit event;
status/clock/audit commit together. Process death rolls SQL transaction back,
leaving durable intent and exact filesystem stage for next explicit reconcile.
Applied/cancelled status replay never projects again, even after later card edits.
Partial drafts may remain after crash as evidence; never guessed into success.
No power-loss/directory-fsync or all-filesystem guarantee is claimed. Filesystems
without safe hard-link publication refuse; existing source stays preserved.

cancel is explicit compensation, dry-run by default. Allowed only at clean source
B with no target, or source B plus exact target A. Execute removes only known A
in the latter case, preserves B, records cancelled/audit, and does not undo SQL
runtime changes. Already-complete target-only stage must reconcile applied.
Unknown source/destination must be manually repaired from preserved evidence
before compensation; no generic force/discard mode. This command is trusted
operator action, not worker authentication or permission to start another worker.

## API and CLI

StateController.apply(command, projection=spec) atomically commits intent;
BoardProjector.prepare constructs/validates that fixed spec. intents(project,
after_sequence=0,limit=100) is bounded read-only query. Board CLI:
python -m coordination_runtime.board_projection --db PATH --repo ROOT
--project-id ID prepare --command-file FILE --filename NAME --expected-sha256 SHA;
reconcile|cancel --request-id ID [--execute]; list [--after N --limit N]. Command
files cap16KiB; output includes metadata/status/digests only, never card body,
SQL, absolute root path or private input. State CLI migrate [--backup NEW]
[--execute] is explicit. No API runs Git, commits, providers or a scheduler.
