function Get-CoordinationPython {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $candidates = @()
    if ($env:COORDINATION_PYTHON) {
        if (-not (Test-Path -LiteralPath $env:COORDINATION_PYTHON -PathType Leaf)) {
            throw 'COORDINATION_PYTHON must point to an existing Python executable.'
        }
        $candidates = @($env:COORDINATION_PYTHON)
    } else {
        $candidates += Join-Path $RepoRoot '.venv\Scripts\python.exe'
        foreach ($name in @('python', 'python3')) {
            $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue
            if ($command) { $candidates += $command.Source }
        }
    }
    foreach ($candidate in $candidates) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        $path = & $candidate -c 'import sys; assert sys.version_info >= (3,11); print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $path) { return [string]($path | Select-Object -Last 1) }
    }
    if (-not $env:COORDINATION_PYTHON) {
        $launcher = Get-Command py -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($launcher) {
            $path = & $launcher.Source -3 -c 'import sys; assert sys.version_info >= (3,11); print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $path) { return [string]($path | Select-Object -Last 1) }
        }
    }
    throw 'Python 3.11+ is required. Install it or set COORDINATION_PYTHON to its executable.'
}
