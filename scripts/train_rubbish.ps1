param(
    [int]$Epochs = 1,
    [int]$ImageSize = 416,
    [string]$Device = "cpu",
    [string]$Batch = "16",
    [switch]$SkipTransform,
    [switch]$SkipValidate,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$datasetName = "Rubbish_data_set"
$classes = 0..9 | ForEach-Object { "class_$_" }

$candidates = @()
$odpLine = (& conda env list 2>$null | Where-Object { $_ -match "^\s*ODP\s+" } | Select-Object -First 1)
if ($odpLine -match "([A-Za-z]:\\.+?)\s*$") {
    $odpPython = Join-Path $Matches[1].Trim() "python.exe"
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
        & $candidate -c "import od_platform, ultralytics, torch" *> $null
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
    throw "No Python interpreter with ODPlatform training dependencies was found. Activate ODP first."
}

$env:PYTHONUTF8 = "1"
Push-Location $repoRoot
try {
    if ($DryRun) {
        Write-Host "Using Python: $python"
        Write-Host "Dataset: $datasetName"
        Write-Host "Epochs: $Epochs ImageSize: $ImageSize Batch: $Batch Device: $Device"
        exit 0
    }

    if (-not $SkipTransform) {
        Write-Host "Transforming and freezing dataset $datasetName ..."
        & $python -m od_platform.cli.transform_data `
            --dataset $datasetName `
            --format yolo `
            --task detect `
            --classes @classes `
            --train-rate 0.8 `
            --val-rate 0.1 `
            --seed 42 `
            --split-strategy stratified_multilabel
        if ($LASTEXITCODE -ne 0) {
            throw "Dataset transformation failed."
        }
    }

    if (-not $SkipValidate) {
        Write-Host "Validating dataset ..."
        & $python -m od_platform.cli.validate_data `
            "apps\platform\configs\datasets\$datasetName.yaml"
        if ($LASTEXITCODE -ne 0) {
            throw "Dataset validation failed. Training stopped."
        }
    }

    Write-Host "Starting training: epochs=$Epochs imgsz=$ImageSize batch=$Batch device=$Device"
    & $python -m od_platform.cli.train_model `
        --config train `
        --data $datasetName `
        --model "models\pretrained\yolov8n.pt" `
        --epochs $Epochs `
        --batch $Batch `
        --imgsz $ImageSize `
        --device $Device `
        --experiment-name "rubbish_yolov8n"
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
