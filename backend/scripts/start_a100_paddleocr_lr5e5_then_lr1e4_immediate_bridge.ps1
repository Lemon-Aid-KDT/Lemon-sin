<#
.SYNOPSIS
Run the low-LR PaddleOCR A100 experiments sequentially without parking on a
high free-memory threshold.

.DESCRIPTION
This bridge starts the lr=0.00005 run first and only starts the lr=0.0001 run
when the first keeper exits successfully. It delegates actual GPU admission and
crash diagnostics to start_a100_paddleocr_sequential_keeper.ps1 so the run keeps
the same logging and privacy behavior as the rest of the A100 PaddleOCR flow.

Official references:
- https://www.paddleocr.ai/latest/en/version2.x/ppocr/model_train/recognition.html
- https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/start-process
#>

param(
    [string]$WorkspaceRoot = "G:\lemon-aid\paddleocr_rec_work",
    [string]$DatasetVersion = "v2",
    [int]$BatchSize = 32,
    [int]$SamplerFirstBatchSize = 32,
    [int]$Epochs = 100,
    [string]$PretrainedModel = "output\supplement_rec_crawling_v2_low_lr_mix_20260610_stage3\best_accuracy",
    [string]$MixedTrainLabelFiles = "G:\lemon-aid\paddleocr_rec_work\rec_dataset\v2\rec\rec_gt_train.txt;G:\lemon-aid\paddleocr_rec_work\rec_dataset\general_korean\rec\rec_gt_train.txt",
    [string]$TrainRatioList = "[1.0,1]",
    [int]$MinFreeMiB = 20000,
    [int]$GpuGuardNeedMiB = 10000,
    [int]$GpuGuardBudgetMiB = 79000,
    [int]$MaxAttempts = 1,
    [int]$PollSeconds = 30,
    [string]$FirstRunSuffix = "v2_low_lr_mix_20260611_lr5e5_b32_sampler32_immediate1",
    [string]$SecondRunSuffix = "v2_low_lr_mix_20260611_lr1e4_b32_sampler32_after_lr5e5"
)

$ErrorActionPreference = "Stop"

$keeper = Join-Path $WorkspaceRoot "Lemon-Aid\backend\scripts\start_a100_paddleocr_sequential_keeper.ps1"
$bridgeLog = Join-Path $WorkspaceRoot "bridge.v2_low_lr_mix_20260611_lr5e5_then_lr1e4_immediate.log"

function Write-Bridge {
    param([Parameter(Mandatory = $true)][string]$Message)

    $line = "$(Get-Date -Format o) $Message"
    Add-Content -LiteralPath $bridgeLog -Value $line -Encoding UTF8
}

function Invoke-KeeperRun {
    param(
        [Parameter(Mandatory = $true)][string]$RunSuffix,
        [Parameter(Mandatory = $true)][string]$LearningRate
    )

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $keeper,
        "-WorkspaceRoot", $WorkspaceRoot,
        "-DatasetVersion", $DatasetVersion,
        "-BatchSize", "$BatchSize",
        "-SamplerFirstBatchSize", "$SamplerFirstBatchSize",
        "-Epochs", "$Epochs",
        "-PretrainedModel", $PretrainedModel,
        "-MixedTrainLabelFiles", $MixedTrainLabelFiles,
        "-TrainRatioList", $TrainRatioList,
        "-RequireMixedTraining",
        "-DisableRecConAug",
        "-MinFreeMiB", "$MinFreeMiB",
        "-GpuGuardNeedMiB", "$GpuGuardNeedMiB",
        "-GpuGuardBudgetMiB", "$GpuGuardBudgetMiB",
        "-MaxAttempts", "$MaxAttempts",
        "-PollSeconds", "$PollSeconds",
        "-RunSuffix", $RunSuffix,
        "-LearningRate", $LearningRate
    )

    Write-Bridge "START suffix=$RunSuffix lr=$LearningRate batch=$BatchSize sampler_first_bs=$SamplerFirstBatchSize min_free_mib=$MinFreeMiB gpu_guard_need_mib=$GpuGuardNeedMiB"
    & powershell.exe @args 2>&1 | ForEach-Object {
        Add-Content -LiteralPath $bridgeLog -Value $_ -Encoding UTF8
    }
    $exitCode = $LASTEXITCODE
    Write-Bridge "EXIT suffix=$RunSuffix code=$exitCode"
    return [int]$exitCode
}

if (-not (Test-Path -LiteralPath $keeper -PathType Leaf)) {
    throw "Missing keeper script: $keeper"
}

if (Test-Path -LiteralPath $bridgeLog -PathType Leaf) {
    Remove-Item -LiteralPath $bridgeLog -Force
}

Write-Bridge "BRIDGE_START mode=lr5e5_then_lr1e4"
$firstExitCode = Invoke-KeeperRun -RunSuffix $FirstRunSuffix -LearningRate "0.00005"

if ($firstExitCode -eq 0) {
    Write-Bridge "LR5E5_SUCCESS_STARTING_LR1E4"
    $secondExitCode = Invoke-KeeperRun -RunSuffix $SecondRunSuffix -LearningRate "0.0001"
    Write-Bridge "BRIDGE_EXIT code=$secondExitCode"
    exit $secondExitCode
}

Write-Bridge "SKIP_LR1E4 reason=lr5e5_exit_code_$firstExitCode"
Write-Bridge "BRIDGE_EXIT code=$firstExitCode"
exit $firstExitCode
