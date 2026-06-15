<#
.SYNOPSIS
Resume the gated PaddleOCR recognizer fine-tune on the Windows A100 host.

.DESCRIPTION
This script is intentionally conservative: it starts the A100 fine-tune only
when both the domain train labels and a general Korean train label file are
present. That guard prevents the domain-only catastrophic forgetting pattern
observed in the earlier failed recognizer experiment.
#>

$ErrorActionPreference = "Stop"

$WorkspaceRoot = "G:\lemon-aid\paddleocr_rec_work"
$RunSuffix = "v2_low_lr_mix_20260610"
$DatasetVersion = "v2"

$DomainTrainLabel = Join-Path $WorkspaceRoot "rec_dataset\$DatasetVersion\rec\rec_gt_train.txt"
$GeneralTrainLabelCandidates = @(
    (Join-Path $WorkspaceRoot "rec_dataset\general_korean\rec\rec_gt_train.txt"),
    (Join-Path $WorkspaceRoot "rec_dataset\paddleocr_general_korean\rec\rec_gt_train.txt"),
    (Join-Path $WorkspaceRoot "rec_dataset\public_korean\rec\rec_gt_train.txt")
)

$GeneralTrainLabel = $GeneralTrainLabelCandidates |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Select-Object -First 1

if (-not (Test-Path -LiteralPath $DomainTrainLabel -PathType Leaf)) {
    throw "Domain train label file is missing. Run the v2 dataset materialization step first."
}
if ([string]::IsNullOrWhiteSpace($GeneralTrainLabel)) {
    throw "General Korean train label file is missing. Prepare a general corpus before running fine-tune."
}

function Get-TextLineCount {
    param([string]$Path)

    $count = 0
    $reader = [System.IO.File]::OpenText($Path)
    try {
        while ($null -ne $reader.ReadLine()) {
            $count += 1
        }
    }
    finally {
        $reader.Dispose()
    }
    return $count
}

$RepoRoot = Join-Path $WorkspaceRoot "Lemon-Aid"
$RunScript = Join-Path $RepoRoot "backend\scripts\run_a100_paddleocr_windows_training.ps1"
$BackgroundScript = Join-Path $RepoRoot "backend\scripts\start_a100_paddleocr_windows_background.ps1"

& powershell -NoProfile -ExecutionPolicy Bypass -File $RunScript `
    -Mode dataset `
    -DatasetVersion $DatasetVersion `
    -RunSuffix $RunSuffix `
    -LearningRate 0.0001 `
    -BatchSize 128 `
    -DisableRecConAug

$MixedTrainLabels = "$DomainTrainLabel;$GeneralTrainLabel"
$DomainLineCount = Get-TextLineCount -Path $DomainTrainLabel
$GeneralLineCount = Get-TextLineCount -Path $GeneralTrainLabel
if ($GeneralLineCount -le 0) {
    throw "General Korean train label file is empty."
}
$GeneralRatio = [Math]::Round([Math]::Min(1.0, $DomainLineCount / $GeneralLineCount), 4)
$TrainRatioList = "[1.0,$GeneralRatio]"

& powershell -NoProfile -ExecutionPolicy Bypass -File $BackgroundScript `
    -Mode full `
    -DatasetVersion $DatasetVersion `
    -RunSuffix $RunSuffix `
    -Epochs 100 `
    -BatchSize 128 `
    -LearningRate 0.0001 `
    -MixedTrainLabelFiles $MixedTrainLabels `
    -TrainRatioList $TrainRatioList `
    -RequireMixedTraining `
    -DisableRecConAug

Write-Host "Submitted PaddleOCR recognizer fine-tune run_suffix=$RunSuffix"
Write-Host "Train ratio list: $TrainRatioList"
Write-Host "Combined log: $WorkspaceRoot\full.$RunSuffix.combined.log"
