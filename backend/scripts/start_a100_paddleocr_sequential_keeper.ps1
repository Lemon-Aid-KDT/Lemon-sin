<#
.SYNOPSIS
Run exactly one A100 PaddleOCR recognition fine-tune job until it starts or
finishes, retrying only that job when GPU-GUARD exits before training begins.

.DESCRIPTION
This keeper prevents accidental parallel PaddleOCR fine-tune launches on the
shared Windows A100 host. It waits while any PaddleOCR train.py process is
active, checks GPU-GUARD reserved budget and available GPU memory before each
registration attempt, launches a single run via
start_a100_paddleocr_windows_background.ps1, and stops when a checkpoint exists
or MaxAttempts is reached.

The script logs only process state, numeric GPU memory, and checkpoint presence.
It does not print OCR labels, provider payloads, or private image paths.

Official references:
- https://www.paddleocr.ai/latest/en/version2.x/ppocr/model_train/recognition.html
- https://learn.microsoft.com/en-us/powershell/module/cimcmdlets/invoke-cimmethod
#>

param(
    [string]$WorkspaceRoot = "G:\lemon-aid\paddleocr_rec_work",
    [string]$DatasetVersion = "v2",
    [string]$RunSuffix = "v2_low_lr_mix_20260610_stage4_lr5e5_from_stage3_best_retry2",
    [int]$BatchSize = 128,
    [int]$SamplerFirstBatchSize = 0,
    [int]$Epochs = 100,
    [double]$LearningRate = 0.00005,
    [string]$PretrainedModel = "output\supplement_rec_crawling_v2_low_lr_mix_20260610_stage3\best_accuracy",
    [string]$MixedTrainLabelFiles = "G:\lemon-aid\paddleocr_rec_work\rec_dataset\v2\rec\rec_gt_train.txt;G:\lemon-aid\paddleocr_rec_work\rec_dataset\general_korean\rec\rec_gt_train.txt",
    [string]$TrainRatioList = "[1.0,1]",
    [switch]$RequireMixedTraining = $true,
    [switch]$DisableRecConAug = $true,
    [ValidateRange(0, 80000)]
    [int]$MinFreeMiB = 30000,
    [ValidateRange(0, 120000)]
    [int]$GpuGuardNeedMiB = 16000,
    [ValidateRange(1, 120000)]
    [int]$GpuGuardBudgetMiB = 79000,
    [ValidateRange(1, 100)]
    [int]$MaxAttempts = 12,
    [ValidateRange(30, 3600)]
    [int]$PollSeconds = 180
)

$ErrorActionPreference = "Stop"

$startScriptPath = Join-Path $WorkspaceRoot "Lemon-Aid\backend\scripts\start_a100_paddleocr_windows_background.ps1"
$stateLog = Join-Path $WorkspaceRoot "sequential_keeper.$RunSuffix.state.log"
$paddleRoot = Join-Path $WorkspaceRoot "PaddleOCR"
$outputDir = Join-Path $paddleRoot "output\supplement_rec_crawling_$RunSuffix"
$bestParams = Join-Path $outputDir "best_accuracy.pdparams"
$latestParams = Join-Path $outputDir "latest.pdparams"
$combinedLog = Join-Path $WorkspaceRoot "full.$RunSuffix.combined.log"
$attemptLogDir = Join-Path $WorkspaceRoot "diagnostics\paddleocr_attempts\$RunSuffix"

function Write-State {
    param([string]$Message)

    $now = Get-Date -Format o
    Add-Content -LiteralPath $stateLog -Value "$now $Message" -Encoding UTF8
}

function Get-FreeGpuMemoryMiB {
    try {
        $value = & nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>$null | Select-Object -First 1
        if ([string]::IsNullOrWhiteSpace($value)) {
            return 0
        }
        return [int]($value.Trim())
    }
    catch {
        return 0
    }
}

function Get-PaddleOCRTrainProcesses {
    return @(
        Get-CimInstance Win32_Process | Where-Object {
            $commandLine = $_.CommandLine
            $commandLine -and
            $commandLine -like "*.venv-paddle-rec-v2-clean\Scripts\python.exe*" -and
            $commandLine -like "*tools\train.py*"
        }
    )
}

