[CmdletBinding()]
param(
    [switch]$Run,
    [string]$Model = 'qwen/qwen3.8-27b',
    [ValidatePattern('^[a-f0-9]{16}$')]
    [string]$ResumePayload
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

if (-not $Run) {
    if ($ResumePayload) { throw '-ResumePayload requires -Run.' }
    & hermes --version
    exit $LASTEXITCODE
}

Push-Location $repoRoot
try {
    $recovery = ''
    if ($ResumePayload) {
        $inbox = Join-Path $repoRoot "coordination\monitor\inbox\hermes-coordination-pilot\$ResumePayload.json"
        $payload = Get-Content -LiteralPath $inbox -Raw | ConvertFrom-Json
        if ($payload.worker_id -ne 'hermes-coordination-pilot' -or
            $payload.project_id -ne 'agent-coordination-system' -or
            $payload.payload_id -ne $ResumePayload -or
            $payload.task_id -notmatch '^[a-zA-Z0-9._-]+$' -or
            $payload.task_card_path -notmatch '^coordination/task-board/ready/[^/\\]+\.md$') {
            throw 'Recovery payload does not match this worker and repository.'
        }
        $cardPath = Join-Path $repoRoot $payload.task_card_path
        $expectedState = 'READY'
        if (-not (Test-Path -LiteralPath $cardPath -PathType Leaf)) {
            $cardPath = Join-Path $repoRoot ($payload.task_card_path -replace '/ready/', '/in_progress/')
            $expectedState = 'IN_PROGRESS'
        }
        $card = Get-Content -LiteralPath $cardPath -Raw
        $header = [regex]::Match($card, '(?s)\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)').Groups[1].Value
        if ($header -notmatch ('(?m)^status: ' + $expectedState + '\r?$') -or
            $header -notmatch '(?m)^owner: hermes-coordination-pilot\r?$' -or
            $header -notmatch ('(?m)^task_id: ' + [regex]::Escape($payload.task_id) + '\r?$')) {
            throw 'Recovery requires the original READY or IN_PROGRESS task with matching owner.'
        }
        $recovery = "Operator recovery override for skill steps 1 and 2: activation already succeeded. Do not activate again. Read $inbox and continue ONLY task $($payload.task_id) from that durable handoff."
        $taskId = [string]$payload.task_id
        $payloadId = $ResumePayload
        if ($expectedState -eq 'IN_PROGRESS') {
            $recovery += " Override step 4: this task is already claimed at $cardPath; do not claim again. Verify and correct any existing delivery evidence. Use the exact payload ID $ResumePayload; do not assume claim_task.py updated an existing progress file, and do not claim submission succeeded before verifying it. Record any provider failure as a residual risk. Then run validation and submit this task using submit_task.py."
        }
    } else {
        # Poll without acknowledging: an idle wake-up needs no model call.
        $poll = & (Join-Path $repoRoot 'scripts\run_python.ps1') scripts/orchestrate.py worker poll hermes-coordination-pilot --json
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        $pending = ($poll | Out-String | ConvertFrom-Json)
        if ($pending.worker_id -ne 'hermes-coordination-pilot') {
            throw 'Unexpected worker in polling result.'
        }
        if (@($pending.notifications).Count -eq 0) {
            Write-Output 'No eligible delivery for hermes-coordination-pilot.'
            exit 0
        }
        $selected = @($pending.notifications)[0]
        $taskId = [string]$selected.task_id
        $payloadId = [string]$selected.payload_id
        if ($selected.project_id -ne 'agent-coordination-system' -or
            $taskId -notmatch '^[a-zA-Z0-9._-]+$' -or $payloadId -notmatch '^[a-f0-9]{16}$') {
            throw 'Unexpected project, task or payload identifier in polling result.'
        }
    }

    $skill = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'SKILL.md') -Raw
    $prompt = @"
You are the controlled Hermes coordination worker. Execute the following
repository skill exactly once, then stop. This operator-authorized invocation
may use the configured model provider for this assigned task only.
The expected task is $taskId and payload is $payloadId; reject any other handoff.
Only terminal and process tools are available. Read and write files through
Python's standard library in terminal; do not call other tool names.
Use the current repository at $repoRoot; do not pull or change branches.
Set workdir='$($repoRoot.Replace('\', '/'))' on every terminal call.
For Python commands use the quoted executable
'C:/Users/angel/AppData/Local/Programs/Python/Python312/python.exe'.
The terminal is Git Bash on Windows; use forward slashes and quote paths.
Read AGENTS.md, PLAN.md and PROGRESS.md before material work. Preserve existing edits.
Use claim_task.py and submit_task.py for lifecycle changes. Run the repository
validator before submission and fix its findings. Format delivery evidence
using coordination/templates/delivery-report.md. Do not read credentials or session transcripts.
Never enable automatic tool approval, --yolo, or --oneshot.
Groq's observed allowance is 8000 tokens per minute. Keep requests small and terminal
output concise (at most 2500 characters per call), read only relevant sections
of large context files, and batch required reads. After reading the task
and protocol, batch its safe coordination-only claim, short delivery report,
validation and submission when applicable. A pilot report needs at most 250
words. Do not print unrelated file inventories or git diffs. Use Python's
standard library through terminal for file reads and writes.

$skill

$recovery
"@
    & (Join-Path $PSScriptRoot 'run-session.ps1') -Model $Model -Prompt $prompt -TaskId $taskId -PayloadId $payloadId
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
