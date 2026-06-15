<#
.SYNOPSIS
Start lr1e4 only after the current lr5e5 PaddleOCR run succeeds.

.DESCRIPTION
This bridge is intentionally narrow: it watches one known lr5e5 run, and only
launches the lr1e4 follow-up if the first combined log reports exit_code=0.
The follow-up launch sets GPU_GUARD_DISABLE=1 so the run starts immediately
instead of re-entering the GPU-GUARD queue.
#>

$ErrorActionPreference = "Stop"

$WorkspaceRoot = "G:\lemon-aid\paddleocr_rec_work"
$FirstRunSuffix = "v2_low_lr_mix_20260611_lr5e5_b16_sampler16_noguard_now3"
$SecondRunSuffix = "v2_low_lr_mix_20260611_lr1e4_b16_sampler16_noguard_after_lr5e5_now3"

$FirstLog = Join-Path $WorkspaceRoot "full.$FirstRunSuffix.combined.log"
$SecondLaunch = Join-Path $WorkspaceRoot "launch.full.$SecondRunSuffix.ps1"
$SecondLog = Join-Path $WorkspaceRoot "full.$SecondRunSuffix.combined.log"
$BridgeLog = Join-Path $WorkspaceRoot "bridge.$FirstRunSuffix.to.$SecondRunSuffix.log"

function Write-BridgeLog {
    param([string]$Message)

    $line = (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + " " + $Message
    Add-Content -LiteralPath $BridgeLog -Value $line -Encoding UTF8
}

function Get-FirstRunProcessCount {
    $processes = @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.CommandLine -match [regex]::Escape($FirstRunSuffix) -and
                $_.CommandLine -match "tools\\train.py"
            }
    )
    return $processes.Count
}

Write-BridgeLog "BRIDGE_START first=$FirstRunSuffix second=$SecondRunSuffix"

while ($true) {
    $activeCount = Get-FirstRunProcessCount
    if ($activeCount -eq 0) {
        break
    }

    $lastLine = ""
    if (Test-Path -LiteralPath $FirstLog -PathType Leaf) {
        $lastLine = Get-Content -LiteralPath $FirstLog -Tail 1 -ErrorAction SilentlyContinue
    }
    Write-BridgeLog "WAIT first_active_count=$activeCount last=$lastLine"
    Start-Sleep -Seconds 300
}

if (-not (Test-Path -LiteralPath $FirstLog -PathType Leaf)) {
    Write-BridgeLog "STOP first_log_missing"
    exit 2
}

$firstTail = Get-Content -LiteralPath $FirstLog -Tail 200
if (-not ($firstTail -match "PaddleOCR train.py exit_code=0")) {
    Write-BridgeLog "STOP first_not_success_no_lr1e4"
    exit 3
}

Write-BridgeLog "FIRST_SUCCESS launching_lr1e4"

$secondLaunchLines = @(
    '$ErrorActionPreference = "Stop"',
    '$env:GPU_GUARD_DISABLE = "1"',
    '$env:CUDA_VISIBLE_DEVICES = "0"',
    "& ""G:\lemon-aid\paddleocr_rec_work\Lemon-Aid\backend\scripts\run_a100_paddleocr_windows_training.ps1"" -Mode full -DatasetVersion v2 -RunSuffix ""$SecondRunSuffix"" -BatchSize 16 -SamplerFirstBatchSize 16 -Epochs 100 -LearningRate 0.0001 -PretrainedModel ""output\supplement_rec_crawling_$FirstRunSuffix\best_accuracy"" -MixedTrainLabelFiles ""G:\lemon-aid\paddleocr_rec_work\rec_dataset\v2\rec\rec_gt_train.txt;G:\lemon-aid\paddleocr_rec_work\rec_dataset\general_korean\rec\rec_gt_train.txt"" -TrainRatioList ""[1.0,1]"" -RequireMixedTraining -DisableRecConAug"
)
Set-Content -LiteralPath $SecondLaunch -Value $secondLaunchLines -Encoding UTF8

$command = 'cmd.exe /c powershell -NoProfile -ExecutionPolicy Bypass -File "' +
    $SecondLaunch + '" > "' + $SecondLog + '" 2>&1'
$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = $command
    CurrentDirectory = Join-Path $WorkspaceRoot "PaddleOCR"
}

Write-BridgeLog "SECOND_CREATED process_id=$($result.ProcessId) return_value=$($result.ReturnValue) log=$SecondLog"
