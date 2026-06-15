# -*- coding: utf-8 -*-
"""(A) 최종 파이프라인 — Grounding DINO 탐지 → DINOv3 마스킹 분류 (end-to-end).

Grounding DINO로 한상의 모든 음식 영역을 찾고(단일요리 bias 없음, NMS+면적밴드 정리)
→ 각 음식을 '나머지 마스킹' 후 DINOv3로 분류 → 박스+한글라벨 시각화.
YOLO 디텍터(1~2개) 대비 다중요리 실제 동작 검증.
usage: python -u _test_gdino_dino_e2e.py
출력: D:\...\friend_contributed\gdino_dino_e2e\
"""
from __future__ import annotations

import sys
from pathlib import Path

import torch
from PIL import Image, ImageDraw, ImageFont
from transformers import AutoProcessor, GroundingDinoForObjectDetection

sys.path.insert(0, r"C:\Lemon-sin\backend\food_image_analysis\dino_classifier")
from food_pipeline_dino import FoodPipeline  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
OUT = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\gdino_dino_e2e")
FONT = r"C:\Windows\Fonts\malgun.ttf"
GDINO = "IDEA-Research/grounding-dino-tiny"
PROMPT = "food. dish. bowl of food. plate of food."
BOX_TH, AREA_MIN, AREA_MAX, NMS_IOU = 0.20, 0.03, 0.55, 0.5
dev = "cuda" if torch.cuda.is_available() else "cpu"

SAMPLES = [
    ("anon_004/KakaoTalk_20260515_153209337_07.jpg", "수육·칼국수·제육·만두"),
    ("anon_007/KakaoTalk_20260515_154803302_17.jpg", "튀김우동 2그릇"),
    ("anon_010/KakaoTalk_20260516_025933802_20.jpg", "라면·돈가스·김밥"),
    ("anon_010/KakaoTalk_20260516_024114883_20.jpg", "치킨·떡볶이·로제떡볶이"),
    ("anon_008/KakaoTalk_20260515_195354702.jpg", "돈가스·카레우동·고로케"),
    ("anon_001/KakaoTalk_20260515_152203757.jpg", "떡볶이·튀김·반찬 한상"),
]


def _iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def main():
    print("Grounding DINO + DINOv3 로드...")
    gproc = AutoProcessor.from_pretrained(GDINO)
    gdino = GroundingDinoForObjectDetection.from_pretrained(GDINO).to(dev).eval()
    fp = FoodPipeline()  # DINOv3 분류기(디텍터는 안 씀)
    OUT.mkdir(exist_ok=True)

    def detect(im):
        inputs = gproc(images=im, text=PROMPT, return_tensors="pt").to(dev)
        with torch.no_grad():
            out = gdino(**inputs)
        try:
            res = gproc.post_process_grounded_object_detection(
                out, inputs.input_ids, box_threshold=BOX_TH, text_threshold=BOX_TH,
                target_sizes=[im.size[::-1]])[0]
        except TypeError:
            res = gproc.post_process_grounded_object_detection(
                out, threshold=BOX_TH, text_threshold=BOX_TH, target_sizes=[im.size[::-1]])[0]
        W, H = im.size
        band = [(b, s) for b, s in zip(res["boxes"].cpu().tolist(), res["scores"].cpu().tolist())
                if AREA_MIN * W * H <= (b[2] - b[0]) * (b[3] - b[1]) <= AREA_MAX * W * H]
        band.sort(key=lambda x: -x[1])
        kept = []
        for b, s in band:
            if all(_iou(b, k) < NMS_IOU for k in kept):
                kept.append(b)
        return kept

    for k, (rel, vlm) in enumerate(SAMPLES):
        im = Image.open(BASE / rel).convert("RGB")
        boxes = detect(im)
        foods = fp.classify_boxes(im, boxes)
        names = [(f["name_ko"], round(f["conf"], 2)) for f in foods]
        print(f"  {k:02d} {rel.split('/')[-1]} -> {len(foods)}개 {names}  | VLM:{vlm}")
        vis = im.copy(); d = ImageDraw.Draw(vis); W = im.width
        try:
            font = ImageFont.truetype(FONT, max(20, W // 36))
        except OSError:
            font = ImageFont.load_default()
        for f in foods:
            x1, y1, x2, y2 = f["box"]
            d.rectangle([x1, y1, x2, y2], outline=(34, 197, 94), width=max(3, W // 260))
            lab = f"{f['name_ko']} {f['conf']*100:.0f}%"
            tb = d.textbbox((x1, y1), lab, font=font)
            ty = max(0, y1 - (tb[3] - tb[1]) - 8)
            d.rectangle([x1, ty, x1 + (tb[2]-tb[0]) + 10, ty + (tb[3]-tb[1]) + 8], fill=(34, 197, 94))
            d.text((x1 + 5, ty + 2), lab, fill="white", font=font)
        vis.save(OUT / f"{k:02d}_{len(foods)}food_{rel.replace('/', '_')}")
    print(f"\n시각화: {OUT}")


if __name__ == "__main__":
    main()
