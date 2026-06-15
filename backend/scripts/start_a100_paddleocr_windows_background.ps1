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
    [ValidateSet("dataset", "smoke", "full", "export", "early-stop")]
    [string]$Mode = "full",

    [string]$WorkspaceRoot = "G:\lemon-aid\paddleocr_rec_work",
    [string]$DatasetVersion = "v2",
    [string]$RunSuffix = "v2_clean",
    [int]$BatchSize = 128,
    [int]$SamplerFirstBatchSize = 0,
    [int]$Epochs = 100,
    [double]$LearningRate = 0.0001,
    [string]$Checkpoints = "",
    [string]$PretrainedModel = "",
    [string]$MixedTrainLabelFiles = "",
    [string]$TrainRatioList = "",
    [switch]$RequireMixedTraining,
    [switch]$DisableRecConAug,
    [ValidateRange(1, 100)]
    [int]$EarlyStopPatienceEpochs = 5,
    [ValidateRange(10, 3600)]
    [int]$EarlyStopPollSeconds = 60
)

$ErrorActionPreference = "Stop"

$runScriptPath = Join-Path $WorkspaceRoot "Lemon-Aid\backend\scripts\run_a100_paddleocr_windows_training.ps1"
$watchScriptPath = Join-Path $WorkspaceRoot "Lemon-Aid\backend\scripts\watch_a100_paddleocr_windows_early_stop.ps1"
$workdir = Join-Path $WorkspaceRoot "Lemon-Aid"

function ConvertTo-SingleQuotedPowerShellArgument {
    param([string]$Value)

    return "'" + $Value.Replace("'", "''") + "'"
}

function ConvertTo-PowerShellFloatArgument {
    param([double]$Value)

    return $Value.ToString("0.################", [Globalization.CultureInfo]::InvariantCulture)
}

if ($Mode -eq "early-stop") {
    $scriptPath = $watchScriptPath
    $logPath = Join-Path $WorkspaceRoot "early_stop.$RunSuffix.combined.log"
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "A100 early-stop watcher is missing: $scriptPath"
    }
    $command = 'cmd.exe /c powershell -NoProfile -ExecutionPolicy Bypass -File "{0}" -RunSuffix {1} -PatienceEpochs {2} -PollSeconds {3} > "{4}" 2>&1' -f $scriptPath, $RunSuffix, $EarlyStopPatienceEpochs, $EarlyStopPollSeconds, $logPath
}
else {
    $scriptPath = $runScriptPath
    $logPath = Join-Path $WorkspaceRoot "$Mode.$RunSuffix.combined.log"
    $launchScriptPath = Join-Path $WorkspaceRoot "launch.$Mode.$RunSuffix.ps1"
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) {
        throw "A100 run script is missing: $scriptPath"
    }

    $learningRateArg = ConvertTo-PowerShellFloatArgument -Value $LearningRate
    $optionalArgs = " -BatchSize $BatchSize -Epochs $Epochs -LearningRate $learningRateArg"
    if ($SamplerFirstBatchSize -gt 0) {
        $optionalArgs += " -SamplerFirstBatchSize $SamplerFirstBatchSize"
    }
    if (-not [string]::IsNullOrWhiteSpace($Checkpoints)) {
        $optionalArgs += " -Checkpoints " + (ConvertTo-SingleQuotedPowerShellArgument -Value $Checkpoints)
    }
    if (-not [string]::IsNullOrWhiteSpace($PretrainedModel)) {
        $optionalArgs += " -PretrainedModel " + (ConvertTo-SingleQuotedPowerShellArgument -Value $PretrainedModel)
    }
    if (-not [string]::IsNullOrWhiteSpace($MixedTrainLabelFiles)) {
        $optionalArgs += " -MixedTrainLabelFiles " + (ConvertTo-SingleQuotedPowerShellArgument -Value $MixedTrainLabelFiles)
    }
    if (-not [string]::IsNullOrWhiteSpace($TrainRatioList)) {
        $optionalArgs += " -TrainRatioList " + (ConvertTo-SingleQuotedPowerShellArgument -Value $TrainRatioList)
    }
    if ($RequireMixedTraining) {
        $optionalArgs += " -RequireMixedTraining"
    }
    if ($DisableRecConAug) {
        $optionalArgs += " -DisableRecConAug"
    }

    $scriptInvocation = '& {0} -Mode {1} -DatasetVersion {2} -RunSuffix {3}{4}' -f `
        (ConvertTo-SingleQuotedPowerShellArgument -Value $scriptPath),
        (ConvertTo-SingleQuotedPowerShellArgument -Value $Mode),
        (ConvertTo-SingleQuotedPowerShellArgument -Value $DatasetVersion),
        (ConvertTo-SingleQuotedPowerShellArgument -Value $RunSuffix),
        $optionalArgs
    Set-Content -LiteralPath $launchScriptPath -Value @(
        '$ErrorActionPreference = "Stop"',
        $scriptInvocation
    ) -Encoding UTF8

    $command = 'cmd.exe /c powershell -NoProfile -ExecutionPolicy Bypass -File "{0}" > "{1}" 2>&1' -f $launchScriptPath, $logPath
}

$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = $command
    CurrentDirectory = $workdir
}

if ($result.ReturnValue -ne 0) {
    throw "Win32_Process.Create failed. return_value=$($result.ReturnValue)"
}

Write-Host "created mode=$Mode process_id=$($result.ProcessId) return_value=$($result.ReturnValue) log=$logPath"
