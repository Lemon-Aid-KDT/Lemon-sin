"""
② is_food 게이트 학습 + 평가
=============================
classifier/embeddings/is_food.npz (CLIP 임베딩)을 읽어
food vs not_food 로지스틱 회귀 헤드를 학습한다.

- train/val/test 층화 분할
- 정확도 / precision·recall·F1 / 혼동행렬 / ROC-AUC 보고
- '다시 촬영' 게이트용 확률 임계값 추천
- 헤드(joblib) + 메타데이터(json) 저장

실행:
    python classifier/02_train_is_food.py
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
import joblib

BASE = Path(r"C:\Users\KDS22\Documents\GitHub\1_image\lemon-aid")
CACHE_FILE = Path(os.environ.get(
    "IS_FOOD_CACHE",
    str(BASE / "classifier" / "embeddings" / "is_food.npz"),
))
MODEL_DIR = BASE / "classifier" / "models"
MODEL_FILE = MODEL_DIR / "is_food_head.joblib"
META_FILE = MODEL_DIR / "is_food_head.json"

# food=양성(1). 게이트는 "음식일 확률"을 본다.
POSITIVE_LABEL = "food"
TEST_SIZE = 0.15
VAL_SIZE = 0.15
RANDOM_SEED = 42


def load_data():
    if not CACHE_FILE.exists():
        raise SystemExit(
            f"임베딩 캐시가 없습니다: {CACHE_FILE}\n"
            "먼저 실행: python classifier/01_extract_embeddings.py"
        )
    data = np.load(CACHE_FILE, allow_pickle=True)
    X = data["embeddings"].astype(np.float32)
    labels = data["labels"].astype(str)
    y = (labels == POSITIVE_LABEL).astype(int)  # food=1, not_food=0
    paths = data["paths"].astype(str)
    return X, y, paths


def main():
    print("=" * 60)
    print("② is_food 게이트 학습")
    print("=" * 60)

    X, y, paths = load_data()
    n_pos, n_neg = int(y.sum()), int((1 - y).sum())
    print(f"\n샘플: {len(y):,}장  (food={n_pos:,} / not_food={n_neg:,})")

    # train / temp 분할 → temp 를 val/test 로 다시 분할 (층화)
    X_tr, X_tmp, y_tr, y_tmp, p_tr, p_tmp = train_test_split(
        X, y, paths, test_size=TEST_SIZE + VAL_SIZE,
        stratify=y, random_state=RANDOM_SEED,
    )
    rel = TEST_SIZE / (TEST_SIZE + VAL_SIZE)
    X_val, X_te, y_val, y_te, p_val, p_te = train_test_split(
        X_tmp, y_tmp, p_tmp, test_size=rel, stratify=y_tmp, random_state=RANDOM_SEED,
    )
    print(f"분할: train={len(y_tr):,} / val={len(y_val):,} / test={len(y_te):,}")

    # 로지스틱 회귀 (클래스 불균형 보정) + 확률 보정
    print("\n학습 중...")
    base = LogisticRegression(
        C=1.0, max_iter=2000, class_weight="balanced", n_jobs=-1,
    )
    clf = CalibratedClassifierCV(base, method="sigmoid", cv=5)
    clf.fit(X_tr, y_tr)

    # ── 평가 ──────────────────────────────────────────────────────────────
    def report(name, Xs, ys, ps):
        prob = clf.predict_proba(Xs)[:, 1]
        pred = (prob >= 0.5).astype(int)
        acc = accuracy_score(ys, pred)
        auc = roc_auc_score(ys, prob)
        print(f"\n── {name} ── (n={len(ys)})")
        print(f"정확도: {acc*100:.2f}%   ROC-AUC: {auc:.4f}")
        print(classification_report(
            ys, pred, target_names=["not_food", "food"], digits=3,
        ))
        cm = confusion_matrix(ys, pred)
        print("혼동행렬 [행=실제, 열=예측]  (not_food, food)")
        print(f"  not_food: {cm[0]}")
        print(f"  food    : {cm[1]}")
        return prob, pred, acc, auc

    report("Validation", X_val, y_val, p_val)
    te_prob, te_pred, te_acc, te_auc = report("Test", X_te, y_te, p_te)

    # ── 게이트 임계값 추천 ─────────────────────────────────────────────────
    # "음식이라고 통과시키려면 prob >= threshold". 높일수록 not_food 오통과↓.
    print("\n=== '다시 촬영' 게이트 임계값별 동작 (test 기준) ===")
    print(" thr | food통과율 | not_food오통과 | 재촬영요청율")
    val_prob = clf.predict_proba(X_val)[:, 1]
    for thr in [0.5, 0.6, 0.7, 0.8, 0.9]:
        passed = te_prob >= thr
        food_pass = passed[y_te == 1].mean() if (y_te == 1).any() else 0
        nf_leak = passed[y_te == 0].mean() if (y_te == 0).any() else 0
        retake = (~passed).mean()
        print(f" {thr:.1f} |   {food_pass*100:5.1f}%  |     {nf_leak*100:5.1f}%     |   {retake*100:5.1f}%")

    # ── 라벨 노이즈 후보: 모델이 강하게 반대한 학습 예시 ──────────────────
    all_prob = clf.predict_proba(X)[:, 1]
    # food 라벨인데 음식 확률 매우 낮음 / not_food 인데 매우 높음
    food_suspect = [(p, pr) for p, yy, pr in zip(paths, y, all_prob) if yy == 1 and pr < 0.1]
    nf_suspect = [(p, pr) for p, yy, pr in zip(paths, y, all_prob) if yy == 0 and pr > 0.9]
    food_suspect.sort(key=lambda t: t[1])
    nf_suspect.sort(key=lambda t: -t[1])
    print(f"\n=== 라벨 오류 의심 (검수 추천) ===")
    print(f"  food 폴더인데 음식 아닐듯: {len(food_suspect)}장")
    for p, pr in food_suspect[:8]:
        print(f"    p={pr:.3f}  {p}")
    print(f"  not_food 폴더인데 음식일듯: {len(nf_suspect)}장")
    for p, pr in nf_suspect[:8]:
        print(f"    p={pr:.3f}  {p}")

    # ── 저장 ───────────────────────────────────────────────────────────────
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_FILE)
    meta = {
        "task": "is_food_gate",
        "trained": str(date.today()),
        "backbone": "openai/clip-vit-large-patch14",
        "embed_dim": int(X.shape[1]),
        "positive_label": POSITIVE_LABEL,
        "classes": {"0": "not_food", "1": "food"},
        "n_train": len(y_tr),
        "n_test": len(y_te),
        "test_accuracy": round(float(te_acc), 4),
        "test_roc_auc": round(float(te_auc), 4),
        "recommended_gate_threshold": 0.6,
        "note": "prob>=threshold 이면 food 통과, 미만이면 사용자에게 재촬영 요청",
    }
    META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {MODEL_FILE}")
    print(f"저장: {META_FILE}")
    print("\n→ 다음: streamlit run classifier/app.py")


if __name__ == "__main__":
    main()
