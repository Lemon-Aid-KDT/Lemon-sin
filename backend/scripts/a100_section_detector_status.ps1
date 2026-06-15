$ErrorActionPreference = "Stop"

$Base = "G:\lemon-aid\section_dataset_v2_panel_pseudo_a100"
$TaskName = "LemonAidYolo26s300NoEarly52G"

Write-Host "---FILE---"
Test-Path (Join-Path $Base "a100_section_detector_300_noearly_task.ps1")

Write-Host "---TASK---"
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    $task | Select-Object TaskName, State
    $task.Actions | Format-List *
    Get-ScheduledTaskInfo -TaskName $TaskName | Select-Object LastRunTime, LastTaskResult, NextRunTime
} else {
    Write-Host "NO_TASK"
}

Write-Host "---GPU---"
& nvidia-smi --query-gpu=memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits

Write-Host "---PROC---"
Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -and (
            $_.CommandLine.Contains($Base) -or
            $_.CommandLine.Contains("train_ultralytics_section_detector.py") -or
            $_.CommandLine.Contains("300ep_noearly")
        )
    } |
    Select-Object ProcessId, Name, CommandLine

Write-Host "---STATE---"
$stateLog = Join-Path $Base "queue_keeper.state.log"
if (Test-Path $stateLog) {
    Get-Content $stateLog -Tail 30
}

Write-Host "---RUNS---"
$runs = Join-Path $Base "runs"
if (Test-Path $runs) {
    Get-ChildItem $runs -Directory |
        Where-Object { $_.Name -like "*300ep*" } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 10 Name, LastWriteTime

    Write-Host "---RUN_FILES---"
    Get-ChildItem $runs -Directory |
        Where-Object { $_.Name -like "*300ep*" } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 5 |
        ForEach-Object {
            Write-Host ("### " + $_.Name)
            Get-ChildItem $_.FullName -Recurse -File |
                Sort-Object LastWriteTime -Descending |
                Select-Object -First 12 FullName, Length, LastWriteTime
        }
}
