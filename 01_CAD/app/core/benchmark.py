"""
DrawingLLM 성능 벤치마크 모듈

파이프라인 각 단계의 성능을 정량 측정한다.

벤치마크 항목:
  1. 모델 로딩 시간    — CLIP, SentenceTransformer, OCR 초기화
  2. 임베딩 처리량     — 이미지/텍스트 임베딩 생성 throughput
  3. 검색 레이턴시     — 단건/연속 검색 응답 시간 분포
  4. 등록 처리량       — 전체 파이프라인 (OCR + 임베딩 + 저장) throughput
  5. 메모리 사용량     — 각 컴포넌트별 메모리 점유
  6. 스케일링 특성     — DB 크기 대비 검색 시간 변화

사용법:
  from core.benchmark import Benchmarker
  bm = Benchmarker(pipeline)
  report = bm.run_all()
  bm.print_report(report)
"""

import gc
import os
import sys
import time
import json
import tracemalloc
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np
from loguru import logger


@dataclass
class TimingResult:
    """단일 타이밍 측정 결과"""
    name: str
    samples: list[float] = field(default_factory=list)  # 초 단위

    @property
    def mean(self) -> float:
        return np.mean(self.samples) if self.samples else 0.0

    @property
    def std(self) -> float:
        return np.std(self.samples) if len(self.samples) > 1 else 0.0

    @property
    def p50(self) -> float:
        return float(np.percentile(self.samples, 50)) if self.samples else 0.0

    @property
    def p95(self) -> float:
        return float(np.percentile(self.samples, 95)) if self.samples else 0.0

    @property
    def p99(self) -> float:
        return float(np.percentile(self.samples, 99)) if self.samples else 0.0

    @property
    def min(self) -> float:
        return float(np.min(self.samples)) if self.samples else 0.0

    @property
    def max(self) -> float:
        return float(np.max(self.samples)) if self.samples else 0.0

    @property
    def throughput(self) -> float:
        """초당 처리 건수"""
        return len(self.samples) / sum(self.samples) if sum(self.samples) > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "count": len(self.samples),
            "mean_sec": round(self.mean, 4),
            "std_sec": round(self.std, 4),
            "p50_sec": round(self.p50, 4),
            "p95_sec": round(self.p95, 4),
            "p99_sec": round(self.p99, 4),
            "min_sec": round(self.min, 4),
            "max_sec": round(self.max, 4),
            "throughput_per_sec": round(self.throughput, 2),
        }


@dataclass
class MemorySnapshot:
    """메모리 사용량 스냅샷"""
    label: str
    rss_mb: float        # Resident Set Size
    peak_mb: float = 0.0  # tracemalloc peak
    delta_mb: float = 0.0  # 이전 대비 증가분


@dataclass
class BenchmarkReport:
    """전체 벤치마크 리포트"""
    system_info: dict = field(default_factory=dict)
    model_load: dict = field(default_factory=dict)       # 모델 로딩
    embedding: dict = field(default_factory=dict)         # 임베딩 처리량
    search: dict = field(default_factory=dict)            # 검색 레이턴시
    registration: dict = field(default_factory=dict)      # 등록 처리량
    memory: list = field(default_factory=list)            # 메모리 스냅샷
    scaling: dict = field(default_factory=dict)           # 스케일링
    llm: dict = field(default_factory=dict)               # Phase 4: LLM 레이턴시

    def to_dict(self) -> dict:
        return {
            "system_info": self.system_info,
            "model_load": self.model_load,
            "embedding": self.embedding,
            "search": self.search,
            "registration": self.registration,
            "memory": self.memory,
            "scaling": self.scaling,
            "llm": self.llm,
        }


