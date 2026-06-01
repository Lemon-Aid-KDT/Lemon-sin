"""chicken-galbi ↔ fried-chicken 라벨노이즈 zoom 감사.

bal500 학습셋(실제 학습 대상)에서 해당 클래스 표본을 큰 타일로 펼치고 GT 박스를 그린다.
파일 stem의 aihub 원본코드(예: train_A13001_...)를 캡션·집계해 이질 소스코드 혼입을 탐지.
CPU only. 출력: zoom_label_chicken-galbi.png / zoom_label_fried-chicken.png
"""

from __future__ import annotations

import collections
import re
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

DS = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo63_bal500\train")
YAML = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_taxo63_bal500\data.yaml")
OUT_DIR = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review")
FONT = r"C:\Windows\Fonts\malgun.ttf"
TILE, COLS, N, PAD, HEAD = 300, 6, 24, 8, 46
CODE_RE = re.compile(r"_([A-Z]\d+)_")

TARGETS = ["chicken-galbi", "fried-chicken"]


def name2idx() -> dict[str, int]:
    names = yaml.safe_load(YAML.read_text(encoding="utf-8"))["names"]
    items = names.items() if isinstance(names, dict) else enumerate(names)
    return {n: int(i) for i, n in items}


def first_class(lbl: Path) -> int | None:
    for line in lbl.read_text(encoding="utf-8").splitlines():
        p = line.split()
        if len(p) >= 5:
            return int(p[0])
    return None


def src_code(stem: str) -> str:
    m = CODE_RE.search(stem)
    return m.group(1) if m else "?"


def draw_tile(stem: str) -> Image.Image:
    img = Image.open(DS / "images" / f"{stem}.jpg").convert("RGB")
    W, H = img.size
    d = ImageDraw.Draw(img)
    for line in (DS / "labels" / f"{stem}.txt").read_text(encoding="utf-8").splitlines():
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


def build(cname: str, idx: int) -> Path:
    stems = sorted(p.stem for p in (DS / "labels").glob("*.txt") if first_class(p) == idx)
    codes = collections.Counter(src_code(s) for s in stems)
    step = max(1, len(stems) // N)
    picks = stems[::step][:N]
    rows = (len(picks) + COLS - 1) // COLS
    W = COLS * (TILE + PAD) + PAD
    H = HEAD + rows * (TILE + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    code_str = " ".join(f"{c}:{n}" for c, n in codes.most_common())
    d.text((PAD, 8), f"{cname}  n={len(stems)}  (빨강=GT)  소스코드 {code_str}",
           font=ImageFont.truetype(FONT, 22), fill=(20, 20, 20))
    fn = ImageFont.truetype(FONT, 14)
    for i, stem in enumerate(picks):
        r, c = divmod(i, COLS)
        x, y = PAD + c * (TILE + PAD), HEAD + r * (TILE + PAD)
        sheet.paste(draw_tile(stem), (x, y))
        d.rectangle([x, y, x + 70, y + 18], fill=(0, 0, 0))
        d.text((x + 3, y + 1), src_code(stem), font=fn, fill=(255, 255, 0))
    out = OUT_DIR / f"zoom_label_{cname}.png"
    sheet.save(out)
    print(f"{cname}: n={len(stems)} codes={dict(codes)} -> {out.name}")
    return out


if __name__ == "__main__":
    n2i = name2idx()
    for t in TARGETS:
        build(t, n2i[t])
