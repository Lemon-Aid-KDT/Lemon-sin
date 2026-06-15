# -*- coding: utf-8 -*-
"""CLIP 라인어 프로브(가벼운 파인튜닝) — wild 545 동일셋 평가.

CLIP 이미지 인코더 동결 → 40클래스 선형 분류기(LogisticRegression)만 학습.
학습원천 3종 비교(어떤 데이터가 wild에 전이되나):
  (a) realworld만(rw_ 1177)  (b) AIHub studio만(클래스당 cap)  (c) 둘 다
평가: wild 545 동일셋 top-1. zero-shot 0.712 / exp16b 0.598 / 앙상블 0.723 대비.
usage: python -u _eval_clip_linearprobe_wild.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
import yaml
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

sys.stdout.reconfigure(encoding="utf-8")
EVAL = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_eval545_supported40.txt")
WBASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
AIHUB = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo50")
PLUSRW = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_taxo50_plus_realworld")
CLIP_ID = "openai/clip-vit-base-patch16"
CAP_AIHUB = 150  # 클래스당 studio 샘플 상한(라인어 프로브엔 충분, 가벼움)
EXCLUDE10 = {"seafood-jjim", "seafood-spicy-tang", "seafood-clear-tang", "squid-dish",
             "shrimp-dish", "grilled-beef", "jjamppong", "fried-rice", "dumplings", "rice-bowl"}

dev = "cuda" if torch.cuda.is_available() else "cpu"
_clip = CLIPModel.from_pretrained(CLIP_ID).to(dev).eval()
_proc = CLIPProcessor.from_pretrained(CLIP_ID)


def names_of(ds: Path):
    nm = yaml.safe_load((ds / "data.yaml").read_text(encoding="utf-8"))["names"]
    return nm if isinstance(nm, list) else [nm[i] for i in sorted(nm)]


@torch.no_grad()
def feats(paths, bs=64):
    out = []
    for i in range(0, len(paths), bs):
        ims = []
        for p in paths[i:i + bs]:
            try:
                ims.append(Image.open(p).convert("RGB"))
            except Exception:
                ims.append(Image.new("RGB", (224, 224)))
        inp = _proc(images=ims, return_tensors="pt").to(dev)
        fe = _clip.get_image_features(**inp)
        fe = fe / fe.norm(dim=-1, keepdim=True)
        out.append(fe.cpu().numpy())
    return np.concatenate(out) if out else np.zeros((0, 512))


def collect(ds: Path, prefix_glob: str, cap: int | None):
    """라벨 첫 줄 클래스로 (path, class_en) 수집. 지원 40만, 클래스당 cap."""
    names = names_of(ds)
    by_cls = {}
    label_dir = ds / "train" / "labels"
    for lf in sorted((ds / "train" / "labels").glob(prefix_glob + ".txt")):
        line = lf.read_text(encoding="utf-8").splitlines()
        if not line or not line[0].strip():
            continue
        ci = int(line[0].split()[0])
        cls = names[ci]
        if cls in EXCLUDE10:
            continue
        img = ds / "train" / "images" / (lf.stem + ".jpg")
        if not img.exists():
            continue
        by_cls.setdefault(cls, []).append(img)
    paths, labels = [], []
    for cls, imgs in by_cls.items():
        sel = imgs[:cap] if cap else imgs
        paths += sel; labels += [cls] * len(sel)
    return paths, labels


def main():
    # wild 545
    items = [(WBASE / ln.split("\t")[0].replace("\\", "/"), ln.split("\t")[1])
             for ln in EVAL.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    wild_paths = [p for p, _ in items]; wild_gt = [g for _, g in items]
    print(f"wild 평가 {len(items)}장 / CLIP 특징 추출중...")
    Xw = feats(wild_paths)

    # 학습원천
    print("realworld 특징 추출...")
    rw_p, rw_y = collect(PLUSRW, "rw_*", None)
    Xrw = feats(rw_p)
    print(f"  realworld {len(rw_p)}장 ({len(set(rw_y))}클래스)")
    print(f"AIHub studio 특징 추출 (클래스당 {CAP_AIHUB})...")
    ai_p, ai_y = collect(AIHUB, "*", CAP_AIHUB)
    Xai = feats(ai_p)
    print(f"  AIHub {len(ai_p)}장 ({len(set(ai_y))}클래스)")

    def run(name, X, y):
        # torch 선형 프로브 (CLIP 특징 동결, 선형층만 학습) — sklearn DLL 회피
        classes = sorted(set(y))
        cidx = {c: i for i, c in enumerate(classes)}
        Xt = torch.tensor(X, dtype=torch.float32, device=dev)
        yt = torch.tensor([cidx[c] for c in y], dtype=torch.long, device=dev)
        # 클래스 역빈도 가중(불균형 보정)
        cnt = np.bincount([cidx[c] for c in y], minlength=len(classes)).astype(float)
        w = torch.tensor((cnt.sum() / (len(classes) * np.maximum(cnt, 1))), dtype=torch.float32, device=dev)
        lin = torch.nn.Linear(X.shape[1], len(classes)).to(dev)
        opt = torch.optim.AdamW(lin.parameters(), lr=1e-3, weight_decay=1e-4)
        lossf = torch.nn.CrossEntropyLoss(weight=w)
        lin.train()
        for _ in range(300):
            opt.zero_grad(); loss = lossf(lin(Xt), yt); loss.backward(); opt.step()
        lin.eval()
        with torch.no_grad():
            pidx = lin(torch.tensor(Xw, dtype=torch.float32, device=dev)).argmax(1).cpu().numpy()
        pred = [classes[i] for i in pidx]
        acc = np.mean([pred[i] == wild_gt[i] for i in range(len(wild_gt))])
        from collections import defaultdict
        agg = defaultdict(lambda: [0, 0])
        for i, g in enumerate(wild_gt):
            agg[g][0] += 1; agg[g][1] += int(pred[i] == g)
        return acc, agg, pred

    print("\n================= CLIP 라인어 프로브 (wild 545) =================")
    print("  비교: zero-shot 0.712 / exp16b 0.598 / 앙상블(w.5) 0.723 / 오라클 0.840")
    results = {}
    for name, X, y in [("realworld만", Xrw, rw_y),
                       ("AIHub studio만", Xai, ai_y),
                       ("둘 다(rw+studio)", np.concatenate([Xrw, Xai]), rw_y + ai_y)]:
        acc, agg, pred = run(name, X, y)
        results[name] = (acc, agg)
        print(f"  {name:18s} top-1 {acc:.3f}")

    # 가장 좋은 변형의 한식 약점 클래스 회복 확인 (jjigae-red 등)
    best = max(results, key=lambda k: results[k][0])
    print(f"\n[{best}] 한식 국물 클래스 회복 (zero-shot에서 약했던):")
    agg = results[best][1]
    for c in ["jjigae-red", "rice-soup", "kalguksu", "savory-pancake", "doenjang-jjigae", "korean-ramyeon-red"]:
        if c in agg and agg[c][0] > 0:
            print(f"  {c:22s} n={agg[c][0]:3d}  {agg[c][1]/agg[c][0]:.2f}")


if __name__ == "__main__":
    main()
