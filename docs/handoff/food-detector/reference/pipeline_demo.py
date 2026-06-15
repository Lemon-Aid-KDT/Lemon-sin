# -*- coding: utf-8 -*-
"""통합 파이프라인 데모 — 디텍터(v3+CLIP) → 분류기(exp16b, 지원 40클래스).

한 장의 사진에서: ①v3 디텍터가 음식 영역 박스를 찾고(다중 음식 대응)
②CLIP 필터가 비음식 박스를 거르고 ③각 박스 crop을 exp16b 분류기가 음식 종류로 판별한다.
분류기 단독 데모(app_exp16b_40cls_demo.py)가 한상 사진에서 0~1박스였던 한계를
디텍터 박스로 보완하는 구조 검증용.

디텍터 설정 기본값 = README_디텍터_최종.md §2 확정값 (conf 0.30 · NMS IoU 0.15 ·
agnostic · max_det 50 · imgsz 512 · CLIP 0.25 · padding 1.0).

Run:
    streamlit run backend/food_image_analysis/detector/pipeline_demo.py --server.port 8505

Reference:
    디텍터: detector_best.pt (이 폴더, v3)  /  분류기: runs/food_yolo/exp16b_*/weights/best.pt
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # food_filter import용
ROOT = HERE.parents[2]  # 저장소 루트

DET_PT = HERE / "detector_best.pt"
CLS_PT = Path(
    os.environ.get(
        "EXP16B_WEIGHTS",
        str(
            ROOT / "runs" / "food_yolo"
            / "exp16b_taxo50_aihubreal_pc1_s42_b16_w8_cache_disk_det_true" / "weights" / "best.pt"
        ),
    )
)
TEST_DIR = ROOT / "data" / "food_images" / "raw" / "test_data"
FONT_PATH = r"C:\Windows\Fonts\malgun.ttf"

# 분류기 서비스 미지원 10클래스 (exp16b 인수인계 키트와 동일 기준)
EXCLUDED = {"seafood-jjim", "seafood-spicy-tang", "seafood-clear-tang", "squid-dish",
            "shrimp-dish", "grilled-beef", "jjamppong", "fried-rice", "dumplings", "rice-bowl"}

KR_NAME: dict[str, str] = {
    "barbecue-ribs": "갈비", "black-bean-noodles": "짜장면", "braised-chicken": "찜닭",
    "braised-pork-hock": "족발", "bread": "빵", "bulgogi": "불고기", "cake": "케이크",
    "cold-noodles": "냉면", "curry": "카레", "dim-sum": "딤섬", "fish-cake": "어묵",
    "fried-chicken": "후라이드치킨", "fried-food-platter": "튀김(모둠)", "grilled-fish": "생선구이",
    "grilled-pork-belly": "삼겹살", "hamburger": "햄버거", "korean-blood-sausage": "순대",
    "mixed-rice-bowl": "비빔밥", "pasta": "파스타", "pizza": "피자", "raw-fish": "회",
    "rice-porridge": "죽", "rice-soup": "국밥", "salad": "샐러드", "sandwich": "샌드위치",
    "savory-pancake": "전/부침개", "seaweed-rice-roll": "김밥", "spicy-mixed-noodles": "비빔국수",
    "sushi": "초밥", "takoyaki": "타코야키", "udon": "우동", "western-cream-soup": "양식수프",
    "japanese-ramen": "일본라멘", "korean-ramyeon-red": "라면", "tteokbokki-red": "떡볶이",
    "pork-cutlet-dry": "돈가스", "kalguksu": "칼국수", "rice-noodle-soup": "쌀국수",
    "jjigae-red": "빨간찌개", "doenjang-jjigae": "된장찌개",
}


def kr(name: str) -> str:
    """영문 클래스명 → 한글 표시명 (없으면 원문)."""
    return KR_NAME.get(name, name)


@st.cache_resource
def load_detector() -> YOLO:
    """v3 디텍터 로드 (1-class food)."""
    return YOLO(str(DET_PT))


@st.cache_resource
def load_classifier() -> tuple[YOLO, list[int]]:
    """exp16b 분류기 로드 + 지원 40클래스 인덱스 산출."""
    m = YOLO(str(CLS_PT))
    sup = sorted(i for i, n in m.names.items() if n not in EXCLUDED)
    return m, sup


@st.cache_resource
def load_clip():
    """CLIP 음식/비음식 필터 (첫 호출 시 가중치 ~600MB 자동 다운로드)."""
    from food_filter import CLIPFoodFilter

    return CLIPFoodFilter()


def classify_crop(cls_model: YOLO, sup_idx: list[int], crop: Image.Image,
                  conf_min: float) -> tuple[str | None, float]:
    """박스 crop을 exp16b로 분류 — 최고 신뢰도 지원클래스 1개 반환 (미달 시 None)."""
    r = cls_model.predict(crop, conf=0.01, classes=sup_idx, verbose=False)[0]
    if not len(r.boxes):
        return None, 0.0
    bi = int(np.argmax(r.boxes.conf.tolist()))
    name = cls_model.names[int(r.boxes.cls[bi])]
    cf = float(r.boxes.conf[bi])
    return (name, cf) if cf >= conf_min else (None, cf)


def draw_results(img: Image.Image, rows: list[dict]) -> Image.Image:
    """박스 + 한글 라벨 오버레이 (PIL — 한글 폰트)."""
    out = img.copy()
    d = ImageDraw.Draw(out)
    fs = max(16, out.width // 45)
    try:
        font = ImageFont.truetype(FONT_PATH, fs)
    except OSError:
        font = ImageFont.load_default()
    for row in rows:
        x1, y1, x2, y2 = row["box"]
        color = (34, 197, 94) if row["food"] else (148, 163, 184)
        d.rectangle([x1, y1, x2, y2], outline=color, width=max(3, out.width // 300))
        label = f"{kr(row['food'])} {row['cls_conf']:.2f}" if row["food"] else "미인식"
        tb = d.textbbox((x1, y1), label, font=font)
        ty = max(0, y1 - (tb[3] - tb[1]) - 8)
        d.rectangle([x1, ty, x1 + (tb[2] - tb[0]) + 10, ty + (tb[3] - tb[1]) + 8], fill=color)
        d.text((x1 + 5, ty + 2), label, fill="white", font=font)
    return out


# ============================ UI ============================
st.set_page_config(page_title="디텍터+분류기 통합 데모", page_icon="🍱", layout="wide")
st.title("🍱 통합 파이프라인 — 음식 영역 검출 → 종류 분류")
st.caption(
    "①v3 디텍터(1-class)가 음식 위치를 찾고 → ②CLIP이 비음식을 거르고 → "
    "③exp16b(지원 40클래스)가 각 박스의 음식 종류를 판별  |  한상(다중 음식) 사진 대응 검증용"
)

if not DET_PT.exists():
    st.error(f"디텍터 모델 없음: `{DET_PT}` — 파일공유로 detector_best.pt를 이 폴더에 복사하세요.")
    st.stop()
if not CLS_PT.exists():
    st.error(f"분류기 모델 없음: `{CLS_PT}` — EXP16B_WEIGHTS 환경변수로 경로 지정 가능.")
    st.stop()

det = load_detector()
cls_model, SUP_IDX = load_classifier()

with st.sidebar:
    st.header("⚙️ 디텍터 (최종 설정 기본값)")
    det_conf = st.slider("detector conf", 0.05, 0.9, 0.30, 0.05)
    det_iou = st.slider("NMS IoU (낮을수록 겹침 병합)", 0.05, 0.95, 0.15, 0.05)
    imgsz = st.select_slider("imgsz", options=[512, 640, 768], value=512)
    st.header("🔍 CLIP 필터")
    use_clip = st.checkbox("CLIP 비음식 거르기", value=True, key="use_clip")
    clip_th = st.slider("CLIP food 임계값", 0.05, 0.95, 0.25, 0.05)
    st.caption("첫 사용 시 가중치 ~600MB 다운로드(1회)")
    st.header("🍽️ 분류기 (exp16b)")
    cls_conf = st.slider("분류 최소 conf (미만 = 미인식)", 0.02, 0.9, 0.10, 0.01)
    st.caption(f"지원 {len(SUP_IDX)}클래스 — 미지원 10종은 출력 안 됨")
    st.divider()
    test_imgs = sorted(p.name for p in TEST_DIR.glob("*.jpg")) if TEST_DIR.exists() else []
    picked = st.selectbox("📂 test_data 샘플", ["(업로드 사용)"] + test_imgs)

uploaded = st.file_uploader("이미지 업로드 — 한상(다중 음식) 사진 환영", type=["jpg", "jpeg", "png", "webp"])

img: Image.Image | None = None
src = None
if uploaded is not None:
    img = Image.open(uploaded).convert("RGB")
    src = uploaded.name
elif picked and picked != "(업로드 사용)":
    img = Image.open(TEST_DIR / picked).convert("RGB")
    src = picked

if img is None:
    st.info("👆 이미지를 업로드하거나 test_data 샘플을 선택하세요.")
    st.stop()

# ① 디텍터 — 음식 영역
r = det.predict(img, conf=det_conf, iou=det_iou, agnostic_nms=True, max_det=50,
                imgsz=imgsz, verbose=False)[0]
boxes = [tuple(map(float, b)) for b in r.boxes.xyxy.tolist()]
det_confs = [float(c) for c in r.boxes.conf.tolist()]

if not boxes:
    st.image(img, caption=src, width="stretch")
    st.error("## 🚫 음식 영역을 찾지 못했어요. 다시 찍어주세요.")
    st.stop()

# ② CLIP — 비음식 박스 제거 (padding 1.0 = 박스 그대로)
crops = [img.crop((x1, y1, x2, y2)) for x1, y1, x2, y2 in boxes]
clip_scores: list[float | None] = [None] * len(boxes)
keep = [True] * len(boxes)
if use_clip:
    flt = load_clip()
    keep, scores = flt.filter(crops, threshold=clip_th)
    clip_scores = list(scores)

# ③ 분류기 — 박스별 음식 종류
rows = []
for i, ((x1, y1, x2, y2), dcf, kp) in enumerate(zip(boxes, det_confs, keep)):
    if not kp:
        continue
    food, ccf = classify_crop(cls_model, SUP_IDX, crops[i], cls_conf)
    rows.append({"box": (x1, y1, x2, y2), "det_conf": dcf,
                 "clip": clip_scores[i], "food": food, "cls_conf": ccf})

col_img, col_info = st.columns([3, 2])
with col_img:
    st.image(draw_results(img, rows), caption=f"{src} — 음식영역 {len(boxes)}개 → CLIP 통과 {len(rows)}개",
             width="stretch")

with col_info:
    n_named = sum(1 for x in rows if x["food"])
    st.subheader(f"결과: 음식 {n_named}개 판별 / 영역 {len(rows)}개")
    dropped = len(boxes) - len(rows)
    if dropped:
        st.caption(f"CLIP이 비음식 박스 {dropped}개 제거")
    for i, row in enumerate(sorted(rows, key=lambda x: -x["cls_conf"]), 1):
        nm = kr(row["food"]) if row["food"] else "미인식(지원 40종 밖이거나 불확실)"
        clip_s = f" · CLIP {row['clip']:.2f}" if row["clip"] is not None else ""
        st.write(f"**{i}. {nm}** — 분류 {row['cls_conf']*100:.0f}% · 영역 {row['det_conf']*100:.0f}%{clip_s}")
    st.caption(
        "※ 미인식 = 분류기 지원 40종 밖(반찬·미지원 음식)이거나 신뢰도 미달. "
        "AI 결과는 참고용이며 사용자가 확인·수정합니다 (진단·처방 아님)."
    )
