<#
.SYNOPSIS
Run the Windows A100 PaddleOCR recognition preflight, dataset gate, smoke, full,
or export step.

.DESCRIPTION
This operator script is intended for the VS Code Remote SSH terminal on the A100
Windows server. It performs count-only dataset validation before any training,
keeps preflight usable before the private dataset has been copied, and never
prints label text or provider payloads.

Official references:
- https://www.paddleocr.ai/latest/en/version3.x/installation.html
- https://www.paddleocr.ai/latest/en/version2.x/ppocr/model_train/recognition.html
- https://www.paddlepaddle.org.cn/documentation/docs/install/pip/windows-pip_en.html
- https://raw.githubusercontent.com/PaddlePaddle/PaddleOCR/main/configs/rec/PP-OCRv5/multi_language/korean_PP-OCRv5_mobile_rec.yml
#>

param(
    [ValidateSet("preflight", "dataset", "smoke", "full", "export")]
    [string]$Mode = "preflight",

    [string]$WorkspaceRoot = "G:\lemon-aid\paddleocr_rec_work",
    [string]$DatasetVersion = "v2",
    [string]$RunSuffix = "v2_clean",
    [string]$PythonExe = "",
    [string]$GpuId = "0",
    [int]$BatchSize = 128,
    [int]$SamplerFirstBatchSize = 0,
    [int]$Epochs = 100,
    [double]$LearningRate = 0.0001,
    [string]$Checkpoints = "",
    [string]$MixedTrainLabelFiles = "",
    [string]$TrainRatioList = "",
    [switch]$RequireMixedTraining,
    [switch]$DisableRecConAug,
    [string]$PretrainedModel = "pretrain\korean_PP-OCRv5_mobile_rec_pretrained",
    [string]$PretrainedModelUrl = "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_pretrained_model/korean_PP-OCRv5_mobile_rec_pretrained.pdparams"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

if ([string]::IsNullOrWhiteSpace($RunSuffix)) {
    $RunSuffix = $DatasetVersion
}
if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = Join-Path $WorkspaceRoot ".venv-paddle-rec-v2-clean\Scripts\python.exe"
}

$DatasetDir = Join-Path $WorkspaceRoot "rec_dataset\$DatasetVersion"
$PaddleOCRRoot = Join-Path $WorkspaceRoot "PaddleOCR"
$CountGateScript = Join-Path $PSScriptRoot "validate_paddleocr_rec_dataset_counts.py"
$CountGateSummary = Join-Path $WorkspaceRoot "paddleocr-rec-crawling-$DatasetVersion-count-gate.json"
$TrainLabel = Join-Path $DatasetDir "rec\rec_gt_train.txt"
$ValLabel = Join-Path $DatasetDir "rec\rec_gt_val.txt"
$DictFile = Join-Path $DatasetDir "dict.txt"
$SmokeOutput = "output\supplement_rec_crawling_${RunSuffix}_smoke"
$FullOutput = "output\supplement_rec_crawling_$RunSuffix"

function Get-TextLineCount {
    param([string]$Path)

    $count = 0
    Get-Content -LiteralPath $Path -ReadCount 1000 -Encoding UTF8 | ForEach-Object {
        $count += $_.Count
    }
    return $count
}

function Assert-FileLineCount {
    param(
        [string]$Path,
        [int]$Expected,
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Name file is missing."
    }
    $actual = Get-TextLineCount -Path $Path
    Write-Host "$Name lines: $actual"
    if ($actual -ne $Expected) {
        throw "$Name line count mismatch. expected=$Expected actual=$actual"
    }
}

