<#
.SYNOPSIS
Start the Windows A100 PaddleOCR operator script as a detached background run.

.DESCRIPTION
This launcher uses Win32_Process.Create instead of Start-Process because SSH
sessions on the Windows A100 host can drop or truncate redirected child output.
It keeps all output in a mode-specific combined log under the A100 workspace and
does not print private labels, crop paths, or provider payloads.
#>

param(
    [ValidateSet("dataset", "smoke", "full", "export")]
    [string]$Mode = "full",

    [string]$WorkspaceRoot = "G:\lemon-aid\paddleocr_rec_work",
    [string]$DatasetVersion = "v2",
    [string]$RunSuffix = "v2_clean"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $WorkspaceRoot "Lemon-Aid\backend\scripts\run_a100_paddleocr_windows_training.ps1"
$workdir = Join-Path $WorkspaceRoot "Lemon-Aid"
$logPath = Join-Path $WorkspaceRoot "$Mode.$RunSuffix.combined.log"

if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
    throw "A100 run script is missing: $scriptPath"
}

$command = 'cmd.exe /c powershell -NoProfile -ExecutionPolicy Bypass -File "{0}" -Mode {1} -DatasetVersion {2} -RunSuffix {3} > "{4}" 2>&1' -f $scriptPath, $Mode, $DatasetVersion, $RunSuffix, $logPath
$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = $command
    CurrentDirectory = $workdir
}

if ($result.ReturnValue -ne 0) {
    throw "Win32_Process.Create failed. return_value=$($result.ReturnValue)"
}

Write-Host "created mode=$Mode process_id=$($result.ProcessId) return_value=$($result.ReturnValue) log=$logPath"
