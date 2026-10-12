# Local Agent Completion Loop

## Contract

Codex defines the task packets, owners, dependencies and independent acceptance
checks. The local controller then runs a finite serial chain:

```text
exact task dispatch -> acknowledged durable inbox -> OpenCode or Hermes
  -> worker claim / implementation / delivery report / REVIEW submission
  -> controller checks receipt, scope, format and pinned acceptance checks
     -> accepted DONE -> dispatch the next dependency-ready task
     -> needs_fix -> same-task repair -> recheck (bounded attempts)
  -> every listed task accepted -> completion report -> exit
```

The repository task board remains authoritative. Workers cannot review,
accept, dispatch another task, merge or push. The controller is the delegated
Codex control plane; it does not open or message another Codex chat. It accepts
only tasks assigned to `LOCAL_LOOP` with an explicit machine-checkable review
contract. Qualitative review, unrelated historical tasks and unlisted work
retain their designated reviewer. No GitHub push is needed for this local loop.

## Prerequisites

- Windows checkout with Git, PowerShell and Python 3.11+ (verified on 3.12).
- The Python wrapper resolves `COORDINATION_PYTHON`, the checkout's `.venv`,
  then PATH/Windows Python launcher. Worker prompts use that resolved path.
- Installed OpenCode and Hermes with their existing working providers.
- Central project registration must point to this exact checkout.
- Workers `opencode-coordination-pilot` and `hermes-coordination-pilot` must be
  enabled for `agent-coordination-system`; ready routes go to registered workers
  and review routes to the orchestrator.
- Keep both native worker schedules disabled and both legacy Hermes jobs paused
  while a controller run owns worker execution. Do not launch another worker
  manually against the same task.
- Reserve this checkout during a run: concurrent unrelated writes can cause a
  conservative terminal scope failure and require investigation. Use an isolated
  checkout with matching local registration when concurrent work is needed.

