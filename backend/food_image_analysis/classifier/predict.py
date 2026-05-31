"""
추론 모듈 (모델만 담당)
=======================
이미지 → "음식일 확률" 만 돌려준다.
임계값 판정 · 재촬영 요청 같은 '제어/UX'는 여기서 하지 않는다.
그건 Streamlit(app.py)이 슬라이더로 조절하며 담당한다.

사용:
    from predict import FoodClassifier
    clf = FoodClassifier()
    prob = clf.predict_image(pil_image)   # 0.0 ~ 1.0 (음식일 확률)
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from PIL import Image

from clip_features import CLIPEncoder

BASE = Path(__file__).resolve().parent
MODEL_FILE = BASE / "models" / "is_food_head.joblib"
META_FILE = BASE / "models" / "is_food_head.json"


class FoodClassifier:
    """공유 CLIP 백본 + is_food 헤드. 확률만 반환한다."""

    def __init__(self, encoder: CLIPEncoder | None = None):
        if not MODEL_FILE.exists():
            raise FileNotFoundError(
                f"학습된 모델이 없습니다: {MODEL_FILE}\n"
                "먼저 학습하세요: python classifier/02_train_is_food.py"
            )
        self.clf = joblib.load(MODEL_FILE)
        self.meta = (
            json.loads(META_FILE.read_text(encoding="utf-8"))
            if META_FILE.exists() else {}
        )
        # 백본은 여러 단계가 공유 — 외부에서 만든 인코더를 넘겨 재사용 가능
        self.encoder = encoder or CLIPEncoder()

    def predict_image(self, image: Image.Image) -> float:
        """PIL 이미지 → 음식일 확률(0~1)."""
        emb = self.encoder.embed_images([image.convert("RGB")])
        return float(self.clf.predict_proba(emb)[0, 1])

    def predict_path(self, path: str | Path) -> float | None:
        """파일 경로 → 음식일 확률. 열 수 없으면 None."""
        try:
            img = Image.open(path)
        except Exception:
            return None
        return self.predict_image(img)

    def predict_images(self, images: list[Image.Image]) -> list[float]:
        """여러 PIL 이미지 → 확률 리스트 (배치 처리로 빠름)."""
        if not images:
            return []
        embs = self.encoder.embed_images([im.convert("RGB") for im in images])
        return [float(p) for p in self.clf.predict_proba(embs)[:, 1]]
