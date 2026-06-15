# -*- coding: utf-8 -*-
"""실전 파이프라인 데모 — 디텍터 + DINOv3 마스킹 분류 + 영양 (Streamlit).

사진 업로드 → ①디텍터로 음식들 검출 → ②각 음식을 '나머지 음식 마스킹' 후 DINOv3 분류
→ ③박스+한글 라벨 오버레이 + 음식별 영양 카드. 다중요리(한상) 대응.
Run:
    streamlit run backend/food_image_analysis/dino_classifier/app_pipeline_dino_demo.py --server.port 8506
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from food_pipeline_dino import FoodPipeline, kr  # noqa: E402

ROOT = HERE.parents[2]
NUTRITION_CSV = ROOT / "docs" / "deliverables" / "nutrition-40class" / "food_nutrition_40class.csv"
TEST_DIR = ROOT / "data" / "food_images" / "raw" / "test_data"
FONT = r"C:\Windows\Fonts\malgun.ttf"


@st.cache_resource
def load_pipeline() -> FoodPipeline:
    """파이프라인(디텍터+DINOv3+프로브)을 1회 로드한다."""
    return FoodPipeline()


@st.cache_data
def load_nutrition() -> dict[str, dict[str, str]]:
    """40클래스 영양 정보(100g 기준)를 로드한다."""
    if not NUTRITION_CSV.exists():
        return {}
    table = {}
    with NUTRITION_CSV.open(encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            table[r["class_en"]] = r
    return table


def draw(im: Image.Image, foods: list[dict]) -> Image.Image:
    """박스 + 한글 라벨 오버레이."""
    out = im.convert("RGB").copy()
    d = ImageDraw.Draw(out)
    fs = max(16, out.width // 40)
    try:
        font = ImageFont.truetype(FONT, fs)
    except OSError:
        font = ImageFont.load_default()
    for f in foods:
        x1, y1, x2, y2 = f["box"]
        d.rectangle([x1, y1, x2, y2], outline=(34, 197, 94), width=max(3, out.width // 300))
        label = f"{f['name_ko']} {f['conf'] * 100:.0f}%"
        tb = d.textbbox((x1, y1), label, font=font)
        ty = max(0, y1 - (tb[3] - tb[1]) - 8)
        d.rectangle([x1, ty, x1 + (tb[2] - tb[0]) + 10, ty + (tb[3] - tb[1]) + 8], fill=(34, 197, 94))
        d.text((x1 + 5, ty + 2), label, fill="white", font=font)
    return out


st.set_page_config(page_title="음식 분석 파이프라인 (DINOv3)", page_icon="🍱", layout="wide")
st.title("🍱 음식 분석 파이프라인 — 디텍터 + DINOv3 + 방해음식 마스킹")
st.caption("디텍터로 음식 위치 검출 → 각 음식 분류 시 나머지 음식 마스킹(맥락 보존) → DINOv3 40종 분류 + 영양")

pipe = load_pipeline()
nutrition = load_nutrition()

with st.sidebar:
    st.header("⚙️ 설정")
    pipe.det_conf = st.slider("디텍터 신뢰도", 0.1, 0.7, 0.25, 0.05)
    st.caption(f"분류기: DINOv3-vitb16 + 선형프로브 ({len(pipe.classes)}종)")
    st.caption("다중요리: 각 음식 분류 시 나머지 음식 회색 마스킹(겹침 시 타겟 복원)")
    test_imgs = sorted(p.name for p in TEST_DIR.glob("*.jpg")) if TEST_DIR.exists() else []
    picked = st.selectbox("📂 test_data 샘플", ["(업로드)"] + test_imgs)

up = st.file_uploader("이미지 업로드 (한상 사진 환영)", type=["jpg", "jpeg", "png", "webp"])
im = None
if up is not None:
    im = Image.open(up)
elif picked and picked != "(업로드)":
    im = Image.open(TEST_DIR / picked)

if im is None:
    st.info("👆 이미지를 올리거나 샘플을 선택하세요.")
    st.stop()

foods = pipe.analyze(im)
col_img, col_info = st.columns([3, 2])
with col_img:
    if not foods:
        st.image(im, width="stretch")
        st.error("## 🚫 음식을 찾지 못했어요. 다시 찍어주세요.")
        st.stop()
    st.image(draw(im, foods), caption=f"{len(foods)}개 음식 검출", width="stretch")

with col_info:
    st.subheader(f"🍽️ 검출된 음식 {len(foods)}개")
    for k, f in enumerate(foods, 1):
        st.markdown(f"**{k}. {f['name_ko']}** — 분류 {f['conf'] * 100:.0f}%  ·  `{f['name_en']}`")
        n = nutrition.get(f["name_en"])
        if n:
            kcal = n.get("kcal_100g", "?"); sv = n.get("serving_g", "?")
            st.caption(f"   100g당 {kcal}kcal · 1인분 {sv}g · 나트륨 {n.get('sodium_mg','?')}mg · 당류 {n.get('sugar_g','?')}g")
    st.caption("※ 결과는 참고용 — 진단·처방이 아니며 사용자가 확인·수정합니다.")