function Assert-DatasetGate {
    Write-Host "Checking count-only dataset gate..."
    if (Test-Path -LiteralPath $CountGateScript -PathType Leaf) {
        & $PythonExe $CountGateScript `
            --dataset-dir $DatasetDir `
            --summary-output $CountGateSummary
        if ($LASTEXITCODE -ne 0) {
            throw "Dataset count gate failed."
        }
        Write-Host "Dataset gate passed."
        return
    }

    Assert-FileLineCount -Path $TrainLabel -Expected 70778 -Name "train"
    Assert-FileLineCount -Path $ValLabel -Expected 6828 -Name "val"
    Assert-FileLineCount -Path $DictFile -Expected 1066 -Name "dict"
    Write-Host "Dataset gate passed."
}

function Assert-ExportInputs {
    Write-Host "Checking export inputs..."
    Assert-FileLineCount -Path $DictFile -Expected 1066 -Name "dict"
    $bestCheckpoint = Join-Path $PaddleOCRRoot "$FullOutput\best_accuracy"
    $bestParams = "$bestCheckpoint.pdparams"
    if (-not (Test-Path -LiteralPath $bestParams -PathType Leaf)) {
        throw "best_accuracy checkpoint parameters are missing: $bestParams"
    }
    Write-Host "Export inputs passed. checkpoint_prefix=$bestCheckpoint"
}

function Resolve-PaddleOCRConfig {
    $candidates = @(
        "configs\rec\PP-OCRv5\multi_language\korean_PP-OCRv5_mobile_rec.yml"
    )
    foreach ($candidate in $candidates) {
        $path = Join-Path $PaddleOCRRoot $candidate
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            return $candidate
        }
    }
    throw "korean_PP-OCRv5_mobile_rec.yml was not found under the PaddleOCR checkout."
}

function Resolve-EffectivePaddleOCRConfig {
    $configPath = Resolve-PaddleOCRConfig
    if (-not $DisableRecConAug) {
        return $configPath
    }

    $sourcePath = Join-Path $PaddleOCRRoot $configPath
    $generatedConfigDir = Join-Path $WorkspaceRoot "generated_configs"
    $targetPath = Join-Path $generatedConfigDir "korean_PP-OCRv5_mobile_rec_no_recconaug.yml"
    New-Item -ItemType Directory -Force -Path $generatedConfigDir | Out-Null

    $sourceLines = Get-Content -LiteralPath $sourcePath -Encoding UTF8
    $outputLines = New-Object System.Collections.Generic.List[string]
    $skippingRecConAug = $false
    foreach ($line in $sourceLines) {
        if ($line -match '^\s*-\s*RecConAug\s*:') {
            $skippingRecConAug = $true
            continue
        }
        if ($skippingRecConAug) {
            if ($line -match '^\s*-\s*[A-Za-z0-9_]+\s*:') {
                $skippingRecConAug = $false
            }
            else {
                continue
            }
        }
        $outputLines.Add($line)
    }

    Set-Content -LiteralPath $targetPath -Value $outputLines -Encoding UTF8
    Write-Host "Using generated PaddleOCR config with RecConAug disabled."
    return $targetPath
}

function Resolve-PretrainedModel {
    if ([string]::IsNullOrWhiteSpace($PretrainedModel)) {
        return ""
    }

    $modelPrefix = $PretrainedModel
    if ($modelPrefix.EndsWith(".pdparams")) {
        $modelPrefix = $modelPrefix.Substring(0, $modelPrefix.Length - ".pdparams".Length)
    }

    $modelFile = "$modelPrefix.pdparams"
    if ([System.IO.Path]::IsPathRooted($modelFile)) {
        $modelFilePath = $modelFile
    }
    else {
        $modelFilePath = Join-Path $PaddleOCRRoot $modelFile
    }

    if (-not (Test-Path -LiteralPath $modelFilePath -PathType Leaf)) {
        Write-Host "Downloading Korean PP-OCRv5 pretrained recognition weights..."
        $modelParent = Split-Path -Parent $modelFilePath
        New-Item -ItemType Directory -Force -Path $modelParent | Out-Null
        Invoke-WebRequest -Uri $PretrainedModelUrl -OutFile $modelFilePath
    }

    return $modelPrefix
}

