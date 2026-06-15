<#
.SYNOPSIS
Early-stop watcher for noshm/nometric runs whose metrics live in stdout.<suffix>.log.

.DESCRIPTION
Variant of Lemon-Aid/backend/scripts/watch_a100_paddleocr_windows_early_stop.ps1.
Why a variant: the 2026-06-11 noshm runners redirect all ppocr INFO lines to
G:\...\stdout.<suffix>.log and leave output\...\train.log at 0 bytes, so the
original watcher never reaches "ready". PaddleOCR exposes no first-class
early-stopping switch, so stopping the matched train.py processes after stale
evals remains the supported approach. Optionally starts a follow-up runner
right after stopping (used to hand off lr5e5_b16 -> lr1e4 because the bridge
only auto-starts lr1e4 on exit_code 0, which a forced stop never produces).
#>

param(
    [string]$WorkspaceRoot = "G:\lemon-aid\paddleocr_rec_work",
    [Parameter(Mandatory = $true)]
    [string]$RunSuffix,

    [ValidateRange(1, 100)]
    [int]$PatienceEpochs = 10,

    [ValidateRange(1, 100)]
    [int]$MinEvaluatedEpoch = 5,

    [ValidateRange(10, 3600)]
    [int]$PollSeconds = 60,

    [string]$StartAfterStopScript = "",

    [switch]$Once,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$paddleRoot = Join-Path $WorkspaceRoot "PaddleOCR"
$outputName = "supplement_rec_crawling_$RunSuffix"
$metricLog = Join-Path $WorkspaceRoot ("stdout." + $RunSuffix + ".log")
$statusPath = Join-Path $WorkspaceRoot ("early_stop." + $RunSuffix + ".status.json")

function Get-RunProgress {
    if (-not (Test-Path -LiteralPath $metricLog -PathType Leaf)) {
        return [PSCustomObject]@{
            status = "waiting_for_metric_log"
            metric_log = $metricLog
        }
    }

    $latestTrainEpoch = $null
    $latestEvalEpoch = $null
    $latestEvalAcc = $null
    $latestEvalNormEditDis = $null
    $bestEpoch = $null
    $bestAcc = $null
    $bestNormEditDis = $null

    foreach ($line in Get-Content -LiteralPath $metricLog -Tail 4000) {
        if ($line -match "epoch:\s*\[(\d+)/(\d+)\]") {
            $latestTrainEpoch = [int]$Matches[1]
        }
        elseif ($line -match "cur metric,\s*acc:\s*([0-9.]+),\s*norm_edit_dis:\s*([0-9.]+)") {
            $latestEvalEpoch = $latestTrainEpoch
            $latestEvalAcc = [double]$Matches[1]
            $latestEvalNormEditDis = [double]$Matches[2]
        }
        elseif ($line -match "best metric,\s*acc:\s*([0-9.]+).*norm_edit_dis:\s*([0-9.]+).*best_epoch:\s*(\d+)") {
            $bestAcc = [double]$Matches[1]
            $bestNormEditDis = [double]$Matches[2]
            $bestEpoch = [int]$Matches[3]
        }
    }

    if ($null -eq $latestEvalEpoch -or $null -eq $bestEpoch) {
        return [PSCustomObject]@{
            status = "waiting_for_eval_metric"
            latest_train_epoch = $latestTrainEpoch
            metric_log = $metricLog
        }
    }

    $staleEpochs = $latestEvalEpoch - $bestEpoch
    [PSCustomObject]@{
        status = "ready"
        latest_train_epoch = $latestTrainEpoch
        latest_eval_epoch = $latestEvalEpoch
        latest_eval_acc = $latestEvalAcc
        latest_eval_norm_edit_dis = $latestEvalNormEditDis
        best_epoch = $bestEpoch
        best_acc = $bestAcc
        best_norm_edit_dis = $bestNormEditDis
        stale_eval_epochs = $staleEpochs
        patience_epochs = $PatienceEpochs
        min_evaluated_epoch = $MinEvaluatedEpoch
        metric_log = $metricLog
    }
}

function Get-MatchingTrainingProcesses {
    $escapedOutputName = [regex]::Escape($outputName)
    Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        $_.CommandLine -match "\.venv-paddle-rec-v2-clean\\Scripts\\python\.exe" -and
        $_.CommandLine -match "tools[\\/]train\.py" -and
        $_.CommandLine -match $escapedOutputName
    }
}

function Stop-MatchingTrainingProcesses {
    param([object[]]$Processes)

    $stopped = @()
    foreach ($process in $Processes) {
        $stopped += [PSCustomObject]@{
            pid = $process.ProcessId
            name = $process.Name
        }
        if (-not $DryRun) {
            Stop-Process -Id $process.ProcessId -Force
        }
    }
    return $stopped
}

function Start-FollowUpRunner {
    if ([string]::IsNullOrWhiteSpace($StartAfterStopScript)) {
        return $null
    }
    if (-not (Test-Path -LiteralPath $StartAfterStopScript -PathType Leaf)) {
        return [PSCustomObject]@{ started = $false; error = "runner script missing: $StartAfterStopScript" }
    }
    if ($DryRun) {
        return [PSCustomObject]@{ started = $false; dry_run = $true; runner = $StartAfterStopScript }
    }
    $cmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$StartAfterStopScript`""
    $result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $cmd
        CurrentDirectory = $WorkspaceRoot
    }
    return [PSCustomObject]@{
        started = ($result.ReturnValue -eq 0)
        return_value = $result.ReturnValue
        pid = $result.ProcessId
        runner = $StartAfterStopScript
    }
}

function Write-Status {
    param([hashtable]$Payload)

    $Payload["checked_at"] = (Get-Date).ToString("o")
    $Payload["run_suffix"] = $RunSuffix
    $Payload["output_name"] = $outputName
    $Payload["dry_run"] = [bool]$DryRun
    $json = $Payload | ConvertTo-Json -Depth 6
    $json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    # Write-Host keeps the console echo out of the function's output stream so
    # Invoke-EarlyStopCheck can return a clean boolean to the poll loop.
    Write-Host $json
}

function Invoke-EarlyStopCheck {
    $progress = Get-RunProgress
    $payload = @{
        progress = $progress
        action = "none"
        stopped_processes = @()
    }

    if ($progress.status -ne "ready") {
        Write-Status -Payload $payload
        return $false
    }

    $shouldStop = (
        $progress.latest_eval_epoch -ge $MinEvaluatedEpoch -and
        $progress.stale_eval_epochs -ge $PatienceEpochs
    )
    $payload["should_stop"] = $shouldStop

    if (-not $shouldStop) {
        Write-Status -Payload $payload
        return $false
    }

    $procs = @(Get-MatchingTrainingProcesses)
    $payload["matched_process_count"] = $procs.Count
    if ($procs.Count -eq 0) {
        $payload["action"] = "stop_requested_but_no_matching_process"
        Write-Status -Payload $payload
        return $false
    }

    $payload["action"] = if ($DryRun) { "would_stop" } else { "stopped" }
    $payload["stopped_processes"] = @(Stop-MatchingTrainingProcesses -Processes $procs)
    $followUp = Start-FollowUpRunner
    if ($null -ne $followUp) {
        $payload["follow_up_runner"] = $followUp
    }
    Write-Status -Payload $payload
    return (-not $DryRun)
}

do {
    $stoppedNow = Invoke-EarlyStopCheck
    if ($Once -or $stoppedNow) {
        break
    }
    Start-Sleep -Seconds $PollSeconds
} while ($true)
