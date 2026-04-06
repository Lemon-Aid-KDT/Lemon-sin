#!/usr/bin/env python3
"""
Phase C-3: 텍스트 임베딩 강화

카테고리별 키워드를 텍스트 임베딩에 결합하여 검색 성능을 개선한다.

Before: "{ocr_text} {category}"  → OCR 텍스트가 치수 위주라 검색 매칭 저조
After:  "{short_keywords} {ocr_text} {category}"  → 핵심 키워드(3-5단어)로 의미적 매칭 개선

실행:
  python scripts/enhance_embeddings.py --step both       # 백업 + 강화
  python scripts/enhance_embeddings.py --step backup      # 백업만
  python scripts/enhance_embeddings.py --step enhance     # 강화만
  python scripts/enhance_embeddings.py --step restore     # 원본 복원
"""

import os
import sys
import json
import time
import shutil
import argparse
import unicodedata
from pathlib import Path
from datetime import datetime

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# 프로젝트 루트를 sys.path에 추가
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

VECTOR_STORE_DIR = PROJECT_DIR / "data" / "vector_store"
KEYWORDS_FILE = PROJECT_DIR / "data" / "category_keywords.json"
METADATA_DIR = PROJECT_DIR / "data" / "metadata"
BATCH_SIZE = 500


def backup_database():
    """ChromaDB 파일 백업"""
    print("=" * 60)
    print("  ChromaDB 백업")
    print("=" * 60)

    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    src = VECTOR_STORE_DIR / "chroma.sqlite3"
    if not src.exists():
        print(f"  [ERROR] {src} 파일이 없습니다.")
        return False

    dst = METADATA_DIR / f"chroma.sqlite3.backup_{timestamp}"
    size_mb = src.stat().st_size / (1024 * 1024)
    print(f"  원본: {src} ({size_mb:.1f}MB)")
    print(f"  백업: {dst}")

    shutil.copy2(src, dst)
    print(f"  백업 완료: {dst.name}")
    return True


def _shorten_keywords(full_keywords: str, max_terms: int = 5) -> str:
    """전체 키워드에서 핵심 term만 추출 (영문 + 한글 각각 max_terms개)"""
    import re
    tokens = full_keywords.split()
    en_terms = []
    kr_terms = []
    for t in tokens:
        if re.search(r'[\uac00-\ud7a3]', t):
            if len(kr_terms) < max_terms:
                kr_terms.append(t)
        else:
            if len(en_terms) < max_terms:
                en_terms.append(t)
    return " ".join(en_terms + kr_terms)


