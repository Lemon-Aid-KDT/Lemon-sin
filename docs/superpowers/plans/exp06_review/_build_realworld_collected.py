"""실환경 수집 학습셋 빌드 — team_collected + web_crawl KEEP를 박싱·group-split·YOLO 데이터셋화.

- 박스: exp11 best.pt 모델박스(최고conf, conf>=0.10). 미탐지=단일요리라 center fallback(0.5,0.5,0.9,0.9).
- group: team=세션id(orig_..._<10digit>_p_) 또는 파일명, web=folder/file. 같은 group은 train/val 안 갈림(누수 방지).
- split: 클래스별 group 단위 ~15% val(결정적). 클래스 이미지 <7이면 전부 train.
- 출력: data/food_images/processed/realworld_collected_v1/{train,val}/{images,labels} + data.yaml(taxo59).
"""
from __future__ import annotations
import os, re, shutil
from collections import defaultdict
from pathlib import Path
import cv2, numpy as np, yaml
from ultralytics import YOLO

RAW = Path(r"C:\Lemon-sin\data\food_images\raw")
TEAM = RAW / "team_collected"
WEB = RAW / "web_crawl"
DST = Path(r"C:\Lemon-sin\data\food_images\processed\realworld_collected_v1")
NAMES_SRC = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo59_bal1500\data.yaml")
WEIGHTS = r"C:\Lemon-sin\runs\food_yolo\exp11_yolo26s_taxo59bal1500_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt"
CONF = 0.10

names = yaml.safe_load(NAMES_SRC.read_text(encoding="utf-8"))["names"]
names = names if isinstance(names, list) else [names[i] for i in sorted(names)]
nidx = {n: i for i, n in enumerate(names)}


def load_keep():
    items = []  # (cls, abspath, group, srctag)
    for ln in (RAW / "team_keep_list.txt").read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        cls, fn = ln.split("\t")
        m = re.search(r"_(\d{10,})_p_", fn)
        group = f"team/{m.group(1)}" if m else f"team/{fn}"
        items.append((cls, TEAM / fn, group, "team"))
    for ln in (RAW / "web_crawl_keep_list.txt").read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        cls, ff = ln.split("\t")
        items.append((cls, WEB / ff, f"web/{ff}", "web"))
    return items


def main():
    if DST.exists():
        shutil.rmtree(DST)
    for s in ("train", "val"):
        (DST / s / "images").mkdir(parents=True, exist_ok=True)
        (DST / s / "labels").mkdir(parents=True, exist_ok=True)
    items = [it for it in load_keep() if it[0] in nidx]
    # 클래스별 group-split (결정적: group 정렬 후 7개당 1개 val)
    by_cls = defaultdict(list)
    for it in items:
        by_cls[it[0]].append(it)
    val_groups = set()
    for cls, its in by_cls.items():
        groups = sorted({it[2] for it in its})
        if len(its) >= 7:
            for gi, g in enumerate(groups):
                if gi % 7 == 0:
                    val_groups.add(g)

    m = YOLO(WEIGHTS)
    stat = defaultdict(lambda: [0, 0, 0, 0])  # cls -> [train, val, modelbox, fallback]
    n_bad = 0
    for cls, p, group, src in items:
        im = cv2.imread(str(p))
        if im is None:
            n_bad += 1
            continue
        H, W = im.shape[:2]
        r = m.predict(im, conf=CONF, verbose=False, device=0)[0]
        if len(r.boxes):
            bi = int(np.argmax(r.boxes.conf.tolist()))
            x1, y1, x2, y2 = r.boxes.xyxy[bi].tolist()
            cx, cy, bw, bh = (x1 + x2) / 2 / W, (y1 + y2) / 2 / H, (x2 - x1) / W, (y2 - y1) / H
            box_kind = 2
        else:
            cx, cy, bw, bh = 0.5, 0.5, 0.9, 0.9  # 단일요리 center fallback
            box_kind = 3
        split = "val" if group in val_groups else "train"
        stem = f"rw_{src}_{cls}_{re.sub(r'[^A-Za-z0-9가-힣]', '_', p.stem)}_{stat[cls][0]+stat[cls][1]}"
        dimg = DST / split / "images" / f"{stem}.jpg"
        try:
            os.link(str(p), dimg)
        except OSError:
            shutil.copy2(str(p), dimg)
        (DST / split / "labels" / f"{stem}.txt").write_text(
            f"{nidx[cls]} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n", encoding="utf-8")
        stat[cls][0 if split == "train" else 1] += 1
        stat[cls][box_kind] += 1

    block = "\n".join(f"  {i}: {n}" for i, n in enumerate(names))
    (DST / "data.yaml").write_text(
        f"path: {DST.as_posix()}\ntrain: train/images\nval: val/images\nnc: {len(names)}\nnames:\n{block}\n",
        encoding="utf-8")
    tr = sum(s[0] for s in stat.values()); va = sum(s[1] for s in stat.values())
    mb = sum(s[2] for s in stat.values()); fb = sum(s[3] for s in stat.values())
    print(f"=== realworld_collected_v1 빌드 완료 ===")
    print(f"train {tr} / val {va} / 총 {tr+va} ({len(stat)}클래스) | 모델박스 {mb} / fallback {fb} / 로드실패 {n_bad}")
    print("클래스별 (train/val):")
    for cls in sorted(stat, key=lambda c: -(stat[c][0] + stat[c][1])):
        s = stat[cls]
        print(f"  {cls:22s} {s[0]:3d}/{s[1]:2d}")


if __name__ == "__main__":
    main()
