# -*- coding: utf-8 -*-
"""단일요리 음식 분석 데모 (Streamlit) — exp16b 게이트 + DINOv3 분류 + 영양.

Run:
    streamlit run backend/food_image_analysis/food_classifier/app.py --server.port 8510
(DINOv3 게이트 모델이라 첫 실행 시 HF_TOKEN 필요 — README 참조)
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from food_classifier import FoodClassifier, kr  # noqa: E402

ROOT = HERE.parents[2]
TEST_DIR = ROOT / "data" / "food_images" / "raw" / "test_data"
FONT = r"C:\Windows\Fonts\malgun.ttf"


@st.cache_resource
def load() -> FoodClassifier:
    """분류기 1회 로드 (exp16b + DINOv3 + 프로브 + 영양표)."""
    return FoodClassifier()


def draw(im: Image.Image, r: dict) -> Image.Image:
    """대표 박스 + 한글 라벨."""
    out = im.convert("RGB").copy()
    d = ImageDraw.Draw(out)
    try:
        font = ImageFont.truetype(FONT, max(18, out.width // 36))
    except OSError:
        font = ImageFont.load_default()
    x1, y1, x2, y2 = r["box"]
    d.rectangle([x1, y1, x2, y2], outline=(34, 197, 94), width=max(3, out.width // 280))
    lab = f"{r['name_ko']} {r['conf'] * 100:.0f}%"
    tb = d.textbbox((x1, y1), lab, font=font)
    ty = max(0, y1 - (tb[3] - tb[1]) - 8)
    d.rectangle([x1, ty, x1 + (tb[2] - tb[0]) + 10, ty + (tb[3] - tb[1]) + 8], fill=(34, 197, 94))
    d.text((x1 + 5, ty + 2), lab, fill="white", font=font)
    return out


st.set_page_config(page_title="음식 분석 (단일요리)", page_icon="🍱", layout="wide")
st.title("🍱 음식 분석 — 단일요리")
st.caption("음식 하나만 나오게 촬영 → exp16b 음식 유무 확인 → DINOv3 40종 분류 → 영양 정보")

fc = load()
with st.sidebar:
    fc.det_conf = st.slider("음식 유무 임계값", 0.05, 0.5, 0.10, 0.01)
    st.caption(f"분류: DINOv3-vitb16 + 선형프로브 ({len(fc.classes)}종, 전체이미지)")
    test_imgs = sorted(p.name for p in TEST_DIR.glob("*.jpg")) if TEST_DIR.exists() else []
    picked = st.selectbox("📂 test_data 샘플", ["(업로드)"] + test_imgs)

up = st.file_uploader("음식 사진 (한 음식만)", type=["jpg", "jpeg", "png", "webp"])
im = Image.open(up) if up else (Image.open(TEST_DIR / picked) if picked and picked != "(업로드)" else None)
if im is None:
    st.info("👆 음식 하나가 나온 사진을 올리거나 샘플을 선택하세요.")
    st.stop()

r = fc.analyze(im)
ci, cv = st.columns([3, 2])
with ci:
    if r is None:
        st.image(im, width="stretch")
        st.error("## 🚫 음식이 없어요. 다시 찍어주세요.")
        st.stop()
    st.image(draw(im, r), width="stretch")
with cv:
    st.subheader(f"🍽️ {r['name_ko']}  ·  {r['conf'] * 100:.0f}%")
    st.caption(f"`{r['name_en']}`")
    n = r["nutrition"]
    if n:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("열량", f"{n.get('kcal_100g','?')} kcal")
        c2.metric("탄수", f"{n.get('carb_g','?')} g")
        c3.metric("단백", f"{n.get('protein_g','?')} g")
        c4.metric("지방", f"{n.get('fat_g','?')} g")
        st.caption(f"100g 기준 · 1인분 {n.get('serving_g','?')}g · 나트륨 {n.get('sodium_mg','?')}mg · 당류 {n.get('sugar_g','?')}g")
    st.caption("※ 참고용 정보 — 진단·처방이 아니며 사용자가 확인·수정합니다.")
