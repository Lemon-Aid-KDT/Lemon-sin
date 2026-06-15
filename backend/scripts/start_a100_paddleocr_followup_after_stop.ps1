<#
.SYNOPSIS
Wait for one A100 PaddleOCR run to stop, then export and launch a follow-up.

.DESCRIPTION
This Windows-side operator waits until the source PaddleOCR recognizer training
process for a run suffix is no longer present. It then exports the source
``best_accuracy`` checkpoint and launches a new lower-LR experiment from the
source best weights via ``Global.pretrained_model``. Using pretrained weights
instead of ``Global.checkpoints`` intentionally avoids carrying over optimizer
and scheduler state when the follow-up experiment changes learning rate.

The script only reads count metadata and model checkpoint files. It does not
print or persist raw OCR text, provider payloads, private image bytes, or label
content.

Official references:
- https://www.paddleocr.ai/latest/en/version2.x/ppocr/model_train/recognition.html
- https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html
#>

param(
    [string]$WorkspaceRoot = "G:\lemon-aid\paddleocr_rec_work",
    [string]$DatasetVersion = "v2",
    [string]$SourceRunSuffix = "v2_low_lr_mix_20260610_stage3",
    [string]$NewRunSuffix = "v2_low_lr_mix_20260610_stage4_lr5e5_from_stage3_best",
    [int]$BatchSize = 128,
    [int]$Epochs = 100,
    [double]$LearningRate = 0.00005,
    [ValidateRange(10, 3600)]
    [int]$PollSeconds = 120,
    [ValidateRange(1, 168)]
    [int]$TimeoutHours = 48,
    [switch]$SkipSourceExport
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($SourceRunSuffix)) {
    throw "SourceRunSuffix is required."
}
if ([string]::IsNullOrWhiteSpace($NewRunSuffix)) {
    throw "NewRunSuffix is required."
}
if ($SourceRunSuffix -eq $NewRunSuffix) {
    throw "SourceRunSuffix and NewRunSuffix must be different."
}

$repoRoot = Join-Path $WorkspaceRoot "Lemon-Aid"
$paddleRoot = Join-Path $WorkspaceRoot "PaddleOCR"
$runScript = Join-Path $repoRoot "backend\scripts\run_a100_paddleocr_windows_training.ps1"
$backgroundScript = Join-Path $repoRoot "backend\scripts\start_a100_paddleocr_windows_background.ps1"
$statusPath = Join-Path $WorkspaceRoot "followup.$SourceRunSuffix.to.$NewRunSuffix.status.json"
$sourceOutputName = "supplement_rec_crawling_$SourceRunSuffix"
$sourceBestRelativePrefix = "output\supplement_rec_crawling_$SourceRunSuffix\best_accuracy"
$sourceBestParams = Join-Path $paddleRoot "$sourceBestRelativePrefix.pdparams"
$domainTrainLabel = Join-Path $WorkspaceRoot "rec_dataset\$DatasetVersion\rec\rec_gt_train.txt"
$generalTrainLabelCandidates = @(
    (Join-Path $WorkspaceRoot "rec_dataset\general_korean\rec\rec_gt_train.txt"),
    (Join-Path $WorkspaceRoot "rec_dataset\paddleocr_general_korean\rec\rec_gt_train.txt"),
    (Join-Path $WorkspaceRoot "rec_dataset\public_korean\rec\rec_gt_train.txt")
)

function Write-Status {
    param([hashtable]$Payload)

    $Payload["checked_at"] = (Get-Date).ToString("o")
    $Payload["source_run_suffix"] = $SourceRunSuffix
    $Payload["new_run_suffix"] = $NewRunSuffix
    $Payload["status_path"] = $statusPath
    $Payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
    $Payload | ConvertTo-Json -Depth 6
}

function Get-MatchingTrainingProcesses {
    param([string]$RunSuffix)

    $outputNamePattern = [regex]::Escape("supplement_rec_crawling_$RunSuffix")
    Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        $_.CommandLine -match "\\.venv-paddle-rec-v2-clean\\Scripts\\python\.exe" -and
        $_.CommandLine -match "tools\\train\.py" -and
        $_.CommandLine -match $outputNamePattern
    }
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

