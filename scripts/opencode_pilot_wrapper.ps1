param([string]$RuntimePath)

$runtimeDigest = 'b53b698473bfa46e09487e485a7f1ad5b4881f8a8b319d3619aa251f3be8ae10'
try {
    if (-not $RuntimePath.EndsWith('.cmd', [StringComparison]::OrdinalIgnoreCase) -or
        (Get-FileHash -LiteralPath $RuntimePath -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant() -ne $runtimeDigest) { exit 126 }
} catch { exit 126 }
& $RuntimePath @args
exit $LASTEXITCODE