def load_keywords(keywords_file: Path = None, max_terms: int = 5) -> dict[str, str]:
    """카테고리 키워드 로드 (핵심 term만 추출)"""
    kw_path = keywords_file or KEYWORDS_FILE
    if not kw_path.exists():
        print(f"  [ERROR] {kw_path} 파일이 없습니다.")
        sys.exit(1)

    with open(kw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    keywords = data.get("keywords", {})
    # NFC 정규화 + 핵심 term만 추출
    normalized = {}
    for k, v in keywords.items():
        key = unicodedata.normalize("NFC", k)
        normalized[key] = _shorten_keywords(v, max_terms=max_terms)
    print(f"  카테고리 키워드: {len(normalized)}개 로드 (max {max_terms} terms/lang)")
    return normalized


def _get_embedder(model_type: str = "e5"):
    """임베딩 모델 반환"""
    if model_type == "minilm":
        from sentence_transformers import SentenceTransformer

        class MiniLMWrapper:
            def __init__(self):
                self.model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
                self.model_name = "paraphrase-multilingual-MiniLM-L12-v2"

            def embed_batch(self, texts, batch_size=64, prefix_type=None):
                return self.model.encode(texts, batch_size=batch_size, show_progress_bar=True)

        return MiniLMWrapper()
    else:
        from core.embeddings import TextEmbedder
        embedder = TextEmbedder()
        embedder._init_model()
        return embedder


def enhance_embeddings(keywords: dict[str, str], model_type: str = "e5"):
    """텍스트 임베딩을 키워드 결합으로 재생성"""
    print("=" * 60)
    print(f"  텍스트 임베딩 강화 (키워드 + OCR, model={model_type})")
    print("=" * 60)

    import chromadb

    # ChromaDB 연결
    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    img_coll = client.get_collection("drawings_image")
    text_coll = client.get_collection("drawings_text")

    print(f"  이미지 컬렉션: {img_coll.count():,}건")
    print(f"  텍스트 컬렉션: {text_coll.count():,}건")

    # 임베딩 모델 로드
    print(f"  임베딩 모델 로드 중 ({model_type})...", end="", flush=True)
    embedder = _get_embedder(model_type)
    print(f" OK (model={embedder.model_name})")

    # 이미지 컬렉션에서 전체 ID + 메타데이터 수집
    print(f"\n  전체 도면 메타데이터 수집 중...")
    total_count = img_coll.count()
    all_ids = []
    all_metas = []

    offset = 0
    while offset < total_count:
        chunk = img_coll.get(limit=BATCH_SIZE, offset=offset, include=["metadatas"])
        all_ids.extend(chunk["ids"])
        all_metas.extend(chunk["metadatas"])
        offset += len(chunk["ids"])
        if len(chunk["ids"]) == 0:
            break

    print(f"  수집 완료: {len(all_ids):,}건")

    # 배치 단위로 강화 + 재임베딩
    print(f"\n  키워드 강화 임베딩 시작...")
    start_time = time.time()
    processed = 0
    stats = {"with_keywords": 0, "fallback": 0}
    no_keyword_cats = set()

    for batch_start in range(0, len(all_ids), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(all_ids))
        batch_ids = all_ids[batch_start:batch_end]
        batch_metas = all_metas[batch_start:batch_end]

        texts = []
        valid_ids = []
        valid_metas = []

        for did, meta in zip(batch_ids, batch_metas):
            if meta is None:
                meta = {}

            cat = meta.get("category", "")
            cat_nfc = unicodedata.normalize("NFC", cat)
            ocr_text = meta.get("ocr_text", "")

            kw = keywords.get(cat_nfc, "")
            readable_cat = cat.replace("_", " ").replace("&", "and")
            if kw:
                text = f"{kw} {ocr_text} {readable_cat}".strip()
                stats["with_keywords"] += 1
            else:
                no_keyword_cats.add(cat)
                text = f"{readable_cat} {ocr_text}".strip()
                stats["fallback"] += 1

            if not text:
                text = cat or "unknown"

            texts.append(text)
            valid_ids.append(did)
            safe_meta = {k: v for k, v in meta.items() if v is not None} if meta else {}
            if not safe_meta:
                safe_meta = {"_placeholder": "true"}
            valid_metas.append(safe_meta)

        if not texts:
            continue

        # 임베딩 생성
        prefix = "passage" if model_type == "e5" else None
        embeddings = embedder.embed_batch(texts, batch_size=64, prefix_type=prefix)
        emb_list = [emb.tolist() for emb in embeddings]

        # ChromaDB upsert
        text_coll.upsert(
            ids=valid_ids,
            embeddings=emb_list,
            metadatas=valid_metas,
        )

        processed += len(valid_ids)
        elapsed = time.time() - start_time
        speed = processed / elapsed if elapsed > 0 else 0
        remaining = (len(all_ids) - processed) / speed if speed > 0 else 0
        print(f"\r  진행: {processed:,}/{len(all_ids):,} "
              f"({processed * 100 / len(all_ids):.1f}%) | "
              f"{speed:.0f}건/s | 남은: {remaining:.0f}s", end="", flush=True)

    elapsed = time.time() - start_time
    print(f"\n\n  완료: {processed:,}건, {elapsed:.0f}초 ({elapsed / 60:.1f}분)")
    print(f"  키워드 적용: {stats['with_keywords']:,}건")
    print(f"  폴백(카테고리명): {stats['fallback']:,}건")
    if no_keyword_cats:
        print(f"  키워드 미등록 카테고리: {sorted(no_keyword_cats)}")
    print(f"  텍스트 컬렉션 최종: {text_coll.count():,}건")

    # 결과 저장
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "action": "enhance_embeddings",
        "timestamp": datetime.now().isoformat(),
        "text_format": "{short_keywords} {ocr_text} {category}",
        "model": embedder.model_name,
        "e5_prefix": "passage",
        "total_processed": processed,
        "stats": stats,
        "elapsed_seconds": round(elapsed, 2),
        "no_keyword_categories": sorted(no_keyword_cats),
        "keywords_file": str(KEYWORDS_FILE),
    }
    result_path = METADATA_DIR / f"enhance_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  결과 저장: {result_path}")


