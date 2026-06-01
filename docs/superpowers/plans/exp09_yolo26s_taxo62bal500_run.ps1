# exp09: YOLO26s + taxonomy v3 balanced (chicken-galbi 라벨노이즈 정리). baseline = exp07.
# 변경점 = 데이터셋(taxo63->taxo62: chicken-galbi 삭제, B12003->fried, B12144 drop). 모델/설정은 exp07과 동일.
# 주의: MuSGD 옵티마이저 자동선택 버그 가능 -> 학습 시작 로그에서 실제 optimizer/lr 확인.
# 주의: 백틱 줄-연속은 CRLF에서 PowerShell 파싱이 깨지므로 인자 배열 splatting 사용.

param(
    [int]$Batch = 16,
    [int]$Epochs = 50,
    [string]$RunName = "exp09_yolo26s_taxo62bal500_pc1"
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$yolo       = "C:\Lemon-sin\backend\.venv\Scripts\yolo.exe"
$venvPython = "C:\Lemon-sin\backend\.venv\Scripts\python.exe"
$dataYaml   = "C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo62_bal500\data.yaml"
$project    = "C:\Lemon-sin\runs\food_yolo"
$fullName   = "$RunName" + "_b$Batch" + "_w8_cache_disk_det_true"
$dsRoot     = "C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo62_bal500"
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
Write-Host "=== 데이터셋 파일 개수 ===" -ForegroundColor Cyan
foreach ($s in @('train\images','train\labels','val\images','val\labels')) {
    $cnt = (Get-ChildItem (Join-Path $dsRoot $s) -File -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host ("  {0,-14} : {1} files" -f $s, $cnt)
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
Write-Host "=== exp09 학습 시작 (YOLO26s + taxo62 v3 balanced) ===" -ForegroundColor Cyan
Write-Host "name:  $fullName" -ForegroundColor White
Write-Host "model: yolo26s.pt | batch: $Batch | epochs: $Epochs | imgsz: 640 | workers: 8 | cache: disk | det: true | seed: 42" -ForegroundColor White
Write-Host "(yolo26s ~9.5M, 8GB는 batch=16 권장. exp07과 동일 설정 = 데이터셋만 변수)" -ForegroundColor DarkGray
Write-Host "[주의] 학습 시작 로그에서 실제 optimizer(MuSGD/AdamW)/lr 확인할 것" -ForegroundColor Yellow
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
    "seed=42",
    "deterministic=true",
    "patience=15",
    "plots=false",
    "project=$project",
    "name=$fullName"
)
& $yolo @trainArgs
