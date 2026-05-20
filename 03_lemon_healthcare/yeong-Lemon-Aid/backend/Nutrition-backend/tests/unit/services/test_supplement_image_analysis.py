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
from src.learning.object_storage import (
    LearningImageObjectInput,
    LearningImageObjectStore,
    StoredLearningImage,
)
from src.models.db.learning import LearningImageObject
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.privacy import ConsentType
from src.models.schemas.supplement_parser import SupplementStructuredParseResult
from src.ocr.base import (
    OCRAdapter,
    OCRBlock,
    OCRBoundingPoly,
    OCRError,
    OCRImageInput,
    OCRPage,
    OCRParagraph,
    OCRResult,
    OCRVertex,
    OCRWord,
)
from src.security.auth import AuthenticatedUser
from src.services.supplement_image_analysis import (
    OCR_ROI_CROP_UNAVAILABLE_CODE,
    OCR_VERIFICATION_MISMATCH_CODE,
    SupplementImageAnalysisAdapters,
    analyze_supplement_image,
)
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
        self.added_learning_image: LearningImageObject | None = None
        self.committed = False
        self.refresh_count = 0

    def begin(self) -> _TransactionContext:
        """Return a fake transaction context.

        Returns:
            Fake transaction context.
        """
        return _TransactionContext()

    async def scalar(self, statement: object) -> object | None:
        """Return fake rows for idempotency, parser, and learning-object lookups.

        Args:
            statement: SQLAlchemy select statement.

        Returns:
            Stored analysis row, or None for learning-object lookups.
        """
        if "learning_image_objects" in str(statement):
            return None
        return self.added_analysis

    def add(self, record: object) -> None:
        """Capture the ORM record being added.

        Args:
            record: ORM object passed by the service.

        Returns:
            None.
        """
        if isinstance(record, LearningImageObject):
            self.added_learning_image = record
            return
        self.added_analysis = cast(SupplementAnalysisRun, record)

    async def refresh(self, record: object) -> None:
        """Populate server-generated fields after fake persistence.

        Args:
            record: ORM object to refresh.

        Returns:
            None.
        """
        if isinstance(record, LearningImageObject):
            if getattr(record, "id", None) is None:
                record.id = uuid4()
            return
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

    async def rollback(self) -> None:
        """Provide rollback support for learning storage error paths.

        Returns:
            None.
        """


class _FakeOCRAdapter(OCRAdapter):
    """Fake OCR adapter returning configured text."""

    def __init__(
        self,
        text: str,
        *,
        confidence: float | None = 0.88,
        provider: str = "fake-ocr",
        pages: tuple[OCRPage, ...] = (),
        fail: bool = False,
    ) -> None:
        self.text = text
        self.confidence = confidence
        self.provider = provider
        self.pages = pages
        self.fail = fail
        self.received_image: OCRImageInput | None = None
        self.call_count = 0

    async def extract_text(self, image: OCRImageInput) -> OCRResult:
        """Capture image input and return fake OCR text.

        Args:
            image: OCR image input.

        Returns:
            Fake OCR result.

        Raises:
            OCRError: When the adapter is configured to fail.
        """
        self.call_count += 1
        self.received_image = image
        if self.fail:
            raise OCRError("fake ocr failure")
        return OCRResult(
            text=self.text,
            provider=self.provider,
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


class _FakeVisionCandidatesAdapter(VisionAdapter):
    """Fake vision adapter returning multiple ROI candidates."""

    def __init__(self, regions: tuple[BoundingBox, ...]) -> None:
        self.regions = regions
        self.call_count = 0

    async def detect_label_region(self, image_bytes: bytes) -> BoundingBox:
        """Return the highest-priority ROI from configured candidates.

        Args:
            image_bytes: Validated image bytes.

        Returns:
            First configured ROI.

        Raises:
            VisionError: When no candidates are configured.
        """
        regions = await self.detect_label_regions(image_bytes)
        if not regions:
            raise VisionError("no candidate regions")
        return regions[0]

    async def detect_label_regions(self, image_bytes: bytes) -> tuple[BoundingBox, ...]:
        """Return all configured candidates.

        Args:
            image_bytes: Validated image bytes.

        Returns:
            Candidate ROIs.
        """
        self.call_count += 1
        assert image_bytes
        return self.regions


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


class _FakeLearningImageObjectStore(LearningImageObjectStore):
    """Fake object store that captures consent-gated learning image bytes."""

    def __init__(self) -> None:
        self.payload: LearningImageObjectInput | None = None
        self.deleted_uri: str | None = None

    async def put_image(self, payload: LearningImageObjectInput) -> StoredLearningImage:
        """Capture a retained learning image payload.

        Args:
            payload: Image object payload from the learning pipeline.

        Returns:
            Fake stored object reference.
        """
        self.payload = payload
        return StoredLearningImage(object_uri="local://fake-learning-image", provider="local")

    async def get_image(self, object_uri: str, version_id: str | None = None) -> bytes:
        """Return the captured image bytes.

        Args:
            object_uri: Object URI ignored by the fake.
            version_id: Optional version ignored by the fake.

        Returns:
            Captured image bytes.

        Raises:
            AssertionError: If no payload was stored.
        """
        _ = (object_uri, version_id)
        assert self.payload is not None
        return self.payload.image_bytes

    async def delete_image(self, object_uri: str, version_id: str | None = None) -> None:
        """Capture delete calls for rollback tests.

        Args:
            object_uri: Object URI to delete.
            version_id: Optional version ignored by the fake.

        Returns:
            None.
        """
        _ = version_id
        self.deleted_uri = object_uri


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


def _png_bytes(
    *,
    width: int = 3,
    height: int = 2,
    color: tuple[int, int, int] = (255, 255, 255),
) -> bytes:
    """Return a tiny PNG image.

    Returns:
        PNG image bytes.
    """
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=color).save(buffer, format="PNG")
    return buffer.getvalue()


