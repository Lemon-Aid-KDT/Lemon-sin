"""Supplement image analysis orchestration service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import Self, cast
from uuid import uuid4

import pytest
from fastapi import UploadFile
from PIL import Image
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import Settings
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.supplement_parser import SupplementStructuredParseResult
from src.ocr.base import (
    OCRAdapter,
    OCRBlock,
    OCRBoundingPoly,
    OCRImageInput,
    OCRPage,
    OCRParagraph,
    OCRResult,
    OCRVertex,
    OCRWord,
)
from src.security.auth import AuthenticatedUser
from src.services.supplement_image_analysis import (
    OCR_VERIFICATION_MISMATCH_CODE,
    SupplementImageAnalysisAdapters,
    analyze_supplement_image,
)
from src.services.supplement_intake import supplement_analysis_run_to_preview
from src.vision.base import BoundingBox, VisionAdapter, VisionError
from starlette.datastructures import Headers


class _TransactionContext:
    """Async context manager used by the fake session transaction."""

    async def __aenter__(self) -> Self:
        """Enter the fake transaction.

        Returns:
            Context manager instance.
        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Exit the fake transaction.

        Args:
            *_exc_info: Exception information ignored by the fake context.

        Returns:
            None.
        """


class _FakePipelineSession:
    """Fake async session for image analysis orchestration tests."""

    def __init__(self) -> None:
        self.added_analysis: SupplementAnalysisRun | None = None
        self.committed = False
        self.refresh_count = 0

    def begin(self) -> _TransactionContext:
        """Return a fake transaction context.

        Returns:
            Fake transaction context.
        """
        return _TransactionContext()

    async def scalar(self, _statement: object) -> SupplementAnalysisRun | None:
        """Return the stored analysis row for parser lookup.

        Args:
            _statement: SQLAlchemy select statement.

        Returns:
            Stored analysis row.
        """
        return self.added_analysis

    def add(self, record: object) -> None:
        """Capture the ORM record being added.

        Args:
            record: ORM object passed by the service.

        Returns:
            None.
        """
        self.added_analysis = cast(SupplementAnalysisRun, record)

    async def refresh(self, record: object) -> None:
        """Populate server-generated fields after fake persistence.

        Args:
            record: ORM object to refresh.

        Returns:
            None.
        """
        supplement_run = cast(SupplementAnalysisRun, record)
        if getattr(supplement_run, "id", None) is None:
            supplement_run.id = uuid4()
        supplement_run.created_at = datetime.now(UTC)
        supplement_run.updated_at = datetime.now(UTC)
        self.refresh_count += 1

    async def commit(self) -> None:
        """Record a parser commit.

        Returns:
            None.
        """
        self.committed = True


class _FakeOCRAdapter(OCRAdapter):
    """Fake OCR adapter returning configured text."""

    def __init__(
        self,
        text: str,
        *,
        confidence: float | None = 0.88,
        pages: tuple[OCRPage, ...] = (),
    ) -> None:
        self.text = text
        self.confidence = confidence
        self.pages = pages
        self.received_image: OCRImageInput | None = None
        self.call_count = 0

    async def extract_text(self, image: OCRImageInput) -> OCRResult:
        """Capture image input and return fake OCR text.

        Args:
            image: OCR image input.

        Returns:
            Fake OCR result.
        """
        self.call_count += 1
        self.received_image = image
        return OCRResult(
            text=self.text,
            provider="fake-ocr",
            confidence=self.confidence,
            pages=self.pages,
        )


class _FakeVisionAdapter(VisionAdapter):
    """Fake vision adapter returning a configured ROI."""

    def __init__(self, region: BoundingBox | None = None, *, fail: bool = False) -> None:
        self.region = region or BoundingBox(
            x=0,
            y=0,
            width=2,
            height=2,
            confidence=0.9,
            label="supplement_label",
        )
        self.fail = fail
        self.call_count = 0

    async def detect_label_region(self, image_bytes: bytes) -> BoundingBox:
        """Capture detector calls and return or raise a fake ROI.

        Args:
            image_bytes: Validated image bytes.

        Returns:
            Configured ROI.

        Raises:
            VisionError: When configured to fail.
        """
        self.call_count += 1
        if self.fail:
            raise VisionError("fake detector failure")
        assert image_bytes
        return self.region


class _FakeMultimodalOCRAdapter(OCRAdapter):
    """Fake local vision LLM OCR fallback adapter."""

    def __init__(self, text: str = "비타민 D 1000") -> None:
        self.text = text
        self.received_image: OCRImageInput | None = None
        self.call_count = 0

    async def extract_text(self, image: OCRImageInput) -> OCRResult:
        """Capture fallback input and return configured candidate text.

        Args:
            image: OCR image input with optional ROI.

        Returns:
            Fake OCR-like result.
        """
        self.call_count += 1
        self.received_image = image
        return OCRResult(text=self.text, provider="ollama_vision_assist", confidence=None)


class _FakeParser:
    """Fake structured parser for OCR text."""

    def __init__(self, result: SupplementStructuredParseResult) -> None:
        self.result = result
        self.received_text: str | None = None

    async def parse_supplement_ocr_text(
        self,
        ocr_text: str,
    ) -> SupplementStructuredParseResult:
        """Capture OCR text and return a configured parser result.

        Args:
            ocr_text: OCR text passed by the service.

        Returns:
            Configured structured parse result.
        """
        self.received_text = ocr_text
        return self.result


def _settings() -> Settings:
    """Return service test settings.

    Returns:
        Settings object.
    """
    return Settings(privacy_hash_secret=SecretStr("test-privacy-secret"))


def _user() -> AuthenticatedUser:
    """Return an authenticated user fixture.

    Returns:
        Authenticated user model.
    """
    return AuthenticatedUser(
        subject="user_123",
        issuer="https://auth.example.com/",
        claims={"sub": "user_123"},
    )


def _png_bytes() -> bytes:
    """Return a tiny PNG image.

    Returns:
        PNG image bytes.
    """
    buffer = BytesIO()
    Image.new("RGB", (3, 2), color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _upload(data: bytes) -> UploadFile:
    """Build an UploadFile for service tests.

    Args:
        data: File bytes.

    Returns:
        UploadFile object.
    """
    return UploadFile(
        file=BytesIO(data),
        filename="label.png",
        headers=Headers({"content-type": "image/png"}),
    )


def _parse_result() -> SupplementStructuredParseResult:
    """Return a valid structured parser result.

    Returns:
        Structured supplement parse result fixture.
    """
    return SupplementStructuredParseResult.model_validate(
        {
            "parsed_product": {"product_name": "비타민 D 1000"},
            "ingredient_candidates": [
                {
                    "display_name": "비타민 D",
                    "amount": 25,
                    "unit": "ug",
                    "confidence": 0.91,
                }
            ],
            "low_confidence_fields": [],
            "warnings": [],
        }
    )


def _ocr_page() -> OCRPage:
    """Return coordinate-bearing OCR words for deterministic layout parsing."""
    words = (
        _ocr_word("Supplement", 10, 10, 110, 40, 0, 0.92),
        _ocr_word("Facts", 120, 10, 190, 40, 1, 0.91),
        _ocr_word("Vitamin", 10, 50, 90, 80, 2, 0.9),
        _ocr_word("D", 100, 50, 115, 80, 3, 0.9),
        _ocr_word("25", 170, 50, 200, 80, 4, 0.88),
        _ocr_word("ug", 205, 50, 230, 80, 5, 0.88),
        _ocr_word("섭취방법", 10, 100, 90, 130, 6, 0.87),
        _ocr_word("1일", 110, 100, 145, 130, 7, 0.86),
        _ocr_word("1정", 155, 100, 190, 130, 8, 0.86),
    )
    paragraph = OCRParagraph(
        text=" ".join(word.text for word in words),
        confidence=0.89,
        bounding_box=None,
        words=words,
    )
    block = OCRBlock(
        text=paragraph.text,
        confidence=0.89,
        bounding_box=None,
        block_type="TEXT",
        paragraphs=(paragraph,),
    )
    return OCRPage(width=300, height=200, confidence=0.89, blocks=(block,))


def _ocr_word(
    text: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
    word_index: int,
    confidence: float,
) -> OCRWord:
    """Return one OCR word with a rectangular bounding polygon."""
    return OCRWord(
        text=text,
        confidence=confidence,
        bounding_box=OCRBoundingPoly(
            vertices=(
                OCRVertex(x=left, y=top),
                OCRVertex(x=right, y=top),
                OCRVertex(x=right, y=bottom),
                OCRVertex(x=left, y=bottom),
            )
        ),
        block_index=0,
        paragraph_index=0,
        word_index=word_index,
    )


@pytest.mark.asyncio
async def test_analyze_supplement_image_defaults_to_intake_only() -> None:
    """Verify the orchestration service preserves the existing intake-only behavior."""
    fake_session = _FakePipelineSession()

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        "client-1",
        _settings(),
    )

    assert result.parser_used is False
    assert result.ocr_result is None
    assert result.vision_region is None
    assert result.record.ocr_text_hash is None
    assert result.record.algorithm_version == "supplement-intake-v1.0.0"
    preview = supplement_analysis_run_to_preview(result.record)
    assert preview.pipeline_metadata.ocr_provider == "intake-only"
    assert preview.pipeline_metadata.image_count == 1
    assert preview.pipeline_metadata.image_role == "unknown"
    assert preview.pipeline_metadata.ocr_text_present is False
    assert preview.pipeline_metadata.ocr_confidence_bucket == "none"
    assert preview.pipeline_metadata.vision_roi_used is False
    assert preview.pipeline_metadata.roi_count == 0
    assert preview.pipeline_metadata.section_count == 0
    assert preview.pipeline_metadata.llm_parser_used is False
    assert preview.pipeline_metadata.parser_contract_version is None
    assert preview.pipeline_metadata.missing_required_sections == [
        "supplement_facts",
        "intake_method",
    ]
    assert fake_session.committed is False


@pytest.mark.asyncio
async def test_analyze_supplement_image_runs_ocr_then_parser_when_adapter_supplied() -> None:
    """Verify an injected OCR adapter can feed the existing structured parser service."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter(" 비타민 D 1000\n비타민 D 25 ug ")
    fake_parser = _FakeParser(_parse_result())

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        _settings(),
        adapters=SupplementImageAnalysisAdapters(ocr=fake_ocr, parser=fake_parser),
    )

    assert result.parser_used is True
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "fake-ocr"
    assert fake_ocr.received_image is not None
    assert fake_ocr.received_image.mime_type == "image/png"
    assert fake_parser.received_text == "비타민 D 1000\n비타민 D 25 μg"
    assert result.record.ocr_provider == "fake-ocr"
    assert result.record.parsed_snapshot["parsed_product"]["product_name"] == "비타민 D 1000"
    assert result.record.parsed_snapshot["parser_metadata"]["raw_ocr_text_stored"] is False
    preview = supplement_analysis_run_to_preview(result.record)
    assert preview.pipeline_metadata.ocr_provider == "fake-ocr"
    assert preview.pipeline_metadata.ocr_text_present is True
    assert preview.pipeline_metadata.ocr_confidence_bucket == "medium"
    assert preview.pipeline_metadata.llm_parser_used is True
    assert preview.pipeline_metadata.parser_contract_version == result.record.algorithm_version
    assert preview.pipeline_metadata.missing_required_sections == ["intake_method"]
    assert fake_session.committed is True


