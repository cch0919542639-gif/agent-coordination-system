# GitHub handoff: explicit sender and receiver

This optional pilot exchanges existing assigned READY cards and receipts through
Git. FINISHED means runner completion, not reviewed/DONE. The seven existing
console views and login setup work without handoff configuration. Installing
these files does not activate a live service, provider or schedule.

## Local configuration

Follow the [console setup guide](console-download-guide.md) for login. Prepare a
separate handoff JSON file and external state directory on each computer. Keep
console tokens and databases local. repository must identify the current canonical
checkout and remote_url must match its origin. Use existing Git credential
management; JSON contains no credentials or token URLs. Confirm the project,
code branch, dedicated queue branch, peers and any runner with the governing task.

External JSON contains exactly these fields. Replace every example locally:

```json
{
  "schema_version": 1,
  "mode": "coordinator",
  "project_id": "project",
  "repository": "C:/Work/console",
  "state_dir": "C:/HandoffState/coordinator",
  "remote_url": "https://github.com/OWNER/REPOSITORY.git",
  "code_ref": "refs/heads/codex/console-handoff-sync-01",
  "queue_ref": "refs/heads/codex/handoff-project",
  "machine_id": "sender",
  "owner": "coordinator",
  "peers": [{"machine_id": "worker-pc", "owner": "worker"}],
  "evidence_ref_prefix": "refs/heads/docs/console-",
  "evidence_revision": "REPLACE_WITH_EXACT_40_HEX_TESTED_COMMIT",
  "min_tests": 131,
  "runner": null,
  "execution_enabled": false
}
```

This is a template, not a runnable setup. State is external and bound to this
configuration. Select an allowlisted full code ref and dedicated handoff queue
ref. An absent queue has a40zero head. For a worker, choose mode worker and its
own machine_id/owner matching the assigned READY card and sender peer mapping,
with distinct local repository/state paths. evidence_ref_prefix and
evidence_revision may both be null when evidence discovery is not configured;
configured evidence must match the exact tested commit.

Choose execution eligibility and any locally approved runner before init. The
entire configuration, including execution_enabled and runner, is bound to the
store. Editing false to true or adding/changing a runner after initialization
is refused as CONFIG_CHANGED/BINDING_MISMATCH. This pilot provides no configuration
migration or claim-recovery procedure; preserve the original state and config.
A new store cannot simply resume a remote claim owned by the old store.

After the local choices are authorized, use the CLI:

```powershell
py -3.13 scripts/github_handoff.py --config C:/Private/handoff.json init
py -3.13 scripts/github_handoff.py --config C:/Private/handoff.json summary
py -3.13 scripts/github_handoff.py --config C:/Private/handoff.json sync
```

init creates only new/matching handoff state, without creating console credentials
or altering the existing schema4 runtime. sync fetches configured refs and verifies
evidence/receipts without launching a task. summary reads local cached metadata;
it is not a connection test. Offline/fetch errors and missing state remain visible.

## Console preview and confirmation

```powershell
py -3.13 scripts/console_setup.py serve --state-dir C:/Private/console-state --handoff-config C:/Private/handoff.json --port 8766 --duration 300
```

The serve option is ephemeral: it does not migrate saved authentication settings
or initialize handoff state. In 跨機交接, navigation and5second refresh only read
the local summary. Manual sync is explicit: Operator can preview; Administrator
must create and confirm its own one-use60second plan; Viewer only reads. Console
sync does not start the receiver or a runner.

Select an existing READY task and a peer with the same owner. The UI displays
task_id, machine_id, expected_card_sha256 (64hex), expected_revision (40hex) and
expected_queue_head (40hex), all strings. The returned preview also displays
allowed_scope and forbidden_scope from that exact hash-bound READY card. Inspect
both displayed repository-relative scope lists and the exact card/version bindings
before confirming; caller-supplied scope lists cannot replace the card's scope.
The server rechecks all
five fields at execution: changed card/code/queue, expired/used/other-session plans
refuse. Refresh and preview again after a change. Dispatch publishes an immutable
assignment/card snapshot using queue fast-forward CAS without committing local
source or changing formal task cards.

## Receiver and periodic synchronization

A coordinator foreground watch syncs only; a worker syncs and receives at most one
own assignment per cycle. cycles1..120 and interval60..3600seconds have a
7200second wall-clock deadline including Git and runner work, not just scheduled
waits (default30cycles/60seconds). The loop stops before another cycle when its
deadline is reached and bounds each remaining wait. For example:

```powershell
py -3.13 scripts/github_handoff.py --config C:/Private/handoff.json watch --cycles 3 --interval 60
```

Keep its terminal open; stop with Ctrl+C or wait for finite completion. No
scheduler/autostart task is installed. receive/watch without --execute launches
no runner. If execution will be needed, obtain local approval and initialize with
execution_enabled true and an approved runner from the outset; continue running
without --execute until the operator explicitly intends execution. Keep the bound
configuration unchanged. runner contains argv, script, sha256 and
timeout_seconds1..900. script is
a canonical approved local file outside the editable worker workspace; argv
contains its literal script argument. The CLI appends the received payload path
with shell=False. Changed runner hashes refuse; remote task text supplies no
command. A provider launcher requires its own approved adapter/activation. Pilot
tests use a disposable local bare remote and harmless synthetic runners only.

Both local permission and explicit receive/watch --execute are required. A remote
claim is published and verified before launch. Durable inbox/receipts, local
dedupe and cross-clone claim identity prevent duplicate execution. Owned Windows
JobProcess containment records actual root exit and stopped-tree proof. UNKNOWN
or interrupted RUNNING needs manual recovery; receipt publication retries do not
rerun a task. Preserve state/outbox during transport diagnosis.

VERIFIED_PASS is technical verification for the labeled tested commit, not formal
acceptance or physical-host attestation. FAIL/INVALID/STALE versions may coexist.
RECEIVED/RUNNING/FINISHED/FAILED/UNKNOWN remains separate from formal repository
READY/IN_PROGRESS/REVIEW/DONE and independent review.
