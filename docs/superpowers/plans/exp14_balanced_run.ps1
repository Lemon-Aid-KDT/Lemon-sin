# exp14 balanced: YOLO26s + taxo59. cap1500 균등화, 부족클래스 빈자리를 클린 selectstar(per-image 하베스트)로 채움.
# exp13(일부에 +800 초과보강->잠식) 대비 진단. baseline = exp11(noSS)·exp13(불균형). val 동일. seed=42.
# 박스: 모델 tight박스만(fallback 없음). 데이터셋은 _build_exp14_balanced.py 가 생성.
# 주의: ps1은 UTF-8 BOM 저장, 백틱 대신 splatting. MuSGD 자동선택 -> 시작 로그서 optimizer/lr 확인.

param(
    [int]$Batch = 16,
    [int]$Epochs = 50,
    [int]$Seed = 42,
    [string]$RunName = "exp14_balanced_pc1"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$yolo       = "C:\Lemon-sin\backend\.venv\Scripts\yolo.exe"
$venvPython = "C:\Lemon-sin\backend\.venv\Scripts\python.exe"
$dataYaml   = "C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_exp14_balanced\data.yaml"
$project    = "C:\Lemon-sin\runs\food_yolo"
$fullName   = "$RunName" + "_s$Seed" + "_b$Batch" + "_w8_cache_disk_det_true"
$dsRoot     = "C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_exp14_balanced"
$trainCache = "$dsRoot\train\labels.cache"
$valCache   = "$dsRoot\val\labels.cache"

Write-Host ""
Write-Host "=== 사전 점검 ===" -ForegroundColor Cyan
if (-not (Test-Path $yolo))     { Write-Host "ERROR: yolo.exe 없음" -ForegroundColor Red; exit 1 }
Write-Host "OK: yolo.exe" -ForegroundColor Green
if (-not (Test-Path $dataYaml)) { Write-Host "ERROR: data.yaml 없음 -> $dataYaml (먼저 _build_exp14_balanced.py 실행)" -ForegroundColor Red; exit 1 }
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
Write-Host "=== 데이터셋 파일 개수 ===" -ForegroundColor Cyan
foreach ($s in @('train\images','train\labels','val\images','val\labels')) {
    $cnt = (Get-ChildItem (Join-Path $dsRoot $s) -File -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host ("  {0,-14} : {1} files" -f $s, $cnt)
}

Write-Host ""
Write-Host "=== GPU ===" -ForegroundColor Cyan
nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits

Write-Host ""
Write-Host "=== exp14 balanced 학습 시작 (seed=$Seed) ===" -ForegroundColor Cyan
Write-Host "name:  $fullName" -ForegroundColor White
Write-Host "[주의] 시작 로그에서 실제 optimizer(MuSGD/AdamW)/lr 확인할 것" -ForegroundColor Yellow
Write-Host ""

$trainArgs = @(
    "detect", "train",
    "model=yolo26s.pt",
    "data=$dataYaml",
    "epochs=$Epochs",
    "imgsz=640",
    "batch=$Batch",
    "workers=8",
    "cache=disk",
    "device=0",
    "seed=$Seed",
    "deterministic=true",
    "patience=15",
    "plots=false",
    "project=$project",
    "name=$fullName"
)
& $yolo @trainArgs
