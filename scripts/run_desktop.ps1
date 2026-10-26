param(
    [switch]$SmokeTest
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$mainScript = Join-Path $repoRoot "apps\desktop\main.py"

if (-not (Test-Path -LiteralPath $mainScript)) {
    throw "Desktop entry not found: $mainScript"
}

$currentPython = (Get-Command python -ErrorAction SilentlyContinue).Source
$candidates = @()
if ($currentPython) {
    $candidates += $currentPython
}

$condaBase = (& conda info --base 2>$null | Select-Object -First 1)
if ($condaBase) {
    $basePython = Join-Path $condaBase "python.exe"
    if (Test-Path -LiteralPath $basePython) {
        $candidates += $basePython
    }
}

$desktopPython = $null
foreach ($candidate in ($candidates | Select-Object -Unique)) {
    $probeSucceeded = $false
    try {
        & $candidate -c "import PySide6" *> $null
        $probeSucceeded = ($LASTEXITCODE -eq 0)
    } catch {
        $probeSucceeded = $false
    }
    if ($probeSucceeded) {
        $desktopPython = $candidate
        break
    }
}

if (-not $desktopPython) {
    throw "No Python interpreter with PySide6 was found. Install it with: python -m pip install PySide6"
}

# The base Anaconda installation can otherwise load two OpenMP runtimes.
if (-not $env:KMP_DUPLICATE_LIB_OK) {
    $env:KMP_DUPLICATE_LIB_OK = "TRUE"
}
$env:PYTHONUTF8 = "1"
if ($SmokeTest) {
    $env:ODP_DESKTOP_SMOKE_TEST = "1"
}

Write-Host "Using desktop Python: $desktopPython"
& $desktopPython $mainScript
exit $LASTEXITCODE
