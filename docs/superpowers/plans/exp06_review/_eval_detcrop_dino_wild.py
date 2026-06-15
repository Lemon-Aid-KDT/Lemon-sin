# -*- coding: utf-8 -*-
"""디텍터 크롭 → DINOv3 프로브 — 한상(다중요리) 구조 검증.

실제 서비스 구조 = 디텍터(인계 1-class)로 음식 위치 크롭 → DINOv3-vitb16 분류.
지금까지 0.839는 '풀이미지(단일요리)' 기준 → 크롭 기준으로 재학습·재평가해 비교.
시드 고정(풀 vs 크롭 공정비교).
usage: python -u _eval_detcrop_dino_wild.py   (GPU, HF_TOKEN 설정 후)
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import yaml
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
from ultralytics import YOLO

sys.stdout.reconfigure(encoding="utf-8")
EVAL = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_eval545_supported40.txt")
WBASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
PLUSRW = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_taxo50_plus_realworld")
DET = Path(r"C:\Lemon-sin\backend\food_image_analysis\detector\detector_best.pt")
DINO_ID = "facebook/dinov3-vitb16-pretrain-lvd1689m"
SEED = 42
EXCLUDE10 = {"seafood-jjim", "seafood-spicy-tang", "seafood-clear-tang", "squid-dish",
             "shrimp-dish", "grilled-beef", "jjamppong", "fried-rice", "dumplings", "rice-bowl"}
dev = "cuda" if torch.cuda.is_available() else "cpu"

det = YOLO(str(DET))
_proc = AutoImageProcessor.from_pretrained(DINO_ID)
_model = AutoModel.from_pretrained(DINO_ID).to(dev).eval()
_nodet = {"full": 0, "n": 0}


def crop_food(im: Image.Image):
    """디텍터 최고conf 박스로 크롭(패드 5%). 미검출 시 풀이미지(fallback)."""
    _nodet["n"] += 1
    r = det.predict(im, conf=0.25, iou=0.15, agnostic_nms=True, max_det=50, imgsz=512, verbose=False)[0]
    if not len(r.boxes):
        _nodet["full"] += 1
        return im
    bi = int(r.boxes.conf.argmax())
    x1, y1, x2, y2 = [float(v) for v in r.boxes.xyxy[bi]]
    W, H = im.size
    px, py = (x2 - x1) * 0.05, (y2 - y1) * 0.05
    return im.crop((max(0, x1 - px), max(0, y1 - py), min(W, x2 + px), min(H, y2 + py)))


@torch.no_grad()
def feats(paths, do_crop, bs=48):
    out = []
    for i in range(0, len(paths), bs):
        ims = []
        for p in paths[i:i + bs]:
            try:
                im = Image.open(p).convert("RGB")
            except Exception:
                im = Image.new("RGB", (224, 224))
            ims.append(crop_food(im) if do_crop else im)
        inp = _proc(images=ims, return_tensors="pt").to(dev)
        o = _model(**inp)
        f = getattr(o, "pooler_output", None)
        if f is None:
            f = o.last_hidden_state[:, 0]
        f = f / f.norm(dim=-1, keepdim=True)
        out.append(f.cpu().numpy())
    return np.concatenate(out)


def names_of(ds):
    nm = yaml.safe_load((ds / "data.yaml").read_text(encoding="utf-8"))["names"]
    return nm if isinstance(nm, list) else [nm[i] for i in sorted(nm)]


def collect(ds, glob):
    names = names_of(ds)
    by = {}
    for lf in sorted((ds / "train" / "labels").glob(glob + ".txt")):
        ln = lf.read_text(encoding="utf-8").splitlines()
        if not ln or not ln[0].strip():
            continue
        cls = names[int(ln[0].split()[0])]
        if cls in EXCLUDE10:
            continue
        img = ds / "train" / "images" / (lf.stem + ".jpg")
        if img.exists():
            by.setdefault(cls, []).append(img)
    paths, labels = [], []
    for c, ims in by.items():
        paths += ims; labels += [c] * len(ims)
    return paths, labels


def probe(Xtr, ytr, Xw, wild_gt):
    torch.manual_seed(SEED); np.random.seed(SEED)
    classes = sorted(set(ytr)); cidx = {c: i for i, c in enumerate(classes)}
    Xt = torch.tensor(Xtr, dtype=torch.float32, device=dev)
    yt = torch.tensor([cidx[c] for c in ytr], dtype=torch.long, device=dev)
    cnt = np.bincount([cidx[c] for c in ytr], minlength=len(classes)).astype(float)
    w = torch.tensor(cnt.sum() / (len(classes) * np.maximum(cnt, 1)), dtype=torch.float32, device=dev)
    lin = torch.nn.Linear(Xtr.shape[1], len(classes)).to(dev)
    opt = torch.optim.AdamW(lin.parameters(), lr=1e-3, weight_decay=1e-4)
    lossf = torch.nn.CrossEntropyLoss(weight=w)
    lin.train()
    for _ in range(300):
        opt.zero_grad(); lossf(lin(Xt), yt).backward(); opt.step()
    lin.eval()
    with torch.no_grad():
        pidx = lin(torch.tensor(Xw, dtype=torch.float32, device=dev)).argmax(1).cpu().numpy()
    pred = [classes[i] for i in pidx]
    acc = np.mean([pred[i] == wild_gt[i] for i in range(len(wild_gt))])
    agg = defaultdict(lambda: [0, 0])
    for i, g in enumerate(wild_gt):
        agg[g][0] += 1; agg[g][1] += int(pred[i] == g)
    return acc, agg


def main():
    items = [(WBASE / ln.split("\t")[0].replace("\\", "/"), ln.split("\t")[1])
             for ln in EVAL.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    wp = [p for p, _ in items]; wg = [g for _, g in items]
    rw_p, rw_y = collect(PLUSRW, "rw_*")
    print(f"wild {len(items)} / realworld 학습 {len(rw_p)} / 모델 DINOv3-vitb16 / seed {SEED}")
    print("비교 기준: 풀이미지 DINOv3 0.839 / exp16b 0.598\n")

    print("특징 추출: realworld FULL...")
    Xrw_full = feats(rw_p, False)
    print("특징 추출: realworld CROP(디텍터)...")
    nd0 = _nodet["full"]; Xrw_crop = feats(rw_p, True)
    rw_fallback = _nodet["full"] - nd0
    print("특징 추출: wild FULL...")
    Xw_full = feats(wp, False)
    print("특징 추출: wild CROP(디텍터)...")
    nd1 = _nodet["full"]; Xw_crop = feats(wp, True)
    wild_fallback = _nodet["full"] - nd1

    acc_full, agg_full = probe(Xrw_full, rw_y, Xw_full, wg)
    acc_crop, agg_crop = probe(Xrw_crop, rw_y, Xw_crop, wg)

    print("\n================= 디텍터 크롭 vs 풀이미지 (DINOv3-vitb16, wild 545) =================")
    print(f"  풀이미지 (train full → eval full)   : {acc_full:.3f}   (재현, 미검출 fallback rw {rw_fallback}/wild {wild_fallback})")
    print(f"  디텍터 크롭 (train crop → eval crop) : {acc_crop:.3f}")
    print(f"  차이(크롭-풀): {acc_crop - acc_full:+.3f}")
    print(f"  ※ wild 미검출(풀이미지 fallback): {wild_fallback}/{len(wp)}장")

    print("\n[크롭 기준 한식국물 per-class]")
    for c in ["jjigae-red", "rice-soup", "kalguksu", "savory-pancake", "doenjang-jjigae"]:
        if c in agg_crop and agg_crop[c][0]:
            a = agg_crop[c]; b = agg_full.get(c, [a[0], 0])
            print(f"  {c:20s} n={a[0]:3d}  풀 {b[1]/a[0]:.2f} → 크롭 {a[1]/a[0]:.2f}")


if __name__ == "__main__":
    main()
