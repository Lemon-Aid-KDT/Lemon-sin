"""짬뽕(spicy-seafood-noodles) 데이터 오염 검증 montage.

코드별로 세션 분산 샘플 N장을 한 행에 펼쳐, 같은 'OO짬뽕' 이름 아래
실제 음식 형태가 일관적인지/이질적인지 눈으로 확인한다. (일회성 헬퍼)
"""

from __future__ import annotations

import glob
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMG_DIR = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_split\train\images")
OUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\montage_jjamppong_check.png")
FONT = r"C:\Windows\Fonts\malgun.ttf"

TILE, N, LABELW, PAD, HEADER = 200, 5, 200, 8, 50

# (label, code, train, note)
CODES = [
    ("나가사끼짬뽕", "A14018", 430, "흰국물?"),
    ("꼬막짬뽕", "B11016", 260, "빨강?"),
    ("차돌짬뽕", "B11097", 260, "빨강?"),
    ("짬뽕(기본)", "B12110", 130, "빨강?"),
    ("쟁반짬뽕", "B11092", 90, "볶음?"),
    ("짬뽕쌀국수", "A14110", 220, "쌀국수?"),
    ("짬뽕차돌쌀국수", "A14111", 250, "쌀국수?"),
]


def _samples(code: str, n: int) -> list[Image.Image]:
    hits = sorted(glob.glob(str(IMG_DIR / f"train_{code}_*.jpg")))
    if not hits:
        return []
    # 세션 분산: 균등 간격으로 n장
    step = max(1, len(hits) // n)
    picks = hits[::step][:n]
    out = []
    for p in picks:
        im = Image.open(p).convert("RGB")
        im.thumbnail((TILE, TILE))
        c = Image.new("RGB", (TILE, TILE), (235, 235, 235))
        c.paste(im, ((TILE - im.width) // 2, (TILE - im.height) // 2))
        out.append(c)
    return out


def build() -> Path:
    f_t = ImageFont.truetype(FONT, 24)
    f_l = ImageFont.truetype(FONT, 20)
    f_s = ImageFont.truetype(FONT, 14)
    rows = len(CODES)
    W = LABELW + N * (TILE + PAD) + PAD
    H = HEADER + rows * (TILE + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 12), "짬뽕(spicy-seafood-noodles) 코드별 실제 사진 — 형태 일관성 검증",
           font=f_t, fill=(20, 20, 20))
    for r, (label, code, tr, note) in enumerate(CODES):
        y = HEADER + r * (TILE + PAD)
        d.text((PAD, y + TILE // 2 - 30), label, font=f_l, fill=(0, 0, 0))
        d.text((PAD, y + TILE // 2), f"{code}", font=f_s, fill=(90, 90, 90))
        d.text((PAD, y + TILE // 2 + 20), f"train {tr}", font=f_s, fill=(90, 90, 90))
        d.text((PAD, y + TILE // 2 + 40), f"추정:{note}", font=f_s, fill=(150, 80, 80))
        for i, tile in enumerate(_samples(code, N)):
            x = LABELW + i * (TILE + PAD)
            sheet.paste(tile, (x, y))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    return OUT


if __name__ == "__main__":
    print("WROTE", build())