class Benchmarker:
    """파이프라인 성능 벤치마커"""

    def __init__(self, pipeline=None, data_dir: str | Path | None = None):
        """
        Args:
            pipeline: DrawingPipeline 인스턴스 (None이면 벤치마크 시 생성)
            data_dir: 샘플 도면 디렉토리
        """
        self.pipeline = pipeline
        self.data_dir = Path(data_dir) if data_dir else None
        self._image_files: list[Path] = []

    def _collect_images(self, max_count: int = 100) -> list[Path]:
        """벤치마크용 이미지 파일 수집"""
        if self._image_files:
            return self._image_files[:max_count]

        search_dirs = []
        if self.data_dir:
            search_dirs.append(self.data_dir)
        if self.pipeline:
            search_dirs.append(Path(self.pipeline.upload_dir))

        exts = {".png", ".jpg", ".jpeg"}
        for d in search_dirs:
            if d.exists():
                for f in sorted(d.rglob("*")):
                    if f.is_file() and f.suffix.lower() in exts and "{" not in str(f):
                        self._image_files.append(f)

        return self._image_files[:max_count]

    @staticmethod
    def _get_system_info() -> dict:
        """시스템 정보 수집"""
        import platform
        info = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
        }

        try:
            import torch
            info["torch"] = torch.__version__
            info["cuda_available"] = torch.cuda.is_available()
            info["mps_available"] = (
                hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
            )
            if torch.cuda.is_available():
                info["gpu"] = torch.cuda.get_device_name(0)
        except ImportError:
            pass

        try:
            import psutil
            mem = psutil.virtual_memory()
            info["total_ram_gb"] = round(mem.total / (1024**3), 1)
        except ImportError:
            pass

        return info

    @staticmethod
    def _get_rss_mb() -> float:
        """현재 프로세스 RSS (MB)"""
        try:
            import psutil
            return psutil.Process(os.getpid()).memory_info().rss / (1024**2)
        except ImportError:
            # psutil 없으면 /proc 파싱 (Linux) 또는 resource (macOS)
            try:
                import resource
                return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # macOS: KB
            except Exception:
                return 0.0

    # ─────────────────────────────────────────
    # 1. 모델 로딩 벤치마크
    # ─────────────────────────────────────────

    def bench_model_load(self) -> dict:
        """각 모델의 초기 로딩 시간 측정"""
        logger.info("[벤치마크] 모델 로딩 시간 측정")
        results = {}

        # OpenCLIP
        try:
            import open_clip
            import torch

            gc.collect()
            start = time.time()
            model, _, preprocess = open_clip.create_model_and_transforms(
                "ViT-L-14", pretrained="datacomp_xl_s13b_b90k", device="cpu",
            )
            elapsed = time.time() - start
            results["openclip_vit_l14"] = {"time_sec": round(elapsed, 3), "status": "ok"}
            del model, preprocess
            gc.collect()
        except Exception as e:
            results["openclip_vit_l14"] = {"time_sec": 0, "status": f"error: {e}"}

        # SentenceTransformer
        try:
            from sentence_transformers import SentenceTransformer

            gc.collect()
            start = time.time()
            st_model = SentenceTransformer(
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
            elapsed = time.time() - start
            results["sentence_transformer"] = {"time_sec": round(elapsed, 3), "status": "ok"}
            del st_model
            gc.collect()
        except Exception as e:
            results["sentence_transformer"] = {"time_sec": 0, "status": f"error: {e}"}

        # PaddleOCR / EasyOCR
        try:
            from paddleocr import PaddleOCR

            gc.collect()
            start = time.time()
            ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False, use_gpu=False)
            elapsed = time.time() - start
            results["paddleocr"] = {"time_sec": round(elapsed, 3), "status": "ok"}
            del ocr
            gc.collect()
        except ImportError:
            try:
                import easyocr

                gc.collect()
                start = time.time()
                reader = easyocr.Reader(["en"], gpu=False)
                elapsed = time.time() - start
                results["easyocr"] = {"time_sec": round(elapsed, 3), "status": "ok"}
                del reader
                gc.collect()
            except Exception as e:
                results["ocr"] = {"time_sec": 0, "status": f"error: {e}"}

        return results

    # ─────────────────────────────────────────
    # 2. 임베딩 처리량 벤치마크
    # ─────────────────────────────────────────

    def bench_embedding_throughput(self, n_images: int = 50, n_texts: int = 100) -> dict:
        """이미지/텍스트 임베딩 생성 throughput 측정"""
        logger.info("[벤치마크] 임베딩 처리량 측정")
        results = {}

        images = self._collect_images(n_images)
        if not images:
            logger.warning("벤치마크용 이미지 없음")
            return results

        # 이미지 임베딩 (단건)
        from core.embeddings import ImageEmbedder, TextEmbedder
        img_embedder = ImageEmbedder(model_name="ViT-L-14")
        img_timing = TimingResult(name="openclip_image_single")

        for img_path in images[:n_images]:
            start = time.time()
            try:
                img_embedder.embed_image(img_path)
                img_timing.samples.append(time.time() - start)
            except Exception:
                pass

        results["clip_image_single"] = img_timing.to_dict()

        # 이미지 임베딩 (배치)
        batch_sizes = [8, 16, 32]
        for bs in batch_sizes:
            batch_paths = [str(p) for p in images[:min(n_images, 64)]]
            start = time.time()
            try:
                img_embedder.embed_images_batch(batch_paths, batch_size=bs)
                total_time = time.time() - start
                results[f"clip_image_batch_{bs}"] = {
                    "total_sec": round(total_time, 3),
                    "count": len(batch_paths),
                    "throughput_per_sec": round(len(batch_paths) / total_time, 2),
                }
            except Exception as e:
                results[f"clip_image_batch_{bs}"] = {"error": str(e)}

        # 텍스트 임베딩
        text_embedder = TextEmbedder()
        sample_texts = [
            "flange drawing Ø80", "brake caliper", "gear shaft transmission",
            "engine cylinder head bolt", "wiring harness connector",
            "변속기 입력 샤프트", "차체 도어 힌지 브래킷", "전장 배터리 트레이",
            "SUS304 stainless steel", "bearing housing assembly",
        ] * (n_texts // 10)

        text_timing = TimingResult(name="text_embedding_single")
        for text in sample_texts[:n_texts]:
            start = time.time()
            text_embedder.embed(text)
            text_timing.samples.append(time.time() - start)

        results["text_embedding_single"] = text_timing.to_dict()

        # CLIP 텍스트 인코더 (크로스모달)
        clip_text_timing = TimingResult(name="clip_text_encoding")
        for text in sample_texts[:50]:
            start = time.time()
            img_embedder.embed_text(text)
            clip_text_timing.samples.append(time.time() - start)

        results["clip_text_encoding"] = clip_text_timing.to_dict()

        return results

    # ─────────────────────────────────────────
    # 3. 검색 레이턴시 벤치마크
    # ─────────────────────────────────────────

    def bench_search_latency(self, n_queries: int = 50) -> dict:
        """검색 레이턴시 분포 측정"""
        logger.info("[벤치마크] 검색 레이턴시 측정")

        if not self.pipeline:
            logger.warning("파이프라인 없음 — 검색 벤치마크 스킵")
            return {}

        stats = self.pipeline.get_stats()
        if stats["total_drawings"] == 0:
            logger.warning("등록된 도면 없음 — 검색 벤치마크 스킵")
            return {}

        results = {}

        queries = [
            "flange drawing", "gear shaft", "brake caliper", "engine piston",
            "bearing housing", "bracket mounting", "transmission clutch",
            "door hinge body", "battery tray", "wiring connector",
            "플랜지", "기어 샤프트", "브레이크 캘리퍼", "엔진 실린더",
            "변속기", "서스펜션 암", "도어 힌지", "배터리 트레이",
            "SUS304 part", "Ø50 dimension",
        ]
        # 쿼리 반복하여 n_queries 건 확보
        queries = (queries * (n_queries // len(queries) + 1))[:n_queries]

        # 텍스트 검색 (하이브리드)
        text_timing = TimingResult(name="text_search_hybrid")
        for query in queries:
            start = time.time()
            self.pipeline.search_by_text(query, top_k=10)
            text_timing.samples.append(time.time() - start)

        results["text_search_hybrid"] = text_timing.to_dict()

        # 이미지 검색
        images = self._collect_images(20)
        if images:
            img_timing = TimingResult(name="image_search")
            for img_path in images[:min(n_queries, 20)]:
                start = time.time()
                try:
                    self.pipeline.search_by_image(img_path, top_k=10)
                    img_timing.samples.append(time.time() - start)
                except Exception:
                    pass

            results["image_search"] = img_timing.to_dict()

        # Warmup 제거 후 재측정 (최초 몇 건은 캐시 미적중)
        if len(text_timing.samples) > 5:
            warm_timing = TimingResult(name="text_search_warmed")
            warm_timing.samples = text_timing.samples[5:]
            results["text_search_warmed"] = warm_timing.to_dict()

        results["db_size"] = stats["total_drawings"]

        return results

    # ─────────────────────────────────────────
    # 4. 등록 처리량 벤치마크
    # ─────────────────────────────────────────

    def bench_registration_throughput(self, n_files: int = 20) -> dict:
        """도면 등록 전체 파이프라인 throughput (OCR + 임베딩 + DB 저장)"""
        logger.info("[벤치마크] 등록 처리량 측정")

        if not self.pipeline:
            return {}

        images = self._collect_images(n_files)
        if not images:
            return {}

        # 단계별 시간 측정
        ocr_timing = TimingResult(name="ocr_extract")
        img_emb_timing = TimingResult(name="image_embedding")
        txt_emb_timing = TimingResult(name="text_embedding")
        total_timing = TimingResult(name="register_total")

        for img_path in images[:n_files]:
            t0 = time.time()

            # OCR
            try:
                t1 = time.time()
                ocr_result = self.pipeline._ocr.extract(str(img_path))
                ocr_timing.samples.append(time.time() - t1)
            except Exception:
                ocr_text = ""
                ocr_timing.samples.append(time.time() - t1)

            # 이미지 임베딩
            t2 = time.time()
            try:
                self.pipeline._image_embedder.embed_image(img_path)
            except Exception:
                pass
            img_emb_timing.samples.append(time.time() - t2)

            # 텍스트 임베딩
            t3 = time.time()
            try:
                text = getattr(ocr_result, "full_text", "") or ""
                if text.strip():
                    self.pipeline._text_embedder.embed(text)
            except Exception:
                pass
            txt_emb_timing.samples.append(time.time() - t3)

            total_timing.samples.append(time.time() - t0)

        return {
            "ocr_extract": ocr_timing.to_dict(),
            "image_embedding": img_emb_timing.to_dict(),
            "text_embedding": txt_emb_timing.to_dict(),
            "register_total": total_timing.to_dict(),
            "files_tested": min(n_files, len(images)),
        }

    # ─────────────────────────────────────────
    # 5. 메모리 프로파일링
    # ─────────────────────────────────────────

    def bench_memory(self) -> list[dict]:
        """컴포넌트별 메모리 사용량 측정"""
        logger.info("[벤치마크] 메모리 사용량 측정")
        snapshots = []

        baseline = self._get_rss_mb()
        snapshots.append({"label": "baseline", "rss_mb": round(baseline, 1), "delta_mb": 0})

        # OpenCLIP 로드
        try:
            import open_clip
            import torch
            gc.collect()
            before = self._get_rss_mb()
            model, _, preprocess = open_clip.create_model_and_transforms(
                "ViT-L-14", pretrained="datacomp_xl_s13b_b90k", device="cpu",
            )
            after = self._get_rss_mb()
            snapshots.append({
                "label": "openclip_vit_l14",
                "rss_mb": round(after, 1),
                "delta_mb": round(after - before, 1),
            })
            del model, preprocess
            gc.collect()
        except Exception:
            pass

        # SentenceTransformer 로드
        try:
            from sentence_transformers import SentenceTransformer
            gc.collect()
            before = self._get_rss_mb()
            st = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            after = self._get_rss_mb()
            snapshots.append({
                "label": "sentence_transformer",
                "rss_mb": round(after, 1),
                "delta_mb": round(after - before, 1),
            })
            del st
            gc.collect()
        except Exception:
            pass

        # ChromaDB
        try:
            import chromadb
            gc.collect()
            before = self._get_rss_mb()
            if self.pipeline:
                _ = self.pipeline._vector_store.get_stats()
            else:
                import tempfile
                client = chromadb.PersistentClient(path=tempfile.mkdtemp())
                col = client.get_or_create_collection("bench")
                col.add(ids=["t"], embeddings=[[0.1] * 512])
            after = self._get_rss_mb()
            snapshots.append({
                "label": "chromadb",
                "rss_mb": round(after, 1),
                "delta_mb": round(after - before, 1),
            })
        except Exception:
            pass

        return snapshots

    # ─────────────────────────────────────────
    # 6. 스케일링 특성
    # ─────────────────────────────────────────

    def bench_scaling(self, query: str = "flange drawing", steps: int = 5) -> dict:
        """DB 크기 대비 검색 시간 변화 측정 (현재 DB에서 top_k 변화)"""
        logger.info("[벤치마크] 스케일링 특성 측정")

        if not self.pipeline:
            return {}

        stats = self.pipeline.get_stats()
        db_size = stats["total_drawings"]
        if db_size == 0:
            return {}

        # top_k 변화에 따른 검색 시간
        top_k_values = [1, 3, 5, 10, 20, 50]
        top_k_values = [k for k in top_k_values if k <= db_size]

        scaling_data = []
        for k in top_k_values:
            times = []
            for _ in range(10):  # 10회 반복 평균
                start = time.time()
                self.pipeline.search_by_text(query, top_k=k)
                times.append(time.time() - start)

            scaling_data.append({
                "top_k": k,
                "mean_sec": round(np.mean(times), 4),
                "std_sec": round(np.std(times), 4),
            })

        return {
            "db_size": db_size,
            "query": query,
            "top_k_scaling": scaling_data,
        }

    # ─────────────────────────────────────────
    # 7. LLM 레이턴시 벤치마크 (Phase 4)
    # ─────────────────────────────────────────

    def bench_llm_latency(self, n_images: int = 5) -> dict:
        """LLM 응답 레이턴시 측정 (컨텍스트 유무 비교).

        측정 항목:
          1. describe_drawing — 컨텍스트 없음 (Baseline)
          2. describe_drawing — 컨텍스트 있음 (이미지 모드)
          3. describe_drawing — 컨텍스트 있음 (텍스트 전용)
          4. generate_metadata — 컨텍스트 유무
          5. 환각률: 각 응답에 HallucinationDetector.validate() 실행

        Args:
            n_images: 측정할 이미지 수

        Returns:
            dict: 레이턴시 및 환각률 결과
        """
        logger.info("[벤치마크] LLM 레이턴시 측정")

        if not self.pipeline:
            logger.warning("파이프라인 없음 — LLM 벤치마크 스킵")
            return {}

        from core.llm import AnalysisContext, HallucinationDetector

        images = self._collect_images(n_images)
        if not images:
            logger.warning("벤치마크용 이미지 없음")
            return {}

        llm = self.pipeline._llm
        results = {}

        # 샘플 컨텍스트 구성 (실제 OCR 데이터 기반)
        def _make_context(img_path: Path) -> AnalysisContext:
            """이미지에서 OCR/YOLO 컨텍스트를 실제 추출한다."""
            ctx = AnalysisContext()
            try:
                ocr_result = self.pipeline._ocr.extract(str(img_path))
                ctx.part_numbers = ocr_result.part_numbers
                ctx.dimensions = ocr_result.dimensions
                ctx.materials = ocr_result.materials
                ctx.ocr_text = ocr_result.full_text[:300]
            except Exception:
                pass
            if self.pipeline._classifier:
                try:
                    yolo_res = self.pipeline._classifier.classify(img_path)
                    ctx.yolo_category = yolo_res.category
                    ctx.yolo_confidence = yolo_res.confidence
                    ctx.yolo_top_k = yolo_res.top_k
                except Exception:
                    pass
            return ctx

        # 1. Baseline (컨텍스트 없음)
        baseline_timing = TimingResult(name="describe_no_context")
        for img in images[:n_images]:
            start = time.time()
            try:
                llm.describe_drawing(img)
            except Exception:
                pass
            baseline_timing.samples.append(time.time() - start)
        results["describe_no_context"] = baseline_timing.to_dict()

        # 2. 컨텍스트 + 이미지
        ctx_timing = TimingResult(name="describe_with_context")
        hallucination_scores = []
        for img in images[:n_images]:
            ctx = _make_context(img)
            start = time.time()
            try:
                resp = llm.describe_drawing(img, context=ctx)
                if ctx.has_context() and not resp.startswith("[오류]"):
                    vr = HallucinationDetector.validate(resp, ctx)
                    hallucination_scores.append(vr.score)
            except Exception:
                pass
            ctx_timing.samples.append(time.time() - start)
        results["describe_with_context"] = ctx_timing.to_dict()

        # 3. 텍스트 전용 모드 (풍부한 컨텍스트 시뮬레이션)
        text_only_timing = TimingResult(name="describe_text_only")
        rich_ctx = AnalysisContext(
            yolo_category="Shafts",
            yolo_confidence=0.92,
            yolo_top_k=[("Shafts", 0.92), ("Gears", 0.04)],
            part_numbers=["SH-1234"],
            materials=["S45C"],
            dimensions=["Ø50mm", "100mm", "M8x1.25"],
            title_block_data={"drawing_number": "SH-1234", "material": "S45C"},
        )
        for _ in range(min(n_images, 3)):
            start = time.time()
            try:
                llm.describe_drawing(images[0], context=rich_ctx)
            except Exception:
                pass
            text_only_timing.samples.append(time.time() - start)
        results["describe_text_only"] = text_only_timing.to_dict()

        # 4. 메타데이터 비교
        meta_baseline = TimingResult(name="metadata_no_context")
        meta_ctx = TimingResult(name="metadata_with_context")
        for img in images[:min(n_images, 3)]:
            start = time.time()
            try:
                llm.generate_metadata(img)
            except Exception:
                pass
            meta_baseline.samples.append(time.time() - start)

            ctx = _make_context(img)
            start = time.time()
            try:
                llm.generate_metadata(img, context=ctx)
            except Exception:
                pass
            meta_ctx.samples.append(time.time() - start)

        results["metadata_no_context"] = meta_baseline.to_dict()
        results["metadata_with_context"] = meta_ctx.to_dict()

        # 5. 환각률 요약
        if hallucination_scores:
            results["hallucination"] = {
                "mean_score": round(float(np.mean(hallucination_scores)), 3),
                "min_score": round(float(np.min(hallucination_scores)), 3),
                "max_score": round(float(np.max(hallucination_scores)), 3),
                "samples": len(hallucination_scores),
            }

        return results

    # ─────────────────────────────────────────
    # 전체 실행
    # ─────────────────────────────────────────

    def run_all(
        self,
        skip_model_load: bool = False,
        skip_llm: bool = True,
    ) -> BenchmarkReport:
        """전체 벤치마크 실행

        Args:
            skip_model_load: 모델 로딩 벤치마크 스킵
            skip_llm: LLM 벤치마크 스킵 (Ollama 서버 필요)
        """
        logger.info("=" * 50)
        logger.info("전체 벤치마크 시작")
        logger.info("=" * 50)

        report = BenchmarkReport()
        report.system_info = self._get_system_info()

        if not skip_model_load:
            report.model_load = self.bench_model_load()

        report.embedding = self.bench_embedding_throughput()
        report.search = self.bench_search_latency()
        report.registration = self.bench_registration_throughput()
        report.memory = self.bench_memory()
        report.scaling = self.bench_scaling()

        if not skip_llm:
            report.llm = self.bench_llm_latency()

        logger.info("전체 벤치마크 완료")
        return report

    # ─────────────────────────────────────────
    # 리포트 출력
    # ─────────────────────────────────────────

    def print_report(self, report: BenchmarkReport):
        """벤치마크 리포트 콘솔 출력"""
        print("\n" + "=" * 65)
        print("  ⚡ DrawingLLM 성능 벤치마크 리포트")
        print("=" * 65)

        # 시스템 정보
        si = report.system_info
        print(f"\n  🖥️  시스템: {si.get('platform', '?')}")
        print(f"      CPU: {si.get('cpu_count', '?')} cores  |  RAM: {si.get('total_ram_gb', '?')} GB")
        print(f"      PyTorch: {si.get('torch', '?')}  |  "
              f"CUDA: {si.get('cuda_available', False)}  |  MPS: {si.get('mps_available', False)}")

        # 모델 로딩
        if report.model_load:
            print(f"\n  {'─' * 55}")
            print(f"  📦 모델 로딩 시간")
            for name, data in report.model_load.items():
                t = data.get("time_sec", 0)
                status = data.get("status", "?")
                bar = "█" * int(t * 2) + "░" * max(0, 20 - int(t * 2))
                icon = "✅" if status == "ok" else "❌"
                print(f"    {icon} {name:<28} {t:>6.2f}초  {bar}")

        # 임베딩 처리량
        if report.embedding:
            print(f"\n  {'─' * 55}")
            print(f"  🔢 임베딩 처리량")
            for name, data in report.embedding.items():
                if isinstance(data, dict) and "mean_sec" in data:
                    tp = data.get("throughput_per_sec", 0)
                    mean = data.get("mean_sec", 0)
                    p95 = data.get("p95_sec", 0)
                    print(f"    {name:<28} 평균={mean:.4f}초  P95={p95:.4f}초  {tp:.1f}/초")
                elif isinstance(data, dict) and "throughput_per_sec" in data:
                    tp = data.get("throughput_per_sec", 0)
                    total = data.get("total_sec", 0)
                    cnt = data.get("count", 0)
                    print(f"    {name:<28} {cnt}건/{total:.1f}초  {tp:.1f}/초")

        # 검색 레이턴시
        if report.search:
            print(f"\n  {'─' * 55}")
            print(f"  🔍 검색 레이턴시  (DB: {report.search.get('db_size', '?')}건)")
            target = 3.0
            for name in ["text_search_hybrid", "text_search_warmed", "image_search"]:
                data = report.search.get(name)
                if not data:
                    continue
                mean = data.get("mean_sec", 0)
                p50 = data.get("p50_sec", 0)
                p95 = data.get("p95_sec", 0)
                status = "✅" if p95 <= target else "⚠️" if p95 <= target * 1.5 else "❌"
                print(f"    {status} {name:<28} 평균={mean:.3f}초  P50={p50:.3f}초  P95={p95:.3f}초")
            print(f"    목표: P95 ≤ {target}초")

        # 등록 처리량
        if report.registration:
            print(f"\n  {'─' * 55}")
            print(f"  📝 등록 단계별 소요 시간 (파일 {report.registration.get('files_tested', '?')}건)")
            stages = ["ocr_extract", "image_embedding", "text_embedding", "register_total"]
            for name in stages:
                data = report.registration.get(name)
                if not data:
                    continue
                mean = data.get("mean_sec", 0)
                pct = ""
                total_mean = report.registration.get("register_total", {}).get("mean_sec", 1)
                if name != "register_total" and total_mean > 0:
                    pct = f"({mean / total_mean * 100:.0f}%)"
                label = {
                    "ocr_extract": "OCR 추출",
                    "image_embedding": "이미지 임베딩",
                    "text_embedding": "텍스트 임베딩",
                    "register_total": "전체 (합계)",
                }.get(name, name)
                print(f"    {label:<20} 평균={mean:.3f}초  {pct}")

        # 메모리
        if report.memory:
            print(f"\n  {'─' * 55}")
            print(f"  🧠 메모리 사용량 (RSS)")
            for snap in report.memory:
                label = snap.get("label", "?")
                rss = snap.get("rss_mb", 0)
                delta = snap.get("delta_mb", 0)
                delta_str = f"+{delta:.0f}MB" if delta > 0 else ""
                bar = "█" * int(rss / 100) + "░" * max(0, 20 - int(rss / 100))
                print(f"    {label:<24} {rss:>7.0f} MB  {delta_str:>8}  {bar}")

        # 스케일링
        if report.scaling and report.scaling.get("top_k_scaling"):
            print(f"\n  {'─' * 55}")
            print(f"  📈 Top-K 스케일링 (DB: {report.scaling.get('db_size', '?')}건)")
            for item in report.scaling["top_k_scaling"]:
                k = item["top_k"]
                mean = item["mean_sec"]
                bar = "█" * int(mean * 50)
                print(f"    K={k:<4}  {mean:.4f}초  {bar}")

        # LLM 레이턴시 (Phase 4)
        if report.llm:
            print(f"\n  {'─' * 55}")
            print(f"  🤖 LLM 레이턴시 (Phase 4)")
            llm_items = [
                ("describe_no_context", "설명 (Baseline)"),
                ("describe_with_context", "설명 (컨텍스트+이미지)"),
                ("describe_text_only", "설명 (텍스트 전용)"),
                ("metadata_no_context", "메타데이터 (Baseline)"),
                ("metadata_with_context", "메타데이터 (컨텍스트)"),
            ]
            for key, label in llm_items:
                data = report.llm.get(key)
                if not data:
                    continue
                mean = data.get("mean_sec", 0)
                p95 = data.get("p95_sec", 0)
                cnt = data.get("count", 0)
                print(f"    {label:<28} 평균={mean:.2f}초  P95={p95:.2f}초  (n={cnt})")

            # 환각률
            hal = report.llm.get("hallucination")
            if hal:
                mean_score = hal.get("mean_score", 0)
                print(f"\n    🔍 환각 검증 점수: 평균={mean_score:.1%} "
                      f"(min={hal.get('min_score', 0):.1%}, "
                      f"max={hal.get('max_score', 0):.1%}, "
                      f"n={hal.get('samples', 0)})")

        print("\n" + "=" * 65)

    def save_report(self, report: BenchmarkReport, path: str | Path):
        """벤치마크 리포트 JSON 저장"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"벤치마크 리포트 저장: {path}")