function Resolve-Checkpoints {
    if ([string]::IsNullOrWhiteSpace($Checkpoints)) {
        return ""
    }

    $checkpointPrefix = $Checkpoints
    if ($checkpointPrefix.EndsWith(".pdparams")) {
        $checkpointPrefix = $checkpointPrefix.Substring(0, $checkpointPrefix.Length - ".pdparams".Length)
    }

    $checkpointFile = "$checkpointPrefix.pdparams"
    if ([System.IO.Path]::IsPathRooted($checkpointFile)) {
        $checkpointFilePath = $checkpointFile
    }
    else {
        $checkpointFilePath = Join-Path $PaddleOCRRoot $checkpointFile
    }

    if (-not (Test-Path -LiteralPath $checkpointFilePath -PathType Leaf)) {
        throw "Checkpoint weights are missing: $checkpointFilePath"
    }

    return $checkpointPrefix
}

function ConvertTo-PaddleStringListLiteral {
    param([string[]]$Items)

    $quotedItems = @()
    foreach ($item in $Items) {
        $escapedItem = $item.Replace("'", "''")
        $quotedItems += "'$escapedItem'"
    }
    return "[" + ($quotedItems -join ",") + "]"
}

function ConvertTo-PaddleFloatLiteral {
    param([double]$Value)

    return $Value.ToString("0.################", [Globalization.CultureInfo]::InvariantCulture)
}

function Resolve-TrainLabelFiles {
    if ([string]::IsNullOrWhiteSpace($MixedTrainLabelFiles)) {
        $labelFiles = @($TrainLabel)
    }
    else {
        $labelFiles = @(
            $MixedTrainLabelFiles -split "[;]" |
                ForEach-Object { $_.Trim() } |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        )
    }

    if ($RequireMixedTraining -and $labelFiles.Count -lt 2) {
        throw "Mixed training was required, but fewer than two training label files were provided."
    }

    foreach ($labelFile in $labelFiles) {
        if (-not (Test-Path -LiteralPath $labelFile -PathType Leaf)) {
            throw "Training label file is missing."
        }
    }

    return $labelFiles
}

