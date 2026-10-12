param([string]$Model, [string]$Prompt, [string]$TaskId, [string]$PayloadId)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$command = Get-Command hermes -CommandType Application -ErrorAction Stop
$python = Join-Path (Split-Path -Parent $command.Source) 'python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Hermes Python runtime is missing.' }
& $python (Join-Path $PSScriptRoot 'run_session.py') --model $Model --prompt $Prompt --task-id $TaskId --payload-id $PayloadId
exit $LASTEXITCODE
