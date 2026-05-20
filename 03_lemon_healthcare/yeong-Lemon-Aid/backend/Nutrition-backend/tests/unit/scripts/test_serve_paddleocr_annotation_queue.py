"""Tests for the local PaddleOCR annotation queue helper."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from src.learning.paddleocr_finetuning import PaddleOCRFineTuningExportError

from scripts.serve_paddleocr_annotation_queue import (
    AnnotationQueueError,
    annotation_to_samples,
    load_annotation_queue,
    write_verified_manifest,
)


def test_annotation_payload_exports_human_verified_samples(tmp_path: Path) -> None:
    """Verify human-verified boxes and transcripts become exporter-ready samples."""
    queue_dir = _write_queue(tmp_path)
    queue = load_annotation_queue(queue_dir)
    queue_item = queue["items"][0]
    annotation = {
        "queue_id": queue_item["queue_id"],
        "human_verified": True,
        "field_type": "numeric_unit",
        "language_mix": "ko_en",
        "boxes": [
            {
                "transcription": "비타민 D 25 ug",
                "points": [[10, 10], [120, 10], [120, 28], [10, 28]],
            },
            {
                "transcription": "ignored",
                "points": [[0, 0], [5, 0], [5, 5], [0, 5]],
                "ignore": True,
            },
        ],
        "recognition_transcripts": ["비타민 D 25 ug"],
    }

    samples = annotation_to_samples(queue_item=queue_item, annotation=annotation)
    summary = write_verified_manifest(queue_dir=queue_dir, annotations=[annotation])

    assert len(samples) == 2
    assert samples[0]["task_type"] == "detection"
    assert samples[0]["boxes"][1]["transcription"] == "###"
    assert samples[1]["task_type"] == "recognition"
    assert samples[1]["verified_transcript"] == "비타민 D 25 ug"
    manifest = json.loads(Path(summary["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "paddleocr-finetuning-manifest-v1"
    assert len(manifest["items"]) == 2
    assert manifest["items"][1]["verified_transcript"] == "비타민 D 25 ug"
    assert summary["raw_ocr_text_stored"] is False


def test_annotation_rejects_unverified_or_raw_payloads(tmp_path: Path) -> None:
    """Verify raw provider payloads and unverified labels are rejected."""
    queue_dir = _write_queue(tmp_path)
    queue_item = load_annotation_queue(queue_dir)["items"][0]

    with pytest.raises(AnnotationQueueError, match="human_verified"):
        annotation_to_samples(
            queue_item=queue_item,
            annotation={"queue_id": queue_item["queue_id"], "human_verified": False},
        )
    with pytest.raises(PaddleOCRFineTuningExportError, match="raw_provider_payload"):
        annotation_to_samples(
            queue_item=queue_item,
            annotation={
                "queue_id": queue_item["queue_id"],
                "human_verified": True,
                "raw_provider_payload": {"text": "not allowed"},
            },
        )


def _write_queue(tmp_path: Path) -> Path:
    queue_dir = tmp_path / "queue"
    queue_dir.mkdir()
    (queue_dir / "images" / "train").mkdir(parents=True)
    (queue_dir / "images" / "train" / "queue-0001-abcdef123456.png").write_bytes(b"fake")
    payload = {
        "schema_version": "paddleocr-annotation-queue-v1",
        "generated_at": "2026-05-17T00:00:00+00:00",
        "source_root_hash": "source-root-abcdef1234567890",
        "items": [
            {
                "queue_id": "queue-0001-abcdef123456",
                "sample_id": "sample-abcdef1234567890",
                "source_image_id": "image-abcdef1234567890",
                "image_path": "images/train/queue-0001-abcdef123456.png",
                "image_sha256": "abcdef1234567890abcdef1234567890",
                "width": 320,
                "height": 240,
                "mime_type": "image/png",
                "product_group_id": "product-abcdef1234567890",
                "split_group": "split-abcdef1234567890",
                "split": "train",
                "source_kind": "detail",
                "task_types": ["detection", "recognition"],
                "human_verified": False,
                "bootstrap_boxes": [],
                "quality_labels": ["detail_page"],
            }
        ],
    }
    (queue_dir / "annotation_queue.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    return queue_dir
