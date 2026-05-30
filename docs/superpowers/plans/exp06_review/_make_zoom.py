"""특정 코드의 다량 샘플을 큰 타일로 펼쳐 오염(이질 이미지) 확대 검증."""

from __future__ import annotations

import glob
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMG_DIR = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_split\train\images")
OUT_DIR = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review")
FONT = r"C:\Windows\Fonts\malgun.ttf"
TILE, COLS, N, PAD, HEAD = 300, 6, 18, 8, 44


def build(label: str, code: str) -> Path:
    hits = sorted(glob.glob(str(IMG_DIR / f"train_{code}_*.jpg")))
    step = max(1, len(hits) // N)
    picks = hits[::step][:N]
    rows = (len(picks) + COLS - 1) // COLS
    W = COLS * (TILE + PAD) + PAD
    H = HEAD + rows * (TILE + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 10), f"{label}  ({code})  train={len(hits)}  — 샘플 {len(picks)}장 (세션 분산)",
           font=ImageFont.truetype(FONT, 24), fill=(20, 20, 20))
    fn = ImageFont.truetype(FONT, 13)
    for i, p in enumerate(picks):
        r, c = divmod(i, COLS)
        x = PAD + c * (TILE + PAD)
        y = HEAD + r * (TILE + PAD)
        im = Image.open(p).convert("RGB")
        im.thumbnail((TILE, TILE))
        cv = Image.new("RGB", (TILE, TILE), (235, 235, 235))
        cv.paste(im, ((TILE - im.width) // 2, (TILE - im.height) // 2))
        sheet.paste(cv, (x, y))
        d.text((x + 3, y + 2), Path(p).name.split("_", 2)[-1][:18], font=fn, fill=(255, 255, 0))
    out = OUT_DIR / f"zoom_{code}_{label}.png"
    sheet.save(out)
    return out


if __name__ == "__main__":
    for label, code in [("짬뽕쌀국수", "A14110")]:
        print("WROTE", build(label, code))
