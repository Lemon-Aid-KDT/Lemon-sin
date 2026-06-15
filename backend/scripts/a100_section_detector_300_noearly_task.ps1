$ErrorActionPreference = "Stop"

$Base = "G:\lemon-aid\section_dataset_v2_panel_pseudo_a100"
$Python = "G:\anaconda3\envs\lemonaid_project\python.exe"
$TrainScript = Join-Path $Base "train_ultralytics_section_detector.py"
$Data = Join-Path $Base "dataset.yaml"
$Project = Join-Path $Base "runs"
$StateLog = Join-Path $Base "queue_keeper.state.log"
$Model = "yolo26s.pt"
$Name = "sec_v2_panel_pseudo_a100_yolo26s_300ep_noearly_52g_b070_schtask_v1"
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
    Write-State "WAIT_300_NOEARLY_52G_TASK name=$Name reason=insufficient_free_gpu_mib free_mib=$freeMiB required_mib=$MinFreeMiB"
    exit 3
}

$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and
    $_.CommandLine.Contains($Base) -and
    $_.CommandLine.Contains("train_ultralytics_section_detector.py") -and
    $_.CommandLine.Contains("300ep_noearly")
}
if ($existing) {
    Write-State "EXISTING_300_NOEARLY_52G_TASK name=$Name pid=$($existing.ProcessId)"
    exit 2
}

if (Test-Path $Best) {
    Write-State "SKIP_300_NOEARLY_52G_TASK name=$Name best_exists=$Best"
    exit 0
}

Set-Location $Base
Write-State "TASK_LAUNCH_300_NOEARLY_52G model=$Model name=$Name min_free_mib=$MinFreeMiB free_mib=$freeMiB epochs=300 patience=0 imgsz=1280 batch=0.70 note=scheduled_task_foreground"
& $Python $TrainScript `
    --data $Data `
    --model $Model `
    --project $Project `
    --name $Name `
    --epochs 300 `
    --patience 0 `
    --imgsz 1280 `
    --batch 0.70 `
    --device 0 `
    --workers 2 > $Log 2> $Err
$exitCode = $LASTEXITCODE
Write-State "TASK_EXIT_300_NOEARLY_52G model=$Model name=$Name code=$exitCode"
exit $exitCode