OpenCode's npm shim on this host is not a valid executable. Its launcher uses
the already-installed `opencode-windows-x64/bin/opencode.exe` (verified version
1.18.35), without modifying the global installation. Hermes uses the bounded
installed AIAgent runner verified on v0.19.1 and worker-local Groq `openai/gpt-oss-20b`.
Desktop configuration is unchanged. The OpenCode worker default is now
`opencode/space-bunny-free`: the earlier DeepSeek free ID was absent from the
native model catalog, while a no-tools probe of the replacement succeeded.
The [Zen model catalog](https://opencode.ai/docs/zen/) lists it as temporarily
free with zero-retention processing. Model availability and quotas remain provider
constraints, not completion evidence.

## Plan And Task Packets

Use `coordination/plans/local-agent-loop-pilot-v5.json` as historical completed
evidence. Replay requires its original local runtime state and ACKs; a fresh
clone cannot replay that history because machine state is intentionally ignored.
Follow [fresh-download setup](github-download-verification.md) to create new
registrations, tasks and receipts. For new work, Codex creates scoped READY cards
and a plan with fresh task/run IDs; do not reset demonstration receipts. A plan
contains `version: 1`, a unique `run_id`, and an explicit finite list of tasks.
Each entry declares `task_id`, one supported `owner`, and nonempty `checks`.
Dependencies are read from the authoritative task cards, and must reach DONE
with matching accepted review/report evidence before a dependent task launches.

For each listed card:

- Set `reviewer: LOCAL_LOOP` and `execution_mode: REPO_FIRST`.
- Declare exact allowed write paths and a required `delivery_report`.
- Explain the intended artifact and acceptance checks in the packet.
- Set `local_loop_checks_sha256` to `local_agent_loop.digest(checks)`. This
  binds the card to the exact plan checks; the worker cannot substitute them.

Two check forms are supported:

```json
{"path":"coordination/evidence/example/result.json","json_equals":{"value":21}}
```

```json
{"command":["$PYTHON","tests/check_example_result.py"]}
```

JSON outputs must be within worker scope. Command checks use explicit Python
argv without a shell; their reviewer-owned script must exist outside every
worker-write scope and is pinned by hash. The task contract, plan identity and
checker hashes persist across resume. Check scripts must implement the actual
acceptance criteria; report claims or structural validation alone never justify
automatic acceptance.

## Run

Preview the exact plan first; default mode launches nothing and creates no
runtime state:

```powershell
.\scripts\run_python.ps1 scripts/orchestrate.py local-loop --plan coordination/plans/local-agent-loop-pilot-v5.json
```

Execute that finite plan:

```powershell
.\scripts\run_python.ps1 scripts/orchestrate.py local-loop --plan coordination/plans/local-agent-loop-pilot-v5.json --run
```

The `--run` invocation authorizes only this plan's bounded worker calls and
deterministic reviews. Default limits are two attempts per task, fifteen
minutes per worker, one minute per review-check batch and one hour per run.
The controller scans only listed tasks; it does not drain the global queue.
Exact `worker activate --task-id` selection preserves unrelated deliveries.
The controller supplies the resulting acknowledged inbox to the worker using
`-ResumePayload`, including the first pre-activated session. Repair reuses that
same task's acknowledgement; no delivery is reset or duplicate task activated.

## Evidence And Stop Conditions

Worker output stays in its allowed artifact, delivery and progress files.
Controller stdout contains compact event metadata rather than model/tool
transcripts. Runtime evidence lives under:

```text
coordination/monitor/local-loop/<run_id>/state.json
coordination/monitor/local-loop/<run_id>/events.jsonl
coordination/monitor/local-loop/<run_id>/summary.md
```

The state stores attempt counts, exact payload IDs, pinned contracts, worker
PID and clean exit evidence. The event journal records automatic dispatch,
review, repair and completion. Failed-attempt reviews are retained separately
before the current review report is replaced. The controller acknowledges each
processed review notification, including needs_fix; this records consumption
and does not turn a failed check into acceptance. Successful completion requires
every listed card in DONE, the exact worker/report/reviewer identities, matching
handoffs and passing independent checks. Repeating a completed run rechecks
evidence and invokes no worker.

Provider failure, missing receipt, unexpected ownership, scope changes,
blocked dependencies or exhausted limits stop the run with exit 1. Git-visible
file fingerprints catch changes outside allowed scope while preserving
pre-existing edits. Ignored files, embedded repositories and unreadable files
are not an operating-system sandbox; task rules and worker command approval
remain necessary boundaries. A detected scope breach is terminal for the run.

## Resume And Recovery

After a recorded stopped worker, resume the identical plan explicitly:

```powershell
.\scripts\run_python.ps1 scripts/orchestrate.py local-loop --plan coordination/plans/local-agent-loop-pilot-v5.json --run --resume
```

Completed tasks do not replay. An existing IN_PROGRESS task is repaired from
its durable handoff and skips claim. A REVIEW task is not adopted without a
clean recorded exit, preserved scope and matching contract. No acknowledgement
is reset, and a changed plan cannot reuse a run ID.

Ctrl+C terminates the controller's owned worker/check process tree and prevents
future launches. If the controller was forcibly killed during a launch, it
refuses resume while a worker is alive or a clean process-tree exit cannot be
established. Investigate and stop the exact orphaned process before operator
recovery; a dead PowerShell parent alone does not prove its children stopped.
Do not remove state or reset delivery records to conceal a failed attempt.

## Demonstration

The accepted chain is OpenCode v2-01 -> Hermes v5-02 -> OpenCode v5-03.
OpenCode v2-01 deliberately submitted value6, received needs_fix, and repaired
it to7 automatically using the same ACK. Earlier Hermes plans failed on
compaction, rate limits or incomplete delivery and remain cancelled with
unchanged receipts. V5 depends on that already accepted v2 OpenCode result.

V5 Hermes attempt1 produced21 but hit daily quota and was stopped without
acceptance. Its explicitly resumed second attempt used GPT-OSS20B and the
structured submission helper. After its real REVIEW receipt, scope and JSON
checks passed, the controller accepted it and automatically dispatched OpenCode.
OpenCode wrote the final completed artifact and was accepted. The run completed
at2026-10-12 02:43:51 Asia/Taipei. Replay at02:44:59 launched zero workers.
This demonstrates completion after bounded recovery, not an uninterrupted first
attempt. The focused90-test suite passed; independent qualitative review is
recorded separately from deterministic LOCAL_LOOP acceptance.

See `coordination/evidence/local-loop-pilot-v5/run-summary.json`, sanitized
`run-events.jsonl`, `v2-opencode-automatic-repair-review.md`, worker delivery/review
reports and the governing `phase14-local-loop-01` delivery report.
The independent assessment and explicit resolutions are in `independent-review.md`
and `review-resolution.md` in the same evidence directory.
Publication and fresh GitHub verification are recorded in
`coordination/delivery/phase14-loop-publication-01-delivery-report.md`.
Cross-machine synchronization and continuous unbounded scheduling remain outside
this local finite task-chain contract.
