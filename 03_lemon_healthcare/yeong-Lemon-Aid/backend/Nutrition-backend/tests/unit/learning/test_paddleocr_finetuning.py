"""PaddleOCR fine-tuning manifest helper tests."""

from __future__ import annotations

import json

import pytest
from pydantic import SecretStr, ValidationError
from src.config import Settings
from src.learning.consent_gate import IMAGE_LEARNING_REQUIRED_CONSENTS
from src.learning.paddleocr_finetuning import (
    PaddleOCRFineTuningExportError,
    build_consent_gated_finetuning_manifest,
    detection_label_lines,
    distribution_report,
    evaluate_promotion_gate,
    recognition_label_lines,
    redacted_manifest_dict,
    reject_raw_manifest_fields,
    validate_finetuning_splits,
)
from src.models.schemas.paddleocr_finetuning import (
    PaddleOCRDetectionBox,
    PaddleOCRFineTuningManifest,
    PaddleOCRFineTuningSample,
)
from src.models.schemas.privacy import ConsentType


def _settings() -> Settings:
    """Return settings that allow image-learning export.

    Returns:
        Settings with learning gates and positive retention enabled.
    """
    return Settings(
        _env_file=None,
        privacy_hash_secret=SecretStr("test-privacy-secret"),
        enable_image_learning_pipeline=True,
        enable_pgvector_storage=True,
        image_retention_days=30,
    )


def _recognition_sample(
    *,
    sample_id: str = "sample-rec-001",
    source_image_id: str = "image-a01",
    crop_id: str = "crop-a01",
    product_group_id: str = "product-a",
    image_hash: str = "hash-a01",
    split_group: str = "session-a",
    split: str = "train",
    human_verified: bool = True,
    verified_transcript: str | None = "비타민 D 25 ug",
    session_group_id: str | None = "session-a",
    augmented_source_id: str | None = None,
) -> PaddleOCRFineTuningSample:
    """Build a recognition fine-tuning sample fixture.

    Args:
        sample_id: Pseudonymous sample id.
        source_image_id: Pseudonymous source image id.
        crop_id: Pseudonymous crop id.
        product_group_id: Product grouping key.
        image_hash: Source image hash.
        split_group: Split group.
        split: Dataset split.
        human_verified: Whether labels are manually verified.
        verified_transcript: Human-verified transcript.
        session_group_id: Optional session leakage key.
        augmented_source_id: Optional augmented-source leakage key.

    Returns:
        Fine-tuning sample.
    """
    return PaddleOCRFineTuningSample.model_validate(
        {
            "sample_id": sample_id,
            "source_image_id": source_image_id,
            "crop_id": crop_id,
            "image_path": f"images/{split}/{crop_id}.png",
            "product_group_id": product_group_id,
            "image_hash": image_hash,
            "split_group": split_group,
            "split": split,
            "task_type": "recognition",
            "language_mix": "ko_en",
            "field_type": "numeric_unit",
            "human_verified": human_verified,
            "consent_scope": [consent.value for consent in IMAGE_LEARNING_REQUIRED_CONSENTS],
            "transcript_hash": f"transcript-{sample_id}",
            "verified_transcript": verified_transcript,
            "session_group_id": session_group_id,
            "augmented_source_id": augmented_source_id,
            "source_provider": "paddleocr_local",
            "badcase_categories": ["recognition_error"],
            "quality_labels": ["facts_table_visible"],
        }
    )


def _detection_sample(
    *,
    sample_id: str = "sample-det-001",
    split: str = "val",
) -> PaddleOCRFineTuningSample:
    """Build a detection fine-tuning sample fixture.

    Args:
        sample_id: Pseudonymous sample id.
        split: Dataset split.

    Returns:
        Fine-tuning sample.
    """
    return PaddleOCRFineTuningSample.model_validate(
        {
            "sample_id": sample_id,
            "source_image_id": "image-det-001",
            "crop_id": "crop-det-001",
            "image_path": f"images/{split}/crop-det-001.png",
            "product_group_id": "product-det",
            "image_hash": "hash-det-001",
            "split_group": "session-det",
            "split": split,
            "task_type": "detection",
            "language_mix": "ko",
            "field_type": "ingredient_name",
            "human_verified": True,
            "consent_scope": [consent.value for consent in IMAGE_LEARNING_REQUIRED_CONSENTS],
            "transcript_hash": "transcript-det-001",
            "boxes": [
                PaddleOCRDetectionBox(
                    transcription="아연",
                    points=[(10, 10), (60, 10), (60, 24), (10, 24)],
                )
            ],
            "badcase_categories": ["detection_miss"],
            "quality_labels": ["too_small_text"],
        }
    )


def test_build_consent_gated_finetuning_manifest_allows_verified_samples() -> None:
    """Verify consent and human verification gates allow exportable samples."""
    manifest = build_consent_gated_finetuning_manifest(
        settings=_settings(),
        granted_consents=IMAGE_LEARNING_REQUIRED_CONSENTS,
        items=[_recognition_sample()],
    )

    assert manifest.schema_version == "paddleocr-finetuning-manifest-v1"
    assert manifest.items[0].sample_id == "sample-rec-001"


def test_build_consent_gated_finetuning_manifest_blocks_missing_consent() -> None:
    """Verify missing image-learning consent blocks export."""
    granted = (
        ConsentType.OCR_IMAGE_PROCESSING,
        ConsentType.DATA_RETENTION,
    )

    with pytest.raises(PaddleOCRFineTuningExportError, match="Required image-learning consent"):
        build_consent_gated_finetuning_manifest(
            settings=_settings(),
            granted_consents=granted,
            items=[_recognition_sample()],
        )


