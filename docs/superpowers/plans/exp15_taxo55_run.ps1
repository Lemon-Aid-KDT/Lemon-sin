# exp15 taxo55: 4클래스 drop + (exp15a=AIHub만 / exp15b=AIHub+realworld). yolo26s, val=AIHub taxo55 val.
# 사용: & exp15_taxo55_run.ps1 -Data <data.yaml> -RunName <name>
# 주의: UTF-8 BOM 저장 필수(PS5.1), splatting.

param(
    [string]$Data = "C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo55\data.yaml",
    [string]$RunName = "exp15a_taxo55_aihub_pc1",
    [int]$Batch = 16,
    [int]$Epochs = 50,
    [int]$Seed = 42,
    [int]$Patience = 15
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$yolo     = "C:\Lemon-sin\backend\.venv\Scripts\yolo.exe"
$project  = "C:\Lemon-sin\runs\food_yolo"
$fullName = "$RunName" + "_s$Seed" + "_b$Batch" + "_w8_cache_disk_det_true"
$dsRoot   = Split-Path $Data -Parent

Write-Host ""
Write-Host "=== 사전 점검 ===" -ForegroundColor Cyan
if (-not (Test-Path $yolo)) { Write-Host "ERROR: yolo.exe 없음" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $Data)) { Write-Host "ERROR: data.yaml 없음 -> $Data" -ForegroundColor Red; exit 1 }
Write-Host "OK: yolo.exe, data.yaml" -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $project | Out-Null

Write-Host ""
Write-Host "=== labels.cache 점검(손상 hang 예방: archive 이동) ===" -ForegroundColor Cyan
$archive = "$dsRoot\_archive_cache"
foreach ($c in @("$dsRoot\train\labels.cache", "$dsRoot\val\labels.cache")) {
    if (Test-Path $c) {
        New-Item -ItemType Directory -Force -Path $archive | Out-Null
        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        Move-Item $c (Join-Path $archive "$($c.Split('\')[-2])_labels.cache.$stamp") -Force
        Write-Host "MOVED: $c" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== 데이터셋 파일 개수 ===" -ForegroundColor Cyan
foreach ($s in @('train\images','train\labels','val\images','val\labels')) {
    $cnt = (Get-ChildItem (Join-Path $dsRoot $s) -File -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host ("  {0,-14} : {1}" -f $s, $cnt)
}

Write-Host ""
Write-Host "=== GPU ===" -ForegroundColor Cyan
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader,nounits

Write-Host ""
Write-Host "=== exp15 학습 시작: $fullName (seed=$Seed) ===" -ForegroundColor Cyan
Write-Host "[주의] 시작 로그에서 optimizer(MuSGD/AdamW)/lr 확인" -ForegroundColor Yellow
Write-Host ""

$trainArgs = @(
    "detect", "train",
    "model=yolo26s.pt",
    "data=$Data",
    "epochs=$Epochs",
    "imgsz=640",
    "batch=$Batch",
    "workers=8",
    "cache=disk",
    "device=0",
    "seed=$Seed",
    "deterministic=true",
    "patience=$Patience",
    "plots=false",
    "project=$project",
    "name=$fullName"
)
& $yolo @trainArgs
