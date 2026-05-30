"""다중코드·약한 클래스 데이터품질 감사용 montage + 매니페스트 생성.

각 대상 클래스마다 구성 424코드 1장씩을 한글명 캡션과 함께 그리드로 합성.
워크플로 감사 에이전트가 montage를 읽고 코드별 시각 일관성을 판정한다.
"""

from __future__ import annotations

import csv
import glob
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_split")
IMG_DIR = ROOT / "train" / "images"
INV = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_taxonomy_424_inventory.csv")
OUT_DIR = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\audit")
FONT = r"C:\Windows\Fonts\malgun.ttf"
TILE, COLS, CAP, PAD, HEAD = 190, 6, 46, 6, 40

# 약한/다중코드 우선 (이미 처리한 seafood-stew/noodle-soup/stew/spicy-seafood-noodles 제외;
# 잘 나온 거대 클래스 bread/fried-chicken/pizza/sandwich도 일단 제외)
AUDIT = [
    "soup", "hot-pot", "rice-soup", "rice-bowl", "mixed-rice-bowl", "ramen",
    "curry", "dumplings", "sushi", "salad", "spicy-rice-cakes", "seaweed-rice-roll",
    "grilled-fish", "barbecue-ribs", "raw-fish", "shrimp-dish", "pasta", "pork-cutlet",
]


def _tile(code: str) -> Image.Image:
    hits = sorted(glob.glob(str(IMG_DIR / f"train_{code}_*.jpg")))
    c = Image.new("RGB", (TILE, TILE), (235, 235, 235))
    if hits:
        im = Image.open(hits[len(hits) // 2]).convert("RGB")
        im.thumbnail((TILE, TILE))
        c.paste(im, ((TILE - im.width) // 2, (TILE - im.height) // 2))
    return c


def build(cls: str, items: list[dict]) -> Path:
    f_t = ImageFont.truetype(FONT, 22)
    f_k = ImageFont.truetype(FONT, 16)
    f_s = ImageFont.truetype(FONT, 12)
    rows = (len(items) + COLS - 1) // COLS
    W = COLS * (TILE + PAD) + PAD
    H = HEAD + rows * (TILE + CAP + PAD) + PAD
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 9), f"{cls}  ({len(items)} codes)", font=f_t, fill=(20, 20, 20))
    for i, it in enumerate(items):
        r, c = divmod(i, COLS)
        x = PAD + c * (TILE + PAD)
        y = HEAD + r * (TILE + CAP + PAD)
        sheet.paste(_tile(it["code"]), (x, y))
        d.rectangle([x, y + TILE, x + TILE, y + TILE + CAP], fill=(245, 245, 245))
        d.text((x + 4, y + TILE + 3), it["name"], font=f_k, fill=(0, 0, 0))
        d.text((x + 4, y + TILE + 26), f"{it['code']} tr{it['train']}/va{it['val']}", font=f_s, fill=(90, 90, 90))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"audit_{cls}.png"
    sheet.save(out)
    return out


if __name__ == "__main__":
    rows = list(csv.DictReader(open(INV, encoding="utf-8-sig")))
    manifest = {}
    for cls in AUDIT:
        items = [
            {"code": r["aihub_code"], "name": r["korean_name"],
             "train": int(r["train"]), "val": int(r["val"])}
            for r in rows if r["current_roboflow_class"] == cls
        ]
        items.sort(key=lambda x: -x["train"])
        p = build(cls, items)
        manifest[cls] = {"montage": str(p), "codes": items}
        print(f"{cls}: {len(items)} codes -> {p.name}")
    mpath = OUT_DIR / "manifest.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MANIFEST", mpath)
