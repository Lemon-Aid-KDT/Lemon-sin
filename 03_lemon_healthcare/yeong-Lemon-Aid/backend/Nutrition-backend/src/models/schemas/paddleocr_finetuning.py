"""Schemas for PaddleOCR fine-tuning dataset manifests."""

from __future__ import annotations

import re
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PaddleOCRFineTuningTaskType = Literal["recognition", "detection"]
PaddleOCRFineTuningSplit = Literal["train", "val", "test"]
PaddleOCRLanguageMix = Literal["ko", "en", "ko_en", "numeric_unit"]
PaddleOCRFieldType = Literal[
    "ingredient_name",
    "amount",
    "unit",
    "numeric_unit",
    "daily_intake",
    "precautions",
    "other",
]
PaddleOCRBadcaseCategory = Literal[
    "detection_miss",
    "recognition_error",
    "layout_association_error",
    "parser_error",
    "input_quality_error",
]
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]")


class PaddleOCRDetectionBox(BaseModel):
    """One PaddleOCR text-detection training annotation.

    Attributes:
        transcription: Human-verified text-line transcription used in PaddleOCR
            detection label JSON.
        points: Polygon points in image coordinates.
        ignore: Whether this annotation should be ignored by downstream training.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    transcription: str = Field(min_length=1, max_length=240)
    points: list[tuple[float, float]] = Field(min_length=4, max_length=16)
    ignore: bool = Field(default=False)

    @field_validator("transcription")
    @classmethod
    def validate_transcription(cls, value: str) -> str:
        """Validate text labels do not break PaddleOCR label files.

        Args:
            value: Candidate transcription.

        Returns:
            Validated transcription.

        Raises:
            ValueError: If the transcription contains tab, newline, or control characters.
        """
        return _validate_training_text(value)

    @field_validator("points")
    @classmethod
    def validate_points(cls, values: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """Validate detection polygon points.

        Args:
            values: Candidate polygon points.

        Returns:
            Validated polygon points.

        Raises:
            ValueError: If any point has negative coordinates.
        """
        if any(x < 0 or y < 0 for x, y in values):
            raise ValueError("Detection points must be non-negative.")
        return values


class PaddleOCRFineTuningSample(BaseModel):
    """One redacted PaddleOCR fine-tuning sample.

    Attributes:
        sample_id: Pseudonymous sample id.
        source_image_id: Pseudonymous source image id.
        crop_id: Pseudonymous crop id.
        image_path: Relative dataset image or crop path used by PaddleOCR labels.
        product_group_id: Product/barcode grouping key for split isolation.
        image_hash: Source image or crop hash used for leakage checks.
        split_group: Session or source grouping key that must not cross splits.
        split: Dataset split.
        task_type: Fine-tuning task type.
        language_mix: Language mix category for distribution reporting.
        field_type: Label field type category for distribution reporting.
        human_verified: Whether text/box labels were manually confirmed.
        consent_scope: Consent names captured at export time.
        transcript_hash: Hash of the human-verified transcript.
        verified_transcript: Human-verified recognition label. Excluded from metadata dumps.
        boxes: Human-verified detection boxes.
        session_group_id: Optional session grouping key for leakage checks.
        augmented_source_id: Optional augmentation-source grouping key for leakage checks.
        source_provider: Optional bootstrap provider name.
        badcase_categories: Failure taxonomy labels for reporting.
        quality_labels: Image quality labels for distribution reporting.
        synthetic: Whether the sample is synthetic. Defaults to false.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sample_id: str = Field(min_length=8, max_length=160)
    source_image_id: str = Field(min_length=8, max_length=160)
    crop_id: str = Field(min_length=1, max_length=160)
    image_path: str = Field(min_length=1, max_length=240)
    product_group_id: str = Field(min_length=1, max_length=160)
    image_hash: str = Field(min_length=8, max_length=160)
    split_group: str = Field(min_length=1, max_length=160)
    split: PaddleOCRFineTuningSplit
    task_type: PaddleOCRFineTuningTaskType
    language_mix: PaddleOCRLanguageMix
    field_type: PaddleOCRFieldType
    human_verified: bool
    consent_scope: list[str] = Field(min_length=1, max_length=20)
    transcript_hash: str = Field(min_length=8, max_length=160)
    verified_transcript: str | None = Field(default=None, max_length=240, exclude=True)
    boxes: list[PaddleOCRDetectionBox] = Field(default_factory=list, max_length=120)
    session_group_id: str | None = Field(default=None, max_length=160)
    augmented_source_id: str | None = Field(default=None, max_length=160)
    source_provider: str | None = Field(default=None, max_length=80)
    badcase_categories: list[PaddleOCRBadcaseCategory] = Field(
        default_factory=list,
        max_length=12,
    )
    quality_labels: list[str] = Field(default_factory=list, max_length=20)
    synthetic: bool = Field(default=False)

    @field_validator("image_path")
    @classmethod
    def validate_relative_image_path(cls, value: str) -> str:
        """Validate dataset paths stay relative and portable.

        Args:
            value: Candidate image path.

        Returns:
            Validated relative image path.

        Raises:
            ValueError: If the path is absolute or traverses outside the dataset.
        """
        if value.startswith("/") or "\\" in value or ".." in value.split("/"):
            raise ValueError("image_path must be a safe relative POSIX path.")
        return value

    @field_validator("verified_transcript")
    @classmethod
    def validate_verified_transcript(cls, value: str | None) -> str | None:
        """Validate optional recognition transcript labels.

        Args:
            value: Candidate transcript.

        Returns:
            Validated transcript or None.

        Raises:
            ValueError: If the transcript contains tab, newline, or control characters.
        """
        if value is None:
            return None
        return _validate_training_text(value)

    @field_validator("badcase_categories")
    @classmethod
    def dedupe_badcase_categories(
        cls,
        values: list[PaddleOCRBadcaseCategory],
    ) -> list[PaddleOCRBadcaseCategory]:
        """Deduplicate badcase categories while preserving order.

        Args:
            values: Candidate badcase category list.

        Returns:
            Deduplicated badcase categories.
        """
        return _dedupe_preserve_order(values)

    @field_validator("quality_labels")
    @classmethod
    def dedupe_quality_labels(cls, values: list[str]) -> list[str]:
        """Deduplicate quality labels while preserving order.

        Args:
            values: Candidate quality label list.

        Returns:
            Deduplicated quality labels.
        """
        return _dedupe_preserve_order(values)

    @model_validator(mode="after")
    def validate_task_payload(self) -> Self:
        """Validate task-specific sample payloads.

        Returns:
            Validated sample.

        Raises:
            ValueError: If recognition or detection fields are incompatible.
        """
        if self.task_type == "recognition" and self.boxes:
            raise ValueError("Recognition samples must not contain detection boxes.")
        if self.task_type == "detection" and self.verified_transcript is not None:
            raise ValueError("Detection samples must not contain verified_transcript.")
        return self


class PaddleOCRFineTuningManifest(BaseModel):
    """Redacted PaddleOCR fine-tuning manifest.

    Attributes:
        schema_version: Manifest schema version.
        items: Fine-tuning samples.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["paddleocr-finetuning-manifest-v1"] = "paddleocr-finetuning-manifest-v1"
    items: list[PaddleOCRFineTuningSample] = Field(default_factory=list)


def _validate_training_text(value: str) -> str:
    """Validate one human-verified training label.

    Args:
        value: Candidate text.

    Returns:
        Validated text.

    Raises:
        ValueError: If the text contains tab, newline, or control characters.
    """
    if "\t" in value or "\n" in value or "\r" in value or CONTROL_CHARACTER_PATTERN.search(value):
        raise ValueError("Training labels must not contain tab, newline, or control characters.")
    return value


def _dedupe_preserve_order[T](values: list[T]) -> list[T]:
    """Deduplicate list values while preserving order.

    Args:
        values: Candidate values.

    Returns:
        Deduplicated values.
    """
    normalized: list[T] = []
    seen: set[T] = set()
    for value in values:
        if value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return normalized
