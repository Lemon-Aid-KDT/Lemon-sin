$p = "C:\Lemon-sin\runs\food_yolo\exp14_balanced_pc1_s42_b16_w8_cache_disk_det_true\results.csv"
while ($true) {
    Clear-Host
    $l = (Import-Csv $p)[-1]
    Write-Host ("exp14  epoch {0}/50  |  mAP50 {1}  |  mAP50-95 {2}  |  val_cls_loss {3}" -f $l.epoch, $l.'metrics/mAP50(B)', $l.'metrics/mAP50-95(B)', $l.'val/cls_loss')
    nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader
    Write-Host "(60s refresh, Ctrl+C to stop)"
    Start-Sleep 60
}
