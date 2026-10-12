[CmdletBinding()]
param(
    [switch]$Run,
    [string]$Model = 'openai/gpt-oss-20b',
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
        $recovery = "Authorized pre-activated handoff override for skill steps 1 and 2: activation already succeeded. Do not activate again. Read $inbox and continue ONLY task $($payload.task_id) from that durable handoff."
        $taskId = [string]$payload.task_id
        $payloadId = $ResumePayload
        if ($expectedState -eq 'IN_PROGRESS') {
            $recovery += " Override step 4: this task is already claimed at $cardPath; do not claim again. Read coordination/reviews/review-$taskId.md when it exists and fix its findings. Verify and correct any existing delivery evidence. Use the exact payload ID $ResumePayload; do not assume claim_task.py updated an existing progress file, and do not claim submission succeeded before verifying it. Record any provider failure as a residual risk. Then run validation and submit this task using submit_task.py."
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

    if (-not $ResumePayload) {
        $cards = @(Get-ChildItem -LiteralPath (Join-Path $repoRoot 'coordination/task-board/ready') -Filter '*.md' | Where-Object {
            (Get-Content -LiteralPath $_.FullName -Raw) -match ('(?m)^task_id: ' + [regex]::Escape($taskId) + '\r?$')
        })
        if ($cards.Count -ne 1) { throw 'Assigned task must have one READY packet.' }
        $card = Get-Content -LiteralPath $cards[0].FullName -Raw
        $header = [regex]::Match($card, '(?s)\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)').Groups[1].Value
        if ($header -notmatch '(?m)^owner: hermes-coordination-pilot\r?$' -or $header -notmatch '(?m)^status: READY\r?$') { throw 'Assigned packet owner or state mismatch.' }
    }
    $objective = [regex]::Match($card, '(?ms)^## Objective\r?\n(.*?)(?=^## |\z)').Groups[1].Value.Trim()
    if (-not $objective) { throw 'Assigned packet must state its Objective.' }
    $scope = [regex]::Match($header, '(?ms)^allowed_scope:\r?\n(.*?)(?=^[a-z_]+:|\z)').Groups[1].Value.Trim()
    if (-not $scope) { throw 'Assigned packet must state its allowed scope.' }
    $packetBrief = "Task objective (retain throughout execution):`n$objective`nAllowed file paths:`n$scope"
    $phaseId = [regex]::Match($header, '(?m)^phase: (.*?)\r?$').Groups[1].Value.Trim()
    $deliveryTemplate = (Get-Content -LiteralPath (Join-Path $repoRoot 'coordination/templates/delivery-report.md') -Raw).Replace('TASK-ID-HERE', $taskId).Replace('AGENT-NAME', 'hermes-coordination-pilot').Replace('PHASE-ID-HERE', $phaseId)

    $skill = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'SKILL.md') -Raw
    . (Join-Path $repoRoot 'scripts/resolve-python.ps1')
    $python = Get-CoordinationPython -RepoRoot $repoRoot
    $quotedPython = "'" + $python.Replace('\', '/').Replace("'", "'\''") + "'"
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
$quotedPython.
The terminal is Git Bash on Windows; use forward slashes and quote paths.
Read AGENTS.md, PLAN.md and PROGRESS.md before material work. Preserve existing edits.
Use claim_task.py and submit_task.py for lifecycle changes. Run the repository
validator before submission and fix its findings. Format delivery evidence
using coordination/templates/delivery-report.md. Do not read credentials or session transcripts.
Helper syntax: claim_task.py --task-id $taskId --agent hermes-coordination-pilot;
submit_task.py --task-id $taskId --agent hermes-coordination-pilot --payload-id $payloadId --summary 'short truthful execution summary' --artifact 'your actual scoped output path';
orchestrate.py validate. These scripts live under scripts/ in this repository.
After completing the artifact, use the submit helper's --summary and --artifact
mode. It verifies the ACK, owner, artifact existence/scope/hash, produces the
canonical report, runs validation and submits in one invocation. You need not manually
write Markdown delivery fields. Never claim successful submission before this
helper exits zero and the actual REVIEW receipt exists.
Never enable automatic tool approval, --yolo, or --oneshot.
Groq's observed allowance is 8000 tokens per minute. Keep requests small and terminal
output concise (at most 2500 characters per call), and tool-call scripts short
(at most 150 words; split longer scripts across calls). Read only relevant sections
of large context files, and batch required reads. After reading the task
and protocol, batch its safe coordination-only claim, short delivery report,
validation and submission when applicable. A pilot report needs at most 250
words. Do not print unrelated file inventories or git diffs. Use Python's
standard library through terminal for file reads and writes.
The report's Status must be exactly DELIVERED. Write a long report in separate
short calls (header, then append sections); do not truncate a Python string.
Update your progress file explicitly: claim_task.py may preserve an existing
file from a previous task. Use subprocess.run([...], check=True) for helpers,
with the quoted Python executable as the first argument.

$packetBrief

Required delivery format (preserve these literal labels and all sections):
$deliveryTemplate

$skill

$recovery
"@
    & (Join-Path $PSScriptRoot 'run-session.ps1') -Model $Model -Prompt $prompt -TaskId $taskId -PayloadId $payloadId
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
