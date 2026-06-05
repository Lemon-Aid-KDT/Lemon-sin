"""exp14 balanced 데이터셋 — cap1500인데 부족 클래스 빈자리를 클린 selectstar로 채움.

exp13(일부 클래스만 +800 초과보강 → prior 쏠림/잠식) 대비 진단용 balanced 버전:
  - 모든 클래스 cap 1500 (초과 금지 = 개수 균등화)
  - AIHub<1500 클래스만 클린 selectstar(harvest)로 1500까지 채움
  - selectstar 박스는 모델(exp11) tight 박스만, full-image fallback 없음(과발화 차단)
  - val은 bal1500과 동일(공정 비교)

선행: _harvest_ss_clean.py 로 ss_harvest_clean_list.tsv 생성되어 있어야 함.
"""
from __future__ import annotations

import glob
import os
import shutil
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

SRC = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500")
DST = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_exp14_balanced")
SS = Path(r"C:\Lemon-sin\data\food_images\raw\selectstar")
HARVEST = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\ss_harvest_clean_list.tsv")
WEIGHTS = r"C:\Lemon-sin\runs\food_yolo\exp11_yolo26s_taxo59bal1500_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt"
CAP = 1500
CONF = 0.10


def hardlink(src: str, dst: Path) -> None:
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def hardlink_split(split: str) -> int:
    n = 0
    for sub in ("images", "labels"):
        (DST / split / sub).mkdir(parents=True, exist_ok=True)
        for f in glob.glob(str(SRC / split / sub / "*")):
            hardlink(f, DST / split / sub / os.path.basename(f))
            if sub == "images":
                n += 1
    return n


def main() -> None:
    names = yaml.safe_load((SRC / "data.yaml").read_text(encoding="utf-8"))["names"]
    names = names if isinstance(names, list) else [names[i] for i in sorted(names)]
    nidx = {n: i for i, n in enumerate(names)}

    if DST.exists():
        shutil.rmtree(DST)
    tr = hardlink_split("train")
    va = hardlink_split("val")
    print(f"하드링크 base: train {tr} / val {va}")

    # 현재 클래스별 train 개수
    cur = defaultdict(int)
    for lf in glob.glob(str(DST / "train" / "labels" / "*.txt")):
        try:
            with open(lf) as f:
                ln = f.readline().split()
                if ln:
                    cur[int(ln[0])] += 1
        except Exception:
            pass

    # harvest 로드: cls -> [folder/file]
    harvest = defaultdict(list)
    for line in HARVEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cls, ff = line.split("\t")
        harvest[cls].append(ff)

    m = YOLO(WEIGHTS)
    added_total = 0
    summary = []
    for cls, items in harvest.items():
        if cls not in nidx:
            continue
        tidx = nidx[cls]
        need = CAP - cur[tidx]
        if need <= 0:
            summary.append((cls, cur[tidx], 0, "cap도달-skip"))
            continue
        added = boxed = nobox = 0
        for ff in sorted(items):
            if added >= need:
                break
            folder, fn = ff.split("/", 1)
            p = str(SS / folder / "png" / fn)
            im = cv2.imread(p)
            if im is None:
                continue
            H, W = im.shape[:2]
            r = m.predict(im, conf=CONF, verbose=False, device=0)[0]
            if not len(r.boxes):
                nobox += 1
                continue  # fallback 없음
            bi = int(np.argmax(r.boxes.conf.tolist()))
            x1, y1, x2, y2 = r.boxes.xyxy[bi].tolist()
            cx, cy, bw, bh = (x1 + x2) / 2 / W, (y1 + y2) / 2 / H, (x2 - x1) / W, (y2 - y1) / H
            stem = f"ss_{folder}_{os.path.splitext(fn)[0]}"
            dimg = DST / "train" / "images" / f"{stem}.png"
            hardlink(p, dimg)
            (DST / "train" / "labels" / f"{stem}.txt").write_text(
                f"{tidx} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n", encoding="utf-8")
            added += 1
            boxed += 1
        added_total += added
        summary.append((cls, cur[tidx], added, f"->{cur[tidx]+added} (box{boxed}/nobox{nobox})"))

    block = "\n".join(f"  {i}: {n}" for i, n in enumerate(names))
    (DST / "data.yaml").write_text(
        f"path: {DST.as_posix()}\ntrain: train/images\nval: val/images\n"
        f"nc: {len(names)}\nnames:\n{block}\n", encoding="utf-8")
    n_tr = len(glob.glob(str(DST / "train" / "images" / "*.jpg"))) + len(glob.glob(str(DST / "train" / "images" / "*.png")))
    print(f"\n=== exp14 balanced 빌드 완료 ===")
    print(f"train 총 {n_tr} (+selectstar {added_total}) / val {va}")
    print("클래스별 보강:")
    for cls, before, added, note in sorted(summary, key=lambda s: -s[2]):
        if added > 0:
            print(f"  {cls:22s} {before} {note}")
    skipped = [s for s in summary if s[2] == 0]
    if skipped:
        print(f"보강 0(cap도달/박스없음): {', '.join(s[0] for s in skipped)}")


if __name__ == "__main__":
    main()
