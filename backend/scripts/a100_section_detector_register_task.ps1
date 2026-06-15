$ErrorActionPreference = "Stop"

$TaskName = "LemonAidYolo26s300NoEarly52G"
$Cmd = "G:\lemon-aid\section_dataset_v2_panel_pseudo_a100\a100_section_detector_300_noearly_task.cmd"
$StateLog = "G:\lemon-aid\section_dataset_v2_panel_pseudo_a100\queue_keeper.state.log"

function Write-State {
    param([string]$Message)
    $now = Get-Date -Format o
    Add-Content -Path $StateLog -Value "$now $Message" -Encoding UTF8
}

schtasks.exe /Delete /TN $TaskName /F | Out-Null
$start = (Get-Date).AddMinutes(3).ToString("HH:mm")
schtasks.exe /Create /TN $TaskName /SC ONCE /ST $start /TR $Cmd /F | Out-Null
schtasks.exe /Run /TN $TaskName | Out-Null
Write-State "TASK_REGISTERED_AND_RUN_300_NOEARLY_52G task=$TaskName cmd=$Cmd start=$start"

schtasks.exe /Query /TN $TaskName /V /FO LIST
