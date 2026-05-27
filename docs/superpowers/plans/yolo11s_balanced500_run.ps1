[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# PC2 YOLO11s + balanced_500 학습
# exp03_yolo11s_balanced500_pc2_b<BATCH>_w8_cache_disk_det_true
# 사전: docs/superpowers/specs/2026-05-27-aihub-yolo-balanced500-yolo11s-design.md

param(
    [int]$Batch = 32,
    [int]$Epochs = 50,
    [string]$RunName = "exp03_yolo11s_balanced500_pc2"
)

$yolo       = "C:\Lemon-Aid\Lemon-sin\backend\.venv\Scripts\yolo.exe"
$venvPython = "C:\Lemon-Aid\Lemon-sin\backend\.venv\Scripts\python.exe"
$dataYaml   = "C:\Lemon-Aid\Lemon-sin\data\food_images\aihub_yolo_50_balanced_500\data.yaml"
$project    = "C:\Lemon-Aid\Lemon-sin\runs\food_yolo"
$fullName   = "$RunName" + "_b$Batch" + "_w8_cache_disk_det_true"
$trainCache = "C:\Lemon-Aid\Lemon-sin\data\food_images\aihub_yolo_50_balanced_500\train\labels.cache"
$valCache   = "C:\Lemon-Aid\Lemon-sin\data\food_images\aihub_yolo_50_balanced_500\val\labels.cache"

Write-Host ""
Write-Host "=== 사전 점검 ===" -ForegroundColor Cyan

if (-not (Test-Path $yolo)) {
    Write-Host "ERROR: yolo.exe 없음" -ForegroundColor Red; exit 1
}
Write-Host "OK: yolo.exe 존재" -ForegroundColor Green

if (-not (Test-Path $dataYaml)) {
    Write-Host "ERROR: data.yaml 없음 -> $dataYaml" -ForegroundColor Red
    Write-Host "       Task 7의 다운샘플 실행을 먼저 끝내세요." -ForegroundColor Yellow
    exit 1
}
Write-Host "OK: data.yaml 존재" -ForegroundColor Green

New-Item -ItemType Directory -Force -Path $project | Out-Null
Write-Host "OK: project 폴더 준비 ($project)" -ForegroundColor Green

Write-Host ""
Write-Host "=== data.yaml (앞 4줄) ===" -ForegroundColor Cyan
Get-Content $dataYaml -TotalCount 4

Write-Host ""
Write-Host "=== labels.cache 점검 ===" -ForegroundColor Cyan
$archive = "C:\Lemon-Aid\Lemon-sin\data\food_images\aihub_yolo_50_balanced_500\_archive_cache"
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
if (-not $cacheFound) {
    Write-Host "OK: labels.cache 없음 -> fresh scan" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== 데이터셋 파일 개수 ===" -ForegroundColor Cyan
$dst = "C:\Lemon-Aid\Lemon-sin\data\food_images\aihub_yolo_50_balanced_500"
foreach ($s in @('train\images','train\labels','val\images','val\labels')) {
    $p = Join-Path $dst $s
    $cnt = (Get-ChildItem $p -File -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host "  $s : $cnt files"
}

Write-Host ""
Write-Host "=== GPU ===" -ForegroundColor Cyan
nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits

Write-Host ""
Write-Host "=== PyTorch CUDA ===" -ForegroundColor Cyan
& $venvPython -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"

Write-Host ""
Write-Host "=== C 드라이브 여유 ===" -ForegroundColor Cyan
$c = Get-PSDrive C
"$([math]::Round($c.Free/1GB,1)) GB"

Write-Host ""
Write-Host "=== YOLO11s + balanced_500 학습 시작 ===" -ForegroundColor Cyan
Write-Host "name:   $fullName" -ForegroundColor White
Write-Host "model:  yolo11s.pt | batch: $Batch | epochs: $Epochs | imgsz: 640 | workers: 8 | cache: disk" -ForegroundColor White
Write-Host ""

& $yolo detect train `
    model=yolo11s.pt `
    data="$dataYaml" `
    epochs=$Epochs `
    imgsz=640 `
    batch=$Batch `
    workers=8 `
    cache=disk `
    device=0 `
    seed=42 `
    deterministic=true `
    patience=15 `
    plots=false `
    project="$project" `
    name=$fullName
