# Phase15 offline inbox contract

First implementation slice2026-10-20; task phase15-offline-inbox-01.
Phase7 baseline commit84e7291 precedes this additive module. Independent formal
review governs acceptance. Remote activation remains HOLD.

## Scope and trust

`coordination_runtime.offline_inbox.OfflineInbox` validates one bytes message
and atomically records local metadata. It has no CLI, network, service, worker,
provider, scheduler, controller call, task-board mutation or artifact transfer.
An ACK means **offline durable admission only**. Nothing consumes it to launch.
No production authentication or remote process-custody proof is provided here.

Trusted code supplies an explicit local database path, current exact binding,
one enrolled key reference/epoch and a required `verify_signature(signature,
signed_bytes)` callable. No default permissive verifier exists; only literal
True succeeds. Verifier errors become fixed `signature_invalid`, with no raw
error text. The caller must supply reviewed crypto, authoritative current state
and revocation policy before any future integration. Binding is copied at
construction; current state is never inferred from a message or ACK.
The test HMAC verifier/key is a synthetic fixture, never a production scheme.

## Message validation

Input is UTF-8 bytes, nonempty and at most16KiB. Duplicate keys at every level,
nonfinite JSON, bad UTF-8, excessive nesting, BOM, trailing content, wrong/missing
or unknown fields refuse before SQLite access. Envelope has exactly `body` and
`authentication`. Body matches the Phase7 illustrative field names:

- Identifier fields: controller_id, machine_id, project_id, repository_id,
  task_id, owner, run_id, payload_id, request_id, message_id. ASCII100-character
  bounded identifiers; no paths, private prompts, argv or arbitrary payload.
- Integers: controller_epoch, machine_epoch, attempt, sequence, fence,
  expected_version, execution_budget_ms, protocol_version. Exact integers exclude
  booleans/floats; positive signed64-bit bounds, except version may be0.
- Lowercase hex base_sha40, contract_sha25664 and payload_sha25664.
- Only protocol_version1, operation `dispatch`, execution_budget_ms1..180000.
  Dispatch remains a metadata verb, not permission to execute.

Every field except request_id/message_id/sequence must equal the trusted local
binding, including destination machine/epoch, project/repository/task/owner,
run/payload/attempt, source hashes, current version/fence and approved budget.
This is an exact supplied-authority check, not a live lease/controller check.

Authentication has exactly key_ref/key_epoch/signature. Reference/epoch must
match current local configuration. Signature is128 lowercase hex characters,
decoded to64 bytes. The verifier receives `DOMAIN + canonical(unsigned_envelope)`;
DOMAIN is ASCII `coordination-phase15-offline-v1` followed by NUL. The unsigned
envelope includes complete body plus key_ref/key_epoch; signature is excluded.
Canonical JSON uses sorted keys, ASCII escapes, compact separators, no NaN.
This intentionally offline domain is not an activated remote wire protocol.
No wire-selected algorithm, key, verifier, role or elevated capability is accepted.

## Separate durable journal

Constructor does not open a journal. `initialize()` is explicit, requires an
existing parent, and only initializes an empty DB with application ID0x434F4631,
user_version1. Wrong schemas and existing Controller DBs refuse; no migration.
`receive()` never creates a missing DB. SQLite uses5s finite contention wait,
FULL synchronous transactions and BEGIN IMMEDIATE. It serializes writers;
no daemon, transport queue or custom lock is needed.

Namespace binds controller_id/epoch, machine_id/epoch, project_id/repository_id.
Reusing a journal under another namespace refuses. It records only namespace,
sequence floor, request/message/run/task/fence identifiers, canonical full-envelope
SHA256 and immutable ACK JSON. Raw messages, signatures, keys and private data
are not stored. One transaction commits receipt and high-water mark before ACK.

Exact known request/digest replay returns its original ACK, including after
restart or lost ACK; whitespace/key order differences canonicalize identically.
Changed content under the same request conflicts. An unseen sequence at or below
the durable high-water mark refuses. Message ID and run ID are permanently
unique in this enrolled namespace, with a separate unique task/fence pair;
changing request/payload/attempt/fence cannot reuse a run. A later legitimate
attempt needs a fresh run and authoritative task fence. There is no expiry,
tombstone deletion, retry loop, sequence reset or implicit re-enrollment.

ACK includes phase received_durable, ack_for_message_id, command_digest,
offline_only=true and receipt_digest. The last field hashes canonical ACK
without receipt_digest. ACK has no acceptance, tested/reviewed SHA or stop proof.
An existing receipt never renews a lease or advances a lifecycle.

## Fault evidence and limits

Offline tests cover malformed identity/auth/source, duplicate keys/types/bounds,
signature tamper/denial/error, no DB access on rejection, durable exact replay,
request/content/message/run/task-fence conflicts, reorder/high-water retention,
namespace/foreign-schema refusal, competing processes and actual os._exit before
and after COMMIT. The post-commit crash simulates losing the reply; retry finds
the original receipt. No launch occurs, even on first admission.

This covers local inbox portions of Phase7 F01..F08/F10/F14/F16/F17 only.
There is no remote fault-test claim, TLS/message-crypto deployment, outbox,
process journal/custody, lease clock, cancellation, key rotation service, artifact
receiver or two-machine evidence. Filesystem/SQLite and trusted local verifier
are trusted; malicious DB edits, restoring a stale backup or a compromised host
are outside proof. Lost/corrupt journal stays refused on receive; never initialize
a replacement and infer historical workers stopped. Different enrollment epochs
need separately reviewed reconciliation before any executor integration.

Rollback stops callers and removes this additive integration. Preserve journals,
receipts and all unknown work; never restore old sequence/fence/ACK counters.
Existing schema4 and accepted Phase7 sources remain unchanged.