@pytest.mark.asyncio
async def test_analyze_supplement_image_promotes_ocr_layout_to_preview_sections() -> None:
    """Verify OCR coordinates become reviewable section evidence in the preview."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter(
        "Supplement Facts\nVitamin D 25 ug\n섭취방법 1일 1정",
        pages=(_ocr_page(),),
    )
    fake_parser = _FakeParser(_parse_result())

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        _settings(),
        adapters=SupplementImageAnalysisAdapters(ocr=fake_ocr, parser=fake_parser),
    )

    preview = supplement_analysis_run_to_preview(result.record)
    assert preview.layout_available is True
    assert [section.section_type for section in preview.label_sections] == [
        "supplement_facts",
        "intake_method",
    ]
    assert preview.evidence_spans[-1].source_type == "ocr_layout"
    assert preview.pipeline_metadata.section_count == 2
    assert preview.pipeline_metadata.missing_required_sections == []


@pytest.mark.asyncio
async def test_analyze_supplement_image_passes_yolo_roi_to_ocr_when_enabled() -> None:
    """Verify YOLO ROI metadata is used only as OCR input preprocessing metadata."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("비타민 D 1000")
    fake_parser = _FakeParser(_parse_result())
    region = BoundingBox(
        x=1,
        y=0,
        width=2,
        height=2,
        confidence=0.92,
        label="supplement_label",
        model="local-supplement-roi.pt",
    )
    fake_vision = _FakeVisionAdapter(region)

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        Settings(
            privacy_hash_secret=SecretStr("test-privacy-secret"),
            enable_vision_classifier=True,
        ),
        adapters=SupplementImageAnalysisAdapters(
            ocr=fake_ocr,
            parser=fake_parser,
            vision=fake_vision,
        ),
    )

    assert result.vision_region == region
    assert result.vision_regions == (region,)
    assert fake_vision.call_count == 1
    assert fake_ocr.received_image is not None
    assert fake_ocr.received_image.label_region == region
    assert result.record.parsed_snapshot["pipeline_metadata"]["vision_roi_used"] is True
    assert result.record.parsed_snapshot["detected_product_regions"][0]["label"] == (
        "supplement_label"
    )
    assert result.record.parsed_snapshot["detected_product_regions"][0]["selected"] is True
    preview = supplement_analysis_run_to_preview(result.record)
    assert preview.pipeline_metadata.vision_roi_used is True
    assert preview.pipeline_metadata.roi_count == 1
    assert preview.detected_product_regions[0].selected is True
    assert preview.selected_region_id == "vision-1"
    assert preview.pipeline_metadata.ocr_provider == "fake-ocr"
    assert result.parser_used is True


