"""
DrawingLLM 하이브리드 검색 가중치 튜닝 모듈

이미지(CLIP) / 텍스트(SentenceTransformer) 가중치 최적화를 수행한다.

핵심 아이디어:
  - 모든 쿼리의 임베딩을 사전 계산 (1회)
  - 가중치만 변경하며 hybrid_search 반복 호출 → 매우 빠른 그리드 서치
  - Ground Truth 기반 MRR/Recall 최적화
  - 카테고리별 최적 가중치 분석

사용법:
  from core.weight_tuner import WeightTuner
  tuner = WeightTuner(pipeline, gt_path="data/ground_truth.json")
  result = tuner.grid_search(steps=11)
  tuner.print_result(result)
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np
from loguru import logger


@dataclass
class WeightConfig:
    """단일 가중치 설정"""
    image_weight: float
    text_weight: float

    @property
    def label(self) -> str:
        return f"I:{self.image_weight:.2f}/T:{self.text_weight:.2f}"


@dataclass
class WeightTrialResult:
    """단일 가중치 조합 시험 결과"""
    config: WeightConfig
    mrr: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    precision_at_5: float = 0.0
    map_at_5: float = 0.0
    avg_latency: float = 0.0
    # 복합 점수: MRR과 Recall@5의 가중 평균
    composite_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "image_weight": self.config.image_weight,
            "text_weight": self.config.text_weight,
            "label": self.config.label,
            "mrr": round(self.mrr, 4),
            "recall_at_5": round(self.recall_at_5, 4),
            "recall_at_10": round(self.recall_at_10, 4),
            "precision_at_5": round(self.precision_at_5, 4),
            "map_at_5": round(self.map_at_5, 4),
            "composite_score": round(self.composite_score, 4),
            "avg_latency": round(self.avg_latency, 4),
        }


@dataclass
class TuningResult:
    """전체 튜닝 결과"""
    best_global: WeightTrialResult | None = None
    all_trials: list[WeightTrialResult] = field(default_factory=list)
    best_per_category: dict = field(default_factory=dict)  # {category: WeightTrialResult}
    refinement: WeightTrialResult | None = None  # 세밀 탐색 결과
    total_time_sec: float = 0.0


class WeightTuner:
    """하이브리드 검색 가중치 최적화기"""

    def __init__(
        self,
        pipeline,
        ground_truth_path: str | Path | None = None,
        k_values: list[int] | None = None,
    ):
        self.pipeline = pipeline
        self.k_values = k_values or [1, 3, 5, 10]
        self.ground_truth = []
        self._precomputed: list[dict] | None = None

        if ground_truth_path:
            self._load_ground_truth(ground_truth_path)

    def _load_ground_truth(self, path: str | Path):
        """Ground Truth 로드"""
        path = Path(path)
        if not path.exists():
            logger.warning(f"Ground Truth 없음: {path}")
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.ground_truth = [
            q for q in data.get("queries", [])
            if q.get("type", "text") == "text"
        ]
        logger.info(f"Ground Truth 로드: {len(self.ground_truth)}건")

    # ─────────────────────────────────────────
    # 임베딩 사전 계산
    # ─────────────────────────────────────────

    def precompute_embeddings(self) -> list[dict]:
        """
        모든 쿼리의 CLIP/텍스트 임베딩을 사전 계산한다.
        가중치 그리드 서치 시 임베딩 계산 비용을 제거한다.
        """
        if self._precomputed:
            return self._precomputed

        logger.info("쿼리 임베딩 사전 계산 중...")
        self._precomputed = []

        for gt in self.ground_truth:
            query = gt["query"]

            # CLIP 텍스트 임베딩 (이미지 공간)
            clip_emb = self.pipeline._image_embedder.embed_text(query)
            # SentenceTransformer 텍스트 임베딩
            text_emb = self.pipeline._text_embedder.embed(query)

            self._precomputed.append({
                "query": query,
                "gt": gt,
                "clip_embedding": clip_emb,
                "text_embedding": text_emb,
            })

        logger.info(f"사전 계산 완료: {len(self._precomputed)}건")
        return self._precomputed

    # ─────────────────────────────────────────
    # 관련성 판단 (evaluation.py와 동일 로직)
    # ─────────────────────────────────────────

    @staticmethod
    def _is_relevant(result_category: str, result_filename: str, gt_entry: dict) -> bool:
        """검색 결과의 관련성 판단"""
        rel_cats = gt_entry.get("relevant_categories", [])
        if result_category in rel_cats:
            return True
        patterns = gt_entry.get("relevant_file_patterns", [])
        for pattern in patterns:
            if pattern.endswith("*"):
                if result_filename.lower().startswith(pattern[:-1].lower()):
                    return True
            elif result_filename.lower() == pattern.lower():
                return True
        return False

    # ─────────────────────────────────────────
    # 단일 가중치 시험
    # ─────────────────────────────────────────

    def _evaluate_weight(
        self,
        config: WeightConfig,
        precomputed: list[dict],
        top_k: int = 10,
    ) -> WeightTrialResult:
        """
        단일 가중치 조합으로 전체 쿼리 평가

        사전 계산된 임베딩을 사용하므로 매우 빠르다.
        """
        from core.evaluation import Evaluator

        reciprocal_ranks = []
        recalls_5 = []
        recalls_10 = []
        precisions_5 = []
        aps_5 = []
        latencies = []

        for item in precomputed:
            gt = item["gt"]
            clip_emb = item["clip_embedding"] if config.image_weight > 0 else None
            text_emb = item["text_embedding"] if config.text_weight > 0 else None

            start = time.time()
            results = self.pipeline._vector_store.hybrid_search(
                image_embedding=clip_emb,
                text_embedding=text_emb,
                top_k=top_k,
                image_weight=config.image_weight,
                text_weight=config.text_weight,
            )
            latencies.append(time.time() - start)

            # 관련 항목 판별
            retrieved_ids = []
            relevant_set = set()
            for r in results:
                rid = r.drawing_id
                rcat = r.metadata.get("category", "")
                rfname = r.metadata.get("file_name", "")
                retrieved_ids.append(rid)
                if self._is_relevant(rcat, rfname, gt):
                    relevant_set.add(rid)

            # 메트릭 계산
            reciprocal_ranks.append(Evaluator.reciprocal_rank(relevant_set, retrieved_ids))
            recalls_5.append(Evaluator.recall_at_k(relevant_set, retrieved_ids, 5))
            recalls_10.append(Evaluator.recall_at_k(relevant_set, retrieved_ids, 10))
            precisions_5.append(Evaluator.precision_at_k(relevant_set, retrieved_ids, 5))
            aps_5.append(Evaluator.average_precision_at_k(relevant_set, retrieved_ids, 5))

        n = len(precomputed)
        trial = WeightTrialResult(
            config=config,
            mrr=np.mean(reciprocal_ranks) if reciprocal_ranks else 0,
            recall_at_5=np.mean(recalls_5) if recalls_5 else 0,
            recall_at_10=np.mean(recalls_10) if recalls_10 else 0,
            precision_at_5=np.mean(precisions_5) if precisions_5 else 0,
            map_at_5=np.mean(aps_5) if aps_5 else 0,
            avg_latency=np.mean(latencies) if latencies else 0,
        )
        # 복합 점수: MRR 40% + Recall@5 30% + Precision@5 30%
        trial.composite_score = (
            0.40 * trial.mrr
            + 0.30 * trial.recall_at_5
            + 0.30 * trial.precision_at_5
        )

        return trial

    # ─────────────────────────────────────────
    # 그리드 서치
    # ─────────────────────────────────────────

    def grid_search(
        self,
        steps: int = 11,
        top_k: int = 10,
        optimize_metric: str = "composite",
    ) -> TuningResult:
        """
        이미지/텍스트 가중치 그리드 서치

        Args:
            steps: 그리드 분할 수 (11이면 0.0, 0.1, ..., 1.0)
            top_k: 검색 결과 수
            optimize_metric: 최적화 기준 ("composite", "mrr", "recall_at_5")

        Returns:
            TuningResult: 최적 가중치 및 전체 결과
        """
        logger.info(f"그리드 서치 시작: {steps} steps, metric={optimize_metric}")
        start_time = time.time()

        precomputed = self.precompute_embeddings()
        if not precomputed:
            logger.warning("평가할 쿼리가 없습니다.")
            return TuningResult()

        # 가중치 그리드 생성 (합=1.0 제약)
        alphas = np.linspace(0.0, 1.0, steps)
        configs = [WeightConfig(image_weight=round(a, 2), text_weight=round(1 - a, 2)) for a in alphas]

        result = TuningResult()

        for config in configs:
            trial = self._evaluate_weight(config, precomputed, top_k)
            result.all_trials.append(trial)

            logger.debug(
                f"  {config.label}  MRR={trial.mrr:.3f}  "
                f"R@5={trial.recall_at_5:.3f}  P@5={trial.precision_at_5:.3f}  "
                f"composite={trial.composite_score:.3f}"
            )

        # 최적 가중치 선택
        metric_fn = {
            "composite": lambda t: t.composite_score,
            "mrr": lambda t: t.mrr,
            "recall_at_5": lambda t: t.recall_at_5,
            "recall_at_10": lambda t: t.recall_at_10,
            "precision_at_5": lambda t: t.precision_at_5,
            "map_at_5": lambda t: t.map_at_5,
        }
        key_fn = metric_fn.get(optimize_metric, metric_fn["composite"])
        result.best_global = max(result.all_trials, key=key_fn)

        # 세밀 탐색: 최적 근방 ±0.05 범위
        best_alpha = result.best_global.config.image_weight
        fine_range = np.arange(
            max(0, best_alpha - 0.05),
            min(1.0, best_alpha + 0.06),
            0.01,
        )
        fine_trials = []
        for a in fine_range:
            a = round(a, 2)
            config = WeightConfig(image_weight=a, text_weight=round(1 - a, 2))
            trial = self._evaluate_weight(config, precomputed, top_k)
            fine_trials.append(trial)

        if fine_trials:
            result.refinement = max(fine_trials, key=key_fn)
            # 세밀 결과가 더 좋으면 업데이트
            if key_fn(result.refinement) > key_fn(result.best_global):
                result.best_global = result.refinement

        result.total_time_sec = time.time() - start_time
        logger.info(f"그리드 서치 완료: {result.total_time_sec:.1f}초")
        logger.info(f"최적 가중치: {result.best_global.config.label}")

        return result

    # ─────────────────────────────────────────
    # 카테고리별 최적 가중치
    # ─────────────────────────────────────────

    def per_category_analysis(
        self,
        steps: int = 11,
        top_k: int = 10,
    ) -> dict[str, list[WeightTrialResult]]:
        """
        카테고리별 최적 가중치를 분석한다.

        각 카테고리(engine, chassis 등)에 속하는 쿼리만 분리하여
        독립적으로 그리드 서치한다.

        Returns:
            {category: [WeightTrialResult, ...]} 카테고리별 전체 그리드 결과
        """
        logger.info("카테고리별 가중치 분석 시작")

        precomputed = self.precompute_embeddings()

        # 카테고리별 쿼리 그룹핑
        cat_queries: dict[str, list[dict]] = {}
        for item in precomputed:
            cats = item["gt"].get("relevant_categories", [])
            primary_cat = cats[0] if cats else "uncategorized"
            cat_queries.setdefault(primary_cat, []).append(item)

        alphas = np.linspace(0.0, 1.0, steps)
        configs = [WeightConfig(image_weight=round(a, 2), text_weight=round(1 - a, 2)) for a in alphas]

        results = {}
        for cat, items in cat_queries.items():
            if len(items) < 2:
                continue  # 쿼리 2건 미만은 스킵

            cat_trials = []
            for config in configs:
                trial = self._evaluate_weight(config, items, top_k)
                cat_trials.append(trial)

            results[cat] = cat_trials

        return results

    # ─────────────────────────────────────────
    # 리포트 출력
    # ─────────────────────────────────────────

    def print_result(self, result: TuningResult, per_cat: dict | None = None):
        """튜닝 결과 콘솔 출력"""
        print("\n" + "=" * 70)
        print("  ⚖️  DrawingLLM 하이브리드 가중치 튜닝 결과")
        print("=" * 70)

        if not result.all_trials:
            print("  결과 없음")
            return

        # 전체 그리드 히트맵
        print(f"\n  📊 그리드 서치 결과 ({len(result.all_trials)} configurations)")
        print(f"  {'─' * 60}")
        print(f"  {'가중치':<18} {'MRR':>7} {'R@5':>7} {'R@10':>7} {'P@5':>7} {'복합':>7}")
        print(f"  {'─' * 60}")

        for trial in result.all_trials:
            is_best = (result.best_global and
                       trial.config.image_weight == result.best_global.config.image_weight)
            marker = " ◀ BEST" if is_best else ""

            # 복합 점수 기반 바 차트
            bar_len = int(trial.composite_score * 30)
            bar = "█" * bar_len + "░" * (30 - bar_len)

            print(
                f"  {trial.config.label:<18}"
                f" {trial.mrr:>6.3f}"
                f" {trial.recall_at_5:>6.3f}"
                f" {trial.recall_at_10:>6.3f}"
                f" {trial.precision_at_5:>6.3f}"
                f" {trial.composite_score:>6.3f}"
                f"  {bar}{marker}"
            )

        # 최적 가중치
        best = result.best_global
        if best:
            print(f"\n  {'─' * 60}")
            print(f"  🏆 최적 가중치: {best.config.label}")
            print(f"     이미지(CLIP) 가중치: {best.config.image_weight}")
            print(f"     텍스트(OCR)  가중치: {best.config.text_weight}")
            print(f"     MRR:          {best.mrr:.4f}")
            print(f"     Recall@5:     {best.recall_at_5:.4f}")
            print(f"     Recall@10:    {best.recall_at_10:.4f}")
            print(f"     Precision@5:  {best.precision_at_5:.4f}")
            print(f"     mAP@5:        {best.map_at_5:.4f}")
            print(f"     복합 점수:    {best.composite_score:.4f}")

        # 세밀 탐색
        if result.refinement and result.refinement != result.best_global:
            ref = result.refinement
            print(f"\n  🔬 세밀 탐색 결과: {ref.config.label}")
            print(f"     복합 점수: {ref.composite_score:.4f}")

        # 카테고리별 분석
        if per_cat:
            print(f"\n  {'─' * 60}")
            print(f"  📂 카테고리별 최적 가중치")
            print(f"  {'카테고리':<18} {'최적 가중치':<18} {'MRR':>7} {'R@5':>7} {'복합':>7}")
            print(f"  {'─' * 60}")

            for cat, trials in sorted(per_cat.items()):
                cat_best = max(trials, key=lambda t: t.composite_score)
                print(
                    f"  {cat:<18}"
                    f" {cat_best.config.label:<18}"
                    f" {cat_best.mrr:>6.3f}"
                    f" {cat_best.recall_at_5:>6.3f}"
                    f" {cat_best.composite_score:>6.3f}"
                )

            # 카테고리별 가중치 분산 분석
            best_alphas = [
                max(trials, key=lambda t: t.composite_score).config.image_weight
                for trials in per_cat.values()
            ]
            if best_alphas:
                mean_alpha = np.mean(best_alphas)
                std_alpha = np.std(best_alphas)
                print(f"\n  이미지 가중치 분포: 평균={mean_alpha:.2f}  표준편차={std_alpha:.2f}")
                if std_alpha < 0.1:
                    print(f"  → 카테고리 간 차이 적음: 단일 가중치 사용 권장")
                else:
                    print(f"  → 카테고리 간 차이 큼: 카테고리별 가중치 적용 고려")

        print(f"\n  ⏱️  총 소요 시간: {result.total_time_sec:.1f}초")
        print("=" * 70)

    def save_result(self, result: TuningResult, path: str | Path,
                    per_cat: dict | None = None):
        """튜닝 결과 JSON 저장"""
        data = {
            "best_global": result.best_global.to_dict() if result.best_global else None,
            "refinement": result.refinement.to_dict() if result.refinement else None,
            "total_time_sec": round(result.total_time_sec, 2),
            "all_trials": [t.to_dict() for t in result.all_trials],
            "recommendation": {},
        }

        if result.best_global:
            data["recommendation"] = {
                "image_weight": result.best_global.config.image_weight,
                "text_weight": result.best_global.config.text_weight,
                "update_in": "config/settings.py → image_weight / text_weight",
            }

        if per_cat:
            data["per_category"] = {}
            for cat, trials in per_cat.items():
                cat_best = max(trials, key=lambda t: t.composite_score)
                data["per_category"][cat] = cat_best.to_dict()

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"튜닝 결과 저장: {path}")
