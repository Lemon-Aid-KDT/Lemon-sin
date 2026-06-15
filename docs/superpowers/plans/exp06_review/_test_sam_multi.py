# -*- coding: utf-8 -*-
"""SAM(Segment Anything) 다중요리 분할 테스트 — Grounding DINO와 비교.

SAM은 텍스트 없이 모든 영역을 자동 분할(automatic mask generation) → 마스크.
마스크 → 박스 변환 → 면적밴드+NMS 정리 → 한상서 음식 영역 몇 개 잡는지 + 시각화.
Grounding DINO(텍스트 'food' 타깃) 대비 '모든 것 분할'이 음식에 유리한지 비교.
usage: python -u _test_sam_multi.py
출력: D:\...\friend_contributed\sam_vis\
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from transformers import pipeline

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
OUT = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\sam_vis")
SAM = "facebook/sam-vit-base"
AREA_MIN, AREA_MAX, NMS_IOU = 0.03, 0.55, 0.5

SAMPLES = [
    ("anon_004/KakaoTalk_20260515_153209337_07.jpg", "수육·칼국수·제육·만두"),
    ("anon_007/KakaoTalk_20260515_154803302_17.jpg", "튀김우동 2그릇"),
    ("anon_010/KakaoTalk_20260516_025933802_20.jpg", "라면·돈가스·김밥"),
    ("anon_008/KakaoTalk_20260515_195354702.jpg", "돈가스·카레우동·고로케"),
]


def _iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def main():
    print(f"SAM 로드: {SAM} ...")
    gen = pipeline("mask-generation", model=SAM, device=0)
    OUT.mkdir(exist_ok=True)
    for k, (rel, vlm) in enumerate(SAMPLES):
        im = Image.open(BASE / rel).convert("RGB")
        small = im.copy(); small.thumbnail((1024, 1024))  # SAM 속도
        out = gen(small, points_per_batch=64)
        masks = out["masks"]
        W, H = small.size
        boxes = []
        for m in masks:
            ys, xs = np.where(m)
            if len(xs) == 0:
                continue
            box = [float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())]
            a = (box[2] - box[0]) * (box[3] - box[1])
            if AREA_MIN * W * H <= a <= AREA_MAX * W * H:
                boxes.append((box, a))
        boxes.sort(key=lambda x: -x[1])  # 큰 것부터
        kept = []
        for b, _ in boxes:
            if all(_iou(b, k) < NMS_IOU for k in kept):
                kept.append(b)
        # 원본 스케일로 환산
        sx, sy = im.width / W, im.height / H
        kept_full = [[b[0] * sx, b[1] * sy, b[2] * sx, b[3] * sy] for b in kept]
        print(f"  {k:02d} {rel.split('/')[-1]} -> {len(kept_full)}개 (원시마스크 {len(masks)}) | VLM:{vlm}")
        vis = im.copy(); d = ImageDraw.Draw(vis)
        for b in kept_full:
            d.rectangle(b, outline=(168, 85, 247), width=max(3, im.width // 280))
        vis.save(OUT / f"{k:02d}_{len(kept_full)}box_{rel.replace('/', '_')}")
    print(f"\n시각화: {OUT}")
    print("비교: Grounding DINO는 우동2그릇→2 / 라면돈가스김밥→6 / 수육한상→3 였음")


if __name__ == "__main__":
    main()
