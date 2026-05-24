"""Tests for Naver review-image local PII screening manifest generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from scripts import build_naver_tampermonkey_review_pii_screening_manifest as builder


def _write_image(path: Path, *, size: tuple[int, int] = (640, 480)) -> None:
    """Write a deterministic test image."""
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, "white").save(path, format="JPEG")


def _jsonl_rows(path: Path) -> list[dict[str, object]]:
    """Read JSONL rows from a test artifact."""
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_build_review_pii_screening_manifest_is_local_only(tmp_path: Path) -> None:
    """Verify review rows are emitted as local-only PII screening tasks."""
    source_root = tmp_path / "naver"
    _write_image(source_root / "[오메가3]" / "제품A_123456789" / "리뷰" / "r_1.jpg")
    _write_image(source_root / "[오메가3]" / "제품A_123456789" / "상세페이지" / "d_1.jpg")

    summary = builder.build_review_pii_screening_manifest(
        source_root=source_root,
        output_dir=tmp_path / "out",
        scan_limit=10,
        sample_size=0,
        min_width=100,
        min_height=100,
        max_bytes=1_000_000,
    )

    assert summary["review_candidate_count"] == 1
    assert summary["manifest_row_count"] == 1
    assert summary["external_transfer_allowed_rows"] == 0
    assert summary["pending_local_screening_rows"] == 1
    assert summary["product_dir_literals_stored"] is False
    rows = _jsonl_rows(Path(summary["manifest"]))
    row = rows[0]
    assert row["schema_version"] == builder.SCHEMA_VERSION
    assert row["section"] == "review"
    assert row["contains_personal_data"] is None
    assert row["pii_screening_status"] == "pending_local_screening"
    assert row["external_transfer_allowed"] is False
    assert row["local_processing_allowed"] is True
    assert row["operator_decision_required"] is True
    assert str(row["image_path"]).startswith("$NAVER_TAMPERMONKEY_SOURCE_ROOT/")
    assert '"product_dir":' not in json.dumps(row, ensure_ascii=False)
    assert "product_dir_hash" in row["product"]  # type: ignore[operator]


def test_build_review_pii_screening_manifest_supports_sampling(tmp_path: Path) -> None:
    """Verify sampling can bound large local review queues."""
    source_root = tmp_path / "naver"
    _write_image(source_root / "[비타민C]" / "제품A_11111" / "리뷰" / "r_1.jpg")
    _write_image(source_root / "[마그네슘]" / "제품B_22222" / "리뷰" / "r_1.jpg")

    summary = builder.build_review_pii_screening_manifest(
        source_root=source_root,
        output_dir=tmp_path / "out",
        scan_limit=10,
        sample_size=1,
        min_width=100,
        min_height=100,
        max_bytes=1_000_000,
    )

    assert summary["review_candidate_count"] == 2
    assert summary["manifest_row_count"] == 1


def test_build_review_pii_screening_manifest_rejects_unsafe_payloads() -> None:
    """Verify unsafe payload helper blocks raw fields and local paths."""
    with pytest.raises(ValueError, match="raw_ocr_text"):
        builder._reject_unsafe_payload({"raw_ocr_text": "do not persist"})
    with pytest.raises(ValueError, match="product_dir"):
        builder._reject_unsafe_payload({"product_dir": "제품A_123456789"})
    with pytest.raises(ValueError, match="local path"):
        builder._reject_unsafe_payload({"image_path": "/Volumes/Corsair/raw.jpg"})


def test_build_review_pii_screening_manifest_validates_options(tmp_path: Path) -> None:
    """Verify invalid options fail before scanning."""
    source_root = tmp_path / "naver"
    source_root.mkdir()

    with pytest.raises(ValueError, match="uppercase environment"):
        builder.build_review_pii_screening_manifest(
            source_root=source_root,
            output_dir=tmp_path / "out",
            image_root_env_var="not_upper",
        )
    with pytest.raises(ValueError, match="sample_size"):
        builder.build_review_pii_screening_manifest(
            source_root=source_root,
            output_dir=tmp_path / "out",
            sample_size=-1,
        )
