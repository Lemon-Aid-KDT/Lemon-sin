"""``MultilingualOCRAdapter`` 단위 테스트 — 4가지 분기 검증.

Reference:
    backend/src/ocr/multilingual_adapter.py
"""

from __future__ import annotations

import pytest
from src.ocr.base import OCRAdapter, OCRImageInput, OCRResult
from src.ocr.exceptions import OCRApiError, OCRError
from src.ocr.multilingual_adapter import MultilingualOCRAdapter


class _FakeAdapter(OCRAdapter):
    """호출 횟수와 응답을 제어할 수 있는 테스트용 어댑터."""

    def __init__(
        self,
        engine: str = "fake",
        text: str = "ok",
        confidence: float = 0.9,
        raises: Exception | None = None,
    ) -> None:
        self._engine = engine
        self._text = text
        self._confidence = confidence
        self._raises = raises
        self.call_count = 0

    @property
    def engine_name(self) -> str:
        return self._engine

    async def extract_text(self, _image: OCRImageInput) -> OCRResult:
        self.call_count += 1
        if self._raises is not None:
            raise self._raises
        return OCRResult(text=self._text, confidence=self._confidence, provider=self._engine)


def _image_input() -> OCRImageInput:
    """Return a minimal validated OCR image input."""
    return OCRImageInput(
        image_bytes=b"image",
        mime_type="image/png",
        width=1,
        height=1,
    )


class TestEngineName:
    """engine_name 합성 검증."""

    def test_engine_name_combines_both(self) -> None:
        adapter = MultilingualOCRAdapter(
            primary=_FakeAdapter(engine="paddleocr_v3_korean"),
            secondary=_FakeAdapter(engine="paddleocr_v3_en"),
        )
        assert adapter.engine_name == "multi:paddleocr_v3_korean+paddleocr_v3_en"


class TestBothSucceed:
    """두 어댑터 모두 성공한 경우."""

    @pytest.mark.asyncio
    async def test_primary_higher_confidence_wins(self) -> None:
        """primary confidence 가 더 높으면 primary 결과 반환."""
        primary = _FakeAdapter(engine="ko", text="비타민 C", confidence=0.95)
        secondary = _FakeAdapter(engine="en", text="Vitamin C", confidence=0.70)
        adapter = MultilingualOCRAdapter(primary=primary, secondary=secondary)

        result = await adapter.extract_text(_image_input())

        assert result.text == "비타민 C"
        assert result.provider == "ko"
        assert primary.call_count == 1
        assert secondary.call_count == 1

    @pytest.mark.asyncio
    async def test_secondary_higher_confidence_wins(self) -> None:
        """secondary confidence 가 더 높으면 secondary 결과 반환."""
        primary = _FakeAdapter(engine="ko", text="비타민 C", confidence=0.40)
        secondary = _FakeAdapter(engine="en", text="Vitamin C", confidence=0.95)
        adapter = MultilingualOCRAdapter(primary=primary, secondary=secondary)

        result = await adapter.extract_text(_image_input())

        assert result.text == "Vitamin C"
        assert result.provider == "en"

    @pytest.mark.asyncio
    async def test_tie_breaks_toward_primary(self) -> None:
        """confidence 동률이면 primary 우선."""
        primary = _FakeAdapter(engine="ko", text="비타민", confidence=0.85)
        secondary = _FakeAdapter(engine="en", text="Vitamin", confidence=0.85)
        adapter = MultilingualOCRAdapter(primary=primary, secondary=secondary)

        result = await adapter.extract_text(_image_input())

        assert result.provider == "ko"


class TestOneSideFails:
    """한쪽 어댑터만 실패한 경우 — 성공한 쪽 결과 반환."""

    @pytest.mark.asyncio
    async def test_primary_fails_returns_secondary(self) -> None:
        primary = _FakeAdapter(engine="ko", raises=OCRApiError("ko", "boom"))
        secondary = _FakeAdapter(engine="en", text="Vitamin C", confidence=0.8)
        adapter = MultilingualOCRAdapter(primary=primary, secondary=secondary)

        result = await adapter.extract_text(_image_input())

        assert result.text == "Vitamin C"
        assert result.provider == "en"

    @pytest.mark.asyncio
    async def test_secondary_fails_returns_primary(self) -> None:
        primary = _FakeAdapter(engine="ko", text="비타민 C", confidence=0.8)
        secondary = _FakeAdapter(engine="en", raises=OCRApiError("en", "boom"))
        adapter = MultilingualOCRAdapter(primary=primary, secondary=secondary)

        result = await adapter.extract_text(_image_input())

        assert result.text == "비타민 C"
        assert result.provider == "ko"


class TestBothFail:
    """두 어댑터 모두 실패하면 예외 재발생."""

    @pytest.mark.asyncio
    async def test_both_fail_with_ocr_error_raises(self) -> None:
        primary = _FakeAdapter(engine="ko", raises=OCRApiError("ko", "boom"))
        secondary = _FakeAdapter(engine="en", raises=OCRApiError("en", "boom"))
        adapter = MultilingualOCRAdapter(primary=primary, secondary=secondary)

        with pytest.raises(OCRError):
            await adapter.extract_text(_image_input())

    @pytest.mark.asyncio
    async def test_both_fail_with_generic_exception_wraps_to_api_error(self) -> None:
        """OCRError 가 아닌 예외도 OCRApiError 로 래핑되어 발생."""
        primary = _FakeAdapter(engine="ko", raises=RuntimeError("unknown"))
        secondary = _FakeAdapter(engine="en", raises=RuntimeError("unknown"))
        adapter = MultilingualOCRAdapter(primary=primary, secondary=secondary)

        with pytest.raises(OCRApiError):
            await adapter.extract_text(_image_input())


class TestParallelExecution:
    """두 어댑터가 실제로 병렬 호출되는지 검증."""

    @pytest.mark.asyncio
    async def test_both_adapters_called_once(self) -> None:
        """단일 입력에 대해 각 어댑터가 정확히 1회씩 호출된다."""
        primary = _FakeAdapter(engine="ko", confidence=0.5)
        secondary = _FakeAdapter(engine="en", confidence=0.5)
        adapter = MultilingualOCRAdapter(primary=primary, secondary=secondary)

        await adapter.extract_text(_image_input())

        assert primary.call_count == 1
        assert secondary.call_count == 1
