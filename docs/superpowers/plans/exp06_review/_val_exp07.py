"""exp07(yolo26s) 검증: best.pt -> 클래스별 AP50/AP50-95 CSV. Windows __main__ 가드."""

from __future__ import annotations

import csv
from pathlib import Path

from ultralytics import YOLO

BEST = r"C:\Lemon-sin\runs\food_yolo\exp07_yolo26s_taxo63bal500_pc1_b16_w8_cache_disk_det_true\weights\best.pt"
DATA = r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo63_bal500\data.yaml"
OUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\exp07_per_class_ap.csv")


def main() -> None:
    m = YOLO(BEST)
    r = m.val(data=DATA, imgsz=640, device=0, plots=False, save_json=True, workers=0,
              project=r"C:\Lemon-sin\runs\food_yolo", name="exp07_perclass_val")
    rows = []
    for i, ci in enumerate(r.box.ap_class_index):
        rows.append({"class": m.names[ci],
                     "ap50": round(float(r.box.ap50[i]), 4),
                     "ap50_95": round(float(r.box.maps[ci]), 4)})
    rows.sort(key=lambda x: x["ap50"])
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["class", "ap50", "ap50_95"])
        w.writeheader()
        w.writerows(rows)
    print("overall mAP50", round(float(r.box.map50), 4), "mAP50-95", round(float(r.box.map), 4))
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