def restore_original(model_type: str = "minilm"):
    """원본 텍스트 임베딩 복원: f"{ocr_text} {category}" 형식"""
    print("=" * 60)
    print(f"  원본 텍스트 임베딩 복원 (model={model_type})")
    print("=" * 60)

    import chromadb

    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    img_coll = client.get_collection("drawings_image")
    text_coll = client.get_collection("drawings_text")

    print(f"  이미지 컬렉션: {img_coll.count():,}건")

    embedder = _get_embedder(model_type)

    # 전체 ID + 메타데이터
    total_count = img_coll.count()
    all_ids = []
    all_metas = []
    offset = 0
    while offset < total_count:
        chunk = img_coll.get(limit=BATCH_SIZE, offset=offset, include=["metadatas"])
        all_ids.extend(chunk["ids"])
        all_metas.extend(chunk["metadatas"])
        offset += len(chunk["ids"])
        if len(chunk["ids"]) == 0:
            break

    print(f"  도면 수: {len(all_ids):,}건")
    print(f"\n  원본 포맷으로 재임베딩 시작...")
    start_time = time.time()
    processed = 0

    for batch_start in range(0, len(all_ids), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(all_ids))
        batch_ids = all_ids[batch_start:batch_end]
        batch_metas = all_metas[batch_start:batch_end]

        texts = []
        valid_ids = []
        valid_metas = []

        for did, meta in zip(batch_ids, batch_metas):
            if meta is None:
                meta = {}
            cat = meta.get("category", "")
            ocr_text = meta.get("ocr_text", "")
            text = f"{ocr_text} {cat}".strip() or "unknown"

            texts.append(text)
            valid_ids.append(did)
            safe_meta = {k: v for k, v in meta.items() if v is not None} if meta else {}
            if not safe_meta:
                safe_meta = {"_placeholder": "true"}
            valid_metas.append(safe_meta)

        if not texts:
            continue

        prefix = "passage" if model_type == "e5" else None
        embeddings = embedder.embed_batch(texts, batch_size=64, prefix_type=prefix)
        emb_list = [emb.tolist() for emb in embeddings]

        text_coll.upsert(ids=valid_ids, embeddings=emb_list, metadatas=valid_metas)

        processed += len(valid_ids)
        elapsed = time.time() - start_time
        speed = processed / elapsed if elapsed > 0 else 0
        remaining = (len(all_ids) - processed) / speed if speed > 0 else 0
        print(f"\r  진행: {processed:,}/{len(all_ids):,} "
              f"({processed * 100 / len(all_ids):.1f}%) | "
              f"{speed:.0f}건/s | 남은: {remaining:.0f}s", end="", flush=True)

    elapsed = time.time() - start_time
    print(f"\n\n  복원 완료: {processed:,}건, {elapsed:.0f}초 ({elapsed / 60:.1f}분)")

    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    result_path = METADATA_DIR / f"restore_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump({
            "action": "restore_original",
            "timestamp": datetime.now().isoformat(),
            "text_format": "{ocr_text} {category}",
            "model": embedder.model_name,
            "total_processed": processed,
            "elapsed_seconds": round(elapsed, 2),
        }, f, ensure_ascii=False, indent=2)
    print(f"  결과 저장: {result_path}")


def main():
    parser = argparse.ArgumentParser(description="Phase C-3: 텍스트 임베딩 강화")
    parser.add_argument("--step", required=True,
                        choices=["backup", "enhance", "both", "restore"],
                        help="실행 단계: backup / enhance / both / restore")
    parser.add_argument("--keywords-file", type=str, default=str(KEYWORDS_FILE),
                        help="카테고리 키워드 JSON 파일 경로")
    parser.add_argument("--max-terms", type=int, default=5,
                        help="카테고리당 최대 키워드 수 (영/한 각각, 기본 5)")
    parser.add_argument("--model", type=str, default="minilm",
                        choices=["e5", "minilm"],
                        help="임베딩 모델 (기본 minilm)")
    args = parser.parse_args()

    keywords_file = Path(args.keywords_file)

    if args.step in ("backup", "both"):
        if not backup_database():
            sys.exit(1)

    if args.step in ("enhance", "both"):
        kw = load_keywords(keywords_file, max_terms=args.max_terms)
        enhance_embeddings(kw, model_type=args.model)

    if args.step == "restore":
        restore_original(model_type=args.model)


if __name__ == "__main__":
    main()
