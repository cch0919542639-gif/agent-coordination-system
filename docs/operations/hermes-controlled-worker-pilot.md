# Hermes Controlled-Worker Pilot

## Scope

This pilot uses the repository task board and existing owner-strict activation
contract. Hermes handles one assigned task per invocation; Hermes Kanban is
not used.

## Controlled Launcher

The OpenCode-equivalent entrypoint is
`integrations/hermes-coordination-worker/run-controlled-worker.ps1`.
Verify the installed CLI without calling a model:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File integrations/hermes-coordination-worker/run-controlled-worker.ps1
```

After the operator authorizes an assigned task's model data transfer, run one
worker session:

```powershell
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File integrations/hermes-coordination-worker/run-controlled-worker.ps1 -Run
```

The launcher first polls without acknowledging. An idle invocation exits
without calling Hermes or a model. When work is pending, `run-session.ps1`
resolves the Python interpreter beside the installed Hermes executable and
invokes `run_session.py`. That runner uses Hermes's existing `AIAgent` and
provider resolver with only `terminal,process` tools and at most 24 iterations.
File operations use Python's standard library through terminal, reducing the
tool-definition budget without adding another mechanism.
Requests set `parallel_tool_calls=false`, matching Groq's
[GPT-OSS tool-use contract](https://console.groq.com/docs/tool-use/overview).
Provider tool validation remains enabled.
The launcher preserves the exact packet Objective and allowed paths in the
initial user assignment, so bounded file output or later compaction cannot
replace the requested artifact with generic report-only work. It supplies the
claim/submit helpers' exact task/agent arguments and the exact repository
delivery template with Task ID, Agent and Phase already bound. The submit helper's optional --summary/--artifact/--payload-id mode verifies the
ACK, owner, artifact scope and SHA256, generates canonical fields from the
repository template, runs validation, then submits. Failure retains an
unsubmitted candidate and makes no acceptance claim. Existing manual-report
submission remains compatible. Independent artifact acceptance remains with
the controller/reviewer.
The worker explicitly reads repository context, activates one owner-matching
delivery, claims its task, writes evidence, validates, submits to review, and
stops. Global memory, persona, context-file injection, session storage, and
trajectory recording are disabled for this worker. `platform=cron` avoids the
interactive CLI coding context; every terminal call uses the repository workdir.
The runner supplies a short coordination-worker system brief through Hermes's
system-prompt hooks, so the full interactive persona cannot consume the task
budget. This is scoped to this process and does not change Desktop settings.

The runner caps native context compression at 5,500 estimated tokens, fixes
each main completion at 768 tokens through request overrides, and uses low reasoning
effort for GPT-OSS and no reasoning for a Qwen override. Hermes can
otherwise raise the output limit when repairing a truncated
tool call. Terminal output is capped at 2,500 characters through Hermes's
existing process-local limits cache and restored on exit. This keeps the
worker budget small without changing global config. The compressor protects
the initial assigned message across every compaction and only the last two messages; its interactive default of
twenty protected messages prevents compression in a short worker session.
Native auxiliary compaction is also scoped to the same worker provider/model,
with a 6,000-character serialized input bound, ~400-token summary guidance and
a hard 768-token completion cap through the already-resolved API client, whose
bounded native retries cannot switch provider/model. Micro-compaction is disabled
because its separate call path bypasses this bound.
An output truncated at that cap is rejected rather than installed as a summary.
These worker-process overrides are restored on exit; Desktop config is unchanged.
It prints only API-step counts, sanitized retry status, and completion/failure
metadata. Compression is explicitly enabled, with at most 24 compactions in the bounded session.
For minute-token HTTP429s, the process-local diagnostic hook adds5s of
refill margin before the SDK backoff: observed retry requests grew by ~300
tokens and exhausted the old3-attempt budget by ~2s. Daily quota errors receive
no extra margin. The worker timeout and retry count remain bounded.
Each API request has at most three attempts; the launcher never
automatically starts another worker session or activates another payload.
After each completed tool, the runner checks the acknowledged owner-matching
delivery record, expected durable inbox,
task ID, payload ID, project, owner, original filename, REVIEW card, and report.
A matching receipt interrupts Hermes immediately and returns exit code zero;
a model's completion claim alone cannot pass. The SDK verification-stop gate supplies
at most three reminders to continue the same task when no REVIEW receipt exists,
within the existing 24-call budget. The gate is process-local and restored on exit. This confirms submission only;
the orchestrator still reviews and accepts the artifacts.

The worker default is `openai/gpt-oss-20b`; the current local configuration
routes it to Groq. Desktop keeps its `openai/gpt-oss-120b` default. The launcher
uses existing credentials without reading or
copying them. It does not use `--oneshot` (which bypasses command approval),
`--yolo`, or any automatic approval flag. This is the same prompt-enforced
worker boundary as the earlier pilots, not an operating-system sandbox.
The runner rejects an inherited `HERMES_YOLO_MODE` and denies dangerous-command
approval requests in the headless worker. Safe task scripts remain available.

The currently observed Groq limit is 8,000 tokens per minute. CLI attempts
reached HTTP 429 and then HTTP 413 as individual requests grew past that limit;
terminal-only attempts also exposed unavailable-tool calls from CLI coding
guidance. The bounded runner replaces that path. Keep task packets and tool
output small; larger product tasks still need separate capacity validation.
The 2026-10-11 diagnostic also confirmed the 120B daily allowance was nearly
exhausted (197,362 of 200,000 tokens used, with 2,653 requested). The worker
model override avoids changing Desktop or credentials.
The 20B trial also reached a ten-minute rate-limit wait before claim. Qwen's
authenticated forced-function probe passed with an observed 8K TPM allowance;
its [instruct mode](https://console.groq.com/docs/model/qwen/qwen3.8-27b) uses
`reasoning_effort=none`. No account plan or spend limit was changed.

## 2026-10-11 Verification

Tested with the installed Hermes v0.19.1 runtime. The final default model is
Qwen 3.8 27B on the existing Groq provider; Desktop keeps GPT-OSS 120B.

| Task | Payload | Outcome |
| --- | --- | --- |
| `phase14-hermes-pilot-02` | `a95589198a5074df` | Claimed and submitted during bring-up; operator stop and factual report correction required. Cancelled and superseded. |
| `phase14-hermes-pilot-03` | `c2c5db1912e08505` | Activated, then remained READY during a ten-minute rate-limit wait. Cancelled and superseded. |
| `phase14-hermes-pilot-04` | `a640283f6cd83672` | Fresh normal `-Run`, no recovery parameter: activation, claim, report, validation, REVIEW receipt and acceptance completed. Eight main API calls; exit 0. |

The final runner interrupts immediately after its matching submission receipt.
The actual REVIEW card and WAITING_FOR_REVIEW progress were checked before
orchestrator acceptance. The 21-test focused suite covers launcher failures,
idle behavior, owner/project/identity boundaries, interrupted-task recovery,
request/output limits, approval denial and receipt-driven stop/exit behavior.
Coordination validation and task doctor passed. A baseline hash audit found no
product or other existing task changes; a recent accessible-file inventory
also matched the operator and pilot artifacts.

Events were supplied through the existing local ledger/routing APIs using
`ref=local`, `commit=working-tree`. Review routed one deduplicated orchestrator
payload `55a53031c3ae8f0b`, acknowledged after acceptance. No pushed-commit,
remote monitor, recurring workload or larger product-task run is claimed.

Native scheduler checks verified Hermes CLI discovery under the task principal
and the idle launcher, both with result 0. The original `-Run` action was
restored and the task disabled after testing; both legacy cron jobs stayed
paused. Assigned-task execution was tested through the same launcher directly.

The bring-up also exposed the existing review helper's NEEDS_FIX/folder-status
validation mismatch. The operator normalized the corrected pilot-02 card back
to REVIEW before cancelling it. Automated return-for-fix dispatch is outside
this accepted normal-path test.

### GitHub Publication Validation

The isolated `codex/hermes-launcher-parity` publication branch is based on
`codex/phase14-runtime-adapter-01-source`, keeping unrelated `main` history
and local edits out of this change. Its focused suite passed all 21 tests;
Hermes task cards, delivery reports, reviews and other repository contracts
passed the existing validator. Full coordination validation retains nine
pre-existing missing-label errors in the unchanged
`coordination/reviews/review-phase14.5-05-external.md` from the base branch.
This differs from the successful original working-tree validation, where that
report already had unrelated local corrections. Those corrections are not
included in this Hermes publication.

### Recover An Interrupted Task

A provider failure can occur after activation acknowledges the delivery. Do
not reset that acknowledgement or activate a second task. If the original
task is still READY or IN_PROGRESS and has the same owner, explicitly recover its durable
payload:

```powershell
powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File integrations/hermes-coordination-worker/run-controlled-worker.ps1 -Run -ResumePayload a95589198a5074df
```

The sample ID belongs to the cancelled 2026-10-11 bring-up and must not be
reused. Use the failed run's actual payload ID. Recovery verifies the
worker, central project, payload ID, original card filename, task ID, status,
and owner before starting Hermes. It replaces activation with a read of the
existing inbox and skips claim when the card is already IN_PROGRESS. Missing,
misplaced, changed-owner, blocked, and submitted cards fail closed. Confirm the
previous process has stopped before recovery. This is operator-invoked, never
a scheduled retry; verify and correct partial evidence before submission.

## Windows Task Scheduler

The native task `Hermes Controlled Worker` follows the OpenCode wake-up
mechanism. It runs the launcher with `-Run` every ten minutes, rooted at
`D:\codex work`, under the same interactive principal as
`OpenCode Controlled Worker`. It is **Disabled** by default, ignores overlapping
starts, has no scheduler retries, and stops after fifteen minutes.

For an operator-authorized supervised wake-up:

```powershell
Enable-ScheduledTask -TaskName 'Hermes Controlled Worker'
Start-ScheduledTask -TaskName 'Hermes Controlled Worker'
Disable-ScheduledTask -TaskName 'Hermes Controlled Worker'
Get-ScheduledTaskInfo -TaskName 'Hermes Controlled Worker'
```

Disabling stops future wake-ups; it does not cancel the already running
instance. Use `Stop-ScheduledTask -TaskName 'Hermes Controlled Worker'` to
stop that instance. Never run the native task and Hermes cron concurrently.
Recurring polling still requires a separate operator decision.

## Skill Source

The reviewed source is `integrations/hermes-coordination-worker/SKILL.md`.
The launcher reads it directly and needs no installation. Legacy cron jobs
require a local `coordination-worker` skill link, installed only through the
approved global-resource-link plan. That link is absent from the current
Hermes home (`C:\Users\angel\AppData\Local\hermes\skills`); keep those jobs paused.

## Worker Registration

Register the pilot only for the central project:

```powershell
python scripts/orchestrate.py worker register hermes-coordination-pilot agent-coordination-system
```

## Cron Job

Create exactly one 10-minute job, rooted at this repository, with the local
skill attached:

```powershell
hermes cron create "every 10m" "Run the coordination-worker skill exactly once. If no eligible delivery exists, stop without changes. If one matching delivery exists, process only that task and stop after submitting it to review. Never use Kanban, accept, review, merge, commit, push, select unassigned work, or launch another agent." --name coordination-worker-pilot --skill coordination-worker --workdir "D:\codex work"
```

The legacy job is `d215f82b3e50`. It is currently **paused** after its
single supervised run `a5bffadecd284679968eac30f8248536` completed on
2026-08-02. That run consumed one owner-matching delivery, claimed
`phase14-hermes-pilot-01`, wrote its repository delivery report, and submitted
the task card to `review/`. The local Gateway was healthy for the run.

The additional legacy job `3cffd3c69ae7` is also paused. The native launcher
replaces their wake-up dependency for the current flow; do not resume either
legacy job without resolving the missing skill link and choosing one scheduler.

Before any further supervised run, an operator must explicitly resume this
job. A new no-side-effect task also needs an independent authorization for the
model data transfer; resuming the job alone must not be used to dispatch work.

## Safety And Recovery

- `worker activate` writes a durable inbox payload before acknowledging the
  delivery; it does not itself claim or execute a task.
- A task remains subject to the repository task packet and `allowed_scope`.
- Review acceptance remains an orchestrator decision.
- Pause a job with `hermes cron pause <job-id>`.
- Resume only for a supervised test with `hermes cron resume <job-id>`.
- Remove it with `hermes cron remove <job-id>`.
- Disable the native launcher with
  `Disable-ScheduledTask -TaskName 'Hermes Controlled Worker'`; remove its
  registration with `Unregister-ScheduledTask -TaskName 'Hermes Controlled Worker'`.
- Remove only the Hermes skill junction after verifying its target. Do not
  delete the source skill or alter task cards as part of rollback.
