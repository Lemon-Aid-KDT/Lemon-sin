"""exp12 데이터셋 — taxo59 cap1500 + takoyaki selectstar 실데이터 보강.

가설검증(약점클래스는 실데이터로 개선). bal1500을 그대로 하드링크하고,
takoyaki 클래스에만 selectstar 이미지를 추가(모델박스+selectstar 정답라벨,
미탐지 시 full-image-box). val은 bal1500과 동일.
"""

from __future__ import annotations

import glob
import os
import shutil
from pathlib import Path

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

SRC = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500")
DST = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_exp12_takoyaki")
SS = Path(r"C:\Lemon-sin\data\food_images\raw\selectstar\takoyaki\png")
WEIGHTS = r"C:\Lemon-sin\runs\food_yolo\exp11_yolo26s_taxo59bal1500_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt"
ADD_MAX = 1090  # 410 + 1090 = 1500 (cap1500 유지)


def hardlink_split(split: str) -> int:
    n = 0
    for sub in ("images", "labels"):
        (DST / split / sub).mkdir(parents=True, exist_ok=True)
        for f in glob.glob(str(SRC / split / sub / "*")):
            dst = DST / split / sub / os.path.basename(f)
            if not dst.exists():
                try:
                    os.link(f, dst)
                except OSError:
                    shutil.copy2(f, dst)
            if sub == "images":
                n += 1
    return n


def main() -> None:
    names = yaml.safe_load((SRC / "data.yaml").read_text(encoding="utf-8"))["names"]
    names = names if isinstance(names, list) else [names[i] for i in sorted(names)]
    tidx = names.index("takoyaki")

    tr = hardlink_split("train")
    va = hardlink_split("val")
    print(f"하드링크: train {tr} / val {va}")

    # takoyaki selectstar 라벨 생성 + 추가
    m = YOLO(WEIGHTS)
    imgs = [p for p in sorted(glob.glob(str(SS / "*.png"))) if "._" not in os.path.basename(p)][:ADD_MAX]
    det = fb = 0
    for i, p in enumerate(imgs):
        im = cv2.imread(p)
        if im is None:
            continue
        H, W = im.shape[:2]
        r = m.predict(im, conf=0.10, verbose=False)[0]
        if len(r.boxes):
            bi = int(np.argmax(r.boxes.conf.tolist()))
            x1, y1, x2, y2 = r.boxes.xyxy[bi].tolist()
            cx, cy, bw, bh = (x1 + x2) / 2 / W, (y1 + y2) / 2 / H, (x2 - x1) / W, (y2 - y1) / H
            det += 1
        else:
            cx, cy, bw, bh = 0.5, 0.5, 0.98, 0.98  # full-image fallback
            fb += 1
        stem = f"ss_takoyaki_{i:04d}"
        dimg = DST / "train" / "images" / f"{stem}.png"
        if not dimg.exists():
            try:
                os.link(p, dimg)
            except OSError:
                shutil.copy2(p, dimg)
        (DST / "train" / "labels" / f"{stem}.txt").write_text(
            f"{tidx} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n", encoding="utf-8")
    print(f"takoyaki 추가: {len(imgs)}장 (모델박스 {det} / fallback {fb})")

    block = "\n".join(f"  {i}: {n}" for i, n in enumerate(names))
    (DST / "data.yaml").write_text(
        f"path: {DST.as_posix()}\ntrain: train/images\nval: val/images\n"
        f"nc: {len(names)}\nnames:\n{block}\n", encoding="utf-8")
    n_tr = len(glob.glob(str(DST / "train" / "images" / "*")))
    print(f"WROTE {DST}\\data.yaml | train 총 {n_tr} (takoyaki {410}+{len(imgs)}={410+len(imgs)}) | val {va}")


if __name__ == "__main__":
    main()