function Resolve-GeneralTrainLabel {
    foreach ($candidate in $generalTrainLabelCandidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }
    throw "General Korean train label file is missing."
}

function Resolve-TrainRatioList {
    param(
        [string]$DomainLabelPath,
        [string]$GeneralLabelPath
    )

    $domainLineCount = Get-TextLineCount -Path $DomainLabelPath
    $generalLineCount = Get-TextLineCount -Path $GeneralLabelPath
    if ($domainLineCount -le 0) {
        throw "Domain train label file is empty."
    }
    if ($generalLineCount -le 0) {
        throw "General train label file is empty."
    }

    $generalRatio = [Math]::Round([Math]::Min(1.0, $domainLineCount / $generalLineCount), 4)
    return "[1.0,$generalRatio]"
}

function Assert-RequiredFiles {
    if (-not (Test-Path -LiteralPath $runScript -PathType Leaf)) {
        throw "A100 run script is missing."
    }
    if (-not (Test-Path -LiteralPath $backgroundScript -PathType Leaf)) {
        throw "A100 background script is missing."
    }
    if (-not (Test-Path -LiteralPath $sourceBestParams -PathType Leaf)) {
        throw "Source best checkpoint parameters are missing."
    }
    if (-not (Test-Path -LiteralPath $domainTrainLabel -PathType Leaf)) {
        throw "Domain train label file is missing."
    }
}

Assert-RequiredFiles

$deadline = (Get-Date).AddHours($TimeoutHours)
Write-Status -Payload @{
    status = "waiting_for_source_run_to_stop"
    source_output_name = $sourceOutputName
    poll_seconds = $PollSeconds
    timeout_hours = $TimeoutHours
}

while ($true) {
    $matches = @(Get-MatchingTrainingProcesses -RunSuffix $SourceRunSuffix)
    if ($matches.Count -eq 0) {
        break
    }
    if ((Get-Date) -gt $deadline) {
        throw "Timed out waiting for source run to stop."
    }
    Write-Status -Payload @{
        status = "waiting_for_source_run_to_stop"
        matched_process_count = $matches.Count
        matched_pids = @($matches | ForEach-Object { $_.ProcessId })
        poll_seconds = $PollSeconds
        timeout_hours = $TimeoutHours
    }
    Start-Sleep -Seconds $PollSeconds
}

if (-not $SkipSourceExport) {
    Write-Status -Payload @{
        status = "exporting_source_best"
        source_best_prefix = $sourceBestRelativePrefix
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $runScript `
        -Mode export `
        -DatasetVersion $DatasetVersion `
        -RunSuffix $SourceRunSuffix `
        -DisableRecConAug
    if ($LASTEXITCODE -ne 0) {
        throw "Source best export failed."
    }
}

$generalTrainLabel = Resolve-GeneralTrainLabel
$mixedTrainLabels = "$domainTrainLabel;$generalTrainLabel"
$trainRatioList = Resolve-TrainRatioList -DomainLabelPath $domainTrainLabel -GeneralLabelPath $generalTrainLabel

Write-Status -Payload @{
    status = "launching_followup"
    source_best_prefix = $sourceBestRelativePrefix
    learning_rate = $LearningRate
    batch_size = $BatchSize
    epochs = $Epochs
    train_ratio_list = $trainRatioList
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $backgroundScript `
    -Mode full `
    -DatasetVersion $DatasetVersion `
    -RunSuffix $NewRunSuffix `
    -Epochs $Epochs `
    -BatchSize $BatchSize `
    -LearningRate $LearningRate `
    -PretrainedModel $sourceBestRelativePrefix `
    -MixedTrainLabelFiles $mixedTrainLabels `
    -TrainRatioList $trainRatioList `
    -RequireMixedTraining `
    -DisableRecConAug

if ($LASTEXITCODE -ne 0) {
    throw "Follow-up launch failed."
}

Write-Status -Payload @{
    status = "followup_submitted"
    source_best_prefix = $sourceBestRelativePrefix
    learning_rate = $LearningRate
    batch_size = $BatchSize
    epochs = $Epochs
    train_ratio_list = $trainRatioList
}
