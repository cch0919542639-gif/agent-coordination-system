param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$ScriptPath,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$repoRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'resolve-python.ps1')
$python = Get-CoordinationPython -RepoRoot $repoRoot
$resolvedScript = if ([System.IO.Path]::IsPathRooted($ScriptPath)) {
    $ScriptPath
} else {
    Join-Path $repoRoot $ScriptPath
}

if (-not (Test-Path $resolvedScript)) {
    Write-Error "Script not found: $resolvedScript"
    exit 1
}

& $python $resolvedScript @ScriptArgs
$exitCode = $LASTEXITCODE
if ($null -eq $exitCode) {
    $exitCode = 0
}
exit $exitCode
