<#
.SYNOPSIS
Show sanitized status for a Windows A100 PaddleOCR recognition training run.

.DESCRIPTION
This script is intended to run on the Windows A100 host after SSH login. It
parses PaddleOCR's combined training log and matching process list to report
where recognition fine-tuning is, how much ETA remains, and whether common
dataset/logging failures are visible. It intentionally reports counts, metrics,
and process metadata only; it does not print OCR labels, provider payloads, or
private image paths.

Official references:
- https://www.paddleocr.ai/latest/en/version2.x/ppocr/model_train/recognition.html
- https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html
#>

param(
    [string]$WorkspaceRoot = "G:\lemon-aid\paddleocr_rec_work",
    [string]$RunSuffix = "v2_low_lr_mix_20260610_stage3",
    [ValidateSet("full", "smoke", "dataset", "export")]
    [string]$Mode = "full",
    [ValidateRange(200, 20000)]
    [int]$TailLines = 8000,
    [switch]$Json,
    [switch]$NoGpu
)

$ErrorActionPreference = "Stop"

function ConvertTo-EtaHours {
    param([string]$EtaText)

    if ([string]::IsNullOrWhiteSpace($EtaText)) {
        return $null
    }

    $trimmed = $EtaText.Trim()
    if ($trimmed -match "^(?:(?<days>\d+)\s+days?,\s*)?(?<hours>\d{1,2}):(?<minutes>\d{2}):(?<seconds>\d{2})$") {
        $days = if ($Matches["days"]) { [double]$Matches["days"] } else { 0.0 }
        $hours = [double]$Matches["hours"]
        $minutes = [double]$Matches["minutes"]
        $seconds = [double]$Matches["seconds"]
        return [Math]::Round(($days * 24.0) + $hours + ($minutes / 60.0) + ($seconds / 3600.0), 2)
    }

    return $null
}

function ConvertTo-ProcessAgeHours {
    param([object]$Process)

    if ($null -eq $Process.CreationDate) {
        return $null
    }
    try {
        if ($Process.CreationDate -is [datetime]) {
            $createdAt = $Process.CreationDate
        }
        else {
            $createdAt = [System.Management.ManagementDateTimeConverter]::ToDateTime([string]$Process.CreationDate)
        }
        return [Math]::Round(((Get-Date) - $createdAt).TotalHours, 2)
    }
    catch {
        return $null
    }
}

function Parse-TrainingLine {
    param([string]$Line)

    $pattern = "epoch:\s*\[(?<epoch>\d+)\/(?<total>\d+)\].*global_step:\s*(?<step>\d+),\s*lr:\s*(?<lr>[0-9.]+),\s*acc:\s*(?<acc>[0-9.]+),\s*norm_edit_dis:\s*(?<norm>[0-9.]+).*loss:\s*(?<loss>[0-9.]+).*ips:\s*(?<ips>[0-9.]+)\s+samples/s,\s*eta:\s*(?<eta>[^,]+(?:,\s*\d{1,2}:\d{2}:\d{2})?).*max_mem_reserved:\s*(?<reserved>\d+)\s+MB,\s*max_mem_allocated:\s*(?<allocated>\d+)\s+MB"
    if ($Line -notmatch $pattern) {
        return $null
    }

    $epoch = [int]$Matches["epoch"]
    $total = [int]$Matches["total"]
    [PSCustomObject]@{
        epoch = $epoch
        total_epochs = $total
        percent_complete = if ($total -gt 0) { [Math]::Round(($epoch / [double]$total) * 100.0, 2) } else { $null }
        global_step = [int]$Matches["step"]
        learning_rate = [double]$Matches["lr"]
        train_acc = [double]$Matches["acc"]
        train_norm_edit_dis = [double]$Matches["norm"]
        train_loss = [double]$Matches["loss"]
        ips = [double]$Matches["ips"]
        eta_text = $Matches["eta"].Trim()
        eta_hours = ConvertTo-EtaHours -EtaText $Matches["eta"]
        max_mem_reserved_mb = [int]$Matches["reserved"]
        max_mem_allocated_mb = [int]$Matches["allocated"]
    }
}

