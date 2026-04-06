#!/usr/bin/env python3
"""
Phase C-3: 검색 성능 평가

Ground Truth 142쿼리로 검색 성능을 측정하고 Before/After 비교 테이블을 출력한다.

실행:
  python scripts/evaluate_search.py                # 전체 평가
  python scripts/evaluate_search.py --save-report  # 결과 JSON 저장
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

GROUND_TRUTH = PROJECT_DIR / "data" / "ground_truth_misumi.json"
METADATA_DIR = PROJECT_DIR / "data" / "metadata"

# 베이스라인 성능 (E5 원본 임베딩, 2026-03-06 측정)
BASELINE = {
    "recall_at_1": 0.0761,
    "recall_at_3": 0.2223,
    "recall_at_5": 0.3685,
    "recall_at_10": 0.7394,
    "precision_at_5": 0.7296,
    "mrr": 0.7347,
    "avg_latency": 0.1009,
    "en_recall_at_5": 0.3427,
    "kr_recall_at_5": 0.3944,
    "en_mrr": 0.6808,
    "kr_mrr": 0.7887,
}

TARGETS = {
    "recall_at_5": 0.80,
    "recall_at_10": 0.90,
    "precision_at_5": 0.60,
    "mrr": 0.70,
}


def run_evaluation() -> dict:
    """142쿼리 텍스트 검색 평가 실행"""
    from core.pipeline import DrawingPipeline
    from core.evaluation import Evaluator

    print("=" * 65)
    print("  Ground Truth 검색 성능 평가")
    print("=" * 65)

    # 파이프라인 초기화
    print("\n  파이프라인 초기화 중...")
    pipeline = DrawingPipeline(
        upload_dir=str(PROJECT_DIR / "data" / "sample_drawings"),
        vector_store_dir=str(PROJECT_DIR / "data" / "vector_store"),
    )

    stats = pipeline._vector_store.get_stats()
    print(f"  이미지 컬렉션: {stats['image_collection_count']:,}건")
    print(f"  텍스트 컬렉션: {stats['text_collection_count']:,}건")
    print(f"  텍스트 모델: {pipeline._text_embedder.model_name}")

    # Ground Truth 로드
    evaluator = Evaluator(pipeline, ground_truth_path=GROUND_TRUTH)
    queries = evaluator.ground_truth.get("queries", [])
    text_queries = [q for q in queries if q.get("type", "text") == "text"]
    print(f"  쿼리: {len(text_queries)}건 (전체: {len(queries)})")

    # 평가 실행
    print(f"\n  텍스트 검색 평가 시작...")
    start = time.time()
    text_results = evaluator.evaluate_text_queries()
    eval_time = time.time() - start
    print(f"  평가 완료: {len(text_results)}건, {eval_time:.1f}초")

    if not text_results:
        print("  [ERROR] 평가 결과 없음")
        return {}

    n = len(text_results)

    # 전체 지표
    recall_1 = sum(r.recall_at.get(1, 0) for r in text_results) / n
    recall_3 = sum(r.recall_at.get(3, 0) for r in text_results) / n
    recall_5 = sum(r.recall_at.get(5, 0) for r in text_results) / n
    recall_10 = sum(r.recall_at.get(10, 0) for r in text_results) / n
    prec_5 = sum(r.precision_at.get(5, 0) for r in text_results) / n
    mrr = sum(r.reciprocal_rank for r in text_results) / n
    avg_lat = sum(r.latency for r in text_results) / n

    # EN/KR 분리
    en_results = [r for r in text_results if not any("\uac00" <= c <= "\ud7a3" for c in r.query)]
    kr_results = [r for r in text_results if any("\uac00" <= c <= "\ud7a3" for c in r.query)]

    en_r5 = sum(r.recall_at.get(5, 0) for r in en_results) / len(en_results) if en_results else 0
    kr_r5 = sum(r.recall_at.get(5, 0) for r in kr_results) / len(kr_results) if kr_results else 0
    en_mrr = sum(r.reciprocal_rank for r in en_results) / len(en_results) if en_results else 0
    kr_mrr = sum(r.reciprocal_rank for r in kr_results) / len(kr_results) if kr_results else 0

    metrics = {
        "recall_at_1": round(recall_1, 4),
        "recall_at_3": round(recall_3, 4),
        "recall_at_5": round(recall_5, 4),
        "recall_at_10": round(recall_10, 4),
        "precision_at_5": round(prec_5, 4),
        "mrr": round(mrr, 4),
        "avg_latency": round(avg_lat, 4),
        "en_recall_at_5": round(en_r5, 4),
        "kr_recall_at_5": round(kr_r5, 4),
        "en_mrr": round(en_mrr, 4),
        "kr_mrr": round(kr_mrr, 4),
    }

    # Before/After 비교 테이블
    print(f"\n  {'=' * 70}")
    print(f"  📊 Before/After 비교")
    print(f"  {'=' * 70}")
    print(f"  {'메트릭':<20} {'Before':>10} {'After':>10} {'Delta':>10} {'목표':>8} {'판정':>4}")
    print(f"  {'─' * 70}")

    metric_display = [
        ("Recall@1", "recall_at_1", None),
        ("Recall@3", "recall_at_3", None),
        ("Recall@5", "recall_at_5", 0.80),
        ("Recall@10", "recall_at_10", 0.90),
        ("Precision@5", "precision_at_5", 0.60),
        ("MRR", "mrr", 0.70),
        ("Avg Latency (s)", "avg_latency", None),
    ]

    for label, key, target in metric_display:
        before = BASELINE.get(key, 0)
        after = metrics[key]
        delta = after - before
        delta_str = f"{delta:+.4f}"
        target_str = f"{target:.2f}" if target else "   -"

        if target:
            status = "✅" if after >= target else "⚠️" if after >= target * 0.8 else "❌"
        else:
            status = "  "

        print(f"  {label:<20} {before:>10.4f} {after:>10.4f} {delta_str:>10} {target_str:>8} {status}")

    # 언어별
    print(f"\n  {'─' * 70}")
    print(f"  {'언어별':<20} {'Before':>10} {'After':>10} {'Delta':>10}")
    print(f"  {'─' * 70}")

    for label, key in [("EN Recall@5", "en_recall_at_5"), ("KR Recall@5", "kr_recall_at_5"),
                        ("EN MRR", "en_mrr"), ("KR MRR", "kr_mrr")]:
        before = BASELINE.get(key, 0)
        after = metrics[key]
        delta = after - before
        print(f"  {label:<20} {before:>10.4f} {after:>10.4f} {delta:>+10.4f}")

    print(f"  {'=' * 70}")

    # 실패 쿼리 분석
    failed = [r for r in text_results if r.recall_at.get(5, 0) == 0]
    print(f"\n  ❌ Recall@5=0 실패 쿼리: {len(failed)}/{n}건")
    if failed:
        for r in failed[:15]:
            lang = "KR" if any("\uac00" <= c <= "\ud7a3" for c in r.query) else "EN"
            top5 = r.retrieved_categories[:5]
            print(f"    [{lang}] \"{r.query}\" → {top5}")
        if len(failed) > 15:
            print(f"    ... 외 {len(failed) - 15}건")

    return {
        "timestamp": datetime.now().isoformat(),
        "total_queries": n,
        "en_queries": len(en_results),
        "kr_queries": len(kr_results),
        "metrics": metrics,
        "baseline": BASELINE,
        "failed_count": len(failed),
        "failed_queries": [
            {"query": r.query, "top5_cats": r.retrieved_categories[:5]}
            for r in failed
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Phase C-3: 검색 성능 평가")
    parser.add_argument("--save-report", action="store_true",
                        help="평가 결과를 JSON으로 저장")
    args = parser.parse_args()

    result = run_evaluation()

    if args.save_report and result:
        METADATA_DIR.mkdir(parents=True, exist_ok=True)
        path = METADATA_DIR / f"c3_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n  결과 저장: {path}")


if __name__ == "__main__":
    main()
