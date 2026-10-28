# Curated ACS memory pilot

This is an optional Python3.12+ adapter for reviewed ACS source cards. Git remains
formal authority. No hook, worker, NAS deployment, background sync or provider is
enabled by importing this module or running its offline preview.

## Current boundary

The implemented path is preview → explicit import → extraction verification →
verified recall. Original contract tests used a synthetic HTTP fixture. Two
subsequent synthetic-only WSL trials used the real AgentMemory 0.4.3 core and a
local model: extraction and direct recall worked, but the exact source marker
was absent both times, so this adapter refused activation. Later synthetic trials
used an agent-scoped L1 source-marker strategy and disabled L1 deduplication on
the dedicated test instance. Ten of ten short synthetic questions found their
expected verified card in the top three; replay, adapter withdrawal and one
supersession also passed. This is preliminary evidence, not formal benchmark,
independent review, actual-document approval or NAS deployment acceptance. See
`coordination/evidence/acs-memory-preflight-01/marker-strategy-20261029/`.

The tested instance used `memory.extraction.enableDedup: false` in its YAML and
an admin-applied L1 strategy scoped to the synthetic agent. Disabling deduplication
affects the whole instance, so it is appropriate only for a dedicated pilot after
separate deployment approval. The exact strategy and API sequence are in the
evidence report. Missing markers still refuse activation; there is no fallback to
unverified output. Upstream L2/L3 and raw recall remain outside the adapter's
withdrawal boundary, and storage may grow faster with deduplication disabled.

Only AgentMemory0.4.3 through an explicit numeric loopback HTTP endpoint is
accepted. This endpoint is intended to be the local end of a separately approved
SSH tunnel. No direct NAS LAN URL, DNS alias, embedded credentials, proxy or
redirect is accepted. The adapter checks `/health` before every API call. This
version check is a compatibility check, not cryptographic server attestation.

## Review the offline candidate batch

Run from the ACS checkout; substitute the actual absolute repository path:

```powershell
py -3.13 -B scripts/curated_memory.py preview --repo "<CHECKOUT>" --batch coordination/evidence/acs-memory-preflight-01/candidate-batch.json
```

This reads only committed Git objects and the JSON batch, verifies origin,
40-hex commit, regular-file mode, allowlisted Markdown path, raw blob SHA256 and
line anchor, and prints the proposed summaries and exact batch SHA256. It never
opens a network connection or initializes a receipt DB. Working-tree edits do not
replace pinned Git content; Git replace refs are disabled for these reads.

The shipped ten cards and questions are **unapproved candidates**. Their
`pending-human-review` references deliberately block import even if someone copies
the preview digest. Nine cards are active candidates; one old CP950 failure is
historical/superseded. Do not score that historical-only question as an active
recall hit. A reviewer must freeze a distinct ten-question active benchmark before
claiming the plan's8/10 target; the candidate list alone is not that acceptance.

Review source anchors against summaries, applicability, original review evidence,
privacy, and supersession. Replace each active card's approval reference with the
actual review record; run preview again and approve that new digest. A sensitive
string heuristic rejects common credential, email and private Windows-home forms;
it is not a complete PII detector and does not replace manual review. The adapter
never uploads the whole source document or silently extracts unselected text.

The operator digest is an explicit local attestation to this exact batch. It is
not a digital signature and does not authenticate an independent reviewer or
prove a GitHub PR is approved. Runtime receipts are private operator-controlled
state and must not be writable by untrusted agents.

## Connection and processing approval

Before live operation, deliberately select the model/provider, cost limit and
which selected summaries may be processed; determine whether embedding/recall
also calls an external service. Record the actual authorization reference.
Do not infer permission from this guide, an existing key or a working server.

Create a local connection JSON **outside Git** with these exact keys:

```json
{
  "endpoint": "http://127.0.0.1:18420",
  "server_version": "0.4.3",
  "department_id": "default",
  "team_id": "<ACS_TEAM_ID>",
  "agent_id": "<CURATED_AGENT_ID>",
  "user_id": "<CURATED_USER_ID>",
  "key_env": "AMEM_USER_KEY",
  "processing_authorization_ref": "<ACTUAL_APPROVAL_RECORD>"
}
```

Place the user key in the selected process environment through your secure local
credential workflow, never in this JSON, command arguments, Git or screenshots.
Use a normal memory user, not a department/system admin. Same team+agent but
different users do not share L1 facts: a single-user/two-device pilot uses separate
keys owned by the same curated user. Ordinary user keys can still write their own
scope; a read-only MCP tool is not a server-enforced read-only credential.

