[CmdletBinding()]
param(
    [switch]$Run,
    [string]$Model = 'opencode/deepseek-v4-flash-free'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$env:XDG_CONFIG_HOME = Join-Path $repoRoot 'coordination\monitor\runtime\opencode'

if (-not $Run) {
    & opencode --version
    exit $LASTEXITCODE
}

$prompt = @'
You are the controlled OpenCode coordination worker.
Run exactly one activation: python scripts/orchestrate.py worker activate opencode-coordination-pilot --json.
If no owner-matching delivery is eligible, stop without changes.
If one payload is returned, verify its worker ID, read its task card and
docs/operations/agent-task-execution-protocol.md, and only then claim it.
Work only in that task card's allowed_scope. If blocked, create the required
incident and stop. Otherwise write delivery evidence, submit that one task to
review, and stop.
Never use Kanban; never process a second task; never accept, review, merge,
commit, push, select unassigned work, launch another agent, or enable automatic
tool approval.
'@

& opencode run --pure --dir $repoRoot --model $Model $prompt
exit $LASTEXITCODE