def test_human_verified_false_sample_is_blocked_from_training_export() -> None:
    """Verify bootstrap-only OCR labels cannot become training labels."""
    with pytest.raises(PaddleOCRFineTuningExportError, match="human_verified=true"):
        recognition_label_lines([_recognition_sample(human_verified=False)])


@pytest.mark.parametrize("bad_text", ("bad\ttext", "bad\ntext", "bad\rtext", "bad\x00text"))
def test_training_transcript_rejects_control_characters(bad_text: str) -> None:
    """Verify PaddleOCR label-breaking transcript characters are rejected."""
    with pytest.raises(ValidationError, match="Training labels"):
        _recognition_sample(verified_transcript=bad_text)


def test_recognition_label_lines_use_paddleocr_tab_format() -> None:
    """Verify recognition labels follow PaddleOCR image-path tab transcript shape."""
    lines = recognition_label_lines([_recognition_sample()])

    assert lines["train"] == ["images/train/crop-a01.png\t비타민 D 25 ug"]
    assert lines["val"] == []
    assert lines["test"] == []


def test_detection_label_lines_use_paddleocr_json_format() -> None:
    """Verify detection labels follow PaddleOCR image-path tab JSON shape."""
    lines = detection_label_lines([_detection_sample()])
    image_path, annotation_json = lines["val"][0].split("\t", 1)
    annotations = json.loads(annotation_json)

    assert image_path == "images/val/crop-det-001.png"
    assert annotations == [
        {
            "transcription": "아연",
            "points": [[10.0, 10.0], [60.0, 10.0], [60.0, 24.0], [10.0, 24.0]],
        }
    ]


def test_validate_finetuning_splits_rejects_product_leakage() -> None:
    """Verify the same product cannot cross train/test splits."""
    train_item = _recognition_sample(split="train")
    test_item = _recognition_sample(
        sample_id="sample-rec-002",
        source_image_id="image-b01",
        crop_id="crop-b01",
        image_hash="hash-b01",
        split_group="session-b",
        split="test",
        session_group_id="session-b",
    )

    with pytest.raises(PaddleOCRFineTuningExportError, match="product_group_id crosses splits"):
        validate_finetuning_splits([train_item, test_item])


def test_validate_finetuning_splits_rejects_augmented_source_leakage() -> None:
    """Verify augmented variants cannot cross validation splits."""
    train_item = _recognition_sample(
        split="train",
        augmented_source_id="aug-source-a",
    )
    val_item = _recognition_sample(
        sample_id="sample-rec-003",
        source_image_id="image-c01",
        crop_id="crop-c01",
        product_group_id="product-c",
        image_hash="hash-c01",
        split_group="session-c",
        split="val",
        session_group_id="session-c",
        augmented_source_id="aug-source-a",
    )

    with pytest.raises(PaddleOCRFineTuningExportError, match="augmented_source_id crosses splits"):
        validate_finetuning_splits([train_item, val_item])


def test_redacted_manifest_omits_transcript_text() -> None:
    """Verify metadata sidecar does not persist human transcript strings."""
    manifest = PaddleOCRFineTuningManifest(items=[_recognition_sample(), _detection_sample()])
    redacted = redacted_manifest_dict(manifest)
    serialized = json.dumps(redacted, ensure_ascii=False)

    assert "비타민 D 25 ug" not in serialized
    assert "아연" not in serialized
    assert "transcript_hash" in serialized


def test_distribution_report_counts_split_task_and_field_metadata() -> None:
    """Verify distribution report captures redacted aggregate counts."""
    report = distribution_report([_recognition_sample(), _detection_sample()])

    assert report["item_count"] == 2
    assert report["split_counts"] == {"train": 1, "val": 1}
    assert report["task_type_counts"] == {"detection": 1, "recognition": 1}
    assert report["field_type_counts"] == {"ingredient_name": 1, "numeric_unit": 1}


def test_reject_raw_manifest_fields_blocks_raw_ocr_text() -> None:
    """Verify raw OCR text cannot enter the fine-tuning manifest path."""
    with pytest.raises(PaddleOCRFineTuningExportError, match="raw_ocr_text"):
        reject_raw_manifest_fields({"items": [{"raw_ocr_text": "비타민 D 1000"}]})


def test_evaluate_promotion_gate_requires_improvement_without_regression() -> None:
    """Verify fine-tuned models need one primary improvement and no regressions."""
    baseline = {
        "frozen_test_split_id": "split-v1",
        "numeric_exact_rate": 0.80,
        "unit_exact_rate": 0.75,
        "line_exact_rate": 0.70,
        "parser_success_rate": 0.60,
        "field_exact_rate": 0.65,
    }
    candidate = {
        **baseline,
        "numeric_exact_rate": 0.82,
    }

    decision = evaluate_promotion_gate(baseline=baseline, candidate=candidate)

    assert decision["promotable"] is True
    assert decision["reason"] == "promotion_candidate"


def test_evaluate_promotion_gate_rejects_metric_regression() -> None:
    """Verify any primary metric regression blocks promotion."""
    baseline = {
        "frozen_test_split_id": "split-v1",
        "numeric_exact_rate": 0.80,
        "unit_exact_rate": 0.75,
        "line_exact_rate": 0.70,
        "parser_success_rate": 0.60,
        "field_exact_rate": 0.65,
    }
    candidate = {
        **baseline,
        "numeric_exact_rate": 0.81,
        "unit_exact_rate": 0.74,
    }

    decision = evaluate_promotion_gate(baseline=baseline, candidate=candidate)

    assert decision["promotable"] is False
    assert decision["reason"] == "metric_regressed:unit_exact_rate"