@pytest.mark.asyncio
async def test_analyze_supplement_image_crops_primary_ocr_input_when_policy_enabled() -> None:
    """Verify ROI crop policy sends cropped image bytes to primary OCR."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("비타민 D 1000")
    fake_parser = _FakeParser(_parse_result())
    region = BoundingBox(
        x=1,
        y=0,
        width=2,
        height=2,
        confidence=0.92,
        label="supplement_label",
    )

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        Settings(
            privacy_hash_secret=SecretStr("test-privacy-secret"),
            enable_vision_classifier=True,
            ocr_roi_preprocessing_policy="crop_before_primary",
        ),
        adapters=SupplementImageAnalysisAdapters(
            ocr=fake_ocr,
            parser=fake_parser,
            vision=_FakeVisionAdapter(region),
        ),
    )

    assert result.vision_region == region
    assert fake_ocr.received_image is not None
    assert fake_ocr.received_image.label_region is None
    assert fake_ocr.received_image.mime_type == "image/png"
    assert fake_ocr.received_image.width == 2
    assert fake_ocr.received_image.height == 2
    assert fake_parser.received_text == "비타민 D 1000"


@pytest.mark.asyncio
async def test_analyze_supplement_image_falls_back_to_full_image_ocr_when_vision_fails() -> None:
    """Verify ROI detection failure does not block the OCR-first path."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("비타민 D 1000")
    fake_parser = _FakeParser(_parse_result())
    fake_vision = _FakeVisionAdapter(fail=True)

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        Settings(
            privacy_hash_secret=SecretStr("test-privacy-secret"),
            enable_vision_classifier=True,
        ),
        adapters=SupplementImageAnalysisAdapters(
            ocr=fake_ocr,
            parser=fake_parser,
            vision=fake_vision,
        ),
    )

    assert result.vision_region is None
    assert fake_ocr.received_image is not None
    assert fake_ocr.received_image.label_region is None
    assert result.parser_used is True


