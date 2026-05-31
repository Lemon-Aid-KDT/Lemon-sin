# 야간 자동 실행 오케스트레이터 (사용자 취침 중)
# 흐름: exp07(yolo26s,b16) 완료 대기 -> exp07 검증 -> exp08 ps1 호출(yolo11s,b16) -> exp08 검증
# 새 PowerShell 콘솔에서 실행하고 닫지 말 것. 진행 로그: runs\food_yolo\_overnight_log.txt
# exp07은 다른 콘솔에서 이미 학습 중이라고 가정(여기선 완료만 폴링).
# exp08 정의는 exp08_yolo11s_taxo63bal500_run.ps1 (자식 프로세스로 호출 -> exit 격리).

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$yolo     = "C:\Lemon-sin\backend\.venv\Scripts\yolo.exe"
$dataYaml = "C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo63_bal500\data.yaml"
$project  = "C:\Lemon-sin\runs\food_yolo"
$plans    = "C:\Lemon-sin\docs\superpowers\plans"
$log      = "$project\_overnight_log.txt"

$exp07   = "exp07_yolo26s_taxo63bal500_pc1_b16_w8_cache_disk_det_true"
$exp08   = "exp08_yolo11s_taxo63bal500_pc1_b16_w8_cache_disk_det_true"
$exp08ps1 = "$plans\exp08_yolo11s_taxo63bal500_run.ps1"

# 시스템이 잠들지 않게 유지 (스크립트 종료 시 자동 해제)
$sig = '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
Add-Type -MemberDefinition $sig -Name PowerUtil -Namespace Win32 -ErrorAction SilentlyContinue
[void][Win32.PowerUtil]::SetThreadExecutionState([uint32]2147483649)  # ES_CONTINUOUS | ES_SYSTEM_REQUIRED

function Log($m) {
    $line = "{0}  {1}" -f (Get-Date -Format 'MM-dd HH:mm:ss'), $m
    Write-Host $line -ForegroundColor Cyan
    Add-Content -Path $log -Value $line -Encoding UTF8
}

function Wait-Done($runName, $stableMin = 15) {
    $lp = "$project\$runName\weights\last.pt"
    Log "waiting for $runName (last.pt 변화 없음 > $stableMin min 이면 완료 판정)..."
    while ($true) {
        if (Test-Path $lp) {
            $age = (New-TimeSpan -Start (Get-Item $lp).LastWriteTime -End (Get-Date)).TotalMinutes
            if ($age -gt $stableMin) { Log "$runName 완료 (last.pt 안정 $([int]$age) min)"; return }
        }
        Start-Sleep -Seconds 120
    }
}

function Run-Val($runName, $valName) {
    $best = "$project\$runName\weights\best.pt"
    if (-not (Test-Path $best)) { Log "SKIP val: best.pt 없음 ($runName)"; return }
    Log "validating $runName -> $valName"
    & $yolo @("detect", "val", "model=$best", "data=$dataYaml", "imgsz=640", "device=0",
              "plots=true", "save_json=true", "workers=0", "project=$project", "name=$valName")
    Log "val 완료: $valName"
}

Log "=== overnight runner 시작 ==="

# 1) exp07 완료 대기 (다른 콘솔에서 학습 중)
Wait-Done $exp07 15

# 2) exp07 검증
Run-Val $exp07 ($exp07 + "_val_auto")

# 3) exp08 학습 — 전용 ps1을 자식 프로세스로 호출(exit 격리, 완료까지 블록)
Log "exp08 학습 시작 (yolo11s b16) -> $exp08ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $exp08ps1
Log "exp08 학습 종료"

# 4) exp08 검증
Run-Val $exp08 ($exp08 + "_val_auto")

Log "=== ALL DONE ==="
