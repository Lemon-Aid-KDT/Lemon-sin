"""takoyaki 파일럿 평가 — 모델을 두 평가셋에 측정.

  ① AIHub val takoyaki AP (taxo59 val, 실 GT) — 도메인 전이
  ② selectstar held-out 200 인식률 (top-det==takoyaki) — selectstar 도메인 성능

usage: python _eval_takoyaki_pilot.py <weights.pt> [label]
exp11(기존)·exp12(학습후) 둘 다 동일하게 측정해 비교.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

DATA = r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500\data.yaml"
HELDOUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\exp12_takoyaki_heldout_test.txt")
EXP11 = r"C:\Lemon-sin\runs\food_yolo\exp11_yolo26s_taxo59bal1500_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt"


def main() -> None:
    w = sys.argv[1] if len(sys.argv) > 1 else EXP11
    label = sys.argv[2] if len(sys.argv) > 2 else Path(w).parent.parent.name
    m = YOLO(w)
    names = yaml.safe_load(Path(DATA).read_text(encoding="utf-8"))["names"]
    names = names if isinstance(names, list) else [names[i] for i in sorted(names)]
    tidx = names.index("takoyaki")

    # ① AIHub val takoyaki AP
    r = m.val(data=DATA, split="val", imgsz=640, device=0, workers=0, verbose=False, plots=False)
    tak_ap = None
    for i, ci in enumerate(r.box.ap_class_index):
        if int(ci) == tidx:
            tak_ap = float(r.box.ap50[i])

    # ② selectstar held-out 인식률
    paths = [p.strip() for p in HELDOUT.read_text(encoding="utf-8").splitlines() if p.strip()]
    hit = det = 0
    for p in paths:
        im = cv2.imread(p)
        if im is None:
            continue
        rr = m.predict(im, conf=0.10, verbose=False)[0]
        if len(rr.boxes):
            det += 1
            bi = int(np.argmax(rr.boxes.conf.tolist()))
            if int(rr.boxes.cls[bi]) == tidx:
                hit += 1
    n = len(paths)
    print(f"\n=== [{label}] takoyaki 파일럿 평가 ===")
    print(f"  ① AIHub val takoyaki AP50 : {tak_ap:.4f}  (40장, 실GT)")
    print(f"  ② selectstar held-out 인식률: {hit}/{n} = {hit / n * 100:.1f}%  (탐지율 {det}/{n}={det / n * 100:.0f}%)")


if __name__ == "__main__":
    main()