@pytest.mark.asyncio
async def test_analyze_supplement_image_does_not_call_multimodal_when_ocr_is_usable() -> None:
    """Verify multimodal assist is not a primary path when OCR succeeds."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("비타민 D 1000", confidence=0.88)
    fake_multimodal = _FakeMultimodalOCRAdapter()
    fake_parser = _FakeParser(_parse_result())

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        Settings(
            privacy_hash_secret=SecretStr("test-privacy-secret"),
            enable_multimodal_llm=True,
            multimodal_ocr_assist_policy="low_confidence",
        ),
        adapters=SupplementImageAnalysisAdapters(
            ocr=fake_ocr,
            parser=fake_parser,
            multimodal_ocr=fake_multimodal,
        ),
    )

    assert result.ocr_result is not None
    assert result.ocr_result.provider == "fake-ocr"
    assert fake_multimodal.call_count == 0
    assert fake_parser.received_text == "비타민 D 1000"


@pytest.mark.asyncio
async def test_analyze_supplement_image_calls_multimodal_when_ocr_is_empty() -> None:
    """Verify multimodal assist can provide visible-text candidates after OCR failure."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("", confidence=None)
    fake_multimodal = _FakeMultimodalOCRAdapter("비타민 D 1000\n비타민 D 25 ug")
    fake_parser = _FakeParser(_parse_result())

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        Settings(
            privacy_hash_secret=SecretStr("test-privacy-secret"),
            enable_multimodal_llm=True,
            multimodal_ocr_assist_policy="ocr_empty_only",
        ),
        adapters=SupplementImageAnalysisAdapters(
            ocr=fake_ocr,
            parser=fake_parser,
            multimodal_ocr=fake_multimodal,
        ),
    )

    assert fake_ocr.call_count == 1
    assert fake_multimodal.call_count == 1
    assert fake_parser.received_text == "비타민 D 1000\n비타민 D 25 μg"
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "ollama_vision_assist"
    assert result.record.parsed_snapshot["parser_metadata"]["input_provider"] == (
        "ollama_vision_assist"
    )


