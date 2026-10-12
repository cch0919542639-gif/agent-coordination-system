[CmdletBinding()]
param(
    [switch]$Run,
    [string]$Model = 'opencode/space-bunny-free',
    [ValidatePattern('^[a-f0-9]{16}$')]
    [string]$ResumePayload
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$env:XDG_CONFIG_HOME = Join-Path $repoRoot 'coordination\monitor\runtime\opencode'

# npm's copied shim can be invalid while its installed Windows binary works.
$command = Get-Command opencode -ErrorAction Stop
$native = Join-Path (Split-Path -Parent $command.Source) 'node_modules\opencode-ai\node_modules\opencode-windows-x64\bin\opencode.exe'
$executable = if (Test-Path -LiteralPath $native -PathType Leaf) { $native } else { $command.Source }

if (-not $Run) {
    if ($ResumePayload) { throw '-ResumePayload requires -Run.' }
    & $executable --version
    exit $LASTEXITCODE
}

$handoff = 'Run exactly one activation: python scripts/orchestrate.py worker activate opencode-coordination-pilot --json.'
if ($ResumePayload) {
    $inbox = Join-Path $repoRoot "coordination\monitor\inbox\opencode-coordination-pilot\$ResumePayload.json"
    $payload = Get-Content -LiteralPath $inbox -Raw | ConvertFrom-Json
    if ($payload.worker_id -ne 'opencode-coordination-pilot' -or
        $payload.project_id -ne 'agent-coordination-system' -or
        $payload.payload_id -ne $ResumePayload -or
        $payload.task_id -notmatch '^[a-zA-Z0-9._-]+$' -or
        $payload.task_card_path -notmatch '^coordination/task-board/ready/[^/\\]+\.md$') {
        throw 'Handoff does not match this worker and repository.'
    }
    $cardPath = Join-Path $repoRoot $payload.task_card_path
    $state = 'READY'
    if (-not (Test-Path -LiteralPath $cardPath -PathType Leaf)) {
        $cardPath = Join-Path $repoRoot ($payload.task_card_path -replace '/ready/', '/in_progress/')
        $state = 'IN_PROGRESS'
    }
    $card = Get-Content -LiteralPath $cardPath -Raw
    $header = [regex]::Match($card, '(?s)\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)').Groups[1].Value
    if ($header -notmatch ('(?m)^status: ' + $state + '\r?$') -or
        $header -notmatch '(?m)^owner: opencode-coordination-pilot\r?$' -or
        $header -notmatch ('(?m)^task_id: ' + [regex]::Escape($payload.task_id) + '\r?$')) {
        throw 'Handoff requires the exact READY or IN_PROGRESS task owned by this worker.'
    }
    & (Join-Path $repoRoot 'scripts\run_python.ps1') scripts/verify_worker_handoff.py --task-id $payload.task_id --owner opencode-coordination-pilot --payload-id $ResumePayload
    if ($LASTEXITCODE -ne 0) { throw 'Handoff acknowledgement could not be verified.' }
    $handoff = "Activation already succeeded. Read $inbox and $cardPath. Process ONLY task $($payload.task_id) with acknowledged payload $ResumePayload. Never activate again."
    if ($state -eq 'IN_PROGRESS') {
        $handoff += " This is an authorized repair of the same claimed task. Do not claim again. Read coordination/reviews/review-$($payload.task_id).md and correct its findings before resubmitting."
    }
}

. (Join-Path $repoRoot 'scripts/resolve-python.ps1')
$python = Get-CoordinationPython -RepoRoot $repoRoot
$quotedPython = "'" + $python.Replace('\', '/').Replace("'", "'\''") + "'"
$prompt = @"
You are the controlled OpenCode coordination worker.
$handoff
If no owner-matching delivery is eligible, stop without changes.
If one payload is returned, verify its worker ID, read its task card and
docs/operations/agent-task-execution-protocol.md, and only then claim it.
Read AGENTS.md, PLAN.md and PROGRESS.md before material work. Preserve existing edits.
The terminal is Git Bash on Windows. Use the quoted Python executable
$quotedPython for lifecycle commands.
Use claim_task.py and submit_task.py; format reports with coordination/templates/delivery-report.md.
If a task is already IN_PROGRESS, skip claim and only repair that task.
Work only in that task card's allowed_scope. If blocked, create the required
incident and stop. Otherwise write delivery evidence, submit that one task to
review, verify the card actually reached review/, and stop immediately.
Keep tool output concise and reports at most 250 words. Never read credentials or private transcripts.
Never use Kanban; never process a second task; never accept, review, merge,
commit, push, select unassigned work, launch another agent, or enable automatic
tool approval.
"@

& $executable run --pure --dir $repoRoot --model $Model $prompt
exit $LASTEXITCODE
