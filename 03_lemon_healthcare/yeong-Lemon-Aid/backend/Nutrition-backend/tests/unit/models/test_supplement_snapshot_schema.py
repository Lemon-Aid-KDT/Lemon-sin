"""Supplement parsed snapshot schema tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from src.models.schemas.supplement_snapshot import (
    SUPPLEMENT_PARSED_SNAPSHOT_V2,
    SUPPLEMENT_PARSED_SNAPSHOT_V3,
    SupplementParsedSnapshotV2,
    SupplementParsedSnapshotV3,
    parse_supplement_snapshot,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "supplement_labels"


def test_snapshot_v2_generates_json_schema() -> None:
    """Verify the versioned snapshot contract can produce JSON Schema."""
    schema = SupplementParsedSnapshotV2.model_json_schema()

    assert schema["title"] == "SupplementParsedSnapshotV2"
    assert "source" in schema["properties"]
    assert schema["properties"]["schema_version"]["const"] == SUPPLEMENT_PARSED_SNAPSHOT_V2


def test_snapshot_v3_generates_json_schema() -> None:
    """Verify the expanded versioned snapshot contract can produce JSON Schema."""
    schema = SupplementParsedSnapshotV3.model_json_schema()

    assert schema["title"] == "SupplementParsedSnapshotV3"
    assert "ingredients" in schema["properties"]
    assert "evidence_spans" in schema["properties"]
    assert "layout_context" in schema["properties"]
    assert schema["properties"]["schema_version"]["const"] == SUPPLEMENT_PARSED_SNAPSHOT_V3


def test_snapshot_v2_validates_expected_fixture_snapshots() -> None:
    """Verify committed expected snapshots satisfy the V2 contract."""
    manifest = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
    cases = manifest["cases"]

    for case in cases:
        snapshot_path = FIXTURE_ROOT / case["expected_snapshot_path"]
        snapshot = SupplementParsedSnapshotV2.model_validate_json(
            snapshot_path.read_text(encoding="utf-8")
        )
        assert snapshot.schema_version == SUPPLEMENT_PARSED_SNAPSHOT_V2
        assert snapshot.requires_user_confirmation is True
        assert snapshot.source.raw_image_stored is False
        assert snapshot.source.raw_ocr_text_stored is False
        assert snapshot.source.raw_provider_payload_stored is False


def test_snapshot_v2_rejects_extra_fields_and_raw_storage_flags() -> None:
    """Verify V2 snapshots reject schema drift and raw storage claims."""
    valid_payload: dict[str, Any] = {
        "schema_version": SUPPLEMENT_PARSED_SNAPSHOT_V2,
        "requires_user_confirmation": True,
        "source": {
            "ocr_provider": "manual",
            "ocr_confidence": None,
            "layout_available": False,
            "raw_image_stored": False,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
        },
    }

    with pytest.raises(ValidationError):
        SupplementParsedSnapshotV2.model_validate({**valid_payload, "raw_ocr_text": "secret"})

    invalid_storage_payload = {
        **valid_payload,
        "source": {**valid_payload["source"], "raw_ocr_text_stored": True},
    }
    with pytest.raises(ValidationError):
        SupplementParsedSnapshotV2.model_validate(invalid_storage_payload)


def test_snapshot_v2_normalizes_review_lists() -> None:
    """Verify low-confidence fields and warnings are normalized."""
    snapshot = SupplementParsedSnapshotV2.model_validate(
        {
            "schema_version": SUPPLEMENT_PARSED_SNAPSHOT_V2,
            "requires_user_confirmation": True,
            "source": {
                "ocr_provider": "manual",
                "ocr_confidence": None,
                "layout_available": False,
                "raw_image_stored": False,
                "raw_ocr_text_stored": False,
                "raw_provider_payload_stored": False,
            },
            "low_confidence_fields": [" product ", "", "product"],
            "warnings": ["확인 필요", " ", "확인 필요"],
        }
    )

    assert snapshot.low_confidence_fields == ["product"]
    assert snapshot.warnings == ["확인 필요"]


def test_snapshot_v3_rejects_raw_storage_and_dangling_evidence() -> None:
    """Verify V3 snapshots reject raw storage flags and dangling evidence refs."""
    valid_payload: dict[str, Any] = {
        "schema_version": SUPPLEMENT_PARSED_SNAPSHOT_V3,
        "requires_user_confirmation": True,
        "source": {
            "ocr_provider": "manual",
            "ocr_confidence": None,
            "layout_available": False,
            "raw_image_stored": False,
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "raw_model_response_stored": False,
        },
        "ingredients": [
            {
                "display_name": "비타민 C",
                "amount": 500,
                "unit": "mg",
                "confidence": 0.9,
                "source": "ocr_llm_preview",
                "evidence_refs": ["span:ingredient:0"],
            }
        ],
        "evidence_spans": [
            {
                "span_id": "span:ingredient:0",
                "source_type": "ocr_text",
                "section_type": "nutrition_info",
                "text_excerpt": "비타민 C 500 mg",
            }
        ],
    }

    snapshot = SupplementParsedSnapshotV3.model_validate(valid_payload)

    assert snapshot.ingredients[0].display_name == "비타민 C"

    with pytest.raises(ValidationError):
        SupplementParsedSnapshotV3.model_validate(
            {
                **valid_payload,
                "source": {**valid_payload["source"], "raw_model_response_stored": True},
            }
        )

    with pytest.raises(ValidationError, match="Unknown evidence_refs"):
        SupplementParsedSnapshotV3.model_validate(
            {
                **valid_payload,
                "ingredients": [
                    {
                        "display_name": "비타민 C",
                        "confidence": 0.9,
                        "source": "ocr_llm_preview",
                        "evidence_refs": ["span:missing"],
                    }
                ],
            }
        )


def test_parse_supplement_snapshot_upcasts_v2_fixture_to_v3() -> None:
    """Verify Phase 0 V2 fixture snapshots can be read as V3."""
    raw = json.loads(
        (FIXTURE_ROOT / "expected" / "ko_dense_table_001.snapshot_v2.json").read_text(
            encoding="utf-8"
        )
    )

    snapshot = parse_supplement_snapshot(raw)

    assert snapshot.schema_version == SUPPLEMENT_PARSED_SNAPSHOT_V3
    assert snapshot.product.product_name == "테스트 멀티비타민"
    assert snapshot.ingredients[0].display_name == "비타민 C"
    assert snapshot.source.raw_provider_payload_stored is False


def test_parse_supplement_snapshot_upcasts_legacy_runtime_shape_to_v3() -> None:
    """Verify current runtime snapshot rows can be read as V3."""
    snapshot = parse_supplement_snapshot(
        {
            "parsed_product": {
                "product_name": "비타민 D 1000",
                "serving_size": "1 tablet",
                "daily_servings": 1,
            },
            "ingredient_candidates": [
                {
                    "display_name": "비타민 D",
                    "amount": 25,
                    "unit": "ug",
                    "confidence": 0.91,
                }
            ],
            "low_confidence_fields": ["manufacturer"],
            "parser_metadata": {
                "input_provider": "manual-test",
                "raw_ocr_text_stored": False,
                "raw_model_response_stored": False,
            },
        }
    )

    assert snapshot.schema_version == SUPPLEMENT_PARSED_SNAPSHOT_V3
    assert snapshot.source.ocr_provider == "manual"
    assert snapshot.product.product_name == "비타민 D 1000"
    assert snapshot.serving.serving_size_text == "1 tablet"
    assert snapshot.ingredients[0].display_name == "비타민 D"
    assert snapshot.low_confidence_fields == ["manufacturer"]
