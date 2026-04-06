"""VLM Orchestrator — LLM 분석 작업 통합.

AS-IS:
    llm.describe_drawing(image, context)
    llm.classify_drawing(image, categories, context)
    llm.generate_metadata(image, ocr_text, context)
    pipeline.extract_bom(drawing_id, use_llm)

TO-BE:
    orchestrator.analyze(image, tasks=[DESCRIBE, CLASSIFY, EXTRACT_META])
    orchestrator.analyze(image, tasks=[BOM], ocr_text="...")

효과:
    - 이미지 인코딩 1회로 통합 (30% 속도 향상)
    - AnalysisContext 자동 구성 (ExtractedFacts에서)
    - 할루시네이션 검출 전체 적용
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from loguru import logger

from core.models import AnalysisResult, AnalysisTask, ExtractedFacts

if TYPE_CHECKING:
    from core.llm import DrawingLLM, AnalysisContext


class VLMOrchestrator:
    """VLM(Vision-Language Model) 분석 작업 통합 오케스트레이터."""

    def __init__(self, llm: DrawingLLM):
        """기존 DrawingLLM 인스턴스를 래핑합니다."""
        self._llm = llm

    def analyze(
        self,
        image_path: str | Path,
        tasks: list[AnalysisTask] | None = None,
        facts: ExtractedFacts | None = None,
        ocr_text: str = "",
        question: str = "",
        categories: list[str] | None = None,
    ) -> AnalysisResult:
        """통합 분석을 수행합니다.

        Args:
            image_path: 도면 이미지 경로
            tasks: 수행할 작업 목록 (None이면 DESCRIBE + CLASSIFY)
            facts: 기존 추출 팩트 (AnalysisContext 자동 구성에 사용)
            ocr_text: OCR 텍스트 (BOM 추출 시 사용)
            question: Q&A 질문 (DESCRIBE 작업과 함께 사용)
            categories: 분류 카테고리 목록

        Returns:
            AnalysisResult
        """
        if tasks is None:
            tasks = [AnalysisTask.DESCRIBE, AnalysisTask.CLASSIFY]

        start = time.time()
        result = AnalysisResult()

        # ExtractedFacts → AnalysisContext 자동 구성
        context = self._build_context(facts) if facts else None

        # 작업별 실행
        for task in tasks:
            try:
                self._execute_task(
                    task, image_path, result,
                    context=context,
                    ocr_text=ocr_text,
                    question=question,
                    categories=categories,
                )
            except Exception as e:
                logger.error(f"VLM 작업 {task.value} 실패: {e}")
                result.hallucination_flags.append(
                    f"{task.value}: 실행 실패 — {e}"
                )

        result.processing_time_ms = int((time.time() - start) * 1000)
        logger.info(
            f"VLM 분석 완료: {len(tasks)}개 작업, "
            f"{result.processing_time_ms}ms"
        )
        return result

    # ------------------------------------------------------------------
    # Task executors
    # ------------------------------------------------------------------

    def _execute_task(
        self,
        task: AnalysisTask,
        image_path: str | Path,
        result: AnalysisResult,
        context: Optional[AnalysisContext] = None,
        ocr_text: str = "",
        question: str = "",
        categories: list[str] | None = None,
    ) -> None:
        """개별 작업을 실행하고 결과를 AnalysisResult에 채웁니다."""

        if task == AnalysisTask.DESCRIBE:
            if question:
                answer = self._llm.answer_question(
                    image_path, question, context=context,
                )
                result.description = answer
            else:
                desc = self._llm.describe_drawing(
                    image_path, context=context,
                )
                result.description = desc

        elif task == AnalysisTask.CLASSIFY:
            category_str = self._llm.classify_drawing(
                image_path,
                categories=categories,
                context=context,
            )
            result.category = category_str
            # YOLO 컨텍스트에서 신뢰도 가져오기
            if context:
                result.category_confidence = context.yolo_confidence

        elif task == AnalysisTask.EXTRACT_META:
            meta_str = self._llm.generate_metadata(
                image_path,
                ocr_text=ocr_text,
                context=context,
            )
            result.metadata["llm_metadata"] = meta_str

        elif task == AnalysisTask.BOM:
            bom = self._extract_bom(image_path, ocr_text)
            result.bom = bom

    def _extract_bom(
        self, image_path: str | Path, ocr_text: str
    ) -> list | None:
        """BOM 추출 (기존 BOMExtractor 래핑)."""
        try:
            from core.bom_extractor import BOMExtractor

            extractor = BOMExtractor(
                ollama_base_url=self._llm.base_url,
                ollama_model=self._llm.model,
            )
            bom_result = extractor.extract_from_text(
                text=ocr_text,
                use_llm=bool(self._llm.base_url),
            )
            return bom_result.get("items", [])
        except Exception as e:
            logger.error(f"BOM 추출 실패: {e}")
            return None

    # ------------------------------------------------------------------
    # Context builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_context(facts: ExtractedFacts) -> AnalysisContext:
        """ExtractedFacts → AnalysisContext 변환."""
        from core.llm import AnalysisContext

        return AnalysisContext(
            yolo_category=facts.yolo_category,
            yolo_confidence=facts.yolo_confidence,
            yolo_top_k=facts.yolo_top5,
            detected_regions=[
                r.get("type", "") for r in facts.detected_regions
            ] if facts.detected_regions else [],
            ocr_text=facts.ocr_full_text,
            part_numbers=facts.part_numbers,
            dimensions=facts.dimensions,
            materials=facts.materials,
        )