def _jpeg_with_exif_bytes() -> bytes:
    """Return a tiny JPEG containing client EXIF metadata.

    Returns:
        JPEG image bytes with EXIF tags.
    """
    buffer = BytesIO()
    exif = Image.Exif()
    exif[0x010E] = "client-supplied-label-description"
    exif[0x0110] = "client-camera-model"
    Image.new("RGB", (4, 3), color=(255, 255, 255)).save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def _word(
    text: str,
    left: float,
    top: float,
    right: float,
    bottom: float,
    *,
    confidence: float | None = 0.9,
    word_index: int = 0,
) -> OCRWord:
    """Build an OCR word with a rectangular bounding polygon.

    Args:
        text: OCR word text.
        left: Left coordinate.
        top: Top coordinate.
        right: Right coordinate.
        bottom: Bottom coordinate.
        confidence: Optional OCR word confidence.
        word_index: Word index inside a paragraph.

    Returns:
        OCR word fixture.
    """
    return OCRWord(
        text=text,
        confidence=confidence,
        bounding_box=OCRBoundingPoly(
            vertices=(
                OCRVertex(left, top),
                OCRVertex(right, top),
                OCRVertex(right, bottom),
                OCRVertex(left, bottom),
            )
        ),
        block_index=0,
        paragraph_index=0,
        word_index=word_index,
    )


def _ocr_pages(words: tuple[OCRWord, ...]) -> tuple[OCRPage, ...]:
    """Build normalized OCR pages for layout-aware tests.

    Args:
        words: OCR words.

    Returns:
        OCR page tuple.
    """
    return (
        OCRPage(
            width=400,
            height=260,
            confidence=0.9,
            blocks=(
                OCRBlock(
                    text=" ".join(word.text for word in words),
                    confidence=0.9,
                    bounding_box=None,
                    block_type="TEXT",
                    paragraphs=(
                        OCRParagraph(
                            text=" ".join(word.text for word in words),
                            confidence=0.9,
                            bounding_box=None,
                            words=words,
                        ),
                    ),
                ),
            ),
        ),
    )


