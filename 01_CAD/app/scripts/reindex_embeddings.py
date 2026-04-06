#!/usr/bin/env python3
"""
기존 도면의 텍스트 임베딩을 카테고리 키워드로 보강하여 재인덱싱

Phase 2 검색 파이프라인 강화의 핵심:
  - 기존 `f"{ocr_text} {category}"` → `f"{ocr_text} {category} {category_keywords}"` 보강
  - ChromaDB text collection에 upsert (이미지 임베딩은 변경 없음)

사용법:
  python scripts/reindex_embeddings.py
  python scripts/reindex_embeddings.py --data ./data/vector_store --keywords ./data/category_keywords.json
  python scripts/reindex_embeddings.py --dry-run  # 실제 upsert 없이 검증만

산출물:
  - ChromaDB text collection 업데이트 (기존 drawing_id 유지, 임베딩만 교체)
  - 재인덱싱 통계 출력
"""

import argparse
import json
import sys
import time
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


def build_rich_text(
    ocr_text: str, category: str, category_keywords: dict[str, str]
) -> str:
    """임베딩용 보강 텍스트 생성 (pipeline._build_rich_text와 동일 로직)"""
    parts: list[str] = []
    if ocr_text:
        parts.append(ocr_text[:500])
    if category:
        parts.append(category.replace("_", " "))
    kw = category_keywords.get(category, "")
    if kw:
        parts.append(kw)
    return " ".join(parts).strip()


def main():
    parser = argparse.ArgumentParser(
        description="기존 도면 텍스트 임베딩 재인덱싱 (카테고리 키워드 보강)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data", type=str, default="./data/vector_store",
        help="벡터 스토어 디렉토리 (records.json 위치, 기본: ./data/vector_store)",
    )
    parser.add_argument(
        "--keywords", type=str, default="./data/category_keywords.json",
        help="카테고리 키워드 JSON 경로 (기본: ./data/category_keywords.json)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=64,
        help="임베딩 배치 크기 (기본: 64)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="실제 upsert 없이 검증만 실행",
    )
    args = parser.parse_args()

    print("=" * 65)
    print("  텍스트 임베딩 재인덱싱 (카테고리 키워드 보강)")
    print("=" * 65)

    # 1. records.json 로드
    records_path = Path(args.data) / "records.json"
    if not records_path.exists():
        print(f"  [ERROR] records.json 없음: {records_path}")
        sys.exit(1)

    with open(records_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    print(f"\n  레코드 수: {len(records):,}건")

    # 2. 카테고리 키워드 로드
    kw_path = Path(args.keywords)
    category_keywords: dict[str, str] = {}
    if kw_path.exists():
        with open(kw_path, "r", encoding="utf-8") as f:
            kw_data = json.load(f)
        category_keywords = kw_data.get("keywords", {})
        print(f"  카테고리 키워드: {len(category_keywords)}개 카테고리")
    else:
        print(f"  [WARNING] 키워드 파일 없음: {kw_path}")
        print(f"  → 카테고리명만으로 보강합니다.")

    # 3. 보강 대상 분석
    enrichable = 0
    no_category = 0
    for rid, rdata in records.items():
        cat = rdata.get("category", "")
        if cat and cat in category_keywords:
            enrichable += 1
        elif not cat:
            no_category += 1

    print(f"\n  키워드 보강 가능: {enrichable:,}건")
    print(f"  카테고리 미지정: {no_category:,}건")
    print(f"  기타 (키워드 없음): {len(records) - enrichable - no_category:,}건")

    if args.dry_run:
        print(f"\n  [DRY-RUN] 실제 upsert 없이 종료합니다.")

        # 보강 텍스트 샘플 출력
        print(f"\n  보강 텍스트 샘플 (처음 3건):")
        for i, (rid, rdata) in enumerate(records.items()):
            if i >= 3:
                break
            ocr = rdata.get("ocr_text", "")
            cat = rdata.get("category", "")
            old_text = f"{ocr} {cat}".strip()
            new_text = build_rich_text(ocr, cat, category_keywords)
            print(f"\n  [{rid}] {rdata.get('file_name', 'unknown')}")
            print(f"    기존: {old_text[:100]}...")
            print(f"    보강: {new_text[:100]}...")
        return

    # 4. 임베딩 모델 + 벡터 스토어 초기화
    from core.embeddings import TextEmbedder
    from core.vector_store import VectorStore

    print(f"\n  텍스트 임베딩 모델 로딩...")
    text_embedder = TextEmbedder()

    print(f"  벡터 스토어 연결: {args.data}")
    vector_store = VectorStore(persist_dir=args.data)
    vs_stats = vector_store.get_stats()
    print(f"  기존 텍스트 컬렉션: {vs_stats['text_collection_count']:,}건")

    # 5. 배치 재인덱싱
    print(f"\n  재인덱싱 시작 (batch_size={args.batch_size})...")
    start_time = time.time()

    # 보강 텍스트 생성
    drawing_ids = list(records.keys())
    rich_texts = []
    metadatas = []
    for rid in drawing_ids:
        rdata = records[rid]
        ocr = rdata.get("ocr_text", "")
        cat = rdata.get("category", "")
        rich_text = build_rich_text(ocr, cat, category_keywords)
        rich_texts.append(rich_text)

        # 메타데이터 (기존과 동일 구조 유지)
        meta = {
            "file_path": rdata.get("file_path", ""),
            "file_name": rdata.get("file_name", ""),
            "category": cat,
            "ocr_text": ocr[:500],
            "part_numbers": str(rdata.get("part_numbers", [])),
        }
        metadatas.append(meta)

    # 배치 임베딩 생성
    print(f"  임베딩 생성 중 ({len(rich_texts):,}건)...")
    embeddings = text_embedder.embed_batch(
        rich_texts, batch_size=args.batch_size, prefix_type="passage"
    )

    # ChromaDB upsert
    print(f"  ChromaDB upsert 중...")
    success_count = 0
    error_count = 0
    for i in range(0, len(drawing_ids), args.batch_size):
        batch_ids = drawing_ids[i:i + args.batch_size]
        batch_embs = embeddings[i:i + args.batch_size]
        batch_metas = metadatas[i:i + args.batch_size]

        for did, emb, meta in zip(batch_ids, batch_embs, batch_metas):
            try:
                vector_store.add_drawing(
                    drawing_id=did,
                    text_embedding=emb,
                    metadata=meta,
                )
                success_count += 1
            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    print(f"    [ERROR] {did}: {e}")

        done = min(i + args.batch_size, len(drawing_ids))
        elapsed = time.time() - start_time
        rate = done / elapsed if elapsed > 0 else 0
        print(f"    진행: {done:,}/{len(drawing_ids):,} ({rate:.0f}건/초)")

    elapsed = time.time() - start_time

    # 6. 결과 출력
    print(f"\n{'=' * 65}")
    print(f"  ✅ 재인덱싱 완료")
    print(f"{'=' * 65}")
    print(f"  성공: {success_count:,}건")
    print(f"  실패: {error_count:,}건")
    print(f"  소요: {elapsed:.1f}초 ({success_count / elapsed:.0f}건/초)")

    vs_stats_after = vector_store.get_stats()
    print(f"  텍스트 컬렉션: {vs_stats_after['text_collection_count']:,}건")

    print(f"\n  다음 단계:")
    print(f"    streamlit run app/streamlit_app.py  # 검색 테스트")


if __name__ == "__main__":
    main()
