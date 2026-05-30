[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Re-evaluate the completed exp03 YOLOv8n run on the capped validation split.

$yolo = "C:\Lemon-sin\backend\.venv\Scripts\yolo.exe"
$dataYaml = "C:\Lemon-sin\data\food_images\processed\aihub_yolo_50_minority_aug_train500_val100\data.yaml"
$bestPt = "C:\Lemon-sin\runs\food_yolo\exp03_yolov8n_balanced500_pc1_b48_w8_cache_disk_det_true\weights\best.pt"
$project = "C:\Lemon-sin\runs\food_yolo"
$runName = "exp03_yolov8n_balanced500_pc1_valcap100"

if (-not (Test-Path $yolo)) {
    Write-Host "ERROR: yolo.exe not found: $yolo" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $dataYaml)) {
    Write-Host "ERROR: data.yaml not found: $dataYaml" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $bestPt)) {
    Write-Host "ERROR: best.pt not found: $bestPt" -ForegroundColor Red
    exit 1
}

Write-Host "Validation baseline: $runName" -ForegroundColor Cyan

& $yolo detect val `
    model="$bestPt" `
    data="$dataYaml" `
    imgsz=640 `
    batch=48 `
    device=0 `
    plots=true `
    save_json=true `
    project="$project" `
    name="$runName"
