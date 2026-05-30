"""exp06 클래스 분리 검토용 montage 생성.

각 원본 클래스(seafood-stew/noodle-soup/stew)를 제안 하위클래스로 묶어,
코드별 샘플 이미지 1장 + 한글명/코드/train·val 캡션을 그리드로 합성한다.
사용자 시각 승인용. (일회성 헬퍼)
"""

from __future__ import annotations

import glob
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMG_DIR = Path(r"C:\Lemon-sin\data\food_images\processed\aihub_yolo_split\train\images")
OUT_DIR = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review")
FONT = r"C:\Windows\Fonts\malgun.ttf"

TILE, CAP, COLS, PAD, HEADER = 240, 70, 5, 10, 64

# (subclass, korean, code, train, val)
GROUPS: dict[str, list[tuple[str, str, str, int, int]]] = {
    "seafood-stew": [
        ("해물매운탕", "광어매운탕", "B12021", 260, 10),
        ("해물매운탕", "우럭매운탕", "B12124", 250, 30),
        ("해물매운탕", "알내장탕", "A13023", 350, 60),
        ("해물매운탕", "해물뚝배기", "B12165", 270, 20),
        ("해물맑은탕", "해천탕", "A13037", 400, 90),
        ("해물맑은탕", "해신탕", "A13036", 340, 60),
        ("해물맑은탕", "해물누룽지탕", "A14146", 340, 80),
        ("해물맑은탕", "대구탕", "A13009", 320, 70),
        ("해물찜류", "황태찜", "A13048", 370, 50),
        ("해물찜류", "대구뽈찜", "A13008", 320, 40),
    ],
    "noodle-soup": [
        ("칼국수", "추어칼국수", "A13034", 350, 30),
        ("칼국수", "팥칼국수", "B12161", 260, 0),
        ("칼국수", "칼국수", "B12150", 250, 10),
        ("칼국수", "얼큰칼국수", "B12117", 240, 40),
        ("칼국수", "바지락칼국수", "B12087", 220, 60),
        ("쌀국수", "닭고기쌀국수", "A14025", 370, 40),
        ("쌀국수", "매운해물쌀국수", "A14047", 330, 70),
        ("쌀국수", "소대창쌀국수", "A14083", 310, 30),
        ("쌀국수", "쌀국수", "A14094", 310, 0),
        ("쌀국수", "똠얌꿍쌀국수", "A14032", 300, 50),
        ("쌀국수", "해물쌀국수", "A14148", 300, 50),
        ("쌀국수", "마라쌀국수", "A14043", 290, 80),
        ("쌀국수", "소곱창쌀국수", "A14082", 260, 50),
        ("쌀국수", "불고기쌀국수", "A14064", 230, 50),
        ("쌀국수", "소힘줄(스지)쌀국수", "A14085", 220, 40),
        ("쌀국수", "차돌양지쌀국수", "A14112", 220, 60),
        ("국수일반", "초계국수", "A13029", 340, 50),
        ("국수일반", "어탕국수", "A13024", 280, 80),
        ("국수일반", "멸치국수", "B12075", 280, 10),
        ("국수일반", "고기국수", "B12016", 260, 20),
    ],
    "stew": [
        ("찌개류(붉은)", "꽁치김치찌개", "B12032", 100, 20),
        ("찌개류(붉은)", "김치찜", "B12027", 230, 50),
        ("찌개류(붉은)", "해물순두부찌개", "B12167", 260, 20),
        ("찌개류(붉은)", "황태부대찌개", "A13045", 340, 40),
        ("된장찌개류", "차돌된장찌개", "B12138", 270, 10),
        ("된장찌개류", "바지락된장국", "B12086", 270, 0),
    ],
}

COLORS: dict[str, tuple[int, int, int]] = {
    "해물매운탕": (255, 170, 170),
    "해물맑은탕": (173, 216, 230),
    "해물찜류": (255, 200, 150),
    "칼국수": (200, 230, 180),
    "쌀국수": (255, 240, 170),
    "국수일반": (215, 215, 215),
    "찌개류(붉은)": (255, 180, 180),
    "된장찌개류": (210, 180, 140),
}


def _sample(code: str) -> Image.Image:
    hits = sorted(glob.glob(str(IMG_DIR / f"train_{code}_*.jpg")))
    canvas = Image.new("RGB", (TILE, TILE), (235, 235, 235))
    if hits:
        im = Image.open(hits[0]).convert("RGB")
        im.thumbnail((TILE, TILE))
        canvas.paste(im, ((TILE - im.width) // 2, (TILE - im.height) // 2))
    return canvas


def build(cls_name: str, items: list[tuple[str, str, str, int, int]]) -> Path:
    f_title = ImageFont.truetype(FONT, 26)
    f_sub = ImageFont.truetype(FONT, 18)
    f_kr = ImageFont.truetype(FONT, 19)
    f_sm = ImageFont.truetype(FONT, 14)

    rows = (len(items) + COLS - 1) // COLS
    cw = COLS * TILE + (COLS + 1) * PAD
    ch = HEADER + rows * (TILE + CAP + PAD) + PAD
    sheet = Image.new("RGB", (cw, ch), (255, 255, 255))
    d = ImageDraw.Draw(sheet)

    subs: list[str] = []
    for it in items:
        if it[0] not in subs:
            subs.append(it[0])
    legend = "   ".join(f"■ {s}({sum(1 for x in items if x[0]==s)})" for s in subs)
    d.text((PAD, 8), f"{cls_name} 분리안", font=f_title, fill=(20, 20, 20))
    d.text((PAD, 40), legend, font=f_sub, fill=(80, 80, 80))

    for i, (sub, kr, code, tr, va) in enumerate(items):
        r, c = divmod(i, COLS)
        x = PAD + c * (TILE + PAD)
        y = HEADER + r * (TILE + CAP + PAD)
        sheet.paste(_sample(code), (x, y))
        col = COLORS.get(sub, (220, 220, 220))
        d.rectangle([x, y + TILE, x + TILE, y + TILE + CAP], fill=col)
        d.text((x + 6, y + TILE + 3), f"[{sub}]", font=f_sm, fill=(60, 60, 60))
        d.text((x + 6, y + TILE + 20), kr, font=f_kr, fill=(0, 0, 0))
        flag = "  ⚠val=0" if va == 0 else ""
        d.text((x + 6, y + TILE + 46), f"{code}  tr{tr}/va{va}{flag}", font=f_sm, fill=(90, 90, 90))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"montage_{cls_name}.png"
    sheet.save(out)
    return out


if __name__ == "__main__":
    for name, items in GROUPS.items():
        p = build(name, items)
        print(f"WROTE {p}  ({len(items)} tiles)")
