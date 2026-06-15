# -*- coding: utf-8 -*-
"""앙상블(학습0) — CLIP zero-shot + exp16b score fusion, wild 545 동일셋.

각 이미지에서 두 모델의 40클래스 점수분포를 만들어 가중평균 후 argmax.
  - CLIP: 40프롬프트 코사인유사도 → softmax(100*sim)
  - exp16b: predict(conf=0.01, classes=지원40) → 클래스별 max box conf → 합1 정규화
가중치 w(=CLIP비중) 0.5를 헤드라인(튜닝 없음), 0~1 sweep은 '상한 참고'(test로 w 고르면 과적합).
exp16b 단독 0.598 / CLIP 단독 0.712 / 오라클 0.839 대비.
usage: python -u _eval_ensemble_clip_exp16b.py
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
from ultralytics import YOLO

sys.stdout.reconfigure(encoding="utf-8")
EVAL = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_eval545_supported40.txt")
BASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
EXP16B = Path(r"C:\Lemon-sin\runs\food_yolo\exp16b_taxo50_aihubreal_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt")
OUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\_eval_ensemble_clip_exp16b.csv")
CLIP_ID = "openai/clip-vit-base-patch16"

DESC = {
    "barbecue-ribs": "grilled marinated beef short ribs, galbi",
    "black-bean-noodles": "jjajangmyeon, noodles in black bean sauce",
    "braised-chicken": "braised chicken with vegetables, jjimdak",
    "braised-pork-hock": "braised pork hock, jokbal", "bread": "bread",
    "bulgogi": "bulgogi, Korean marinated grilled beef", "cake": "cake",
    "cold-noodles": "naengmyeon, Korean cold noodles in broth", "curry": "curry rice",
    "dim-sum": "steamed dumplings, dim sum",
    "doenjang-jjigae": "doenjang jjigae, soybean paste stew", "fish-cake": "fish cake, eomuk",
    "fried-chicken": "fried chicken", "fried-food-platter": "assorted deep-fried food, twigim",
    "grilled-fish": "grilled fish", "grilled-pork-belly": "grilled pork belly, samgyeopsal",
    "hamburger": "hamburger", "japanese-ramen": "Japanese ramen noodle soup",
    "jjigae-red": "kimchi jjigae, spicy red Korean stew",
    "kalguksu": "kalguksu, knife-cut noodle soup", "korean-blood-sausage": "sundae, Korean blood sausage",
    "korean-ramyeon-red": "spicy instant ramyeon noodle soup",
    "mixed-rice-bowl": "bibimbap, mixed rice bowl with vegetables", "pasta": "pasta", "pizza": "pizza",
    "pork-cutlet-dry": "pork cutlet, tonkatsu, donkatsu", "raw-fish": "raw fish sashimi, hoe",
    "rice-noodle-soup": "pho, rice noodle soup", "rice-porridge": "rice porridge, juk, congee",
    "rice-soup": "Korean rice and soup, gukbap", "salad": "salad", "sandwich": "sandwich",
    "savory-pancake": "Korean savory pancake, jeon, pajeon", "seaweed-rice-roll": "gimbap, seaweed rice roll",
    "spicy-mixed-noodles": "bibim guksu, spicy mixed cold noodles", "sushi": "sushi",
    "takoyaki": "takoyaki, octopus balls", "tteokbokki-red": "tteokbokki, spicy rice cakes in red sauce",
    "udon": "udon noodle soup", "western-cream-soup": "cream soup",
}
TEMPLATES = ["a photo of {}.", "a photo of {} food.", "a close-up photo of {} on a plate."]
CLASSES = list(DESC.keys())
IDX = {c: i for i, c in enumerate(CLASSES)}


def boot_ci(arr, B=2000, seed=42):
    rng = np.random.default_rng(seed); a = np.asarray(arr, float); n = len(a)
    m = a[rng.integers(0, n, size=(B, n))].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def boot_paired(b, a, B=2000, seed=42):
    rng = np.random.default_rng(seed); b = np.asarray(b, float); a = np.asarray(a, float); n = len(b)
    idx = rng.integers(0, n, size=(B, n)); d = b[idx].mean(axis=1) - a[idx].mean(axis=1)
    return float(d.mean()), (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))), float((d > 0).mean())


def main():
    items = []
    for ln in EVAL.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        p = ln.split("\t"); items.append((p[0].replace("\\", "/"), p[1]))
    n = len(items)
    print(f"앙상블 평가 {n}장 / {len(CLASSES)}클래스")

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    clip = CLIPModel.from_pretrained(CLIP_ID).to(dev).eval()
    proc = CLIPProcessor.from_pretrained(CLIP_ID)
    with torch.no_grad():
        embs = []
        for c in CLASSES:
            tin = proc(text=[t.format(DESC[c]) for t in TEMPLATES], return_tensors="pt", padding=True).to(dev)
            te = clip.get_text_features(**tin); te = te / te.norm(dim=-1, keepdim=True)
            embs.append(te.mean(0))
        text_mat = torch.stack(embs); text_mat = text_mat / text_mat.norm(dim=-1, keepdim=True)

    yolo = YOLO(str(EXP16B))
    sup_idx = sorted(i for i, nm in yolo.names.items() if nm in IDX)

    clip_probs, exp_probs, gts, rows = [], [], [], []
    with torch.no_grad():
        for rel, gt in items:
            im = Image.open(BASE / rel).convert("RGB")
            iin = proc(images=im, return_tensors="pt").to(dev)
            ie = clip.get_image_features(**iin); ie = ie / ie.norm(dim=-1, keepdim=True)
            sims = (ie @ text_mat.T).squeeze(0).cpu().numpy()
            cp = np.exp(100 * (sims - sims.max())); cp = cp / cp.sum()
            # exp16b 40-벡터
            r = yolo.predict(im, conf=0.01, classes=sup_idx, verbose=False)[0]
            ev = np.zeros(len(CLASSES))
            for bi in range(len(r.boxes)):
                nm = yolo.names[int(r.boxes.cls[bi])]
                if nm in IDX:
                    ev[IDX[nm]] = max(ev[IDX[nm]], float(r.boxes.conf[bi]))
            ep = ev / ev.sum() if ev.sum() > 0 else np.zeros(len(CLASSES))
            clip_probs.append(cp); exp_probs.append(ep); gts.append(gt)
            rows.append((rel, gt, CLASSES[int(cp.argmax())], CLASSES[int(ep.argmax())] if ev.sum() > 0 else ""))
    clip_probs = np.array(clip_probs); exp_probs = np.array(exp_probs)

    def acc_at(w):
        fused = w * clip_probs + (1 - w) * exp_probs
        # exp16b 미검출(전부0) 이미지는 CLIP만
        zero = exp_probs.sum(1) == 0
        fused[zero] = clip_probs[zero]
        preds = fused.argmax(1)
        return np.array([int(CLASSES[preds[i]] == gts[i]) for i in range(n)])

    clip_only = np.array([int(CLASSES[clip_probs[i].argmax()] == gts[i]) for i in range(n)])
    exp_only = np.array([int(exp_probs[i].sum() > 0 and CLASSES[exp_probs[i].argmax()] == gts[i]) for i in range(n)])
    ens5 = acc_at(0.5)
    oracle = np.maximum(clip_only, exp_only)

    print("\n================= 앙상블 (학습0, wild 545 동일셋) =================")
    for name, arr in [("exp16b 단독(argmax)", exp_only), ("CLIP 단독", clip_only),
                      ("앙상블 w=0.5 (동일가중)", ens5), ("오라클(OR 상한)", oracle)]:
        lo, hi = boot_ci(arr)
        print(f"  {name:22s} {arr.mean():.3f} [{lo:.3f}~{hi:.3f}]")
    d, (dlo, dhi), p = boot_paired(ens5, clip_only)
    print(f"\n  앙상블 - CLIP단독: {d:+.3f} [{dlo:+.3f}~{dhi:+.3f}] P={p:.2f} -> {'유의' if (dlo>0 or dhi<0) else '노이즈'}")

    print("\n[가중치 sweep — 상한 참고(test로 w 선택은 과적합)]")
    for w in [0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]:
        a = acc_at(w).mean()
        print(f"  w(CLIP)={w:.1f}: {a:.3f}")

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.writer(f); wr.writerow(["image", "gt", "clip_pred", "exp16b_pred", "ens_w0.5_correct"])
        for i, (rel, gt, cpred, epred) in enumerate(rows):
            wr.writerow([rel, gt, cpred, epred, ens5[i]])
    print(f"\nCSV: {OUT.name}")


if __name__ == "__main__":
    main()
