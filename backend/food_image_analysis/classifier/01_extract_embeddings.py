"""
① 임베딩 추출 (느린 1회성 단계, 재시작 가능)
=============================================
output/stage1/{food,not_food} 의 이미지를 CLIP 임베딩으로 변환해
classifier/embeddings/is_food.npz 에 캐시한다.

- CPU에서 가장 오래 걸리는 단계지만 '딱 한 번'만 하면 된다.
- 중간에 끊겨도 이어서 실행하면 남은 것만 처리한다(재시작 가능).
- 학습용으로는 클래스별 상한(LIMIT_PER_CLASS)만 뽑아도 충분하다.

실행:
    conda activate dl_env
    python classifier/01_extract_embeddings.py
(오래 걸리면 백그라운드로 돌려도 됨. 진행분은 계속 저장됨.)
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np

from clip_features import CLIPEncoder, iter_image_paths

# ── 설정 ──────────────────────────────────────────────────────────────────────
BASE = Path(r"C:\Users\KDS22\Documents\GitHub\1_image\lemon-aid")
STAGE1 = BASE / "output" / "stage1"
CLASS_DIRS = {
    "food": STAGE1 / "food",
    "not_food": STAGE1 / "not_food",
}
# 환경변수 IS_FOOD_CACHE 로 캐시 경로 오버라이드 가능(스모크 테스트용)
CACHE_FILE = Path(os.environ.get(
    "IS_FOOD_CACHE",
    str(BASE / "classifier" / "embeddings" / "is_food.npz"),
))

# 클래스별 최대 추출 장수.
#   not_food 는 전체 ~11,047장 → 사실상 전부 사용
#   food 는 28,044장 중 11,000장 샘플링 → 균형 22,000장
# 전부 뽑고 싶으면 None 으로. 환경변수 IS_FOOD_LIMIT 로 오버라이드 가능.
LIMIT_PER_CLASS: int | None = int(os.environ.get("IS_FOOD_LIMIT", "11000"))
BATCH_SIZE = 16
CHECKPOINT_EVERY = 320  # 이미지 N장마다 캐시에 저장(재시작 안전장치)
RANDOM_SEED = 42
# ─────────────────────────────────────────────────────────────────────────────


def load_cache() -> dict[str, dict]:
    """{path_str: {"emb": np.ndarray, "label": str}} 형태로 기존 캐시 로드."""
    if not CACHE_FILE.exists():
        return {}
    data = np.load(CACHE_FILE, allow_pickle=True)
    paths = data["paths"]
    embs = data["embeddings"]
    labels = data["labels"]
    return {
        str(paths[i]): {"emb": embs[i], "label": str(labels[i])}
        for i in range(len(paths))
    }


def save_cache(cache: dict[str, dict]) -> None:
    paths = np.array(list(cache.keys()))
    embs = np.stack([cache[p]["emb"] for p in cache]).astype(np.float32)
    labels = np.array([cache[p]["label"] for p in cache])
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # np.savez_compressed 는 .npz 로 끝나지 않는 경로에 .npz 를 덧붙이므로
    # tmp 도 .npz 로 끝나게 만들어 경로 어긋남을 막는다.
    tmp = CACHE_FILE.parent / (CACHE_FILE.stem + ".tmp.npz")
    np.savez_compressed(tmp, paths=paths, embeddings=embs, labels=labels)
    tmp.replace(CACHE_FILE)


def collect_targets() -> list[tuple[Path, str]]:
    """추출 대상 (경로, 라벨) 목록. 클래스별 상한·셔플 적용."""
    rng = np.random.default_rng(RANDOM_SEED)
    targets: list[tuple[Path, str]] = []
    for label, d in CLASS_DIRS.items():
        if not d.exists():
            print(f"  ⚠ 폴더 없음: {d}")
            continue
        paths = iter_image_paths(d)
        rng.shuffle(paths)
        if LIMIT_PER_CLASS is not None:
            paths = paths[:LIMIT_PER_CLASS]
        targets.extend((p, label) for p in paths)
        print(f"  {label:<10}: {len(paths):,}장 대상")
    rng.shuffle(targets)  # 라벨이 섞이도록
    return targets


def main():
    print("=" * 60)
    print("① CLIP 임베딩 추출")
    print("=" * 60)

    print("\n대상 수집 중...")
    targets = collect_targets()
    print(f"  합계: {len(targets):,}장")

    cache = load_cache()
    print(f"\n기존 캐시: {len(cache):,}장")
    pending = [(p, lbl) for p, lbl in targets if str(p) not in cache]
    print(f"남은 작업: {len(pending):,}장\n")

    if not pending:
        print("✅ 추출할 것이 없습니다. (이미 완료)")
        _summary(cache)
        return

    print("CLIP 모델 로딩...")
    enc = CLIPEncoder()
    print(f"  device={enc.device}, model={enc.model_name}\n")

    t0 = time.time()
    processed = 0
    since_ckpt = 0

    try:
        for start in range(0, len(pending), BATCH_SIZE):
            batch = pending[start : start + BATCH_SIZE]
            batch_paths = [p for p, _ in batch]
            label_of = {str(p): lbl for p, lbl in batch}

            embs, ok_paths = enc.embed_paths(batch_paths, batch_size=BATCH_SIZE)
            for i, p in enumerate(ok_paths):
                cache[str(p)] = {"emb": embs[i], "label": label_of[str(p)]}
            processed += len(ok_paths)
            since_ckpt += len(ok_paths)

            if since_ckpt >= CHECKPOINT_EVERY:
                save_cache(cache)
                since_ckpt = 0

            elapsed = time.time() - t0
            speed = processed / elapsed if elapsed > 0 else 0
            remain = (len(pending) - processed) / speed if speed > 0 else 0
            eta = f"{remain/3600:.1f}h" if remain > 3600 else f"{remain/60:.0f}분"
            print(
                f"[{processed:>6}/{len(pending)}] "
                f"속도 {speed:.1f}장/s | 남은 {eta} | 캐시 {len(cache):,}",
                end="\r",
            )
    except KeyboardInterrupt:
        print("\n중단됨 — 진행분 저장 후 종료. 다시 실행하면 이어서 진행됩니다.")
    finally:
        save_cache(cache)
        print(f"\n\n저장 완료: {CACHE_FILE}")
        _summary(cache)


def _summary(cache: dict[str, dict]) -> None:
    from collections import Counter

    c = Counter(v["label"] for v in cache.values())
    print("\n=== 캐시 내 클래스 분포 ===")
    for label, n in c.most_common():
        print(f"  {label:<10}: {n:,}장")
    print("\n→ 다음: python classifier/02_train_is_food.py")


if __name__ == "__main__":
    main()
