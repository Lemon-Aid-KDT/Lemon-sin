"""Tests for private PaddleOCR fine-tuning queue preparation."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from scripts.prepare_paddleocr_finetuning_queue import (
    prepare_paddleocr_finetuning_queue,
    scan_image_candidates,
)


def test_prepare_queue_copies_redacted_stratified_images(tmp_path: Path) -> None:
    """Verify queue prep copies images privately and stores no source identifiers."""
    source_root = tmp_path / "source"
    detail_dir = source_root / "brand-a" / "product-1" / "상세페이지"
    review_dir = source_root / "brand-b" / "product-2" / "리뷰"
    detail_dir.mkdir(parents=True)
    review_dir.mkdir(parents=True)
    _write_image(detail_dir / "label-detail.jpg", size=(320, 240))
    _write_image(review_dir / "label-review.png", size=(300, 240))
    _write_image(review_dir / "too-small.png", size=(20, 20))
    _write_image(review_dir / "duplicate.png", size=(300, 240))
    (source_root / "not-image.txt").write_text("not an image", encoding="utf-8")
    before_source_files = sorted(path.relative_to(source_root) for path in source_root.rglob("*"))

    output_dir = tmp_path / "queue"
    summary = prepare_paddleocr_finetuning_queue(
        source_root=source_root,
        output_dir=output_dir,
        max_source_images=2,
        min_pixels=10_000,
    )

    after_source_files = sorted(path.relative_to(source_root) for path in source_root.rglob("*"))
    assert before_source_files == after_source_files
    assert summary["selected_image_count"] == 2
    assert summary["raw_source_paths_stored"] is False
    queue = json.loads((output_dir / "annotation_queue.json").read_text(encoding="utf-8"))
    assert queue["schema_version"] == "paddleocr-annotation-queue-v1"
    assert len(queue["items"]) == 2
    assert all(item["human_verified"] is False for item in queue["items"])
    assert all(Path(output_dir, item["image_path"]).exists() for item in queue["items"])
    queue_text = json.dumps(queue, ensure_ascii=False)
    assert "label-detail.jpg" not in queue_text
    assert "label-review.png" not in queue_text
    report = json.loads((output_dir / "public_report.json").read_text(encoding="utf-8"))
    assert report["contains_original_paths"] is False
    assert report["contains_raw_ocr_text"] is False


def test_scan_candidates_excludes_gif_duplicates_and_too_small(tmp_path: Path) -> None:
    """Verify scanner excludes unsafe or low-value images before queue selection."""
    source_root = tmp_path / "source"
    image_dir = source_root / "brand" / "product" / "리뷰"
    image_dir.mkdir(parents=True)
    _write_image(image_dir / "a.png", size=(260, 220))
    _write_image(image_dir / "duplicate.png", size=(260, 220))
    _write_image(image_dir / "small.png", size=(10, 10))
    _write_image(image_dir / "animated.gif", size=(260, 220), image_format="GIF")

    candidates = list(scan_image_candidates(source_root=source_root, min_pixels=10_000))

    assert len(candidates) == 1
    assert candidates[0].source_kind == "review"
    assert candidates[0].image_sha256


def _write_image(path: Path, *, size: tuple[int, int], image_format: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", size, color=(255, 255, 255))
    image.save(path, format=image_format)
