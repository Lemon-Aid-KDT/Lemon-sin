# -*- coding: utf-8 -*-
"""CLIP zero-shot vs exp16b — wild 545장(지원 40클래스) 동일셋 paired 비교.

목적: "웹 대규모 사전학습(CLIP)이 학습 0으로 우리 도메인갭(studio→wild)을 우회하는가"를
exp16b(0.598)와 같은 545장에서 정직하게 측정. CLIP은 풀이미지 zero-shot(40클래스 텍스트 프롬프트
중 코사인유사도 최댓값)으로 분류. 학습 전혀 없음.

지표: per-image top-1 정확도(pred==GT). exp16b와 동일 분모(545)에서 paired 부트스트랩 차이검정.
모델: openai/clip-vit-base-patch16 (캐시됨). transformers<5 필요(설치됨 4.57.6).
usage: python -u _eval_clip_zeroshot_wild.py   (GPU, 학습 중 실행 금지)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

sys.stdout.reconfigure(encoding="utf-8")
EVAL = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_eval545_supported40.txt")
BASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
PERIMG = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\_eval_exp16_clean_perimage.csv")
OUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\_eval_clip_zeroshot_wild.csv")
MODEL_ID = "openai/clip-vit-base-patch16"

# 40클래스 → CLIP 영어 설명 프롬프트 (zero-shot 공정성 위해 자연스러운 영어 음식명)
DESC = {
    "barbecue-ribs": "grilled marinated beef short ribs, galbi",
    "black-bean-noodles": "jjajangmyeon, noodles in black bean sauce",
    "braised-chicken": "braised chicken with vegetables, jjimdak",
    "braised-pork-hock": "braised pork hock, jokbal",
    "bread": "bread",
    "bulgogi": "bulgogi, Korean marinated grilled beef",
    "cake": "cake",
    "cold-noodles": "naengmyeon, Korean cold noodles in broth",
    "curry": "curry rice",
    "dim-sum": "steamed dumplings, dim sum",
    "doenjang-jjigae": "doenjang jjigae, soybean paste stew",
    "fish-cake": "fish cake, eomuk",
    "fried-chicken": "fried chicken",
    "fried-food-platter": "assorted deep-fried food, twigim",
    "grilled-fish": "grilled fish",
    "grilled-pork-belly": "grilled pork belly, samgyeopsal",
    "hamburger": "hamburger",
    "japanese-ramen": "Japanese ramen noodle soup",
    "jjigae-red": "kimchi jjigae, spicy red Korean stew",
    "kalguksu": "kalguksu, knife-cut noodle soup",
    "korean-blood-sausage": "sundae, Korean blood sausage",
    "korean-ramyeon-red": "spicy instant ramyeon noodle soup",
    "mixed-rice-bowl": "bibimbap, mixed rice bowl with vegetables",
    "pasta": "pasta",
    "pizza": "pizza",
    "pork-cutlet-dry": "pork cutlet, tonkatsu, donkatsu",
    "raw-fish": "raw fish sashimi, hoe",
    "rice-noodle-soup": "pho, rice noodle soup",
    "rice-porridge": "rice porridge, juk, congee",
    "rice-soup": "Korean rice and soup, gukbap",
    "salad": "salad",
    "sandwich": "sandwich",
    "savory-pancake": "Korean savory pancake, jeon, pajeon",
    "seaweed-rice-roll": "gimbap, seaweed rice roll",
    "spicy-mixed-noodles": "bibim guksu, spicy mixed cold noodles",
    "sushi": "sushi",
    "takoyaki": "takoyaki, octopus balls",
    "tteokbokki-red": "tteokbokki, spicy rice cakes in red sauce",
    "udon": "udon noodle soup",
    "western-cream-soup": "cream soup",
}
TEMPLATES = ["a photo of {}.", "a photo of {} food.", "a close-up photo of {} on a plate."]


def boot_paired(arr_b, arr_a, B=2000, seed=42):
    rng = np.random.default_rng(seed)
    b = np.asarray(arr_b, float); a = np.asarray(arr_a, float); n = len(b)
    idx = rng.integers(0, n, size=(B, n))
    d = b[idx].mean(axis=1) - a[idx].mean(axis=1)
    return float(d.mean()), (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))), float((d > 0).mean())


def boot_ci(arr, B=2000, seed=42):
    rng = np.random.default_rng(seed)
    a = np.asarray(arr, float); n = len(a)
    m = a[rng.integers(0, n, size=(B, n))].mean(axis=1)
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def main():
    # 평가셋 로드
    items = []
    for ln in EVAL.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        parts = ln.split("\t")
        items.append((parts[0].replace("\\", "/"), parts[1]))  # (relpath, gt_en)
    classes = list(DESC.keys())
    assert len(classes) == 40
    print(f"평가셋 {len(items)}장 / {len(classes)}클래스 zero-shot")

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(MODEL_ID).to(dev).eval()
    proc = CLIPProcessor.from_pretrained(MODEL_ID)

    # 텍스트 임베딩: 클래스별 템플릿 평균 (표준 zero-shot)
    with torch.no_grad():
        cls_embeds = []
        for c in classes:
            texts = [t.format(DESC[c]) for t in TEMPLATES]
            tin = proc(text=texts, return_tensors="pt", padding=True).to(dev)
            te = model.get_text_features(**tin)
            te = te / te.norm(dim=-1, keepdim=True)
            cls_embeds.append(te.mean(dim=0))
        text_mat = torch.stack(cls_embeds)
        text_mat = text_mat / text_mat.norm(dim=-1, keepdim=True)  # [40, D]

    # 이미지 분류
    rows = []
    top1 = top5 = 0
    miss_load = 0
    with torch.no_grad():
        for rel, gt in items:
            p = BASE / rel
            try:
                im = Image.open(p).convert("RGB")
            except Exception:
                miss_load += 1
                rows.append((rel, gt, None, 0, 0)); continue
            iin = proc(images=im, return_tensors="pt").to(dev)
            ie = model.get_image_features(**iin)
            ie = ie / ie.norm(dim=-1, keepdim=True)
            sims = (ie @ text_mat.T).squeeze(0)  # [40]
            order = sims.argsort(descending=True).cpu().numpy()
            pred = classes[int(order[0])]
            in5 = gt in [classes[int(i)] for i in order[:5]]
            s1 = int(pred == gt); s5 = int(in5)
            top1 += s1; top5 += s5
            rows.append((rel, gt, pred, s1, s5))
    n = len(items)
    clip_acc = top1 / n

    # exp16b 동일셋 (perimage 조인)
    exp16b = {}
    with PERIMG.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            exp16b[r["image"].replace("\\", "/")] = int(r["exp16b_strict"])
    clip_arr, exp_arr, matched = [], [], 0
    for rel, gt, pred, s1, s5 in rows:
        if rel in exp16b:
            matched += 1
            clip_arr.append(s1); exp_arr.append(exp16b[rel])
    exp_acc = sum(exp_arr) / len(exp_arr) if exp_arr else 0.0

    clo, chi = boot_ci(clip_arr)
    elo, ehi = boot_ci(exp_arr)
    d, (dlo, dhi), p_cb = boot_paired(clip_arr, exp_arr)

    print(f"\n로드실패 {miss_load} / exp16b 조인 {matched}")
    print("\n================= CLIP zero-shot vs exp16b (wild {0}, 동일셋) =================".format(len(clip_arr)))
    print(f"  CLIP zero-shot top-1 : {clip_acc:.3f} [{clo:.3f}~{chi:.3f}]  (top-5 {top5/n:.3f})")
    print(f"  exp16b (학습된 모델)  : {exp_acc:.3f} [{elo:.3f}~{ehi:.3f}]")
    print(f"  차이 CLIP-exp16b      : {d:+.3f} [{dlo:+.3f}~{dhi:+.3f}]  P(CLIP>exp16b)={p_cb:.2f}")
    sig = "유의" if (dlo > 0 or dhi < 0) else "노이즈(0 포함)"
    print(f"  → {sig}")

    # per-class top1 (n>=10)
    from collections import defaultdict
    agg = defaultdict(lambda: [0, 0])
    for rel, gt, pred, s1, s5 in rows:
        agg[gt][0] += 1; agg[gt][1] += s1
    print("\n[CLIP per-class top-1 (n>=10)]")
    for c in sorted(agg):
        nn, hit = agg[c]
        if nn >= 10:
            print(f"  {c:22s} n={nn:3d}  {hit/nn:.2f}")

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["image", "gt", "clip_pred", "clip_top1", "clip_top5"])
        for row in rows:
            w.writerow(row)
    print(f"\nCSV: {OUT.name}")


if __name__ == "__main__":
    main()
