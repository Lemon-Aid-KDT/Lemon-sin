# -*- coding: utf-8 -*-
# 디텍터 3종 + CLIP on/off 비교 데모 (팀원 인계용)
# 실행: python -m streamlit run compare_demo.py --server.port 8504
import streamlit as st
from ultralytics import YOLO
from PIL import Image, ImageDraw
import numpy as np

st.set_page_config(page_title="LEMON-AID Detector 비교", layout="wide")
st.title("🍋 디텍터 비교 — v3 / fast v5(mos0.5) / fast v5(mos1.0) + CLIP")

import os
HERE = os.path.dirname(os.path.abspath(__file__))   # 이 스크립트가 있는 폴더 기준 (상대경로)
MODELS = {
    "v3 (옛날, 150ep)":        os.path.join(HERE, "detector_best.pt"),
    "fast v5 mos0.5 (30ep)":   os.path.join(HERE, "fastv5_mos05.pt"),
    "fast v5 mos1.0 (30ep)":   os.path.join(HERE, "fastv5_mos10.pt"),
}

with st.sidebar:
    st.markdown("### 설정")
    picks = st.multiselect("비교할 모델", list(MODELS.keys()), default=list(MODELS.keys()))
    conf = st.slider("Detector conf", 0.05, 0.95, 0.30, 0.05)
    iou = st.slider("NMS IoU (낮을수록 겹친박스 합침)", 0.10, 0.95, 0.45, 0.05,
                    help="다중박스 줄이려면 0.4~0.5로 낮춰라")
    agnostic = st.checkbox("agnostic NMS (1-class 권장)", value=True,
                           help="클래스 무시하고 겹치면 합침 — 다중박스 억제")
    max_det = st.slider("max_det (이미지당 최대 박스)", 10, 100, 50, 5)
    imgsz = st.select_slider("imgsz", options=[512, 640], value=512)
    use_clip = st.checkbox("CLIP 필터 적용", value=False)
    clip_thr = st.slider("CLIP food 임계값", 0.1, 0.9, 0.5, 0.05, disabled=not use_clip)
    pad = st.slider("CLIP crop padding", 1.0, 1.5, 1.2, 0.1, disabled=not use_clip)

@st.cache_resource(show_spinner=False)
def load_det(p): return YOLO(p)

@st.cache_resource(show_spinner="CLIP 로드 중...")
def load_clip():
    from food_filter import CLIPFoodFilter
    return CLIPFoodFilter()

def draw(img, boxes, color, confs=None):
    im = img.copy(); d = ImageDraw.Draw(im); W = im.size[0]
    w = max(3, W // 220)
    for i, (x1, y1, x2, y2) in enumerate(boxes):
        d.rectangle([x1, y1, x2, y2], outline=color, width=w)
        if confs is not None:
            d.text((x1 + 3, y1 + 3), f"{confs[i]:.2f}", fill=color)
    return im

clip = load_clip() if use_clip else None
files = st.file_uploader("음식 사진 업로드 (여러 장)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if files:
    for f in files:
        img = Image.open(f).convert("RGB"); W, H = img.size
        st.markdown(f"#### {f.name}")
        cols = st.columns(len(picks))
        for col, name in zip(cols, picks):
            det = load_det(MODELS[name])
            res = det.predict(np.array(img), conf=conf, iou=iou, agnostic_nms=agnostic,
                              max_det=max_det, imgsz=imgsz, verbose=False)[0]
            xyxy = [tuple(map(float, b)) for b in res.boxes.xyxy.tolist()]
            cfs = [float(c) for c in res.boxes.conf]
            removed = 0
            if use_clip and xyxy:
                crops = []
                for (x1, y1, x2, y2) in xyxy:
                    cw, ch = (x2-x1)*pad, (y2-y1)*pad; cx, cy = (x1+x2)/2, (y1+y2)/2
                    crops.append(img.crop((max(0,cx-cw/2), max(0,cy-ch/2), min(W,cx+cw/2), min(H,cy+ch/2))))
                mask, _ = clip.filter(crops, threshold=clip_thr)
                keep = [i for i, m in enumerate(mask) if m]
                removed = len(xyxy) - len(keep)
                xyxy = [xyxy[i] for i in keep]; cfs = [cfs[i] for i in keep]
            with col:
                st.image(draw(img, xyxy, (0, 150, 0) if use_clip else (0, 0, 255), cfs),
                         use_container_width=True)
                cap = f"**{name}** — {len(xyxy)}개"
                if use_clip: cap += f" (CLIP이 {removed}개 삭제)"
                st.caption(cap)
        st.divider()
else:
    st.info("👆 사진 올리면 선택한 모델들을 나란히 비교. CLIP 켜면 거른 결과로 보여줌.\n\n"
            "테스트 추천: ① 한상차림 ② 빈컵/음료 ③ 초밥 ④ 어두운 사진")