function Resolve-TrainRatioOverride {
    param([int]$ExpectedCount)

    if ([string]::IsNullOrWhiteSpace($TrainRatioList)) {
        if ($ExpectedCount -gt 1) {
            throw "Mixed training label files were provided, but TrainRatioList is empty."
        }
        return ""
    }

    $trimmedRatioList = $TrainRatioList.Trim()
    if ($trimmedRatioList -notmatch '^\[[0-9.,\s]+\]$') {
        throw "TrainRatioList must be a numeric list literal, for example [1.0,0.1]."
    }

    $ratioBody = $trimmedRatioList.Substring(1, $trimmedRatioList.Length - 2)
    $ratioValues = @(
        $ratioBody -split "," |
            ForEach-Object { $_.Trim() } |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
    if ($ratioValues.Count -ne $ExpectedCount) {
        throw "TrainRatioList item count does not match training label file count."
    }

    return "Train.dataset.ratio_list=$trimmedRatioList"
}

function Invoke-CudaPreflight {
    Write-Host "Running NVIDIA/Paddle CUDA preflight..."
    Write-Host "Python executable: $PythonExe"
    & $PythonExe --version
    nvidia-smi
    & $PythonExe -c "import paddle; print('cuda', paddle.is_compiled_with_cuda()); print('gpus', paddle.device.cuda.device_count()); paddle.utils.run_check()"
}

function Invoke-PaddleOCRTrain {
    param(
        [string]$OutputDir,
        [int]$EpochCount
    )

    if (-not (Test-Path -LiteralPath $PaddleOCRRoot -PathType Container)) {
        throw "PaddleOCR root is missing."
    }

    Push-Location $PaddleOCRRoot
    try {
        $env:CUDA_VISIBLE_DEVICES = $GpuId
        $configPath = Resolve-EffectivePaddleOCRConfig
        $pretrainedModelArg = Resolve-PretrainedModel
        $checkpointArg = Resolve-Checkpoints
        $trainLabelFiles = Resolve-TrainLabelFiles
        $trainLabelFileList = ConvertTo-PaddleStringListLiteral -Items $trainLabelFiles
        $trainRatioOverride = Resolve-TrainRatioOverride -ExpectedCount $trainLabelFiles.Count
        $learningRateLiteral = ConvertTo-PaddleFloatLiteral -Value $LearningRate
        $effectiveSamplerFirstBatchSize = $SamplerFirstBatchSize
        if ($effectiveSamplerFirstBatchSize -le 0) {
            $effectiveSamplerFirstBatchSize = $BatchSize
        }
        Write-Host "Training label files: $($trainLabelFiles.Count)"
        $trainArgs = @(
            "tools\train.py",
            "-c", $configPath,
            "-o",
            "Global.save_model_dir=$OutputDir",
            "Global.epoch_num=$EpochCount",
            "Global.character_dict_path=$DictFile",
            "Global.use_space_char=True",
            "Optimizer.lr.learning_rate=$learningRateLiteral",
            "Train.dataset.data_dir=$DatasetDir",
            "Train.dataset.label_file_list=$trainLabelFileList",
            "Eval.dataset.data_dir=$DatasetDir",
            "Eval.dataset.label_file_list=['$ValLabel']",
            "Train.loader.batch_size_per_card=$BatchSize",
            "Train.sampler.first_bs=$effectiveSamplerFirstBatchSize",
            "Train.loader.num_workers=0",
            "Eval.loader.num_workers=0"
        )
        if (-not [string]::IsNullOrWhiteSpace($trainRatioOverride)) {
            $trainArgs += $trainRatioOverride
        }
        if (-not [string]::IsNullOrWhiteSpace($checkpointArg)) {
            $trainArgs += "Global.checkpoints=$checkpointArg"
        }
        elseif (-not [string]::IsNullOrWhiteSpace($pretrainedModelArg)) {
            $trainArgs += "Global.pretrained_model=$pretrainedModelArg"
        }
        & $PythonExe @trainArgs
        $trainExitCode = $LASTEXITCODE
        Write-Host "PaddleOCR train.py exit_code=$trainExitCode"
        if ($trainExitCode -ne 0) {
            throw "PaddleOCR train.py failed with exit_code=$trainExitCode"
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-PaddleOCRExport {
    Push-Location $PaddleOCRRoot
    try {
        $configPath = Resolve-EffectivePaddleOCRConfig
        $exportArgs = @(
            "tools\export_model.py",
            "-c", $configPath,
            "-o",
            "Global.pretrained_model=$FullOutput\best_accuracy",
            "Global.character_dict_path=$DictFile",
            "Global.save_inference_dir=$FullOutput\best_accuracy\inference"
        )
        & $PythonExe @exportArgs
        $exportExitCode = $LASTEXITCODE
        Write-Host "PaddleOCR export_model.py exit_code=$exportExitCode"
        if ($exportExitCode -ne 0) {
            throw "PaddleOCR export_model.py failed with exit_code=$exportExitCode"
        }
    }
    finally {
        Pop-Location
    }
}

switch ($Mode) {
    "preflight" {
        Invoke-CudaPreflight
    }
    "dataset" {
        Assert-DatasetGate
    }
    "smoke" {
        Invoke-CudaPreflight
        Assert-DatasetGate
        Invoke-PaddleOCRTrain -OutputDir $SmokeOutput -EpochCount 1
    }
    "full" {
        Invoke-CudaPreflight
        Assert-DatasetGate
        Invoke-PaddleOCRTrain -OutputDir $FullOutput -EpochCount $Epochs
    }
    "export" {
        Assert-ExportInputs
        Invoke-PaddleOCRExport
    }
}
