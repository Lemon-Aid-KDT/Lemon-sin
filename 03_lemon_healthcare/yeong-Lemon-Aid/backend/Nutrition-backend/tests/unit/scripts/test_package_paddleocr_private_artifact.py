"""Tests for private PaddleOCR artifact packaging."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from scripts.package_paddleocr_private_artifact import (
    CHECKSUMS_FILE_NAME,
    PaddleOCRPrivateArtifactError,
    package_paddleocr_private_artifact,
)


def test_package_paddleocr_private_artifact_writes_manifest_summary_and_checksums(
    tmp_path: Path,
) -> None:
    """Verify packager writes a full-private copy and redacted sidecar."""
    queue_dir = _write_queue_dir(tmp_path)
    export_dir = _write_export_dir(tmp_path)
    training_output_dir = _write_training_output_dir(tmp_path)
    source_dir = _write_paddleocr_source_dir(tmp_path)
    output_dir = tmp_path / "artifact"

    summary = package_paddleocr_private_artifact(
        queue_dir=queue_dir,
        export_dir=export_dir,
        training_output_dir=training_output_dir,
        output_dir=output_dir,
        paddleocr_source_dir=source_dir,
        source_dataset_id="naver-tampermonkey-2026-05",
    )

    assert summary["full_private_artifact"] is True
    assert summary["source_dataset_id"] == "naver-tampermonkey-2026-05"
    assert (output_dir / "full_private" / "queue" / "annotation_queue.json").is_file()
    assert (output_dir / "full_private" / "export" / "det" / "train.txt").is_file()
    assert (
        output_dir / "full_private" / "training" / "det" / "inference" / "model.pdmodel"
    ).is_file()

    artifact_manifest = json.loads(
        (output_dir / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    assert artifact_manifest["schema_version"] == "paddleocr-private-artifact-v1"
    assert artifact_manifest["paddleocr"]["network_downloads_used"] is False
    assert artifact_manifest["queue"]["selected_image_count"] == 1
    assert artifact_manifest["training"]["contains_model_files"] is True

    redacted_summary_text = (output_dir / "redacted_summary.json").read_text(encoding="utf-8")
    assert "source-product-label.jpg" not in redacted_summary_text
    assert "비타민 D 25 ug" not in redacted_summary_text
    redacted_summary = json.loads(redacted_summary_text)
    assert redacted_summary["privacy_assertions"] == {
        "contains_original_paths": False,
        "contains_original_file_names": False,
        "contains_raw_ocr_text": False,
        "contains_provider_payload": False,
        "contains_api_credentials": False,
        "contains_image_bytes": False,
    }

    checksum_lines = (output_dir / CHECKSUMS_FILE_NAME).read_text(encoding="utf-8").splitlines()
    model_rel_path = "full_private/training/det/inference/model.pdmodel"
    model_line = next(line for line in checksum_lines if line.endswith(f"  {model_rel_path}"))
    expected_digest = sha256((output_dir / model_rel_path).read_bytes()).hexdigest()
    assert model_line == f"{expected_digest}  {model_rel_path}"


def test_package_paddleocr_private_artifact_blocks_missing_inputs(tmp_path: Path) -> None:
    """Verify missing required queue/export/training inputs fail closed."""
    queue_dir = _write_queue_dir(tmp_path)
    source_dir = _write_paddleocr_source_dir(tmp_path)

    with pytest.raises(PaddleOCRPrivateArtifactError, match="export directory does not exist"):
        package_paddleocr_private_artifact(
            queue_dir=queue_dir,
            export_dir=tmp_path / "missing-export",
            training_output_dir=tmp_path / "missing-training",
            output_dir=tmp_path / "artifact",
            paddleocr_source_dir=source_dir,
            source_dataset_id="naver-tampermonkey-2026-05",
        )


def test_package_paddleocr_private_artifact_rejects_raw_provider_payload(
    tmp_path: Path,
) -> None:
    """Verify forbidden raw/provider fields block artifact creation."""
    queue_dir = _write_queue_dir(tmp_path)
    export_dir = _write_export_dir(tmp_path)
    training_output_dir = _write_training_output_dir(tmp_path)
    source_dir = _write_paddleocr_source_dir(tmp_path)
    queue_path = queue_dir / "annotation_queue.json"
    payload = json.loads(queue_path.read_text(encoding="utf-8"))
    items = payload["items"]
    assert isinstance(items, list)
    first_item = items[0]
    assert isinstance(first_item, dict)
    first_item["raw_provider_payload"] = {"rec_texts": ["not allowed"]}
    queue_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(PaddleOCRPrivateArtifactError, match="raw_provider_payload"):
        package_paddleocr_private_artifact(
            queue_dir=queue_dir,
            export_dir=export_dir,
            training_output_dir=training_output_dir,
            output_dir=tmp_path / "artifact",
            paddleocr_source_dir=source_dir,
            source_dataset_id="naver-tampermonkey-2026-05",
        )


def test_package_paddleocr_private_artifact_rejects_non_empty_output_dir(
    tmp_path: Path,
) -> None:
    """Verify existing artifact directories are not overwritten."""
    queue_dir = _write_queue_dir(tmp_path)
    export_dir = _write_export_dir(tmp_path)
    training_output_dir = _write_training_output_dir(tmp_path)
    source_dir = _write_paddleocr_source_dir(tmp_path)
    output_dir = tmp_path / "artifact"
    output_dir.mkdir()
    (output_dir / "old.txt").write_text("old", encoding="utf-8")

    with pytest.raises(PaddleOCRPrivateArtifactError, match="output directory must be empty"):
        package_paddleocr_private_artifact(
            queue_dir=queue_dir,
            export_dir=export_dir,
            training_output_dir=training_output_dir,
            output_dir=output_dir,
            paddleocr_source_dir=source_dir,
            source_dataset_id="naver-tampermonkey-2026-05",
        )


def _write_queue_dir(tmp_path: Path) -> Path:
    queue_dir = tmp_path / "queue"
    (queue_dir / "images" / "train").mkdir(parents=True)
    (queue_dir / "images" / "train" / "queue-0001-safe.png").write_bytes(b"image-bytes")
    queue_payload = {
        "schema_version": "paddleocr-annotation-queue-v1",
        "generated_at": "2026-05-18T00:00:00+00:00",
        "source_root_hash": "source-root-abc",
        "items": [
            {
                "queue_id": "queue-0001-safe",
                "sample_id": "sample-safe",
                "source_image_id": "image-safe",
                "image_path": "images/train/queue-0001-safe.png",
                "image_sha256": "hash-safe",
                "width": 320,
                "height": 240,
                "mime_type": "image/png",
                "product_group_id": "product-safe",
                "split_group": "split-safe",
                "split": "train",
                "source_kind": "detail",
                "task_types": ["detection", "recognition"],
                "human_verified": False,
                "bootstrap_boxes": [],
                "quality_labels": [],
            }
        ],
    }
    report_payload = {
        "schema_version": "paddleocr-finetuning-queue-report-v1",
        "generated_at": "2026-05-18T00:00:00+00:00",
        "selected_image_count": 1,
        "scanner": {"files_seen": 1, "candidates": 1},
        "split_counts": {"train": 1},
        "source_kind_counts": {"detail": 1},
        "product_group_count": 1,
        "contains_original_paths": False,
        "contains_original_file_names": False,
        "contains_raw_ocr_text": False,
        "contains_provider_payload": False,
        "contains_api_credentials": False,
    }
    (queue_dir / "annotation_queue.json").write_text(
        json.dumps(queue_payload, ensure_ascii=False),
        encoding="utf-8",
    )
    (queue_dir / "public_report.json").write_text(
        json.dumps(report_payload, ensure_ascii=False),
        encoding="utf-8",
    )
    return queue_dir


def _write_export_dir(tmp_path: Path) -> Path:
    export_dir = tmp_path / "export"
    (export_dir / "det").mkdir(parents=True)
    (export_dir / "rec").mkdir(parents=True)
    (export_dir / "det" / "train.txt").write_text(
        'images/train/line.png\t[{"transcription":"비타민 D","points":[[0,0],[1,0],[1,1],[0,1]]}]\n',
        encoding="utf-8",
    )
    (export_dir / "det" / "val.txt").write_text("", encoding="utf-8")
    (export_dir / "rec" / "train.txt").write_text(
        "images/train/crop.png\t비타민 D 25 ug\n",
        encoding="utf-8",
    )
    (export_dir / "rec" / "val.txt").write_text("", encoding="utf-8")
    manifest_payload = {
        "schema_version": "paddleocr-finetuning-manifest-v1",
        "items": [
            {
                "sample_id": "sample-rec-001",
                "image_path": "images/train/crop.png",
                "task_type": "recognition",
                "human_verified": True,
                "transcript_hash": "transcript-hash",
            }
        ],
    }
    report_payload = {
        "item_count": 1,
        "split_counts": {"train": 1},
        "task_type_counts": {"recognition": 1},
        "language_mix_counts": {"ko_en": 1},
        "field_type_counts": {"numeric_unit": 1},
        "human_verified_count": 1,
    }
    (export_dir / "paddleocr-finetuning-manifest.json").write_text(
        json.dumps(manifest_payload, ensure_ascii=False),
        encoding="utf-8",
    )
    (export_dir / "paddleocr-finetuning-distribution.json").write_text(
        json.dumps(report_payload, ensure_ascii=False),
        encoding="utf-8",
    )
    return export_dir


def _write_training_output_dir(tmp_path: Path) -> Path:
    training_output_dir = tmp_path / "models"
    det_inference = training_output_dir / "det" / "inference"
    rec_inference = training_output_dir / "rec" / "inference"
    det_inference.mkdir(parents=True)
    rec_inference.mkdir(parents=True)
    (det_inference / "model.pdmodel").write_bytes(b"det-model")
    (det_inference / "model.pdiparams").write_bytes(b"det-params")
    (rec_inference / "model.pdmodel").write_bytes(b"rec-model")
    (rec_inference / "model.pdiparams").write_bytes(b"rec-params")
    (training_output_dir / "train.log").write_text("training finished\n", encoding="utf-8")
    return training_output_dir


def _write_paddleocr_source_dir(tmp_path: Path) -> Path:
    source_dir = tmp_path / "PaddleOCR"
    tools_dir = source_dir / "tools"
    tools_dir.mkdir(parents=True)
    for name in ("train.py", "eval.py", "export_model.py"):
        (tools_dir / name).write_text("print('stub')\n", encoding="utf-8")
    det_config = source_dir / "configs" / "det" / "PP-OCRv5" / "PP-OCRv5_server_det.yml"
    rec_config = (
        source_dir
        / "configs"
        / "rec"
        / "PP-OCRv5"
        / "multi_language"
        / "korean_PP-OCRv5_mobile_rec.yml"
    )
    det_config.parent.mkdir(parents=True)
    rec_config.parent.mkdir(parents=True)
    det_config.write_text("Global: {}\n", encoding="utf-8")
    rec_config.write_text("Global: {}\n", encoding="utf-8")
    return source_dir