def _upload(data: bytes, content_type: str = "image/png") -> UploadFile:
    """Build an UploadFile for service tests.

    Args:
        data: File bytes.
        content_type: Declared image MIME type.

    Returns:
        UploadFile object.
    """
    return UploadFile(
        file=BytesIO(data),
        filename="label.png",
        headers=Headers({"content-type": content_type}),
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
    assert result.image_quality_report is None
    assert result.record.ocr_text_hash is None
    assert result.record.algorithm_version == "supplement-intake-v1.0.0"
    assert fake_session.committed is True


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
    assert fake_parser.received_text == "비타민 D 1000\n비타민 D 25 ug"
    assert result.record.ocr_provider == "fake-ocr"
    assert result.record.parsed_snapshot["product"]["product_name"] == "비타민 D 1000"
    assert result.record.parsed_snapshot["source"]["raw_ocr_text_stored"] is False
    assert fake_session.committed is True


@pytest.mark.asyncio
async def test_analyze_supplement_image_uses_sanitized_bytes_for_ocr_and_learning() -> None:
    """Verify EXIF metadata is stripped before OCR and learning object storage."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("비타민 D 1000")
    fake_learning_store = _FakeLearningImageObjectStore()
    data = _jpeg_with_exif_bytes()
    with Image.open(BytesIO(data)) as raw_image:
        assert raw_image.getexif()

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(data, "image/jpeg"),
        None,
        Settings(
            privacy_hash_secret=SecretStr("test-privacy-secret"),
            enable_image_learning_pipeline=True,
            enable_pgvector_storage=True,
            image_retention_days=1,
        ),
        adapters=SupplementImageAnalysisAdapters(ocr=fake_ocr),
        learning_consents=(
            ConsentType.OCR_IMAGE_PROCESSING,
            ConsentType.DATA_RETENTION,
            ConsentType.IMAGE_LEARNING_DATASET,
        ),
        learning_object_store=fake_learning_store,
    )

    assert result.learning_image_object_created is True
    assert fake_ocr.received_image is not None
    assert fake_learning_store.payload is not None
    with Image.open(BytesIO(fake_ocr.received_image.image_bytes)) as ocr_image:
        assert not ocr_image.getexif()
    with Image.open(BytesIO(fake_learning_store.payload.image_bytes)) as stored_image:
        assert not stored_image.getexif()
    assert fake_learning_store.payload.image_bytes == fake_ocr.received_image.image_bytes


@pytest.mark.asyncio
async def test_analyze_supplement_image_sends_layout_bundle_to_parser_when_available() -> None:
    """Verify layout-aware OCR is sectioned before the structured parser call."""
    fake_session = _FakePipelineSession()
    words = (
        _word("영양·기능정보", 10, 10, 120, 24, word_index=0),
        _word("비타민", 10, 40, 50, 53, word_index=1),
        _word("D", 56, 40, 66, 53, word_index=2),
        _word("25", 150, 40, 170, 53, word_index=3),
        _word("ug", 176, 40, 194, 53, word_index=4),
    )
    fake_ocr = _FakeOCRAdapter(
        "영양·기능정보\n비타민 D 25 ug",
        provider="google_vision_document",
        pages=_ocr_pages(words),
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

    assert result.parser_used is True
    assert fake_parser.received_text is not None
    assert fake_parser.received_text.startswith("[section:nutrition_info")
    assert "cell=sec-000:r001:c000: 비타민 D" in fake_parser.received_text
    assert result.record.parsed_snapshot["source"]["layout_available"] is True
    assert "parser_input_text" not in result.record.parsed_snapshot["layout_context"]
    assert result.record.parsed_snapshot["label_sections"][0]["section_type"] == "nutrition_info"
    assert result.record.parsed_snapshot["evidence_spans"][0]["source_type"] == "label_layout"


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
    assert fake_vision.call_count == 1
    assert fake_ocr.received_image is not None
    assert fake_ocr.received_image.label_region == region
    assert result.image_quality_report is not None
    assert result.image_quality_report.detected_rois[0].label == "supplement_label"
    assert result.record.parsed_snapshot["image_quality_report"]["detected_rois"][0]["label"] == (
        "supplement_label"
    )
    assert result.parser_used is True


@pytest.mark.asyncio
async def test_analyze_supplement_image_crops_primary_ocr_input_when_policy_enabled() -> None:
    """Verify ROI crop policy sends cropped image bytes to primary OCR."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("비타민 D 1000")
    fake_parser = _FakeParser(_parse_result())
    region = BoundingBox(
        x=50,
        y=30,
        width=160,
        height=120,
        confidence=0.92,
        label="supplement_label",
    )

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes(width=300, height=200, color=(180, 180, 180))),
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
    assert fake_ocr.received_image.width == 160
    assert fake_ocr.received_image.height == 120
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
    assert result.image_quality_report is not None
    assert "roi_not_found" in {issue.reason_code for issue in result.image_quality_report.issues}
    assert "image_quality:roi_not_found" in result.ocr_warning_codes


