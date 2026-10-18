[CmdletBinding()]
param([switch]$Run, [ValidatePattern('^[a-f0-9]{16}$')][string]$ResumePayload)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$repoRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if (-not $Run) { Write-Output 'Preview only; no model or task launched.'; exit 0 }
if (-not $ResumePayload) { throw 'An exact controller-acknowledged payload is required.' }
Push-Location $repoRoot
try {
    & (Join-Path $repoRoot 'scripts/run_python.ps1') scripts/structured_agent_worker.py --runtime reasonix --payload-id $ResumePayload
    exit $LASTEXITCODE
} finally { Pop-Location }
