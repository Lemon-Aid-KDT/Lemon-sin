# exp08: YOLO11s + taxo63 balanced, batch=16 (exp07 yolo26s와 동일 b16 조건 비교)
# 변경 변수 = 모델(yolo26s -> yolo11s). exp07과 batch/데이터/설정 동일 -> 공정한 모델 비교.
# 비교: exp07(yolo26s b16) vs exp08(yolo11s b16). UTF-8 BOM + splatting(백틱 금지).

param(
    [int]$Batch = 16,
    [int]$Epochs = 50,
    [string]$RunName = "exp08_yolo11s_taxo63bal500_pc1"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$yolo       = "C:\Lemon-sin\backend\.venv\Scripts\yolo.exe"
$venvPython = "C:\Lemon-sin\backend\.venv\Scripts\python.exe"
$dataYaml   = "C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo63_bal500\data.yaml"
$project    = "C:\Lemon-sin\runs\food_yolo"
$fullName   = "$RunName" + "_b$Batch" + "_w8_cache_disk_det_true"
$dsRoot     = "C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo63_bal500"
$trainCache = "$dsRoot\train\labels.cache"
$valCache   = "$dsRoot\val\labels.cache"

Write-Host ""
Write-Host "=== 사전 점검 ===" -ForegroundColor Cyan
if (-not (Test-Path $yolo))     { Write-Host "ERROR: yolo.exe 없음" -ForegroundColor Red; exit 1 }
Write-Host "OK: yolo.exe" -ForegroundColor Green
if (-not (Test-Path $dataYaml)) { Write-Host "ERROR: data.yaml 없음 -> $dataYaml" -ForegroundColor Red; exit 1 }
Write-Host "OK: data.yaml" -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $project | Out-Null

Write-Host ""
Write-Host "=== labels.cache 점검 (손상 hang 예방: archive 이동) ===" -ForegroundColor Cyan
$archive = "$dsRoot\_archive_cache"
$cacheFound = $false
foreach ($c in @($trainCache, $valCache)) {
    if (Test-Path $c) {
        $cacheFound = $true
        New-Item -ItemType Directory -Force -Path $archive | Out-Null
        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $destName = "$($c.Split('\')[-2])_labels.cache.$stamp"
        Move-Item $c (Join-Path $archive $destName) -Force
        Write-Host "MOVED: $c -> $archive\$destName" -ForegroundColor Yellow
    }
}
if (-not $cacheFound) { Write-Host "OK: labels.cache 없음 -> fresh scan" -ForegroundColor Green }

Write-Host ""
Write-Host "=== GPU ===" -ForegroundColor Cyan
nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits

Write-Host ""
Write-Host "=== exp08 학습 시작 (YOLO11s + taxo63 balanced, b16) ===" -ForegroundColor Cyan
Write-Host "name:  $fullName" -ForegroundColor White
Write-Host "model: yolo11s.pt | batch: $Batch | epochs: $Epochs | imgsz: 640 | workers: 8 | cache: disk | det: true | seed: 42" -ForegroundColor White
Write-Host ""

$trainArgs = @(
    "detect", "train",
    "model=yolo11s.pt",
    "data=$dataYaml",
    "epochs=$Epochs",
    "imgsz=640",
    "batch=$Batch",
    "workers=8",
    "cache=disk",
    "device=0",
    "seed=42",
    "deterministic=true",
    "patience=15",
    "plots=false",
    "project=$project",
    "name=$fullName"
)
& $yolo @trainArgs
