param(
    [int]$Batch = 48,
    [int]$Epochs = 50,
    [string]$RunName = "exp05_yolov8n_minoritydup_train500_val100_pc1"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Train YOLOv8n on duplicate-oversampled minority train data and capped validation data.

$yolo = "C:\Lemon-sin\backend\.venv\Scripts\yolo.exe"
$venvPython = "C:\Lemon-sin\backend\.venv\Scripts\python.exe"
$dataYaml = "C:\Lemon-sin\data\food_images\processed\aihub_yolo_50_minority_dup_train500_val100\data.yaml"
$project = "C:\Lemon-sin\runs\food_yolo"
$fullName = "$RunName" + "_b$Batch" + "_w8_cache_disk_det_true"
$datasetRoot = "C:\Lemon-sin\data\food_images\processed\aihub_yolo_50_minority_dup_train500_val100"
$trainCache = Join-Path $datasetRoot "train\labels.cache"
$valCache = Join-Path $datasetRoot "val\labels.cache"

if (-not (Test-Path $yolo)) {
    Write-Host "ERROR: yolo.exe not found: $yolo" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $dataYaml)) {
    Write-Host "ERROR: data.yaml not found: $dataYaml" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $project | Out-Null

$archive = Join-Path $datasetRoot "_archive_cache"
foreach ($cachePath in @($trainCache, $valCache)) {
    if (Test-Path $cachePath) {
        New-Item -ItemType Directory -Force -Path $archive | Out-Null
        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $destName = "$($cachePath.Split('\')[-2])_labels.cache.$stamp"
        Move-Item $cachePath (Join-Path $archive $destName) -Force
        Write-Host "Moved cache: $destName" -ForegroundColor Yellow
    }
}

Write-Host "Dataset:" -ForegroundColor Cyan
Get-Content $dataYaml -TotalCount 6

Write-Host "File counts:" -ForegroundColor Cyan
foreach ($splitPath in @("train\images", "train\labels", "val\images", "val\labels")) {
    $count = (Get-ChildItem (Join-Path $datasetRoot $splitPath) -File | Measure-Object).Count
    Write-Host "  $splitPath : $count"
}

Write-Host "GPU:" -ForegroundColor Cyan
nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits

Write-Host "PyTorch CUDA:" -ForegroundColor Cyan
& $venvPython -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"

Write-Host "Training run: $fullName" -ForegroundColor Cyan

& $yolo detect train `
    model=yolov8n.pt `
    data="$dataYaml" `
    epochs=$Epochs `
    imgsz=640 `
    batch=$Batch `
    workers=8 `
    cache=disk `
    device=0 `
    seed=0 `
    deterministic=true `
    patience=100 `
    plots=true `
    project="$project" `
    name="$fullName"