Create a private receipt parent explicitly outside all source checkouts, then use
the same connection and receipt DB for subsequent steps. The DB stores approved
batch manifests, connection metadata, approval time, delivery states and atom IDs;
it stores no key. Preserve the original batch/connection alongside a protected
consistent DB backup. No automatic repair, migration or receipt reset is supplied.

## Import and verify

The following is a template, not an approved live invocation:

```powershell
py -3.13 -B scripts/curated_memory.py import --repo "<CHECKOUT>" --batch "<REVIEWED_BATCH>" --connection "<PRIVATE_CONNECTION_JSON>" --state "<PRIVATE_RECEIPTS_DB>" --approved-sha256 "<EXACT_PREVIEW_SHA256>"
py -3.13 -B scripts/curated_memory.py verify --repo "<CHECKOUT>" --batch "<REVIEWED_BATCH>" --connection "<PRIVATE_CONNECTION_JSON>" --state "<PRIVATE_RECEIPTS_DB>"
```

Only active cards are submitted via official `conversation/add`, each with a
stable session ID and source marker. A durable `uncertain` receipt is committed
before HTTP. A successful API reply becomes `submitted`, not `verified` or done.
Extraction is asynchronous; call verify explicitly after the server processes it.

Verification uses the official scoped `atomic/query`. Every active card must
have an exact marker in an atom; only then is the batch activated transactionally.
The marker's hash binds the approved card, including its source. It proves the
correlation, not model reasoning quality. A scope with more than100atoms is
refused rather than silently using a partial page. Use a dedicated small pilot
scope; paging and a larger deployment are outside this first slice.

Replaying an identical card does not issue another conversation write. If a reply
is lost, import refuses blind resend. Run the explicit read-only reconciliation:

```powershell
py -3.13 -B scripts/curated_memory.py reconcile --repo "<CHECKOUT>" --batch "<REVIEWED_BATCH>" --connection "<PRIVATE_CONNECTION_JSON>" --state "<PRIVATE_RECEIPTS_DB>"
```

Reconcile accepts only one object with role `user`, integer total1 and exact
source-envelope content in that deterministic session. Missing, duplicate or changed remote data remains uncertain. It does
not reset the receipt, submit another message or ask a model to guess delivery.

## Query and revoke context

```powershell
py -3.13 -B scripts/curated_memory.py query --repo "<CHECKOUT>" --batch "<ACTIVE_BATCH>" --connection "<PRIVATE_CONNECTION_JSON>" --state "<PRIVATE_RECEIPTS_DB>" --question "Did the CP950 repair require a UTF-8 workaround?"
```

The adapter accepts candidates only when both their atom ID and source marker
match a verified active card. It outputs the reviewer-approved summary, exact
GitHub source, hash and applicability; unverified model prose, persona and scene
navigation are never forwarded. No network error is converted into an empty
successful history. Pinned history is not a claim about current branch/task state.

Change a card to `superseded`/`withdrawn` in a newly reviewed batch, import that
new digest, and verify it to atomically switch the active batch. Reuse unchanged
cards without resubmission. Old batch queries refuse, including an activation
change detected during an in-flight recall. An all-withdrawn batch activates with
zero network calls and returns no cards. Do not edit/delete formal source history.

This excludes stale material **at this adapter's output boundary**. It does not
delete upstream L1/L2/L3 history or make direct upstream `memory_recall` safe for
the same provenance guarantees. Before raw/native upstream access, separately
prove cleanup or rebuild a fresh scope. Do not expose both query paths and claim
the adapter's active-card policy covers both.

## Optional MCP transport

Use the same arguments with command `mcp` to run stdio JSON-RPC. It exposes only
`acs_memory_recall`, with one string argument `query`. Do not install any capture
hooks. The batch file and source pins are re-read for each tool call; activation
must match the ledger before and after recall. Changing the batch file without
approval+verification refuses query instead of silently adopting it.

The MCP transport has no write/execute/dispatch/acceptance tools. Its process
still holds an ordinary user key, so keep connection/state files protected and
do not mistake tool listing for server-side least privilege. NAS operation,
key management, tunnels, backups, real model qualification and24hour/two-machine
acceptance remain separate gated work.

Git subprocess failures during MCP calls return the same safe unavailable error;
the session remains available for subsequent requests.
