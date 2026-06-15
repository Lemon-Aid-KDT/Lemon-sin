$ErrorActionPreference = "Stop"

$Base = "G:\lemon-aid\section_dataset_v2_panel_pseudo_a100"
$Cmd = Join-Path $Base "a100_section_detector_300_noearly_direct.cmd"
$StateLog = Join-Path $Base "queue_keeper.state.log"

function Write-State {
    param([string]$Message)
    $now = Get-Date -Format o
    Add-Content -Path $StateLog -Value "$now $Message" -Encoding UTF8
}

Write-State "CMDSTART_REQUEST_300_NOEARLY cmd=$Cmd"
$proc = Start-Process -FilePath $Cmd -WorkingDirectory $Base -WindowStyle Minimized -PassThru
Write-State "CMDSTART_REQUEST_PID_300_NOEARLY pid=$($proc.Id)"
Start-Sleep -Seconds 8

Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -and (
            $_.CommandLine.Contains("sec_v2_panel_pseudo_a100_yolo26s_300ep_noearly_52g_b070_cmdstart_v1") -or
            $_.CommandLine.Contains("a100_section_detector_300_noearly_direct.cmd")
        )
    } |
    Select-Object ProcessId, Name, CommandLine
