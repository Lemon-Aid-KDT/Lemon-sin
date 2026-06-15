# -*- coding: utf-8 -*-
"""마스킹 파이프라인 정성 검증 — 실제 다중요리(한상) 사진 시각화.

FoodPipeline(디텍터+DINOv3 마스킹)을 VLM이 'multi'로 분류한 실제 한상 사진에 돌려
박스+한글라벨을 그려 저장. 라벨 없이 눈으로 마스킹 분류 품질 확인용.
출력: D:\...\friend_contributed\pipeline_vis_dino\ (사적사진, git밖)
usage: python -u _vis_pipeline_dino_multi.py   (GPU, HF_TOKEN 설정 후)
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, r"C:\Lemon-sin\backend\food_image_analysis\dino_classifier")
from food_pipeline_dino import FoodPipeline  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
CSV = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\wild_classification_2026-06-04.csv")
BASE = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\inbox")
OUT = Path(r"D:\Deeplearning\lemon\data\raw\friend_contributed\pipeline_vis_dino")
FONT = r"C:\Windows\Fonts\malgun.ttf"
N = 12


def draw(im, foods):
    out = im.convert("RGB").copy()
    d = ImageDraw.Draw(out)
    fs = max(18, out.width // 38)
    try:
        font = ImageFont.truetype(FONT, fs)
    except OSError:
        font = ImageFont.load_default()
    for f in foods:
        x1, y1, x2, y2 = f["box"]
        d.rectangle([x1, y1, x2, y2], outline=(34, 197, 94), width=max(3, out.width // 280))
        lab = f"{f['name_ko']} {f['conf']*100:.0f}%"
        tb = d.textbbox((x1, y1), lab, font=font)
        ty = max(0, y1 - (tb[3] - tb[1]) - 8)
        d.rectangle([x1, ty, x1 + (tb[2]-tb[0]) + 10, ty + (tb[3]-tb[1]) + 8], fill=(34, 197, 94))
        d.text((x1 + 5, ty + 2), lab, fill="white", font=font)
    return out


def main():
    rows = [r for r in csv.DictReader(CSV.open(encoding="utf-8-sig")) if r.get("category", "").strip() == "multi"]
    rows.sort(key=lambda r: (r["folder"], r["file"]))
    sample = rows[::max(1, len(rows) // N)][:N]
    print(f"multi 한상 {len(rows)}장 중 {len(sample)}장 샘플")
    import os
    det_path = os.environ.get("DET_PATH",
                              r"C:\Lemon-sin\backend\food_image_analysis\detector\detector_best.pt")
    print("디텍터:", os.path.basename(os.path.dirname(os.path.dirname(det_path))) or det_path)
    pipe = FoodPipeline(det_conf=0.15, detector_path=det_path)  # 과소탐지 완화(작은 헛박스=면적필터)
    OUT.mkdir(exist_ok=True)
    for k, r in enumerate(sample):
        p = BASE / r["folder"] / r["file"]
        try:
            im = Image.open(p)
        except Exception:
            continue
        foods = pipe.analyze(im)
        names = [(f["name_ko"], round(f["conf"], 2)) for f in foods]
        print(f"  {k:02d} {r['folder']}/{r['file']} -> {len(foods)}개 {names}  | VLM:{r.get('foods','')[:50]}")
        draw(im, foods).save(OUT / f"{k:02d}_{len(foods)}food_{r['folder']}_{r['file']}")
    print(f"\n시각화: {OUT}")


if __name__ == "__main__":
    main()