@pytest.mark.asyncio
async def test_analyze_supplement_image_skips_auto_crop_for_multi_product_roi() -> None:
    """Verify multi-product ROI metadata degrades crop to full-image OCR."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("비타민 D 1000")
    fake_parser = _FakeParser(_parse_result())
    regions = (
        BoundingBox(
            x=10,
            y=10,
            width=80,
            height=90,
            confidence=0.92,
            label="supplement_bottle",
        ),
        BoundingBox(
            x=130,
            y=10,
            width=80,
            height=90,
            confidence=0.91,
            label="supplement_bottle",
        ),
    )

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes(width=240, height=140, color=(180, 180, 180))),
        None,
        Settings(
            privacy_hash_secret=SecretStr("test-privacy-secret"),
            enable_vision_classifier=True,
            ocr_roi_preprocessing_policy="crop_before_primary",
        ),
        adapters=SupplementImageAnalysisAdapters(
            ocr=fake_ocr,
            parser=fake_parser,
            vision=_FakeVisionCandidatesAdapter(regions),
        ),
    )

    assert result.vision_region == regions[0]
    assert fake_ocr.received_image is not None
    assert fake_ocr.received_image.width == 240
    assert fake_ocr.received_image.height == 140
    assert fake_ocr.received_image.label_region == regions[0]
    assert "image_quality:multi_product" in result.ocr_warning_codes
    assert OCR_ROI_CROP_UNAVAILABLE_CODE in result.ocr_warning_codes


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
async def test_analyze_supplement_image_does_not_use_multimodal_as_ocr_replacement() -> None:
    """Verify vision assist does not replace the canonical OCR provider result."""
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
    assert fake_multimodal.call_count == 0
    assert fake_parser.received_text is None
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "fake-ocr"
    assert result.record.ocr_text_hash is None


@pytest.mark.asyncio
async def test_analyze_supplement_image_keeps_low_confidence_ocr_over_multimodal() -> None:
    """Verify low OCR confidence does not make vision assist the selected OCR source."""
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

    assert fake_multimodal.call_count == 0
    assert fake_parser.received_text == "흐린 텍스트"
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "fake-ocr"


@pytest.mark.asyncio
async def test_analyze_supplement_image_uses_configured_multimodal_threshold() -> None:
    """Verify custom OCR confidence threshold can suppress vision assist fallback."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("비타민 D 1000", confidence=0.80)
    fake_multimodal = _FakeMultimodalOCRAdapter("대체 텍스트")
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
            ocr_confidence_threshold=0.70,
        ),
        adapters=SupplementImageAnalysisAdapters(
            ocr=fake_ocr,
            parser=fake_parser,
            multimodal_ocr=fake_multimodal,
        ),
    )

    assert fake_multimodal.call_count == 0
    assert fake_parser.received_text == "비타민 D 1000"
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "fake-ocr"


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
async def test_analyze_supplement_image_runs_secondary_fallback_without_primary() -> None:
    """Verify fallback OCR can run when no primary OCR adapter is configured."""
    fake_session = _FakePipelineSession()
    clova_fallback = _FakeOCRAdapter(
        "비타민 D 1000",
        confidence=0.91,
        provider="clova_ocr",
    )
    fake_parser = _FakeParser(_parse_result())

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        _settings(),
        adapters=SupplementImageAnalysisAdapters(
            parser=fake_parser,
            fallback_ocr_adapters=(clova_fallback,),
        ),
    )

    assert result.ocr_attempted is True
    assert clova_fallback.call_count == 1
    assert fake_parser.received_text == "비타민 D 1000"
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "clova_ocr"


@pytest.mark.asyncio
async def test_analyze_supplement_image_runs_local_fallback_without_primary() -> None:
    """Verify local OCR fallback can run without Google Vision primary OCR."""
    fake_session = _FakePipelineSession()
    local_fallback = _FakeOCRAdapter(
        "아연 8.5 mg",
        confidence=0.89,
        provider="paddleocr_local",
    )
    fake_parser = _FakeParser(_parse_result())

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        _settings(),
        adapters=SupplementImageAnalysisAdapters(
            parser=fake_parser,
            fallback_ocr_adapters=(local_fallback,),
        ),
    )

    assert result.ocr_attempted is True
    assert local_fallback.call_count == 1
    assert fake_parser.received_text == "아연 8.5 mg"
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "paddleocr_local"


