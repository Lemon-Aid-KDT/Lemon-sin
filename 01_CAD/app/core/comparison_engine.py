"""Comparison Engine — 도면 비교 도구 통합.

AS-IS:
    pipeline.compare_dxf(path_a, path_b) → dict
    pipeline.compare_dimensions(id_a, id_b) → dict

TO-BE:
    engine.compare(CompareInput(left, right, mode=DXF_STRUCTURE))
    engine.compare(CompareInput(left, right, mode=DIMENSIONS))
    engine.compare(CompareInput(left, right, mode=VISUAL_DIFF))
    engine.compare(CompareInput(left, right, mode=METADATA))
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from core.models import CompareInput, CompareMode, CompareResult

if TYPE_CHECKING:
    from core.pipeline import DrawingPipeline


class ComparisonEngine:
    """통합 비교 엔진."""

    def __init__(self, pipeline: DrawingPipeline):
        self._pipeline = pipeline

    def compare(self, input: CompareInput) -> CompareResult:
        """통합 비교를 수행합니다.

        Args:
            input: CompareInput (left_record_id, right_record_id, mode)

        Returns:
            CompareResult
        """
        mode = input.mode

        if mode == CompareMode.DXF_STRUCTURE:
            return self._compare_dxf_structure(input)
        elif mode == CompareMode.DIMENSIONS:
            return self._compare_dimensions(input)
        elif mode == CompareMode.VISUAL_DIFF:
            return self._compare_visual(input)
        elif mode == CompareMode.METADATA:
            return self._compare_metadata(input)
        else:
            return CompareResult(
                mode=mode,
                similarity_score=0.0,
                summary=f"지원하지 않는 비교 모드: {mode.value}",
            )

    # ------------------------------------------------------------------
    # Mode implementations
    # ------------------------------------------------------------------

    def _compare_dxf_structure(self, input: CompareInput) -> CompareResult:
        """DXF 구조 비교 (기존 compare_dxf 래핑)."""
        # record_id에서 DXF 경로 해석
        left_dxf = self._resolve_dxf_path(input.left_record_id)
        right_dxf = self._resolve_dxf_path(input.right_record_id)

        if not left_dxf or not right_dxf:
            return CompareResult(
                mode=CompareMode.DXF_STRUCTURE,
                similarity_score=0.0,
                summary="DXF 파일 경로를 찾을 수 없습니다.",
            )

        try:
            from core.dxf_diff import compare_dxf

            diff_result = compare_dxf(left_dxf, right_dxf)

            # 유사도 계산
            total = (
                len(diff_result.matched)
                + len(diff_result.only_in_a)
                + len(diff_result.only_in_b)
            )
            similarity = len(diff_result.matched) / max(total, 1)

            return CompareResult(
                mode=CompareMode.DXF_STRUCTURE,
                similarity_score=similarity,
                summary=diff_result.summary.get("summary", ""),
                details={
                    "matched_count": len(diff_result.matched),
                    "only_in_a_count": len(diff_result.only_in_a),
                    "only_in_b_count": len(diff_result.only_in_b),
                    "layer_diff": diff_result.layer_diff,
                    "summary": diff_result.summary,
                },
            )
        except Exception as e:
            logger.error(f"DXF 구조 비교 실패: {e}")
            return CompareResult(
                mode=CompareMode.DXF_STRUCTURE,
                similarity_score=0.0,
                summary=f"비교 실패: {e}",
            )

    def _compare_dimensions(self, input: CompareInput) -> CompareResult:
        """치수 비교 (기존 compare_dimensions 래핑)."""
        try:
            result = self._pipeline.compare_dimensions(
                input.left_record_id, input.right_record_id,
            )

            if "error" in result:
                return CompareResult(
                    mode=CompareMode.DIMENSIONS,
                    similarity_score=0.0,
                    summary=result["error"],
                )

            similarity = result.get("similarity", 0.0)
            return CompareResult(
                mode=CompareMode.DIMENSIONS,
                similarity_score=similarity,
                summary=f"치수 유사도: {similarity:.1%}",
                details=result,
            )
        except Exception as e:
            logger.error(f"치수 비교 실패: {e}")
            return CompareResult(
                mode=CompareMode.DIMENSIONS,
                similarity_score=0.0,
                summary=f"비교 실패: {e}",
            )

    def _compare_visual(self, input: CompareInput) -> CompareResult:
        """시각적 비교 (이미지 유사도 — 신규 기능)."""
        try:
            from core.renderer import UniversalRenderer
            from core.models import RenderMode

            renderer = UniversalRenderer()

            # 양쪽 이미지 렌더링
            left_path = self._resolve_image_path(input.left_record_id)
            right_path = self._resolve_image_path(input.right_record_id)

            if not left_path or not right_path:
                return CompareResult(
                    mode=CompareMode.VISUAL_DIFF,
                    similarity_score=0.0,
                    summary="이미지 경로를 찾을 수 없습니다.",
                )

            left_render = renderer.render(left_path, RenderMode.FULL)
            right_render = renderer.render(right_path, RenderMode.FULL)

            if not left_render.png_path or not right_render.png_path:
                return CompareResult(
                    mode=CompareMode.VISUAL_DIFF,
                    similarity_score=0.0,
                    summary="렌더링에 실패했습니다.",
                )

            # 이미지 유사도 (SSIM)
            similarity = self._compute_ssim(
                left_render.png_path, right_render.png_path,
            )

            return CompareResult(
                mode=CompareMode.VISUAL_DIFF,
                similarity_score=similarity,
                summary=f"시각적 유사도: {similarity:.1%}",
                left_thumbnail=left_render.png_path,
                right_thumbnail=right_render.png_path,
            )
        except Exception as e:
            logger.error(f"시각적 비교 실패: {e}")
            return CompareResult(
                mode=CompareMode.VISUAL_DIFF,
                similarity_score=0.0,
                summary=f"비교 실패: {e}",
            )

    def _compare_metadata(self, input: CompareInput) -> CompareResult:
        """메타데이터 비교 (OCR 추출값 기반)."""
        rec_a = self._pipeline._records.get(input.left_record_id)
        rec_b = self._pipeline._records.get(input.right_record_id)

        if not rec_a or not rec_b:
            return CompareResult(
                mode=CompareMode.METADATA,
                similarity_score=0.0,
                summary="도면을 찾을 수 없습니다.",
            )

        # 메타데이터 필드 비교
        details = {}
        score_parts = []

        # 카테고리
        cat_match = rec_a.category == rec_b.category
        details["category_match"] = cat_match
        score_parts.append(1.0 if cat_match else 0.0)

        # 재질 겹침
        mats_a = set(rec_a.materials)
        mats_b = set(rec_b.materials)
        if mats_a or mats_b:
            mat_sim = len(mats_a & mats_b) / max(len(mats_a | mats_b), 1)
        else:
            mat_sim = 0.0
        details["material_similarity"] = mat_sim
        score_parts.append(mat_sim)

        # 치수 개수 비교
        dims_a = len(rec_a.dimensions)
        dims_b = len(rec_b.dimensions)
        if dims_a or dims_b:
            dim_ratio = min(dims_a, dims_b) / max(dims_a, dims_b, 1)
        else:
            dim_ratio = 0.0
        details["dimension_count_ratio"] = dim_ratio
        score_parts.append(dim_ratio)

        similarity = sum(score_parts) / max(len(score_parts), 1)

        return CompareResult(
            mode=CompareMode.METADATA,
            similarity_score=similarity,
            summary=f"메타데이터 유사도: {similarity:.1%}",
            details=details,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_dxf_path(self, record_id: str) -> str | None:
        """record_id에서 DXF 파일 경로를 찾습니다.

        record_id가 직접 파일 경로일 수도 있고, drawing_id일 수도 있습니다.
        """
        from pathlib import Path

        # 직접 DXF 경로인 경우
        if Path(record_id).suffix.lower() == ".dxf" and Path(record_id).exists():
            return record_id

        # drawing_id로 레코드 조회
        rec = self._pipeline._records.get(record_id)
        if rec and rec.dxf_path:
            return rec.dxf_path
        return None

    def _resolve_image_path(self, record_id: str) -> str | None:
        """record_id에서 이미지 파일 경로를 찾습니다."""
        from pathlib import Path

        if Path(record_id).suffix.lower() in {".png", ".jpg", ".jpeg"}:
            if Path(record_id).exists():
                return record_id

        rec = self._pipeline._records.get(record_id)
        if rec:
            fp = rec.file_path
            if Path(fp).exists():
                return fp
        return None

    @staticmethod
    def _compute_ssim(img_a: str, img_b: str) -> float:
        """두 이미지의 SSIM(Structural Similarity Index) 계산."""
        try:
            from PIL import Image
            import numpy as np

            a = np.array(Image.open(img_a).convert("L").resize((256, 256)))
            b = np.array(Image.open(img_b).convert("L").resize((256, 256)))

            # 간단한 SSIM 근사 (skimage 없이)
            mean_a, mean_b = a.mean(), b.mean()
            var_a, var_b = a.var(), b.var()
            cov_ab = ((a - mean_a) * (b - mean_b)).mean()

            c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
            ssim = (
                (2 * mean_a * mean_b + c1) * (2 * cov_ab + c2)
            ) / (
                (mean_a ** 2 + mean_b ** 2 + c1) * (var_a + var_b + c2)
            )
            return float(max(0.0, min(1.0, ssim)))
        except Exception:
            return 0.0
