$ErrorActionPreference = "Continue"

$base = "G:\lemon-aid\paddleocr_rec_work"
$runs = @(
  @{
    name = "lr5e5_b16_now10"
    suffix = "v2_png_sanitized_mixed_lr5e5_b16_fixedscale48_noshm_stage3dict_eval100_nometric_noguard_now10"
  },
  @{
    name = "lr5e5_b32_20260611"
    suffix = "v2_png_sanitized_mixed_lr5e5_b32_fixedscale48_noshm_stage3dict_eval100_nometric_noguard_20260611"
  },
  @{
    name = "lr1e4_after_lr5e5"
    # Must match $suffix in a100_lr1e4_after_lr5e5_runner.ps1 (the runner is
    # authoritative); the previous value was a stale draft suffix.
    suffix = "v2_png_sanitized_mixed_lr1e4_b16_fixedscale48_noshm_stage3dict_eval100_nometric_noguard_after_lr5e5"
  }
)

function Write-Section($title) {
  Write-Host ""
  Write-Host "===== $title ====="
}

function Show-RunStatus($name, $suffix) {
  Write-Section $name
  $statusPath = Join-Path $base ("status." + $suffix + ".json")
  $stdoutPath = Join-Path $base ("stdout." + $suffix + ".log")
  $stderrPath = Join-Path $base ("stderr." + $suffix + ".log")
  # Runners save checkpoints under output\supplement_rec_crawling_<suffix>;
  # the bare <suffix> path never exists, which caused false "output dir missing".
  # status.json's save_dir is authoritative when present.
  $outDir = Join-Path (Join-Path $base "PaddleOCR\output") ("supplement_rec_crawling_" + $suffix)

  Write-Host ("suffix=" + $suffix)
  if (Test-Path $statusPath) {
    Write-Host "-- status json --"
    Get-Content $statusPath -Raw
    try {
      $statusJson = Get-Content $statusPath -Raw | ConvertFrom-Json
      if ($statusJson.save_dir) { $outDir = [string]$statusJson.save_dir }
    } catch {}
  } else {
    Write-Host "-- status json missing --"
  }

  $earlyStopPath = Join-Path $base ("early_stop." + $suffix + ".status.json")
  if (Test-Path $earlyStopPath) {
    Write-Host "-- early stop watcher --"
    try {
      $es = Get-Content $earlyStopPath -Raw | ConvertFrom-Json
      Write-Host ("checked_at=" + $es.checked_at + " stale=" + $es.progress.stale_eval_epochs + "/" + $es.progress.patience_epochs + " should_stop=" + $es.should_stop + " action=" + $es.action)
    } catch {
      Write-Host "early stop status unreadable"
    }
  }

  if (Test-Path $outDir) {
    Write-Host "-- output files newest --"
    Get-ChildItem $outDir -Force |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 8 Name, Length, LastWriteTime |
      Format-Table -AutoSize
  } else {
    Write-Host "-- output dir missing --"
  }

  if (Test-Path $stdoutPath) {
    Write-Host "-- latest train/eval lines --"
    Select-String -Path $stdoutPath -Pattern "epoch:|global_step:|cur metric|best metric|save best model|best_epoch|END|Traceback|Error|Exception|exit_code" |
      Select-Object -Last 30 |
      ForEach-Object { $_.Line }
  } else {
    Write-Host "-- stdout missing --"
  }

  if (Test-Path $stderrPath) {
    Write-Host "-- stderr tail --"
    Get-Content $stderrPath -Tail 20
  }
}

Write-Section "time"
Get-Date -Format "yyyy-MM-dd HH:mm:ss K"

Write-Section "gpu apps"
& nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader

Write-Section "matching processes"
$matchText = "paddleocr_rec_work|a100_lr5e5|lr1e4|lr_bridge|then_lr1e4|v2_png_sanitized_mixed"
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -and ($_.CommandLine -match $matchText) } |
  Sort-Object ProcessId |
  Select-Object ProcessId, ParentProcessId, Name, @{Name="CommandLine";Expression={$_.CommandLine.Substring(0, [Math]::Min($_.CommandLine.Length, 260))}} |
  Format-List

foreach ($run in $runs) {
  Show-RunStatus $run.name $run.suffix
}

Write-Section "bridge status"
$bridgeStatus = Join-Path $base "status.lr5e5_then_lr1e4_bridge.json"
if (Test-Path $bridgeStatus) {
  Get-Content $bridgeStatus -Raw
} else {
  Write-Host "bridge status missing"
}
