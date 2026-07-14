param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$ScriptPath,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$python = "C:\Users\angel\AppData\Local\Programs\Python\Python312\python.exe"

if (-not (Test-Path $python)) {
    Write-Error "Python runtime not found at $python"
    exit 1
}

$repoRoot = Split-Path -Parent $PSScriptRoot
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