function Parse-BestMetricLine {
    param([string]$Line)

    if ($Line -notmatch "best metric,\s*acc:\s*(?<acc>[0-9.]+).*norm_edit_dis:\s*(?<norm>[0-9.]+).*best_epoch:\s*(?<epoch>\d+)") {
        return $null
    }

    [PSCustomObject]@{
        best_epoch = [int]$Matches["epoch"]
        best_acc = [double]$Matches["acc"]
        best_norm_edit_dis = [double]$Matches["norm"]
    }
}

function Parse-CurMetricLine {
    param([string]$Line)

    if ($Line -notmatch "cur metric,\s*acc:\s*(?<acc>[0-9.]+),\s*norm_edit_dis:\s*(?<norm>[0-9.]+)") {
        return $null
    }

    [PSCustomObject]@{
        eval_acc = [double]$Matches["acc"]
        eval_norm_edit_dis = [double]$Matches["norm"]
    }
}

function Get-GpuStatus {
    if ($NoGpu) {
        return $null
    }
    try {
        $line = & nvidia-smi --query-gpu=memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits 2>$null | Select-Object -First 1
        if ([string]::IsNullOrWhiteSpace($line)) {
            return $null
        }
        $parts = @($line -split "," | ForEach-Object { $_.Trim() })
        if ($parts.Count -lt 4) {
            return $null
        }
        return [PSCustomObject]@{
            total_mb = [int]$parts[0]
            used_mb = [int]$parts[1]
            free_mb = [int]$parts[2]
            utilization_percent = [int]$parts[3]
        }
    }
    catch {
        return [PSCustomObject]@{
            error = "nvidia-smi query failed"
        }
    }
}

if ([string]::IsNullOrWhiteSpace($RunSuffix)) {
    throw "RunSuffix is required."
}

$logPath = Join-Path $WorkspaceRoot "$Mode.$RunSuffix.combined.log"
$paddleRoot = Join-Path $WorkspaceRoot "PaddleOCR"
$outputName = "supplement_rec_crawling_$RunSuffix"
$outputDir = Join-Path $paddleRoot "output\$outputName"

$logExists = Test-Path -LiteralPath $logPath -PathType Leaf
$latestTrain = $null
$bestMetric = $null
$curMetric = $null
$lastSave = $null
$errorCounts = [PSCustomObject]@{
    missing_image = $null
    parse_error = $null
    traceback = $null
}

if ($logExists) {
    $tail = @(Get-Content -LiteralPath $logPath -Tail $TailLines -Encoding UTF8)
    foreach ($line in $tail) {
        $parsedTrain = Parse-TrainingLine -Line $line
        if ($null -ne $parsedTrain) {
            $latestTrain = $parsedTrain
        }

        $parsedBest = Parse-BestMetricLine -Line $line
        if ($null -ne $parsedBest) {
            $bestMetric = $parsedBest
        }

        $parsedCur = Parse-CurMetricLine -Line $line
        if ($null -ne $parsedCur) {
            $curMetric = $parsedCur
        }

        if ($line -match "save model in (?<path>.+)$") {
            $lastSave = $Matches["path"].Trim()
        }
    }

    $errorCounts = [PSCustomObject]@{
        missing_image = (Select-String -LiteralPath $logPath -Pattern "does not exist" -SimpleMatch -ErrorAction SilentlyContinue | Measure-Object).Count
        parse_error = (Select-String -LiteralPath $logPath -Pattern "error happened" -SimpleMatch -ErrorAction SilentlyContinue | Measure-Object).Count
        traceback = (Select-String -LiteralPath $logPath -Pattern "Traceback" -SimpleMatch -ErrorAction SilentlyContinue | Measure-Object).Count
    }
}

$escapedOutputName = [regex]::Escape($outputName)
$processes = @(
    Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        $_.CommandLine -match "\\.venv-paddle-rec-v2-clean\\Scripts\\python\.exe" -and
        $_.CommandLine -match "tools\\train\.py" -and
        $_.CommandLine -match $escapedOutputName
    } | ForEach-Object {
        [PSCustomObject]@{
            pid = $_.ProcessId
            name = $_.Name
            age_hours = ConvertTo-ProcessAgeHours -Process $_
        }
    }
)