function Get-GpuGuardReservedBudgetMiB {
    $ledgerPaths = @(
        "C:\ProgramData\gpu-guard\ledger.json",
        "C:\ProgramData\GPU-GUARD\ledger.json"
    )

    $ledgerPath = $null
    foreach ($candidate in $ledgerPaths) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $ledgerPath = $candidate
            break
        }
    }

    if ([string]::IsNullOrWhiteSpace($ledgerPath)) {
        return [pscustomobject]@{
            Available = $false
            Status = "missing_ledger"
            Path = ""
            ReservedMiB = 0
            RunningCount = 0
        }
    }

    try {
        $ledger = Get-Content -LiteralPath $ledgerPath -Raw | ConvertFrom-Json
    }
    catch {
        return [pscustomobject]@{
            Available = $false
            Status = "parse_failed"
            Path = $ledgerPath
            ReservedMiB = 0
            RunningCount = 0
        }
    }

    $running = @()
    if ($ledger.PSObject.Properties.Name -contains "running") {
        $running = @($ledger.running)
    }
    elseif ($ledger.PSObject.Properties.Name -contains "jobs") {
        $running = @($ledger.jobs | Where-Object { $_.state -eq "running" -or $_.status -eq "running" })
    }
    elseif ($ledger.PSObject.Properties.Name -contains "processes") {
        $running = @($ledger.processes | Where-Object { $_.state -eq "running" -or $_.status -eq "running" })
    }

    $reservedMiB = 0
    foreach ($entry in $running) {
        foreach ($fieldName in @("reserved_mib", "reservedMiB", "need_mib", "needMiB", "gpu_mem_mib")) {
            if ($entry.PSObject.Properties.Name -contains $fieldName) {
                $value = $entry.$fieldName
                if ($null -ne $value -and "$value" -match "^\d+$") {
                    $reservedMiB += [int]$value
                }
                break
            }
        }
    }

    return [pscustomobject]@{
        Available = $true
        Status = "ok"
        Path = $ledgerPath
        ReservedMiB = $reservedMiB
        RunningCount = $running.Count
    }
}

function Test-CheckpointExists {
    return (Test-Path -LiteralPath $bestParams -PathType Leaf) -or
        (Test-Path -LiteralPath $latestParams -PathType Leaf)
}

function Get-PaddleOCRRunLogSummary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LogPath
    )

    if (-not (Test-Path -LiteralPath $LogPath -PathType Leaf)) {
        return [pscustomobject]@{
            Phase = "no_log"
            ExitCode = ""
            GuardRegistered = $false
            GuardAdmitted = $false
            EpochStarted = $false
            LastGuardLine = ""
            LastEpochLine = ""
            LastExitLine = ""
            LastErrorLine = ""
        }
    }

    $lines = @(Get-Content -LiteralPath $LogPath -Tail 400)
    $guardLines = @($lines | Where-Object { $_ -match "\[GPU-GUARD\]" })
    $epochLines = @($lines | Where-Object { $_ -match "epoch:\s*\[" })
    $exitLines = @($lines | Where-Object { $_ -match "exit_code=(-?\d+)" })
    $errorLines = @(
        $lines | Where-Object {
            $_ -match "Traceback|RuntimeError|OutOfMemory|MemoryError|CUDA error|CUDNN|failed with exit_code|Exception"
        }
    )

    $exitCode = ""
    if ($exitLines.Count -gt 0 -and $exitLines[-1] -match "exit_code=(-?\d+)") {
        $exitCode = $Matches[1]
    }

    $guardRegistered = $guardLines.Count -gt 0
    # Keep this detector ASCII-only. The A100 host can misdecode non-ASCII
    # regex literals under Windows PowerShell, which would hide the real
    # training failure behind a diagnostic parser failure.
    $guardAdmitted = @(
        $guardLines | Where-Object {
            $_ -match "\(inproc\)"
        }
    ).Count -gt 0
    $epochStarted = $epochLines.Count -gt 0

    $phase = "pre_guard"
    if ($epochStarted) {
        $phase = "epoch_started"
    }
    elseif ($guardAdmitted) {
        $phase = "guard_admitted_no_epoch"
    }
    elseif ($guardRegistered) {
        $phase = "guard_waiting"
    }

    return [pscustomobject]@{
        Phase = $phase
        ExitCode = $exitCode
        GuardRegistered = $guardRegistered
        GuardAdmitted = $guardAdmitted
        EpochStarted = $epochStarted
        LastGuardLine = if ($guardLines.Count -gt 0) { $guardLines[-1] } else { "" }
        LastEpochLine = if ($epochLines.Count -gt 0) { $epochLines[-1] } else { "" }
        LastExitLine = if ($exitLines.Count -gt 0) { $exitLines[-1] } else { "" }
        LastErrorLine = if ($errorLines.Count -gt 0) { $errorLines[-1] } else { "" }
    }
}