@pytest.mark.asyncio
async def test_analyze_supplement_image_calls_multimodal_when_ocr_is_low_confidence() -> None:
    """Verify low OCR confidence can trigger the configured vision assist fallback."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("흐린 텍스트", confidence=0.70)
    fake_multimodal = _FakeMultimodalOCRAdapter("비타민 D 1000")
    fake_parser = _FakeParser(_parse_result())

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        Settings(
            privacy_hash_secret=SecretStr("test-privacy-secret"),
            enable_multimodal_llm=True,
            multimodal_ocr_assist_policy="low_confidence",
        ),
        adapters=SupplementImageAnalysisAdapters(
            ocr=fake_ocr,
            parser=fake_parser,
            multimodal_ocr=fake_multimodal,
        ),
    )

    assert fake_multimodal.call_count == 1
    assert fake_parser.received_text == "비타민 D 1000"
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "ollama_vision_assist"


@pytest.mark.asyncio
async def test_analyze_supplement_image_calls_secondary_fallback_after_low_confidence_ocr() -> None:
    """Verify optional secondary OCR providers can recover weak primary OCR."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("흐린 텍스트", confidence=0.70)
    fallback_ocr = _FakeOCRAdapter("비타민 D 1000", confidence=0.83)
    fake_parser = _FakeParser(_parse_result())

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        _settings(),
        adapters=SupplementImageAnalysisAdapters(
            ocr=fake_ocr,
            parser=fake_parser,
            fallback_ocr_adapters=(fallback_ocr,),
        ),
    )

    assert fake_ocr.call_count == 1
    assert fallback_ocr.call_count == 1
    assert fake_parser.received_text == "비타민 D 1000"
    assert result.ocr_result is not None
    assert result.ocr_result.confidence == 0.83


@pytest.mark.asyncio
async def test_analyze_supplement_image_records_multimodal_verification_mismatch() -> None:
    """Verify local vision verification can mark mismatched accepted OCR text."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("비타민 D 1000", confidence=0.91)
    fake_multimodal = _FakeMultimodalOCRAdapter("마그네슘 400")
    fake_parser = _FakeParser(_parse_result())

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        Settings(
            privacy_hash_secret=SecretStr("test-privacy-secret"),
            enable_multimodal_llm=True,
            enable_multimodal_verification=True,
            multimodal_verification_sample_rate=1.0,
            multimodal_verification_threshold=0.95,
        ),
        adapters=SupplementImageAnalysisAdapters(
            ocr=fake_ocr,
            parser=fake_parser,
            multimodal_ocr=fake_multimodal,
        ),
    )

    assert fake_multimodal.call_count == 1
    assert fake_parser.received_text == "비타민 D 1000"
    assert OCR_VERIFICATION_MISMATCH_CODE in result.ocr_warning_codes
    assert result.record.warnings
