while ($true) {
    Clear-Host
    $csv = Get-ChildItem "C:\Lemon-sin\runs\food_yolo\exp1[567]*\results.csv" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($csv) {
        $l = (Import-Csv $csv.FullName)[-1]
        $name = Split-Path (Split-Path $csv.FullName -Parent) -Leaf
        Write-Host $name -ForegroundColor Cyan
        Write-Host ("  epoch {0}/50  |  mAP50 {1}  |  mAP50-95 {2}  |  val_cls {3}" -f $l.epoch, $l.'metrics/mAP50(B)', $l.'metrics/mAP50-95(B)', $l.'val/cls_loss')
        Write-Host ("  updated: {0}" -f $csv.LastWriteTime)
    } else { Write-Host "exp15 results.csv not yet (caching first epoch ~few min)" }
    nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader
    Write-Host "(60s refresh, Ctrl+C to stop)"
    Start-Sleep 60
}
