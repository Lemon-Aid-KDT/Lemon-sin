"""
DrawingLLM 검색 성능 평가 모듈

정보 검색(IR) 표준 메트릭으로 검색 품질을 정량 평가한다.

지표:
  - Recall@K:    상위 K건 중 관련 도면이 1건이라도 포함된 비율
  - Precision@K: 상위 K건 중 관련 도면의 비율
  - MRR:         첫 번째 관련 도면의 역순위 평균
  - mAP@K:       평균 정밀도의 평균 (순위 반영)
  - 응답 시간:    검색 latency

사용법:
  from core.evaluation import Evaluator

  evaluator = Evaluator(pipeline, ground_truth_path="data/ground_truth.json")
  report = evaluator.run_full_evaluation()
  evaluator.print_report(report)
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np
from loguru import logger


@dataclass
class QueryResult:
    """단일 쿼리 평가 결과"""
    query: str
    query_type: str  # "text" or "image"
    relevant_ids: list[str]       # ground truth 관련 도면 ID 또는 카테고리
    retrieved_ids: list[str]      # 검색 결과 도면 ID
    retrieved_categories: list[str]
    scores: list[float]           # 유사도 점수
    latency: float                # 초 단위
    recall_at: dict = field(default_factory=dict)     # {K: float}
    precision_at: dict = field(default_factory=dict)   # {K: float}
    reciprocal_rank: float = 0.0
    ap_at: dict = field(default_factory=dict)          # {K: float}


@dataclass
class EvaluationReport:
    """전체 평가 리포트"""
    num_queries: int = 0
    avg_recall: dict = field(default_factory=dict)      # {K: float}
    avg_precision: dict = field(default_factory=dict)    # {K: float}
    mrr: float = 0.0
    map_at: dict = field(default_factory=dict)           # {K: float}
    avg_latency: float = 0.0
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    query_results: list[QueryResult] = field(default_factory=list)
    by_category: dict = field(default_factory=dict)  # 카테고리별 지표


class Evaluator:
    """검색 성능 평가기"""

    def __init__(
        self,
        pipeline,
        ground_truth_path: str | Path | None = None,
        k_values: list[int] | None = None,
    ):
        """
        Args:
            pipeline: DrawingPipeline 인스턴스
            ground_truth_path: Ground Truth JSON 경로
            k_values: 평가할 K 값 리스트 (기본: [1, 3, 5, 10])
        """
        self.pipeline = pipeline
        self.k_values = k_values or [1, 3, 5, 10]
        self.ground_truth = {}

        if ground_truth_path:
            self._load_ground_truth(ground_truth_path)

    def _load_ground_truth(self, path: str | Path):
        """
        Ground Truth 로드

        형식:
        {
          "queries": [
            {
              "query": "flange drawing",
              "type": "text",
              "relevant_categories": ["flange", "synthetic"],
              "relevant_file_patterns": ["flange_*"]
            }
          ]
        }
        """
        path = Path(path)
        if not path.exists():
            logger.warning(f"Ground Truth 파일 없음: {path}")
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.ground_truth = data
        num = len(data.get("queries", []))
        logger.info(f"Ground Truth 로드: {num}건")

    # ─────────────────────────────────────────
    # 메트릭 계산
    # ─────────────────────────────────────────

    @staticmethod
    def recall_at_k(relevant: set, retrieved: list, k: int) -> float:
        """
        Recall@K: 상위 K건 내 관련 항목이 1개라도 있으면 1, 없으면 0
        (= Hit Rate @ K)

        여러 관련 항목이 있는 경우: 발견된 수 / 전체 관련 수
        """
        if not relevant:
            return 0.0
        top_k = set(retrieved[:k])
        found = len(relevant & top_k)
        return found / len(relevant)

    @staticmethod
    def precision_at_k(relevant: set, retrieved: list, k: int) -> float:
        """Precision@K: 상위 K건 중 관련 항목 비율"""
        if k == 0:
            return 0.0
        top_k = retrieved[:k]
        found = sum(1 for item in top_k if item in relevant)
        return found / k

    @staticmethod
    def reciprocal_rank(relevant: set, retrieved: list) -> float:
        """Reciprocal Rank: 첫 관련 항목의 역순위 (1/rank)"""
        for i, item in enumerate(retrieved):
            if item in relevant:
                return 1.0 / (i + 1)
        return 0.0

    @staticmethod
    def average_precision_at_k(relevant: set, retrieved: list, k: int) -> float:
        """Average Precision@K: 순위 가중 정밀도 평균"""
        if not relevant:
            return 0.0

        hits = 0
        sum_precision = 0.0

        for i, item in enumerate(retrieved[:k]):
            if item in relevant:
                hits += 1
                sum_precision += hits / (i + 1)

        return sum_precision / min(len(relevant), k)

    # ─────────────────────────────────────────
    # 관련성 판단
    # ─────────────────────────────────────────

    def _is_relevant(self, result_category: str, result_filename: str,
                     gt_entry: dict) -> bool:
        """
        검색 결과가 Ground Truth 기준으로 관련 있는지 판단한다.

        판단 기준 (OR):
          1. 결과 카테고리가 relevant_categories에 포함
          2. 파일명이 relevant_file_patterns에 매칭
        """
        # 카테고리 매칭
        rel_cats = gt_entry.get("relevant_categories", [])
        if result_category in rel_cats:
            return True

        # 파일명 패턴 매칭 (prefix*)
        patterns = gt_entry.get("relevant_file_patterns", [])
        for pattern in patterns:
            if pattern.endswith("*"):
                if result_filename.lower().startswith(pattern[:-1].lower()):
                    return True
            elif result_filename.lower() == pattern.lower():
                return True

        return False

    # ─────────────────────────────────────────
    # 평가 실행
    # ─────────────────────────────────────────

    def evaluate_text_queries(self, queries: list[dict] | None = None,
                              top_k: int | None = None) -> list[QueryResult]:
        """
        텍스트 검색 쿼리 평가

        Args:
            queries: 쿼리 리스트 (None이면 ground_truth 사용)
            top_k: 검색 결과 수 (None이면 max(k_values))
        """
        if queries is None:
            queries = self.ground_truth.get("queries", [])
            queries = [q for q in queries if q.get("type", "text") == "text"]

        if not queries:
            logger.warning("평가할 텍스트 쿼리가 없습니다.")
            return []

        max_k = top_k or max(self.k_values)
        results = []

        for gt_entry in queries:
            query = gt_entry["query"]

            # 검색 실행
            start = time.time()
            search_results = self.pipeline.search_by_text(query, top_k=max_k)
            latency = time.time() - start

            # 결과에서 카테고리와 파일명 추출
            retrieved_ids = []
            retrieved_categories = []
            scores = []

            for r in search_results:
                retrieved_ids.append(r.drawing_id)
                retrieved_categories.append(r.metadata.get("category", ""))
                scores.append(r.score)

            # 관련성 판단: 각 결과가 관련 있는지
            relevant_set = set()
            for i, r in enumerate(search_results):
                cat = r.metadata.get("category", "")
                fname = r.metadata.get("file_name", "")
                if self._is_relevant(cat, fname, gt_entry):
                    relevant_set.add(r.drawing_id)

            # 메트릭 계산
            qr = QueryResult(
                query=query,
                query_type="text",
                relevant_ids=list(relevant_set),
                retrieved_ids=retrieved_ids,
                retrieved_categories=retrieved_categories,
                scores=scores,
                latency=latency,
            )

            for k in self.k_values:
                qr.recall_at[k] = self.recall_at_k(relevant_set, retrieved_ids, k)
                qr.precision_at[k] = self.precision_at_k(relevant_set, retrieved_ids, k)
                qr.ap_at[k] = self.average_precision_at_k(relevant_set, retrieved_ids, k)

            qr.reciprocal_rank = self.reciprocal_rank(relevant_set, retrieved_ids)

            results.append(qr)

        return results

    def evaluate_image_queries(self, max_tests: int = 30) -> list[QueryResult]:
        """
        이미지 검색 평가: 등록된 도면으로 자기 검출 + 동카테고리 검색

        자기 자신을 제외한 결과에서 동일 카테고리 도면이 상위에 오는지 평가한다.
        """
        records = self.pipeline.get_all_records()
        if not records:
            return []

        # 카테고리별 샘플링
        by_cat = {}
        for r in records:
            cat = r.category or "uncategorized"
            by_cat.setdefault(cat, []).append(r)

        test_records = []
        for cat, recs in by_cat.items():
            test_records.extend(recs[:5])
        test_records = test_records[:max_tests]

        max_k = max(self.k_values)
        results = []

        for record in test_records:
            if not Path(record.file_path).exists():
                continue

            start = time.time()
            search_results = self.pipeline.search_by_image(record.file_path, top_k=max_k + 1)
            latency = time.time() - start

            # 자기 자신 제외
            filtered = [r for r in search_results if r.drawing_id != record.drawing_id][:max_k]

            # 관련 = 동일 카테고리
            relevant_set = set()
            retrieved_ids = []
            retrieved_categories = []
            scores = []

            for r in filtered:
                rid = r.drawing_id
                rcat = r.metadata.get("category", "")
                retrieved_ids.append(rid)
                retrieved_categories.append(rcat)
                scores.append(r.score)
                if rcat == record.category:
                    relevant_set.add(rid)

            qr = QueryResult(
                query=f"IMAGE:{record.file_name}",
                query_type="image",
                relevant_ids=list(relevant_set),
                retrieved_ids=retrieved_ids,
                retrieved_categories=retrieved_categories,
                scores=scores,
                latency=latency,
            )

            for k in self.k_values:
                qr.recall_at[k] = self.recall_at_k(relevant_set, retrieved_ids, k)
                qr.precision_at[k] = self.precision_at_k(relevant_set, retrieved_ids, k)
                qr.ap_at[k] = self.average_precision_at_k(relevant_set, retrieved_ids, k)

            qr.reciprocal_rank = self.reciprocal_rank(relevant_set, retrieved_ids)
            results.append(qr)

        return results

    def run_full_evaluation(self) -> EvaluationReport:
        """전체 평가 실행"""
        logger.info("전체 평가 시작")

        text_results = self.evaluate_text_queries()
        image_results = self.evaluate_image_queries()
        all_results = text_results + image_results

        if not all_results:
            logger.warning("평가 결과 없음")
            return EvaluationReport()

        report = self._aggregate(all_results)

        # 텍스트/이미지 별도 집계
        if text_results:
            report.by_category["text_search"] = self._aggregate_metrics(text_results)
        if image_results:
            report.by_category["image_search"] = self._aggregate_metrics(image_results)

        logger.info("전체 평가 완료")
        return report

    def _aggregate(self, results: list[QueryResult]) -> EvaluationReport:
        """쿼리 결과들을 집계하여 리포트 생성"""
        report = EvaluationReport(
            num_queries=len(results),
            query_results=results,
        )

        metrics = self._aggregate_metrics(results)
        report.avg_recall = metrics["avg_recall"]
        report.avg_precision = metrics["avg_precision"]
        report.mrr = metrics["mrr"]
        report.map_at = metrics["map_at"]
        report.avg_latency = metrics["avg_latency"]
        report.p50_latency = metrics["p50_latency"]
        report.p95_latency = metrics["p95_latency"]

        return report

    def _aggregate_metrics(self, results: list[QueryResult]) -> dict:
        """메트릭 평균 계산"""
        n = len(results)
        if n == 0:
            return {}

        latencies = [r.latency for r in results]

        metrics = {
            "avg_recall": {},
            "avg_precision": {},
            "map_at": {},
            "mrr": sum(r.reciprocal_rank for r in results) / n,
            "avg_latency": sum(latencies) / n,
            "p50_latency": float(np.percentile(latencies, 50)),
            "p95_latency": float(np.percentile(latencies, 95)),
        }

        for k in self.k_values:
            recalls = [r.recall_at.get(k, 0) for r in results]
            precisions = [r.precision_at.get(k, 0) for r in results]
            aps = [r.ap_at.get(k, 0) for r in results]

            metrics["avg_recall"][k] = sum(recalls) / n
            metrics["avg_precision"][k] = sum(precisions) / n
            metrics["map_at"][k] = sum(aps) / n

        return metrics

    # ─────────────────────────────────────────
    # 리포트 출력
    # ─────────────────────────────────────────

    def print_report(self, report: EvaluationReport):
        """평가 리포트 콘솔 출력"""
        print("\n" + "=" * 65)
        print("  📊 DrawingLLM 검색 성능 평가 리포트")
        print("=" * 65)

        print(f"\n  총 쿼리 수: {report.num_queries}건")
        print(f"  MRR:        {report.mrr:.4f}")

        # 목표 대비 평가
        targets = {
            "Recall@5": 0.80, "Recall@10": 0.90,
            "Precision@5": 0.60, "MRR": 0.70,
        }

        # Recall@K 테이블
        print(f"\n  {'─' * 55}")
        print(f"  {'메트릭':<20} {'값':>8}   {'목표':>8}   {'판정':>4}")
        print(f"  {'─' * 55}")

        for k in self.k_values:
            r = report.avg_recall.get(k, 0)
            target_key = f"Recall@{k}"
            target = targets.get(target_key, None)
            target_str = f"{target:.2f}" if target else "  -  "
            status = "✅" if (target and r >= target) else "⚠️" if (target and r >= target * 0.8) else "❌" if target else "  "
            print(f"  Recall@{k:<13} {r:>8.4f}   {target_str:>8}   {status}")

        print()
        for k in self.k_values:
            p = report.avg_precision.get(k, 0)
            target_key = f"Precision@{k}"
            target = targets.get(target_key, None)
            target_str = f"{target:.2f}" if target else "  -  "
            status = "✅" if (target and p >= target) else "⚠️" if (target and p >= target * 0.8) else "❌" if target else "  "
            print(f"  Precision@{k:<10} {p:>8.4f}   {target_str:>8}   {status}")

        print()
        for k in self.k_values:
            m = report.map_at.get(k, 0)
            print(f"  mAP@{k:<14} {m:>8.4f}")

        # MRR
        mrr_target = targets.get("MRR", 0.70)
        mrr_status = "✅" if report.mrr >= mrr_target else "⚠️" if report.mrr >= mrr_target * 0.8 else "❌"
        print(f"\n  MRR{'':.<16} {report.mrr:>8.4f}   {mrr_target:>8.2f}   {mrr_status}")

        # 응답 시간
        print(f"\n  {'─' * 55}")
        print(f"  응답 시간:")
        print(f"    평균: {report.avg_latency:.3f}초")
        print(f"    P50:  {report.p50_latency:.3f}초")
        print(f"    P95:  {report.p95_latency:.3f}초")
        target_time = 3.0
        time_status = "✅" if report.p95_latency <= target_time else "❌"
        print(f"    목표: ≤{target_time}초 {time_status}")

        # 카테고리별
        if report.by_category:
            print(f"\n  {'─' * 55}")
            print(f"  검색 유형별:")
            for cat_name, metrics in report.by_category.items():
                mrr_val = metrics.get("mrr", 0)
                r5 = metrics.get("avg_recall", {}).get(5, 0)
                p5 = metrics.get("avg_precision", {}).get(5, 0)
                print(f"    {cat_name:<20} MRR={mrr_val:.3f}  R@5={r5:.3f}  P@5={p5:.3f}")

        print("\n" + "=" * 65)

    def save_report(self, report: EvaluationReport, path: str | Path):
        """리포트를 JSON으로 저장"""
        data = {
            "num_queries": report.num_queries,
            "avg_recall": {str(k): round(v, 4) for k, v in report.avg_recall.items()},
            "avg_precision": {str(k): round(v, 4) for k, v in report.avg_precision.items()},
            "mrr": round(report.mrr, 4),
            "map_at": {str(k): round(v, 4) for k, v in report.map_at.items()},
            "latency": {
                "avg": round(report.avg_latency, 4),
                "p50": round(report.p50_latency, 4),
                "p95": round(report.p95_latency, 4),
            },
            "by_category": {},
            "query_details": [],
        }

        for cat, m in report.by_category.items():
            data["by_category"][cat] = {
                "mrr": round(m.get("mrr", 0), 4),
                "avg_recall": {str(k): round(v, 4) for k, v in m.get("avg_recall", {}).items()},
                "avg_precision": {str(k): round(v, 4) for k, v in m.get("avg_precision", {}).items()},
            }

        for qr in report.query_results:
            data["query_details"].append({
                "query": qr.query,
                "type": qr.query_type,
                "recall_at": {str(k): round(v, 4) for k, v in qr.recall_at.items()},
                "precision_at": {str(k): round(v, 4) for k, v in qr.precision_at.items()},
                "reciprocal_rank": round(qr.reciprocal_rank, 4),
                "latency": round(qr.latency, 4),
                "top_results": [
                    {"id": rid, "cat": rcat, "score": round(s, 4)}
                    for rid, rcat, s in zip(qr.retrieved_ids[:5], qr.retrieved_categories[:5], qr.scores[:5])
                ],
            })

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"평가 리포트 저장: {path}")