$bestCheckpointPrefix = Join-Path $outputDir "best_accuracy"
$latestCheckpointPrefix = Join-Path $outputDir "latest"
$checkpoints = [PSCustomObject]@{
    output_dir_exists = (Test-Path -LiteralPath $outputDir)
    best_accuracy_pdparams = (Test-Path -LiteralPath "$bestCheckpointPrefix.pdparams")
    latest_pdparams = (Test-Path -LiteralPath "$latestCheckpointPrefix.pdparams")
}

$status = if ($processes.Count -gt 0) {
    "running"
}
elseif ($checkpoints.best_accuracy_pdparams -or $checkpoints.latest_pdparams) {
    "not_running_checkpoint_exists"
}
elseif ($logExists) {
    "not_running_log_exists"
}
else {
    "not_found"
}

$payload = [PSCustomObject]@{
    checked_at = (Get-Date).ToString("o")
    status = $status
    workspace_root = $WorkspaceRoot
    run_suffix = $RunSuffix
    mode = $Mode
    log_path = $logPath
    log_exists = $logExists
    latest_train = $latestTrain
    latest_eval = $curMetric
    best_metric = $bestMetric
    last_save = $lastSave
    error_counts = $errorCounts
    gpu = Get-GpuStatus
    process_count = $processes.Count
    processes = $processes
    checkpoints = $checkpoints
}

if ($Json) {
    $payload | ConvertTo-Json -Depth 6
    exit 0
}

Write-Host "---A100_PADDLEOCR_STATUS---"
Write-Host "checked_at=$($payload.checked_at)"
Write-Host "status=$($payload.status)"
Write-Host "run_suffix=$RunSuffix"
Write-Host "log=$logPath"
if ($null -ne $latestTrain) {
    Write-Host ("progress={0}/{1} ({2}%) step={3} eta={4} eta_hours={5}" -f `
        $latestTrain.epoch,
        $latestTrain.total_epochs,
        $latestTrain.percent_complete,
        $latestTrain.global_step,
        $latestTrain.eta_text,
        $latestTrain.eta_hours)
    Write-Host ("train acc={0} norm_edit_dis={1} loss={2} lr={3} ips={4}" -f `
        $latestTrain.train_acc,
        $latestTrain.train_norm_edit_dis,
        $latestTrain.train_loss,
        $latestTrain.learning_rate,
        $latestTrain.ips)
    Write-Host ("train_mem reserved_mb={0} allocated_mb={1}" -f `
        $latestTrain.max_mem_reserved_mb,
        $latestTrain.max_mem_allocated_mb)
}
else {
    Write-Host "progress=unavailable"
}

if ($null -ne $bestMetric) {
    Write-Host ("best epoch={0} acc={1} norm_edit_dis={2}" -f `
        $bestMetric.best_epoch,
        $bestMetric.best_acc,
        $bestMetric.best_norm_edit_dis)
}
else {
    Write-Host "best=unavailable"
}

if ($null -ne $curMetric) {
    Write-Host ("latest_eval acc={0} norm_edit_dis={1}" -f $curMetric.eval_acc, $curMetric.eval_norm_edit_dis)
}

if ($null -ne $lastSave) {
    Write-Host "last_save=$lastSave"
}

Write-Host ("errors missing_image={0} parse_error={1} traceback={2}" -f `
    $errorCounts.missing_image,
    $errorCounts.parse_error,
    $errorCounts.traceback)

if ($null -ne $payload.gpu) {
    if ($payload.gpu.PSObject.Properties.Name -contains "error") {
        Write-Host "gpu_error=$($payload.gpu.error)"
    }
    else {
        Write-Host ("gpu total_mb={0} used_mb={1} free_mb={2} util_percent={3}" -f `
            $payload.gpu.total_mb,
            $payload.gpu.used_mb,
            $payload.gpu.free_mb,
            $payload.gpu.utilization_percent)
    }
}

Write-Host "process_count=$($processes.Count)"
foreach ($process in $processes) {
    Write-Host ("process pid={0} name={1} age_hours={2}" -f $process.pid, $process.name, $process.age_hours)
}

Write-Host ("checkpoints output_dir={0} best_accuracy_pdparams={1} latest_pdparams={2}" -f `
    $checkpoints.output_dir_exists,
    $checkpoints.best_accuracy_pdparams,
    $checkpoints.latest_pdparams)
