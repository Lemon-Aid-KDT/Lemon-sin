"""exp13 데이터셋 — taxo59 cap1500 + selectstar 실데이터 다중 OOD 클래스 보강.

exp12(takoyaki) 성공의 일반화 검증. 11개 클래스에 selectstar 추가
(모델박스+selectstar 정답라벨, 미탐지 full-image fallback). 각 클래스 800 train,
마지막 100은 held-out test로 reserve(누수0). val은 bal1500과 동일.
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
DST = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_exp13_selectstar")
SSBASE = Path(r"C:\Lemon-sin\data\food_images\raw\selectstar")
WEIGHTS = r"C:\Lemon-sin\runs\food_yolo\exp12_yolo26s_taxo59tako_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt"
HELDOUT_MANIFEST = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\exp13_selectstar_heldout.tsv")
ADD, HELDOUT = 800, 100

# selectstar 폴더 -> taxo59 클래스 (깨끗 매핑, OOD 위주)
SMAP = {
    "takoyaki": "takoyaki", "jajangmyeon": "black-bean-noodles", "udon": "udon",
    "bulgogi": "bulgogi", "dim_sum": "dim-sum", "ramen": "japanese-ramen",
    "korean_pancake": "savory-pancake", "kimchi_stew": "jjigae-red", "sashimi": "raw-fish",
    "rice_noodle": "rice-noodle-soup", "bibimbap": "mixed-rice-bowl",
}


def hardlink_split(split: str) -> int:
    n = 0
    for sub in ("images", "labels"):
        (DST / split / sub).mkdir(parents=True, exist_ok=True)
        for f in glob.glob(str(SRC / split / sub / "*")):
            d = DST / split / sub / os.path.basename(f)
            if not d.exists():
                try:
                    os.link(f, d)
                except OSError:
                    shutil.copy2(f, d)
            if sub == "images":
                n += 1
    return n


def main() -> None:
    names = yaml.safe_load((SRC / "data.yaml").read_text(encoding="utf-8"))["names"]
    names = names if isinstance(names, list) else [names[i] for i in sorted(names)]
    if DST.exists():
        shutil.rmtree(DST)
    tr = hardlink_split("train")
    va = hardlink_split("val")
    print(f"하드링크: train {tr} / val {va}")

    m = YOLO(WEIGHTS)
    held_lines = []
    summary = []
    for folder, cls in SMAP.items():
        tidx = names.index(cls)
        imgs = [p for p in sorted(glob.glob(str(SSBASE / folder / "png" / "*.png")))
                if "._" not in os.path.basename(p)]
        train_imgs = imgs[:ADD]
        held = imgs[ADD:ADD + HELDOUT]
        det = fb = 0
        for i, p in enumerate(train_imgs):
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
                cx, cy, bw, bh = 0.5, 0.5, 0.98, 0.98
                fb += 1
            stem = f"ss_{folder}_{i:04d}"
            dimg = DST / "train" / "images" / f"{stem}.png"
            if not dimg.exists():
                try:
                    os.link(p, dimg)
                except OSError:
                    shutil.copy2(p, dimg)
            (DST / "train" / "labels" / f"{stem}.txt").write_text(
                f"{tidx} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n", encoding="utf-8")
        for hp in held:
            held_lines.append(f"{cls}\t{hp}")
        summary.append((folder, cls, len(train_imgs), det, fb, len(held)))
        print(f"  {folder:16s}->{cls:20s} train+{len(train_imgs)} (박스{det}/fb{fb}) held{len(held)}")

    HELDOUT_MANIFEST.write_text("\n".join(held_lines) + "\n", encoding="utf-8")
    block = "\n".join(f"  {i}: {n}" for i, n in enumerate(names))
    (DST / "data.yaml").write_text(
        f"path: {DST.as_posix()}\ntrain: train/images\nval: val/images\n"
        f"nc: {len(names)}\nnames:\n{block}\n", encoding="utf-8")
    n_tr = len(glob.glob(str(DST / "train" / "images" / "*.jpg"))) + len(glob.glob(str(DST / "train" / "images" / "*.png")))
    print(f"\nWROTE {DST}\\data.yaml | train 총 {n_tr} (+selectstar {sum(s[2] for s in summary)}) | val {va}")
    print(f"held-out: {len(held_lines)}장 ({len(SMAP)}클래스) -> {HELDOUT_MANIFEST.name}")


if __name__ == "__main__":
    main()
