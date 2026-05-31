"""
음식 게이트 테스트 앱 (Streamlit)
=================================
모델(predict.py)을 불러와, 임계값을 조절하며 "음식 여부"를 확인한다.
- 사진 업로드 → 음식일 확률 표시
- 임계값 슬라이더로 통과/재촬영 기준을 실시간 조절
- 확률이 임계값 미만이면 "다시 촬영" 안내 (앱의 1단계 게이트 동작 시뮬레이션)

실행:
    conda activate dl_env
    streamlit run classifier/app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from PIL import Image

st.set_page_config(page_title="음식 게이트 테스트", page_icon="🍋", layout="wide")

MODEL_FILE = Path(__file__).resolve().parent / "models" / "is_food_head.joblib"


# ── 모델 로딩 (앱 시작 시 1회, 캐시) ──────────────────────────────────────────
@st.cache_resource(show_spinner="CLIP 백본 + 분류기 로딩 중... (최초 1회, 수십 초)")
def load_classifier():
    from predict import FoodClassifier
    return FoodClassifier()


# ── 한 장 판정 + 결과 카드 출력 ──────────────────────────────────────────────
def show_result(img: Image.Image, prob: float, threshold: float, caption: str = ""):
    is_food = prob >= threshold
    col_img, col_res = st.columns([1, 1])
    with col_img:
        st.image(img, caption=caption or None, use_container_width=True)
    with col_res:
        st.metric("음식일 확률", f"{prob*100:.1f}%")
        st.progress(min(max(prob, 0.0), 1.0))
        if is_food:
            st.success(f"✅ 통과 — 음식으로 인식 (기준 {threshold*100:.0f}% 이상)")
            st.caption("→ 앱에서는 다음 단계(메뉴/칼로리 분류)로 넘어갑니다.")
        else:
            st.error(f"📷 다시 촬영 — 음식 인식 실패 (확률 {prob*100:.1f}% < 기준 {threshold*100:.0f}%)")
            st.caption("→ 앱에서는 사용자에게 '음식이 잘 보이게 다시 찍어주세요'를 띄웁니다.")
    st.divider()


def main():
    st.title("🍋 음식 게이트 테스트")
    st.caption("카스케이드 1단계: 사진이 음식인지 판별 → 아니면 재촬영 요청")

    # 모델 준비 확인
    if not MODEL_FILE.exists():
        st.warning(
            "아직 학습된 모델이 없습니다.\n\n"
            "1. 임베딩 추출이 끝나면\n"
            "2. `python classifier/02_train_is_food.py` 로 학습 후\n"
            "3. 이 앱을 새로고침 하세요."
        )
        st.stop()

    clf = load_classifier()
    meta = clf.meta

    # ── 사이드바: 성능 조절 ───────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ 성능 조절")
        default_thr = float(meta.get("recommended_gate_threshold", 0.6))
        threshold = st.slider(
            "통과 임계값 (음식일 확률이 이 값 이상이면 통과)",
            min_value=0.0, max_value=1.0, value=default_thr, step=0.01,
        )
        st.caption(
            "🔼 높이면: 비음식 오통과↓ 대신 재촬영 요청↑\n\n"
            "🔽 낮추면: 통과는 쉽지만 비음식이 새기 쉬움"
        )
        st.divider()
        st.header("📊 모델 정보")
        if meta:
            st.write(f"**백본**: {meta.get('backbone', '?')}")
            st.write(f"**학습일**: {meta.get('trained', '?')}")
            acc = meta.get("test_accuracy")
            auc = meta.get("test_roc_auc")
            if acc is not None:
                st.write(f"**테스트 정확도**: {acc*100:.2f}%")
            if auc is not None:
                st.write(f"**ROC-AUC**: {auc:.4f}")
            st.write(f"**학습 샘플**: {meta.get('n_train', '?')}장")
        else:
            st.caption("메타데이터 없음")

    # ── 입력 방식 선택 ────────────────────────────────────────────────────
    tab_upload, tab_path = st.tabs(["📤 사진 업로드", "📁 폴더 경로로 테스트"])

    with tab_upload:
        files = st.file_uploader(
            "음식/비음식 사진을 올려보세요 (여러 장 가능)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
        )
        if files:
            imgs = [Image.open(f) for f in files]
            with st.spinner(f"{len(imgs)}장 판정 중..."):
                probs = clf.predict_images(imgs)
            n_pass = sum(p >= threshold for p in probs)
            st.info(f"총 {len(imgs)}장 → 통과 {n_pass} / 재촬영 {len(imgs)-n_pass}")
            for img, prob, f in zip(imgs, probs, files):
                show_result(img, prob, threshold, caption=f.name)

    with tab_path:
        st.caption("output 폴더 등 로컬 경로의 사진들을 한 번에 테스트")
        folder = st.text_input(
            "폴더 경로",
            value=str(Path(__file__).resolve().parent.parent / "output" / "stage1" / "not_food"),
        )
        max_n = st.number_input("최대 장수", 1, 200, 12)
        if st.button("이 폴더 판정"):
            from clip_features import iter_image_paths
            paths = iter_image_paths(Path(folder))[: int(max_n)]
            if not paths:
                st.warning("이미지를 찾지 못했습니다.")
            else:
                imgs = [Image.open(p) for p in paths]
                with st.spinner(f"{len(imgs)}장 판정 중..."):
                    probs = clf.predict_images(imgs)
                n_pass = sum(p >= threshold for p in probs)
                st.info(f"총 {len(imgs)}장 → 통과 {n_pass} / 재촬영 {len(imgs)-n_pass}")
                for img, prob, p in zip(imgs, probs, paths):
                    show_result(img, prob, threshold, caption=p.name)


if __name__ == "__main__":
    main()
