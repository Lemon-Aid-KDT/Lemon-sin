"""B12003(닭갈비 후보) 정체 확인 zoom — 비교군 B11003(양념치킨 의심)·B12144(치즈) 동반.

bal500 train 이미지에서 코드별로 큰 타일 + GT 박스. 코드는 파일명 stem에 포함.
출력: zoom_code_compare.png
"""

from __future__ import annotations

import glob
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DS = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo63_bal500\train")
OUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\zoom_code_compare.png")
FONT = r"C:\Windows\Fonts\malgun.ttf"
TILE, COLS, N, PAD, HEAD, ROWH = 300, 8, 8, 8, 46, 30

# (코드, 라벨) — 한 블록(=1행 8장)씩
BLOCKS = [
    ("B12003", "chicken-galbi 소속 (닭갈비? 양념치킨?)"),
    ("B11003", "fried-chicken 소속 (양념치킨 비교군)"),
    ("B12144", "chicken-galbi 소속 (치즈닭갈비)"),
]


def tile(img_path: Path) -> Image.Image:
    img = Image.open(img_path).convert("RGB")
    W, H = img.size
    d = ImageDraw.Draw(img)
    lbl = DS / "labels" / f"{img_path.stem}.txt"
    if lbl.exists():
        for line in lbl.read_text(encoding="utf-8").splitlines():
            p = line.split()
            if len(p) < 5:
                continue
            cx, cy, w, h = (float(v) for v in p[1:5])
            d.rectangle([(cx - w / 2) * W, (cy - h / 2) * H, (cx + w / 2) * W, (cy + h / 2) * H],
                        outline=(255, 40, 40), width=max(3, W // 130))
    img.thumbnail((TILE, TILE))
    cv = Image.new("RGB", (TILE, TILE), (235, 235, 235))
    cv.paste(img, ((TILE - img.width) // 2, (TILE - img.height) // 2))
    return cv


def main() -> None:
    W = COLS * (TILE + PAD) + PAD
    H = HEAD + len(BLOCKS) * (ROWH + TILE + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 10), "코드별 정체 확인 (빨강=GT)", font=ImageFont.truetype(FONT, 24), fill=(20, 20, 20))
    f_b = ImageFont.truetype(FONT, 18)
    y = HEAD
    for code, label in BLOCKS:
        hits = sorted(glob.glob(str(DS / "images" / f"*_{code}_*.jpg")))
        step = max(1, len(hits) // N)
        picks = hits[::step][:N]
        d.text((PAD, y), f"{code}  {label}  (총 {len(hits)}장)", font=f_b, fill=(180, 40, 40))
        y += ROWH
        for i, p in enumerate(picks):
            sheet.paste(tile(Path(p)), (PAD + i * (TILE + PAD), y))
        y += TILE + PAD
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
