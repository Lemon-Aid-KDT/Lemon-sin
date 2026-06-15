$ErrorActionPreference = "Stop"

$Base = "G:\lemon-aid\section_dataset_v2_panel_pseudo_a100"
$Python = "G:\anaconda3\envs\lemonaid_project\python.exe"
$TrainScript = Join-Path $Base "train_ultralytics_section_detector.py"
$Data = Join-Path $Base "dataset.yaml"
$Project = Join-Path $Base "runs"
$StateLog = Join-Path $Base "queue_keeper.state.log"
$Model = "yolo26s.pt"
$Name = "sec_v2_panel_pseudo_a100_yolo26s_300ep_noearly_52g_b070_v3"
$MinFreeMiB = 52000
$Log = Join-Path $Base "train_$Name.log"
$Err = Join-Path $Base "train_$Name.err"
$Best = Join-Path $Project "$Name\weights\best.pt"

function Write-State {
    param([string]$Message)
    $now = Get-Date -Format o
    Add-Content -Path $StateLog -Value "$now $Message" -Encoding UTF8
}

$freeText = (& nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>$null | Select-Object -First 1).Trim()
[int]$freeMiB = $freeText
if ($freeMiB -lt $MinFreeMiB) {
    Write-State "WAIT_300_NOEARLY_52G name=$Name reason=insufficient_free_gpu_mib free_mib=$freeMiB required_mib=$MinFreeMiB"
    Write-Host "WAIT free_mib=$freeMiB required_mib=$MinFreeMiB name=$Name"
    exit 3
}

$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    $_.CommandLine.Contains($Base) -and
    $_.CommandLine.Contains("train_ultralytics_section_detector.py") -and
    $_.CommandLine.Contains("300ep_noearly")
}

if (Test-Path $Best) {
    Write-State "SKIP_300_NOEARLY_52G model=$Model name=$Name best_exists=$Best"
    Write-Host "SKIP_BEST_EXISTS $Best"
    exit 0
}

if ($existing) {
    Write-State "EXISTING_300_NOEARLY_52G name=$Name pid=$($existing.ProcessId)"
    Write-Host "EXISTING_PROCESS pid=$($existing.ProcessId)"
    $existing | Select-Object ProcessId, CommandLine | Format-List
    exit 2
}

$cmd = "cd /d `"$Base`" && `"$Python`" `"$TrainScript`" --data `"$Data`" --model $Model --project `"$Project`" --name $Name --epochs 300 --patience 0 --imgsz 1280 --batch 0.70 --device 0 --workers 2 > `"$Log`" 2> `"$Err`""
Write-State "MANUAL_LAUNCH_300_NOEARLY_52G model=$Model name=$Name min_free_mib=$MinFreeMiB free_mib=$freeMiB epochs=300 patience=0 imgsz=1280 batch=0.70 note=separate_experiment_no_early_stopping_cmd_detach"
$process = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $cmd -WorkingDirectory $Base -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 8
$alive = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and $_.CommandLine.Contains($Name)
}

Write-State "MANUAL_LAUNCH_300_NOEARLY_52G_PID name=$Name cmd_pid=$($process.Id) alive=$([bool]$alive)"
Write-Host "LAUNCHED cmd_pid=$($process.Id) alive=$([bool]$alive) free_mib=$freeMiB name=$Name"
if ($alive) {
    $alive | Select-Object ProcessId, CommandLine | Format-List
}
if (Test-Path $Log) {
    Write-Host "LOG_TAIL"
    Get-Content $Log -Tail 25
}
if (Test-Path $Err) {
    Write-Host "ERR_TAIL"
    Get-Content $Err -Tail 20
}
