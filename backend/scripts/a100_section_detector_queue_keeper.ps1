$ErrorActionPreference = "Stop"

$Base = "G:\lemon-aid\section_dataset_v2_panel_pseudo_a100"
$Python = "G:\anaconda3\envs\lemonaid_project\python.exe"
$TrainScript = Join-Path $Base "train_ultralytics_section_detector.py"
$Data = Join-Path $Base "dataset.yaml"
$Project = Join-Path $Base "runs"
$StateLog = Join-Path $Base "queue_keeper.state.log"
$MinFreeMiB = 52000
$SleepSeconds = 180
$Epochs = 200
$Patience = 200
$Batch = 0.7

$Runs = @(
    @{
        Model = "yolov8s.pt"
        Name = "sec_v2_panel_pseudo_a100_yolov8s_200ep_noearly"
    },
    @{
        Model = "yolo26s.pt"
        Name = "sec_v2_panel_pseudo_a100_yolo26s_200ep_noearly"
    }
)

function Write-State {
    param([string]$Message)
    $now = Get-Date -Format o
    Add-Content -Path $StateLog -Value "$now $Message" -Encoding UTF8
}

function Get-FreeGpuMemoryMiB {
    $value = & nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>$null | Select-Object -First 1
    if (-not $value) {
        return 0
    }
    return [int]($value.Trim())
}

function Has-ThisDatasetProcess {
    $escaped = [regex]::Escape($Base)
    $proc = Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        $_.CommandLine -match $escaped -and
        $_.CommandLine -match "train_ultralytics_section_detector\.py"
    }
    return [bool]$proc
}

New-Item -ItemType Directory -Force $Project | Out-Null
Write-State "QUEUE_START base=$Base min_free_mib=$MinFreeMiB"

foreach ($run in $Runs) {
    $name = $run.Name
    $model = $run.Model
    $best = Join-Path $Project "$name\weights\best.pt"
    $log = Join-Path $Base "train_$name.log"
    $err = Join-Path $Base "train_$name.err"

    if (Test-Path $best) {
        Write-State "SKIP model=$model name=$name best_exists=$best"
        continue
    }

    while ($true) {
        if (Has-ThisDatasetProcess) {
            Write-State "WAIT name=$name reason=existing_dataset_process"
            Start-Sleep -Seconds $SleepSeconds
            continue
        }

        $free = Get-FreeGpuMemoryMiB
        if ($free -lt $MinFreeMiB) {
            Write-State "WAIT name=$name reason=insufficient_free_gpu_mib free_mib=$free required_mib=$MinFreeMiB"
            Start-Sleep -Seconds $SleepSeconds
            continue
        }

        Write-State "LAUNCH model=$model name=$name free_mib=$free epochs=$Epochs patience=$Patience imgsz=1280 batch=$Batch"
        Add-Content -Path $log -Value "`n===== SECTION_DETECTOR_LAUNCH $(Get-Date -Format o) model=$model =====" -Encoding UTF8
        & $Python $TrainScript `
            --data $Data `
            --model $model `
            --project $Project `
            --name $name `
            --epochs $Epochs `
            --patience $Patience `
            --imgsz 1280 `
            --batch $Batch `
            --device 0 `
            --workers 2 `
            >> $log 2>> $err
        $code = $LASTEXITCODE
        Write-State "EXIT model=$model name=$name code=$code"
        break
    }
}

Write-State "QUEUE_DONE"
