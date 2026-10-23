# Phase1b runtime state contract v1

Trusted local controller API, additive to Serial Mode. This package does not
write task cards, claims in Git, delivery/ACK records, provider state or legacy
JSONL. Git remains formal task/review authority. Phase1c will define durable
intent and board reconciliation; no cross-store transaction is claimed here.

## Storage and initialization

Default: coordination/monitor/runtime/coordination-v2/state.db (already ignored,
including journal files). Import/construction/query never initializes a DB.
Explicit init creates schema1 under application_id0x434f4f32; first-init races
serialize. Existing foreign/unknown/future schema refuses before application
mutation. v1 has no legacy import or destructive migration; future schema
upgrades require a separately reviewed migration, consistent backup and dry run.
Use sqlite3, rollback journal and synchronous FULL, BEGIN IMMEDIATE and a5s
busy budget. No new dependency or background process.

Tables: runtime_tasks keyed(project_id,task_id), runs keyed(project_id,run_id),
requests keyed(project_id,request_id), events with global monotonic sequence,
and metadata containing the last successful mutation's UTC millisecond clock.
Only bounded IDs, SHA/digest and runtime metadata are stored, never task text,
argv, cwd, credentials or transcripts. Run IDs cannot be reused in a project.

## Commands and authority

Claim supplies exact project/task/run/owner, base_sha40hex, contract_sha25664hex,
expected_version (zero for absent runtime task), request_id and lease_seconds
(integer1..3600). One transaction checks task version/inactive authority, advances
task version and monotonically increasing fencing generation, inserts claimed
run, idempotency result and audit event. Different projects remain independent.

Every renewal/transition checks project/task/run/owner/fence, expected task
version and unexpired lease before changing state. Successful commands advance
task version, including renewal. Runtime phases follow the documented transition
map in code; completed is runtime-only and cannot declare a task accepted DONE.
Terminal phases cannot renew or transition. Terminal state still holds authority
until explicit controller revoke/retirement; it never implies the process stopped.

Expiry invalidates normal writes and renewal, but never grants blind takeover.
Explicit revoke takes current run/fence/expected_version and an actor/reason,
works even after expiry, advances fence/version, records recovery_required for
nonterminal runs, clears active authority and expires the old lease. Next claim
uses a new run ID and still-higher fence. Revocation controls write authority,
not OS process custody; later launch code must independently prove old-tree
stop or require operator recovery before executing another worker.

Request IDs are project-scoped. Same key/same canonical command returns its
original recorded result without extending lease, advancing version or adding
events; changed arguments with that key refuse. Replies explicitly separate
recorded snapshot from replay status. Replayed historical results never grant
current authority; get/current checks and every new mutation revalidate stored
fence/active run/expiry. After a5s contention failure nothing is acknowledged;
retrying the same key can resolve an ambiguous SQL commit.

Clock is wall-clock UTC milliseconds; successful writes persist a nondecreasing
floor. A backward clock refuses mutations and query lease validity. There is no
automatic clock override. Forward jumps can expire leases and require recovery.
This is not an NTP service or a proof against arbitrary clock tampering.

## Recovery, queries and backup

Run/task changes, result and audit event commit together. Crash before commit
rolls back; crash after commit can replay the same request. No SQL-only command
claims to recover a partially written Git artifact. Read-only get/history and
project-scoped event pagination (limit1..100) create no file and expose only the
runtime metadata above. Authentication/roles/HTTP are future gates; callers of
this local library/CLI are trusted controller code, not untrusted workers.

Backup uses SQLite's consistent online backup into an explicitly named new
file; existing target/source overwrite refuses. Verify integrity/schema before
reporting success; interrupted backup may leave an incomplete target for manual
inspection, never automatically restore it. Recovery restores only an explicit
verified backup after stopping writers and comparing current evidence; do not
delete live DBs, reset fence counters or reuse an old DB while stale workers
could still write. Online restore and rollback of historical fences are not
provided. Source rollback alone must preserve runtime DB and backups.

CLI: python -m coordination_runtime.state_controller --db <explicit-path>
init|get|history|events|apply|backup, with JSON output. apply takes
--command-file containing one exact claim/renew/transition/revoke command;
command files are bounded at16KiB. get/history require --project-id/--task-id;
events requires --project-id and bounded --after/--limit; backup takes --to.
Construction alone performs no filesystem operation.
No CLI operation executes a worker or touches the task board.

Example command JSON for apply (replace digests with the actual frozen sources):

```json
{"op":"claim","project_id":"example","task_id":"task1","run_id":"run1","owner":"worker1","request_id":"claim1","expected_version":0,"lease_seconds":60,"base_sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","contract_sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}
```

renew adds owner/fence/lease_seconds to the common identity/version/request
fields; transition adds owner/fence/phase; revoke adds actor/fence/reason.
Only claim carries source digests; subsequent commands cannot replace them.
Replies contain recorded task snapshot and replayed flag. Always query current
state before treating an old claim receipt as active authority.
