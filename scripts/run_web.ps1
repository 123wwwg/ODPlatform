param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$webRoot = Join-Path $repoRoot "apps\web-backend"

$candidates = @()
$odpLine = (& conda env list 2>$null | Where-Object { $_ -match "^\s*ODP\s+" } | Select-Object -First 1)
if ($odpLine -match "([A-Za-z]:\\.+?)\s*$") {
    $odpRoot = $Matches[1].Trim()
    $odpPython = Join-Path $odpRoot "python.exe"
    if (Test-Path -LiteralPath $odpPython) {
        $candidates += $odpPython
    }
}

$currentPython = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($currentPython) {
    $candidates += $currentPython
}

$python = $null
foreach ($candidate in ($candidates | Select-Object -Unique)) {
    $probeSucceeded = $false
    try {
        & $candidate -c "import django, rest_framework, corsheaders" *> $null
        $probeSucceeded = ($LASTEXITCODE -eq 0)
    } catch {
        $probeSucceeded = $false
    }
    if ($probeSucceeded) {
        $python = $candidate
        break
    }
}

if (-not $python) {
    throw 'No Python interpreter with Django dependencies was found. Activate ODP and run: python -m pip install -r ".\apps\web-backend\requirements.txt"'
}

Push-Location $webRoot
try {
    $env:PYTHONUTF8 = "1"
    Write-Host "Using web Python: $python"
    & $python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) {
        throw "Database migration failed."
    }

    Write-Host "ODPlatform Web: http://127.0.0.1:$Port/"
    Write-Host "Django Admin:  http://127.0.0.1:$Port/admin/"
    & $python manage.py runserver "127.0.0.1:$Port" --noreload
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
