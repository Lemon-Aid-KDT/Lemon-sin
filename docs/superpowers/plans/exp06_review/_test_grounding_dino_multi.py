# -*- coding: utf-8 -*-
"""Grounding DINO 다중요리 탐지 테스트 — 단일요리 bias 없는 범용 탐지기.

기존 YOLO 디텍터(exp16b/인계)는 단일요리 학습이라 한상을 1개로 뭉갬.
Grounding DINO는 텍스트 프롬프트("food")로 객체를 찾아 단일요리 bias가 없음.
한상 사진에서 음식 영역을 몇 개 찾는지 + 시각화로 확인.
usage: python -u _test_grounding_dino_multi.py
출력: D:\...\friend_contributed\gdino_vis\
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch
from PIL import Image, ImageDraw, ImageFont
from transformers import AutoProcessor, GroundingDinoForObjectDetection

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
OUT = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\gdino_vis")
FONT = r"C:\Windows\Fonts\malgun.ttf"
GDINO = "IDEA-Research/grounding-dino-tiny"
dev = "cuda" if torch.cuda.is_available() else "cpu"

# 한상(다중요리) 대표 샘플 + VLM이 본 음식 수
SAMPLES = [
    ("anon_004/KakaoTalk_20260515_153209337_07.jpg", "수육·칼국수·제육·만두·반찬(5+)"),
    ("anon_007/KakaoTalk_20260515_154803302_17.jpg", "튀김우동 2그릇"),
    ("anon_010/KakaoTalk_20260516_025933802_20.jpg", "라면·돈가스·김밥(3)"),
    ("anon_009/KakaoTalk_20260515_192944607.jpg", "브런치 플래터·크림파스타"),
    ("anon_010/KakaoTalk_20260516_024114883_20.jpg", "치킨·떡볶이·로제떡볶이(3)"),
    ("anon_008/KakaoTalk_20260515_195354702.jpg", "돈가스·카레우동·고로케 정식"),
]
PROMPT = "food. dish. bowl of food. plate of food."
BOX_TH, TEXT_TH = 0.20, 0.20
AREA_MIN, AREA_MAX = 0.03, 0.55  # 반찬종지(작음)~접시전체(거대) 제외 밴드
NMS_IOU = 0.5


def _iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _nms_area(boxes, scores, W, H):
    """NMS(중복 병합) + 면적 밴드 필터 → (box, score) 리스트."""
    band = [(b, s) for b, s in zip(boxes, scores)
            if AREA_MIN * W * H <= (b[2] - b[0]) * (b[3] - b[1]) <= AREA_MAX * W * H]
    band.sort(key=lambda x: -x[1])
    kept = []
    for b, s in band:
        if all(_iou(b, k[0]) < NMS_IOU for k in kept):
            kept.append((b, s))
    return kept


def main():
    print(f"Grounding DINO 로드: {GDINO} ...")
    proc = AutoProcessor.from_pretrained(GDINO)
    model = GroundingDinoForObjectDetection.from_pretrained(GDINO).to(dev).eval()
    OUT.mkdir(exist_ok=True)
    print(f"프롬프트: '{PROMPT}' / box_th {BOX_TH}\n")

    for k, (rel, vlm) in enumerate(SAMPLES):
        p = BASE / rel
        im = Image.open(p).convert("RGB")
        inputs = proc(images=im, text=PROMPT, return_tensors="pt").to(dev)
        with torch.no_grad():
            out = model(**inputs)
        try:
            res = proc.post_process_grounded_object_detection(
                out, inputs.input_ids, box_threshold=BOX_TH, text_threshold=TEXT_TH,
                target_sizes=[im.size[::-1]])[0]
        except TypeError:
            res = proc.post_process_grounded_object_detection(
                out, threshold=BOX_TH, text_threshold=TEXT_TH, target_sizes=[im.size[::-1]])[0]
        boxes = res["boxes"].cpu().tolist()
        scores = res["scores"].cpu().tolist()
        W, H = im.size
        keep = _nms_area(boxes, scores, W, H)  # NMS + 면적 밴드
        print(f"  {k:02d} {rel.split('/')[-1]} -> {len(keep)}개 박스 (원시 {len(boxes)}) | VLM:{vlm}")
        # 시각화
        vis = im.copy(); d = ImageDraw.Draw(vis)
        try:
            font = ImageFont.truetype(FONT, max(18, W // 38))
        except OSError:
            font = ImageFont.load_default()
        for b, s in keep:
            d.rectangle(b, outline=(255, 90, 0), width=max(3, W // 280))
            d.text((b[0] + 4, max(0, b[1] - 24)), f"{s:.2f}", fill=(255, 90, 0), font=font)
        vis.save(OUT / f"{k:02d}_{len(keep)}box_{rel.replace('/', '_')}")
    print(f"\n시각화: {OUT}")


if __name__ == "__main__":
    main()
