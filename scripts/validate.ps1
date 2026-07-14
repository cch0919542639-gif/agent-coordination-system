$wrapper = Join-Path $PSScriptRoot "run_python.ps1"

if (-not (Test-Path $wrapper)) {
    Write-Error "Wrapper script not found: $wrapper"
    exit 1
}

& $wrapper "scripts/orchestrate.py" "validate" @args
$exitCode = $LASTEXITCODE
if ($null -eq $exitCode) {
    $exitCode = 0
}
exit $exitCode
