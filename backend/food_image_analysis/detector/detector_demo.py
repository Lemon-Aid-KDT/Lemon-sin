# -*- coding: utf-8 -*-
# 디텍터 단독 데모 — 사진 업로드 → 음식 박스 시각화
# 실행: python -m streamlit run detector_demo.py --server.port 8502
import streamlit as st
from ultralytics import YOLO
from PIL import Image
import numpy as np
import io

st.set_page_config(page_title="LEMON-AID Detector", layout="wide")
st.title("🍋 LEMON-AID 음식 디텍터 데모")

with st.sidebar:
    st.markdown("### 설정")
    model_path = st.text_input("Detector .pt", value=r"D:\runs\detect\fastv5_296\weights\best.pt")
    conf = st.slider("confidence", 0.05, 0.95, 0.30, 0.05)
    iou = st.slider("NMS IoU", 0.3, 0.95, 0.50, 0.05)
    imgsz = st.select_slider("imgsz", options=[512, 640, 768], value=512)
    st.caption("conf 낮추면 더 많이 잡음(recall↑), 높이면 헛박스↓(precision↑)")

@st.cache_resource(show_spinner="모델 로드 중...")
def load_model(p):
    return YOLO(p)

try:
    model = load_model(model_path)
    st.success(f"모델 로드됨: {model_path}")
except Exception as e:
    st.error(f"모델 로드 실패: {e}")
    st.stop()

files = st.file_uploader("음식 사진 업로드 (여러 장 가능)", type=["jpg", "jpeg", "png"],
                         accept_multiple_files=True)

if files:
    for f in files:
        img = Image.open(f).convert("RGB")
        res = model.predict(np.array(img), conf=conf, iou=iou, imgsz=imgsz, verbose=False)[0]
        plotted = res.plot()[:, :, ::-1]  # BGR->RGB
        n = len(res.boxes)
        confs = [round(float(c), 2) for c in res.boxes.conf]

        c1, c2 = st.columns([3, 1])
        with c1:
            st.image(plotted, caption=f"{f.name} — 검출 {n}개", use_container_width=True)
        with c2:
            st.metric("검출된 음식", f"{n} 개")
            if confs:
                st.write("conf:", confs)
                st.caption(f"평균 {sum(confs)/len(confs):.2f} / 최소 {min(confs):.2f}")
            else:
                st.info("검출 없음 (비음식 사진이면 정상)")
        st.divider()
else:
    st.info("👆 사진을 올리면 음식 영역 박스를 쳐줍니다. realapp_raw 폴더 사진들로 테스트해보세요.")
