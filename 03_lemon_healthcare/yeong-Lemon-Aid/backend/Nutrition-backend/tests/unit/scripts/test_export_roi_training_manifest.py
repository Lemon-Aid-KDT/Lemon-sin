"""Tests for the consent-gated ROI manifest exporter script."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import SecretStr
from src.config import Settings
from src.learning.consent_gate import IMAGE_LEARNING_REQUIRED_CONSENTS
from src.learning.roi_manifest import ROIManifestExportError

from scripts.export_roi_training_manifest import export_roi_training_manifest


def _settings() -> Settings:
    """Return export settings with the learning gate enabled.

    Returns:
        Settings for local redacted export tests.
    """
    return Settings(
        _env_file=None,
        privacy_hash_secret=SecretStr("test-privacy-secret"),
        enable_image_learning_pipeline=True,
        enable_pgvector_storage=True,
        image_retention_days=30,
    )


def _manifest_payload() -> dict[str, object]:
    """Return one redacted ROI manifest payload.

    Returns:
        JSON-serializable input payload.
    """
    return {
        "items": [
            {
                "image_id": "image-a01",
                "image_hash": "hash-a01",
                "product_group_id": "product-a",
                "split_group": "session-a",
                "split": "train",
                "consent_scope": [consent.value for consent in IMAGE_LEARNING_REQUIRED_CONSENTS],
                "labels": ["facts_table_visible"],
                "boxes": [
                    {
                        "class_name": "supplement_facts_table",
                        "x_center": 0.5,
                        "y_center": 0.5,
                        "width": 0.4,
                        "height": 0.3,
                    }
                ],
            }
        ]
    }


def test_export_roi_training_manifest_writes_redacted_outputs(tmp_path: Path) -> None:
    """Verify exporter writes manifest, data.yaml, and YOLO labels."""
    input_path = tmp_path / "input.json"
    output_dir = tmp_path / "out"
    input_path.write_text(json.dumps(_manifest_payload(), ensure_ascii=False), encoding="utf-8")

    summary = export_roi_training_manifest(
        input_path=input_path,
        output_dir=output_dir,
        dataset_root="roi-dataset",
        settings=_settings(),
        granted_consents=IMAGE_LEARNING_REQUIRED_CONSENTS,
    )

    assert summary["item_count"] == 1
    assert summary["label_file_count"] == 1
    assert summary["raw_image_stored"] is False
    assert (output_dir / "roi-training-manifest.json").exists()
    assert "names:" in (output_dir / "data.yaml").read_text(encoding="utf-8")
    assert (output_dir / "labels" / "image-a01.txt").read_text(encoding="utf-8") == (
        "3 0.5 0.5 0.4 0.3\n"
    )


def test_export_roi_training_manifest_rejects_raw_image_fields(tmp_path: Path) -> None:
    """Verify exporter blocks raw image fields before writing outputs."""
    input_path = tmp_path / "input.json"
    output_dir = tmp_path / "out"
    payload = _manifest_payload()
    items = payload["items"]
    assert isinstance(items, list)
    first_item = items[0]
    assert isinstance(first_item, dict)
    first_item["raw_image"] = "base64-not-allowed"
    input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ROIManifestExportError, match="raw_image"):
        export_roi_training_manifest(
            input_path=input_path,
            output_dir=output_dir,
            dataset_root="roi-dataset",
            settings=_settings(),
            granted_consents=IMAGE_LEARNING_REQUIRED_CONSENTS,
        )

    assert not output_dir.exists()
