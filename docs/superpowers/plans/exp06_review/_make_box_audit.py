"""박스 감사 montage: 대상 클래스 샘플 이미지에 GT 박스를 그려 박스 품질/라벨 일치 점검.

taxonomy v3 실제 약점(off-by-one 보정 후): ①데이터 빈약 소수클래스(mala/탕수육/제육)
②닭류 구분(chicken-galbi↔fried-chicken). 각 약점 클래스를 실제 혼동 대상과 나란히 배치.
CPU only (exp07 학습과 무관).
"""

from __future__ import annotations

import glob
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DS = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo63_bal500\train")
YAML = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo63_bal500\data.yaml")
OUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\box_audit.png")
FONT = r"C:\Windows\Fonts\malgun.ttf"
TILE, NCOL, LABELW, PAD, HEAD = 260, 5, 150, 6, 40

# WEAK = 약한 약점 클래스(빨강), 각 줄 뒤에 실제 혼동 대상을 인접 배치.
# ① 데이터 빈약 소수클래스  ② 닭류 구분.
WEAK = ["mala-hot-pot", "sweet-and-sour-pork", "stir-fried-pork", "chicken-galbi"]
CONTRAST = ["jjamppong", "fried-food-platter", "fried-chicken", "bulgogi"]
CLUSTER = WEAK  # draw_tile/색상 분기 호환용
TARGETS = ["mala-hot-pot", "jjamppong",          # ③ 빨강군 혼동
           "sweet-and-sour-pork", "fried-food-platter",  # ① 탕수육=튀김+소스
           "stir-fried-pork", "chicken-galbi", "fried-chicken",  # ② 닭/고기 구분
           "bulgogi"]                            # 대조(정탐 양호)


def load_names() -> dict[str, int]:
    name2idx = {}
    for ln in YAML.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if ":" in s and s.split(":")[0].strip().isdigit():
            i, n = s.split(":", 1)
            name2idx[n.strip()] = int(i)
    return name2idx


def first_class(lbl: Path) -> int | None:
    for line in lbl.read_text(encoding="utf-8").splitlines():
        p = line.split()
        if len(p) >= 5:
            return int(p[0])
    return None


def draw_tile(stem: str) -> Image.Image:
    img = Image.open(DS / "images" / f"{stem}.jpg").convert("RGB")
    W, H = img.size
    d = ImageDraw.Draw(img)
    for line in (DS / "labels" / f"{stem}.txt").read_text(encoding="utf-8").splitlines():
        p = line.split()
        if len(p) < 5:
            continue
        cx, cy, w, h = (float(v) for v in p[1:5])
        x1, y1 = (cx - w / 2) * W, (cy - h / 2) * H
        x2, y2 = (cx + w / 2) * W, (cy + h / 2) * H
        d.rectangle([x1, y1, x2, y2], outline=(255, 40, 40), width=max(3, W // 120))
    img.thumbnail((TILE, TILE))
    canvas = Image.new("RGB", (TILE, TILE), (235, 235, 235))
    canvas.paste(img, ((TILE - img.width) // 2, (TILE - img.height) // 2))
    return canvas


def main() -> None:
    name2idx = load_names()
    # 한 번 스캔해서 class_idx -> stems
    by_cls: dict[int, list[str]] = defaultdict(list)
    for lbl in sorted((DS / "labels").glob("*.txt")):
        c = first_class(lbl)
        if c is not None:
            by_cls[c].append(lbl.stem)

    rows = len(TARGETS)
    W = LABELW + NCOL * (TILE + PAD) + PAD
    H = HEAD + rows * (TILE + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    f_t = ImageFont.truetype(FONT, 22)
    f_l = ImageFont.truetype(FONT, 17)
    dr.text((PAD, 10), "박스 감사 (빨강박스=GT) — 빨강명=약점클래스, 초록명=혼동대상/대조", font=f_t, fill=(20, 20, 20))

    for r, cname in enumerate(TARGETS):
        idx = name2idx[cname]
        stems = by_cls.get(idx, [])
        step = max(1, len(stems) // NCOL)
        picks = stems[::step][:NCOL]
        y = HEAD + r * (TILE + PAD)
        col = (200, 60, 60) if cname in CLUSTER else (60, 120, 60)
        dr.text((PAD, y + TILE // 2 - 20), cname, font=f_l, fill=col)
        dr.text((PAD, y + TILE // 2 + 4), f"n={len(stems)}", font=f_l, fill=(110, 110, 110))
        for cidx, stem in enumerate(picks):
            sheet.paste(draw_tile(stem), (LABELW + cidx * (TILE + PAD), y))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