function Save-AttemptDiagnostics {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Attempt
    )

    if (-not (Test-Path -LiteralPath $attemptLogDir -PathType Container)) {
        New-Item -ItemType Directory -Path $attemptLogDir -Force | Out-Null
    }

    $summary = Get-PaddleOCRRunLogSummary -LogPath $combinedLog
    $attemptLogPath = Join-Path $attemptLogDir ("attempt_{0:000}.combined.log" -f $Attempt)
    if (Test-Path -LiteralPath $combinedLog -PathType Leaf) {
        Copy-Item -LiteralPath $combinedLog -Destination $attemptLogPath -Force
    }

    Write-State ("ATTEMPT_SUMMARY attempt={0} phase={1} exit_code={2} guard_registered={3} guard_admitted={4} epoch_started={5} log={6}" -f `
        $Attempt,
        $summary.Phase,
        $summary.ExitCode,
        $summary.GuardRegistered,
        $summary.GuardAdmitted,
        $summary.EpochStarted,
        $attemptLogPath)

    if (-not [string]::IsNullOrWhiteSpace($summary.LastGuardLine)) {
        Write-State "ATTEMPT_LAST_GUARD attempt=$Attempt line=$($summary.LastGuardLine)"
    }
    if (-not [string]::IsNullOrWhiteSpace($summary.LastEpochLine)) {
        Write-State "ATTEMPT_LAST_EPOCH attempt=$Attempt line=$($summary.LastEpochLine)"
    }
    if (-not [string]::IsNullOrWhiteSpace($summary.LastExitLine)) {
        Write-State "ATTEMPT_LAST_EXIT attempt=$Attempt line=$($summary.LastExitLine)"
    }
    if (-not [string]::IsNullOrWhiteSpace($summary.LastErrorLine)) {
        Write-State "ATTEMPT_LAST_ERROR attempt=$Attempt line=$($summary.LastErrorLine)"
    }

    return $summary
}

function Start-SinglePaddleOCRRun {
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $startScriptPath,
        "-Mode", "full",
        "-WorkspaceRoot", $WorkspaceRoot,
        "-DatasetVersion", $DatasetVersion,
        "-RunSuffix", $RunSuffix,
        "-BatchSize", $BatchSize,
        "-Epochs", $Epochs,
        "-LearningRate", $LearningRate.ToString("0.################", [Globalization.CultureInfo]::InvariantCulture),
        "-PretrainedModel", $PretrainedModel,
        "-MixedTrainLabelFiles", $MixedTrainLabelFiles,
        "-TrainRatioList", $TrainRatioList
    )
    if ($SamplerFirstBatchSize -gt 0) {
        $args += @("-SamplerFirstBatchSize", $SamplerFirstBatchSize)
    }
    if ($RequireMixedTraining) {
        $args += "-RequireMixedTraining"
    }
    if ($DisableRecConAug) {
        $args += "-DisableRecConAug"
    }

    & powershell @args
    if ($LASTEXITCODE -ne 0) {
        throw "Background launcher failed. exit_code=$LASTEXITCODE"
    }
}

if (-not (Test-Path -LiteralPath $startScriptPath -PathType Leaf)) {
    throw "Missing A100 background launcher: $startScriptPath"
}

Write-State "KEEPER_START run_suffix=$RunSuffix min_free_mib=$MinFreeMiB gpu_guard_need_mib=$GpuGuardNeedMiB gpu_guard_budget_mib=$GpuGuardBudgetMiB max_attempts=$MaxAttempts batch=$BatchSize sampler_first_bs=$SamplerFirstBatchSize epochs=$Epochs lr=$LearningRate"

$attempt = 0
$pendingGuardTicket = $false
$pendingGuardBaselineReservedMiB = 0
$pendingGuardBaselineRunningCount = 0
while ($attempt -lt $MaxAttempts) {
    if (Test-CheckpointExists) {
        Write-State "DONE reason=checkpoint_exists best=$((Test-Path -LiteralPath $bestParams -PathType Leaf)) latest=$((Test-Path -LiteralPath $latestParams -PathType Leaf))"
        exit 0
    }

    $trainProcesses = @(Get-PaddleOCRTrainProcesses)
    if ($trainProcesses.Count -gt 0) {
        $pids = ($trainProcesses | ForEach-Object { $_.ProcessId }) -join ","
        Write-State "WAIT reason=existing_paddleocr_train_process count=$($trainProcesses.Count) pids=$pids"
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    if ($pendingGuardTicket) {
        $guardBudget = Get-GpuGuardReservedBudgetMiB
        if (
            $guardBudget.Available -and
            (
                $guardBudget.ReservedMiB -gt $pendingGuardBaselineReservedMiB -or
                $guardBudget.RunningCount -gt $pendingGuardBaselineRunningCount
            )
        ) {
            Write-State "WAIT reason=pending_gpu_guard_ticket reserved_mib=$($guardBudget.ReservedMiB) baseline_reserved_mib=$pendingGuardBaselineReservedMiB running_count=$($guardBudget.RunningCount) baseline_running_count=$pendingGuardBaselineRunningCount"
            Start-Sleep -Seconds $PollSeconds
            continue
        }

        $pendingGuardTicket = $false
        Write-State "READY reason=pending_gpu_guard_ticket_released"
    }

    $guardBudget = Get-GpuGuardReservedBudgetMiB
    if ($guardBudget.Available -and $GpuGuardNeedMiB -gt 0) {
        $projectedReservedMiB = $guardBudget.ReservedMiB + $GpuGuardNeedMiB
        if ($projectedReservedMiB -gt $GpuGuardBudgetMiB) {
            Write-State "WAIT reason=gpu_guard_reserved_budget reserved_mib=$($guardBudget.ReservedMiB) need_mib=$GpuGuardNeedMiB projected_mib=$projectedReservedMiB budget_mib=$GpuGuardBudgetMiB running_count=$($guardBudget.RunningCount)"
            Start-Sleep -Seconds $PollSeconds
            continue
        }
        Write-State "READY reason=gpu_guard_reserved_budget reserved_mib=$($guardBudget.ReservedMiB) need_mib=$GpuGuardNeedMiB projected_mib=$projectedReservedMiB budget_mib=$GpuGuardBudgetMiB running_count=$($guardBudget.RunningCount)"
    }
    elseif (-not $guardBudget.Available) {
        Write-State "WARN reason=gpu_guard_ledger_unavailable status=$($guardBudget.Status)"
    }

    $freeMiB = Get-FreeGpuMemoryMiB
    if ($freeMiB -lt $MinFreeMiB) {
        Write-State "WAIT reason=insufficient_free_gpu_mib free_mib=$freeMiB required_mib=$MinFreeMiB"
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    $attempt += 1
    Write-State "LAUNCH attempt=$attempt free_mib=$freeMiB"
    $launchGuardBaselineReservedMiB = $guardBudget.ReservedMiB
    $launchGuardBaselineRunningCount = $guardBudget.RunningCount
    Start-SinglePaddleOCRRun
    Start-Sleep -Seconds $PollSeconds
    $summary = Save-AttemptDiagnostics -Attempt $attempt
    if ($summary.ExitCode -ne "" -and $summary.EpochStarted) {
        Write-State "FAILED reason=train_exited_after_epoch_start attempt=$attempt exit_code=$($summary.ExitCode)"
        exit 1
    }
    if ($summary.ExitCode -ne "" -and $summary.GuardRegistered -and -not $summary.GuardAdmitted -and -not $summary.EpochStarted) {
        $pendingGuardTicket = $true
        $pendingGuardBaselineReservedMiB = $launchGuardBaselineReservedMiB
        $pendingGuardBaselineRunningCount = $launchGuardBaselineRunningCount
        Write-State "WAIT reason=gpu_guard_returned_before_admission attempt=$attempt exit_code=$($summary.ExitCode)"
        Start-Sleep -Seconds $PollSeconds
        continue
    }
}

Write-State "FAILED reason=max_attempts_reached attempts=$attempt"
exit 1
