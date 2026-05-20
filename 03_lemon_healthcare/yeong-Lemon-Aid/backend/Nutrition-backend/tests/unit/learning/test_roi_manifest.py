"""ROI training manifest helper tests."""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from src.config import Settings
from src.learning.consent_gate import IMAGE_LEARNING_REQUIRED_CONSENTS
from src.learning.roi_manifest import (
    ROIManifestExportError,
    build_consent_gated_manifest,
    reject_raw_manifest_fields,
    render_ultralytics_data_yaml,
    validate_manifest_splits,
    yolo_label_lines,
)
from src.models.schemas.image_quality import ROITrainingBox, ROITrainingManifestItem
from src.models.schemas.privacy import ConsentType


def _settings() -> Settings:
    """Return settings that allow consent-gated image learning export.

    Returns:
        Settings with learning flags and positive retention enabled.
    """
    return Settings(
        _env_file=None,
        privacy_hash_secret=SecretStr("test-privacy-secret"),
        enable_image_learning_pipeline=True,
        enable_pgvector_storage=True,
        image_retention_days=30,
    )


def _item(
    *,
    image_id: str = "image-a01",
    image_hash: str = "hash-a01",
    product_group_id: str = "product-a",
    split_group: str = "session-a",
    split: str = "train",
) -> ROITrainingManifestItem:
    """Build a redacted manifest item fixture.

    Args:
        image_id: Pseudonymous image id.
        image_hash: Redacted image hash.
        product_group_id: Product grouping key.
        split_group: Split grouping key.
        split: Dataset split.

    Returns:
        ROI manifest item.
    """
    return ROITrainingManifestItem.model_validate(
        {
            "image_id": image_id,
            "image_hash": image_hash,
            "product_group_id": product_group_id,
            "split_group": split_group,
            "split": split,
            "consent_scope": [consent.value for consent in IMAGE_LEARNING_REQUIRED_CONSENTS],
            "labels": ["facts_table_visible"],
            "boxes": [
                ROITrainingBox(
                    class_name="supplement_facts_table",
                    x_center=0.5,
                    y_center=0.5,
                    width=0.4,
                    height=0.3,
                )
            ],
        }
    )


def test_build_consent_gated_manifest_allows_redacted_items() -> None:
    """Verify allowed consent gates produce a manifest."""
    manifest = build_consent_gated_manifest(
        settings=_settings(),
        granted_consents=IMAGE_LEARNING_REQUIRED_CONSENTS,
        items=[_item()],
    )

    assert manifest.schema_version == "roi-training-manifest-v1"
    assert manifest.items[0].image_id == "image-a01"
    assert manifest.class_names[3] == "supplement_facts_table"


def test_build_consent_gated_manifest_blocks_missing_consent() -> None:
    """Verify missing learning consent blocks export."""
    granted = (
        ConsentType.OCR_IMAGE_PROCESSING,
        ConsentType.DATA_RETENTION,
    )

    with pytest.raises(ROIManifestExportError, match="Required image-learning consent"):
        build_consent_gated_manifest(
            settings=_settings(),
            granted_consents=granted,
            items=[_item()],
        )


def test_validate_manifest_splits_rejects_product_leakage() -> None:
    """Verify the same product group cannot cross train/test splits."""
    train_item = _item(split="train")
    test_item = _item(
        image_id="image-b01",
        image_hash="hash-b01",
        product_group_id="product-a",
        split_group="session-b",
        split="test",
    )

    with pytest.raises(ROIManifestExportError, match="product_group_id crosses splits"):
        validate_manifest_splits([train_item, test_item])


def test_validate_manifest_splits_rejects_image_hash_leakage() -> None:
    """Verify the same source image hash cannot cross splits."""
    train_item = _item(split="train")
    val_item = _item(
        image_id="image-b01",
        image_hash="hash-a01",
        product_group_id="product-b",
        split_group="session-b",
        split="val",
    )

    with pytest.raises(ROIManifestExportError, match="image_hash crosses splits"):
        validate_manifest_splits([train_item, val_item])


def test_render_ultralytics_yaml_and_yolo_label_lines() -> None:
    """Verify conversion output follows the documented YOLO detection shape."""
    item = _item()

    data_yaml = render_ultralytics_data_yaml(dataset_root="/tmp/roi-dataset")
    label_lines = yolo_label_lines(item)

    assert "train: images/train" in data_yaml
    assert "3: supplement_facts_table" in data_yaml
    assert label_lines == ["3 0.5 0.5 0.4 0.3"]


def test_reject_raw_manifest_fields_blocks_raw_ocr_text() -> None:
    """Verify raw OCR text cannot enter the ROI manifest path."""
    with pytest.raises(ROIManifestExportError, match="raw_ocr_text"):
        reject_raw_manifest_fields({"items": [{"raw_ocr_text": "비타민 D 1000"}]})