@pytest.mark.asyncio
async def test_analyze_supplement_image_uses_first_usable_secondary_fallback() -> None:
    """Verify service accepts the first usable fallback adapter from factory order."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("흐린 텍스트", confidence=0.84)
    clova_fallback = _FakeOCRAdapter(
        "비타민 D 1000",
        confidence=0.91,
        provider="clova_ocr",
    )
    local_fallback = _FakeOCRAdapter(
        "다른 로컬 텍스트",
        confidence=0.90,
        provider="paddleocr",
    )
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
            fallback_ocr_adapters=(clova_fallback, local_fallback),
        ),
    )

    assert clova_fallback.call_count == 1
    assert local_fallback.call_count == 0
    assert fake_parser.received_text == "비타민 D 1000"
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "clova_ocr"


@pytest.mark.asyncio
async def test_analyze_supplement_image_keeps_primary_when_secondary_returns_empty() -> None:
    """Verify empty CLOVA fallback text does not replace a weak primary result."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("흐린 텍스트", confidence=0.70)
    clova_fallback = _FakeOCRAdapter("", confidence=None, provider="clova_ocr")
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
            fallback_ocr_adapters=(clova_fallback,),
        ),
    )

    assert clova_fallback.call_count == 1
    assert fake_parser.received_text == "흐린 텍스트"
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "fake-ocr"


@pytest.mark.asyncio
async def test_analyze_supplement_image_keeps_primary_when_secondary_errors() -> None:
    """Verify CLOVA fallback errors degrade to the weak primary OCR result."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("흐린 텍스트", confidence=0.70)
    clova_fallback = _FakeOCRAdapter(
        "unused",
        confidence=0.92,
        provider="clova_ocr",
        fail=True,
    )
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
            fallback_ocr_adapters=(clova_fallback,),
        ),
    )

    assert clova_fallback.call_count == 1
    assert fake_parser.received_text == "흐린 텍스트"
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "fake-ocr"
    assert any(
        code.startswith("ocr_provider_unavailable:clova_ocr") for code in result.ocr_warning_codes
    )


@pytest.mark.asyncio
async def test_analyze_supplement_image_continues_to_local_after_clova_error() -> None:
    """Verify provider errors do not stop later fallback OCR providers."""
    fake_session = _FakePipelineSession()
    clova_fallback = _FakeOCRAdapter(
        "unused",
        confidence=0.92,
        provider="clova_ocr",
        fail=True,
    )
    local_fallback = _FakeOCRAdapter(
        "비타민 C 500 mg",
        confidence=0.90,
        provider="paddleocr_local",
    )
    fake_parser = _FakeParser(_parse_result())

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        _settings(),
        adapters=SupplementImageAnalysisAdapters(
            parser=fake_parser,
            fallback_ocr_adapters=(clova_fallback, local_fallback),
        ),
    )

    assert clova_fallback.call_count == 1
    assert local_fallback.call_count == 1
    assert fake_parser.received_text == "비타민 C 500 mg"
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "paddleocr_local"
    assert any(
        code.startswith("ocr_provider_unavailable:clova_ocr") for code in result.ocr_warning_codes
    )


@pytest.mark.asyncio
async def test_analyze_supplement_image_uses_configured_secondary_threshold() -> None:
    """Verify secondary OCR fallback follows the runtime confidence threshold."""
    fake_session = _FakePipelineSession()
    fake_ocr = _FakeOCRAdapter("비타민 D 1000", confidence=0.80)
    fallback_ocr = _FakeOCRAdapter("대체 텍스트", confidence=0.90)
    fake_parser = _FakeParser(_parse_result())

    result = await analyze_supplement_image(
        cast(AsyncSession, fake_session),
        _user(),
        _upload(_png_bytes()),
        None,
        Settings(
            privacy_hash_secret=SecretStr("test-privacy-secret"),
            ocr_confidence_threshold=0.70,
        ),
        adapters=SupplementImageAnalysisAdapters(
            ocr=fake_ocr,
            parser=fake_parser,
            fallback_ocr_adapters=(fallback_ocr,),
        ),
    )

    assert fallback_ocr.call_count == 0
    assert fake_parser.received_text == "비타민 D 1000"
    assert result.ocr_result is not None
    assert result.ocr_result.provider == "fake-ocr"


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
