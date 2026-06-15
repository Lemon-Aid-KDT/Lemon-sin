# -*- coding: utf-8 -*-
"""DINO 라인어 프로브 — wild 545 동일셋, CLIP 프로브(0.778)와 직접 비교.

DINO는 텍스트 인코더 없음 → zero-shot 불가, 라인어 프로브만 가능.
CLIP 프로브 최고 설정(realworld 977 학습)과 동일 조건으로 DINO 특징만 교체.
모델: DINOv3(게이트일 수 있음, 실패시 skip) + DINOv2-base/large.
usage: python -u _eval_dino_linearprobe_wild.py
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

sys.stdout.reconfigure(encoding="utf-8")
EVAL = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_eval545_supported40.txt")
WBASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
PLUSRW = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_taxo50_plus_realworld")
EXCLUDE10 = {"seafood-jjim", "seafood-spicy-tang", "seafood-clear-tang", "squid-dish",
             "shrimp-dish", "grilled-beef", "jjamppong", "fried-rice", "dumplings", "rice-bowl"}
MODELS = [
    "facebook/dinov3-vitb16-pretrain-lvd1689m",  # DINOv3 (게이트 가능)
    "facebook/dinov2-base",                       # DINOv2 (공개)
    "facebook/dinov2-large",                      # DINOv2-large (공개, 더 큼)
]
dev = "cuda" if torch.cuda.is_available() else "cpu"


def names_of(ds):
    nm = yaml.safe_load((ds / "data.yaml").read_text(encoding="utf-8"))["names"]
    return nm if isinstance(nm, list) else [nm[i] for i in sorted(nm)]


def collect(ds, glob, cap=None):
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
        sel = ims[:cap] if cap else ims
        paths += sel; labels += [c] * len(sel)
    return paths, labels


@torch.no_grad()
def feats(model, proc, paths, bs=64):
    out = []
    for i in range(0, len(paths), bs):
        ims = []
        for p in paths[i:i + bs]:
            try:
                ims.append(Image.open(p).convert("RGB"))
            except Exception:
                ims.append(Image.new("RGB", (224, 224)))
        inp = proc(images=ims, return_tensors="pt").to(dev)
        o = model(**inp)
        f = getattr(o, "pooler_output", None)
        if f is None:
            f = o.last_hidden_state[:, 0]  # CLS 토큰
        f = f / f.norm(dim=-1, keepdim=True)
        out.append(f.cpu().numpy())
    return np.concatenate(out)


def probe(Xtr, ytr, Xw, wild_gt):
    classes = sorted(set(ytr))
    cidx = {c: i for i, c in enumerate(classes)}
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
    wild_paths = [p for p, _ in items]; wild_gt = [g for _, g in items]
    rw_p, rw_y = collect(PLUSRW, "rw_*")
    print(f"wild {len(items)} / realworld 학습 {len(rw_p)}장")
    print("비교 기준: CLIP 프로브 0.778 / CLIP zero-shot 0.712 / exp16b 0.598\n")
    print("================= DINO 라인어 프로브 (realworld 학습, wild 545) =================")

    for mid in MODELS:
        try:
            proc = AutoImageProcessor.from_pretrained(mid)
            model = AutoModel.from_pretrained(mid).to(dev).eval()
        except Exception as e:
            msg = str(e).split("\n")[0][:120]
            print(f"  {mid:48s} 로드 실패(skip): {msg}")
            continue
        Xtr = feats(model, proc, rw_p)
        Xw = feats(model, proc, wild_paths)
        acc, agg = probe(Xtr, rw_y, Xw, wild_gt)
        dim = Xtr.shape[1]
        print(f"  {mid:48s} dim={dim}  top-1 {acc:.3f}")
        rec = []
        for c in ["jjigae-red", "rice-soup", "kalguksu", "savory-pancake"]:
            if c in agg and agg[c][0]:
                rec.append(f"{c}={agg[c][1]/agg[c][0]:.2f}")
        print(f"      한식국물: {' '.join(rec)}")
        del model; torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
