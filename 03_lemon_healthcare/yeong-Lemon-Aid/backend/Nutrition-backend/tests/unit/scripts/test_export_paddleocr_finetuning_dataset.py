"""Tests for the PaddleOCR fine-tuning dataset exporter script."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import SecretStr
from src.config import Settings
from src.learning.consent_gate import IMAGE_LEARNING_REQUIRED_CONSENTS
from src.learning.paddleocr_finetuning import PaddleOCRFineTuningExportError

from scripts.export_paddleocr_finetuning_dataset import export_paddleocr_finetuning_dataset


def _settings() -> Settings:
    """Return export settings with image-learning gates enabled.

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
    """Return a redacted fine-tuning input manifest.

    Returns:
        JSON-serializable manifest payload.
    """
    consent_scope = [consent.value for consent in IMAGE_LEARNING_REQUIRED_CONSENTS]
    return {
        "items": [
            {
                "sample_id": "sample-rec-001",
                "source_image_id": "image-rec-001",
                "crop_id": "crop-rec-001",
                "image_path": "images/train/crop-rec-001.png",
                "product_group_id": "product-rec",
                "image_hash": "hash-rec-001",
                "split_group": "session-rec",
                "split": "train",
                "task_type": "recognition",
                "language_mix": "ko_en",
                "field_type": "numeric_unit",
                "human_verified": True,
                "consent_scope": consent_scope,
                "transcript_hash": "transcript-rec-001",
                "verified_transcript": "비타민 D 25 ug",
                "session_group_id": "session-rec",
                "badcase_categories": ["recognition_error"],
            },
            {
                "sample_id": "sample-det-001",
                "source_image_id": "image-det-001",
                "crop_id": "crop-det-001",
                "image_path": "images/val/crop-det-001.png",
                "product_group_id": "product-det",
                "image_hash": "hash-det-001",
                "split_group": "session-det",
                "split": "val",
                "task_type": "detection",
                "language_mix": "ko",
                "field_type": "ingredient_name",
                "human_verified": True,
                "consent_scope": consent_scope,
                "transcript_hash": "transcript-det-001",
                "boxes": [
                    {
                        "transcription": "아연",
                        "points": [[10, 10], [60, 10], [60, 24], [10, 24]],
                    }
                ],
                "badcase_categories": ["detection_miss"],
            },
        ]
    }


def test_export_paddleocr_finetuning_dataset_writes_redacted_outputs(tmp_path: Path) -> None:
    """Verify exporter writes PaddleOCR labels, sidecar, and report."""
    input_path = tmp_path / "input.json"
    output_dir = tmp_path / "out"
    input_path.write_text(json.dumps(_manifest_payload(), ensure_ascii=False), encoding="utf-8")

    summary = export_paddleocr_finetuning_dataset(
        input_path=input_path,
        output_dir=output_dir,
        dataset_root="paddleocr-ft",
        settings=_settings(),
        granted_consents=IMAGE_LEARNING_REQUIRED_CONSENTS,
    )

    assert summary["item_count"] == 2
    assert summary["recognition_label_count"] == 1
    assert summary["detection_label_count"] == 1
    assert summary["raw_image_stored"] is False
    assert summary["raw_ocr_text_stored"] is False
    assert (output_dir / "rec" / "train.txt").read_text(encoding="utf-8") == (
        "images/train/crop-rec-001.png\t비타민 D 25 ug\n"
    )
    detection_line = (output_dir / "det" / "val.txt").read_text(encoding="utf-8").strip()
    assert detection_line.startswith("images/val/crop-det-001.png\t")
    manifest_text = (output_dir / "paddleocr-finetuning-manifest.json").read_text(encoding="utf-8")
    assert "비타민 D 25 ug" not in manifest_text
    assert "아연" not in manifest_text
    assert "transcript_hash" in manifest_text
    report = json.loads(
        (output_dir / "paddleocr-finetuning-distribution.json").read_text(encoding="utf-8")
    )
    assert report["task_type_counts"] == {"detection": 1, "recognition": 1}


def test_export_paddleocr_finetuning_dataset_rejects_raw_fields(tmp_path: Path) -> None:
    """Verify exporter blocks raw image/OCR fields before writing outputs."""
    input_path = tmp_path / "input.json"
    output_dir = tmp_path / "out"
    payload = _manifest_payload()
    items = payload["items"]
    assert isinstance(items, list)
    first_item = items[0]
    assert isinstance(first_item, dict)
    first_item["raw_provider_payload"] = {"rec_texts": ["not allowed"]}
    input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(PaddleOCRFineTuningExportError, match="raw_provider_payload"):
        export_paddleocr_finetuning_dataset(
            input_path=input_path,
            output_dir=output_dir,
            dataset_root="paddleocr-ft",
            settings=_settings(),
            granted_consents=IMAGE_LEARNING_REQUIRED_CONSENTS,
        )

    assert not output_dir.exists()


def test_export_paddleocr_finetuning_dataset_blocks_missing_consent(tmp_path: Path) -> None:
    """Verify consent gate failures block dataset export."""
    input_path = tmp_path / "input.json"
    output_dir = tmp_path / "out"
    input_path.write_text(json.dumps(_manifest_payload(), ensure_ascii=False), encoding="utf-8")

    with pytest.raises(PaddleOCRFineTuningExportError, match="Required image-learning consent"):
        export_paddleocr_finetuning_dataset(
            input_path=input_path,
            output_dir=output_dir,
            dataset_root="paddleocr-ft",
            settings=_settings(),
            granted_consents=(),
        )

    assert not output_dir.exists()
