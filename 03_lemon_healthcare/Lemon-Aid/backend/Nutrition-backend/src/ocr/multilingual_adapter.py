"""MultilingualOCRAdapter — 두 ``OCRAdapter`` 인스턴스를 동시 호출해 confidence 높은 결과를 선택.

Brand-New-update OCR 95% 목표용 어댑터.

전제:
    한국어 라벨과 영어 라벨이 섞여 들어오는 환경에서, 단일 언어 PaddleOCR
    모델은 다른 언어 텍스트의 신뢰도가 낮다. 두 모델을 동시 가동해 더 자신
    있는 쪽을 채택하면 정확도가 향상된다.

비용:
    메모리: 두 PaddleOCR 인스턴스를 보유 (약 1GB × 2 ≈ 2GB).
    레이턴시: ``asyncio.gather`` 로 병렬 실행 → 최대 어댑터 latency ≈ wall-clock.

선택 규칙:
    1. 두 어댑터를 ``asyncio.gather(..., return_exceptions=True)`` 로 호출.
    2. 둘 다 성공: confidence 높은 쪽 반환. 동률이면 ``primary`` 우선.
    3. 한쪽 실패: 성공한 쪽 반환.
    4. 둘 다 실패: primary 의 ``OCRApiError`` 를 재발생.

Reference:
    docs/dev-guides/07-ocr-pipeline.md §7
    backend/src/ocr/pipeline.py (별도 fallback 슬롯; multi 는 그 안에서 사용 가능)
"""

from __future__ import annotations

import asyncio
import logging

from src.ocr.base import OCRAdapter, OCRResult
from src.ocr.exceptions import OCRApiError, OCRError

logger = logging.getLogger(__name__)


class MultilingualOCRAdapter(OCRAdapter):
    """두 OCR 어댑터를 동시 호출해 confidence 높은 결과를 반환하는 어댑터.

    Attributes:
        primary: 첫 번째 어댑터 (예: PaddleOCR ``lang="korean"``).
        secondary: 두 번째 어댑터 (예: PaddleOCR ``lang="en"``).

    Examples:
        >>> from src.ocr.paddleocr_adapter import PaddleOCRAdapter
        >>> ko = PaddleOCRAdapter(lang="korean")
        >>> en = PaddleOCRAdapter(lang="en")
        >>> multi = MultilingualOCRAdapter(primary=ko, secondary=en)
        >>> result = await multi.extract_text(image_bytes)
    """

    def __init__(self, primary: OCRAdapter, secondary: OCRAdapter) -> None:
        """두 어댑터를 받아 멀티링구얼 채널을 구성.

        Args:
            primary: 1순위 어댑터. 두 결과 confidence 동률 시 이 결과를 채택.
            secondary: 2순위 어댑터.
        """
        self._primary = primary
        self._secondary = secondary

    @property
    def engine_name(self) -> str:
        """``"multi:<primary>+<secondary>"`` 형식."""
        return f"multi:{self._primary.engine_name}+{self._secondary.engine_name}"

    async def extract_text(self, image_bytes: bytes) -> OCRResult:
        """두 어댑터를 병렬 호출 후 confidence 높은 결과를 반환.

        Args:
            image_bytes: 전처리된 이미지 바이트.

        Returns:
            confidence 가 더 높은 어댑터의 ``OCRResult``. engine 필드는 선택된
            쪽 원본 그대로 유지된다 (downstream 분석에서 어떤 모델이 채택되었는지
            추적 가능).

        Raises:
            OCRError: 두 어댑터가 모두 실패한 경우.
        """
        primary_task = asyncio.create_task(self._primary.extract_text(image_bytes))
        secondary_task = asyncio.create_task(self._secondary.extract_text(image_bytes))

        primary_result, secondary_result = await asyncio.gather(
            primary_task,
            secondary_task,
            return_exceptions=True,
        )

        primary_ok = isinstance(primary_result, OCRResult)
        secondary_ok = isinstance(secondary_result, OCRResult)

        if primary_ok and secondary_ok:
            chosen = self._pick_higher_confidence(primary_result, secondary_result)
            logger.info(
                "Multilingual OCR completed",
                extra={
                    "chosen_engine": chosen.engine,
                    "primary_confidence": primary_result.confidence,
                    "secondary_confidence": secondary_result.confidence,
                },
            )
            return chosen

        if primary_ok and not secondary_ok:
            assert isinstance(secondary_result, BaseException)
            logger.warning(
                "Secondary OCR failed, falling back to primary",
                extra={"error": str(secondary_result)},
            )
            return primary_result

        if secondary_ok and not primary_ok:
            assert isinstance(primary_result, BaseException)
            logger.warning(
                "Primary OCR failed, falling back to secondary",
                extra={"error": str(primary_result)},
            )
            return secondary_result

        # 둘 다 실패
        assert isinstance(primary_result, BaseException)
        assert isinstance(secondary_result, BaseException)
        logger.error(
            "Both OCR adapters failed",
            extra={
                "primary_error": str(primary_result),
                "secondary_error": str(secondary_result),
            },
        )
        # primary 의 예외를 재발생; OCRApiError 면 그대로, 아니면 OCRError 로 래핑
        if isinstance(primary_result, OCRError):
            raise primary_result
        raise OCRApiError(self._primary.engine_name, str(primary_result))

    @staticmethod
    def _pick_higher_confidence(a: OCRResult, b: OCRResult) -> OCRResult:
        """두 결과 중 confidence 가 높은 쪽 반환. 동률이면 첫 번째(primary) 채택.

        Args:
            a: primary 결과.
            b: secondary 결과.

        Returns:
            confidence 가 높은 쪽. 동률이면 ``a``.
        """
        if b.confidence > a.confidence:
            return b
        return a
