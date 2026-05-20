"""Supplement parser schema tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from src.models.schemas.supplement_parser import (
    SUPPLEMENT_PARSER_OUTPUT_V2,
    SupplementOCRTextParseRequest,
    SupplementStructuredParseResult,
    SupplementStructuredParseResultV2,
)


def test_structured_parse_result_v2_generates_json_schema() -> None:
    """Verify the expanded parser contract can generate JSON Schema."""
    schema = SupplementStructuredParseResultV2.model_json_schema()

    assert schema["title"] == "SupplementStructuredParseResultV2"
    assert schema["properties"]["schema_version"]["const"] == SUPPLEMENT_PARSER_OUTPUT_V2
    assert "ingredients" in schema["properties"]
    assert "evidence_spans" in schema["properties"]


def test_structured_parse_result_v2_validates_label_fact_sections() -> None:
    """Verify V2 stores label facts and redacted evidence references."""
    result = SupplementStructuredParseResultV2.model_validate(
        {
            "schema_version": SUPPLEMENT_PARSER_OUTPUT_V2,
            "product": {
                "product_name": "비타민 C 플러스",
                "evidence_refs": ["span:product:0"],
            },
            "serving": {
                "serving_size_text": "1회 1정",
                "serving_amount": 1,
                "serving_unit": "정",
                "daily_servings": 1,
                "evidence_refs": ["span:serving:0"],
            },
            "ingredients": [
                {
                    "display_name": "비타민 C",
                    "amount": 500,
                    "unit": "mg",
                    "confidence": 0.94,
                    "evidence_refs": ["span:ingredient:0", "span:ingredient:0"],
                }
            ],
            "intake_method": {
                "text": "1일 1회, 1회 1정을 물과 함께 섭취",
                "structured": {
                    "frequency": "daily",
                    "times_per_day": 1,
                    "amount_per_time": 1,
                    "amount_unit": "정",
                    "with_food": "unknown",
                },
                "evidence_refs": ["span:serving:0"],
            },
            "functional_claims": [
                {
                    "text": "결합조직 형성과 기능 유지에 필요",
                    "claim_type": "label_claim",
                    "evidence_refs": ["span:function:0"],
                }
            ],
            "evidence_spans": [
                {
                    "span_id": "span:product:0",
                    "source_type": "ocr_text",
                    "section_type": "unknown",
                    "text_excerpt": "비타민 C 플러스",
                },
                {
                    "span_id": "span:serving:0",
                    "source_type": "ocr_text",
                    "section_type": "intake_method",
                    "text_excerpt": "1일 1회, 1회 1정을 물과 함께 섭취",
                },
                {
                    "span_id": "span:ingredient:0",
                    "source_type": "ocr_text",
                    "section_type": "nutrition_info",
                    "text_excerpt": "비타민 C 500 mg",
                },
                {
                    "span_id": "span:function:0",
                    "source_type": "ocr_text",
                    "section_type": "functional_info",
                    "text_excerpt": "결합조직 형성과 기능 유지에 필요",
                },
            ],
            "low_confidence_fields": [" manufacturer ", "", "manufacturer"],
            "warnings": ["확인 필요", " ", "확인 필요"],
        }
    )

    assert result.product.product_name == "비타민 C 플러스"
    assert result.parsed_product.serving_size == "1회 1정"
    assert result.ingredients[0].evidence_refs == ["span:ingredient:0"]
    assert result.ingredient_candidates[0].display_name == "비타민 C"
    assert result.low_confidence_fields == ["manufacturer"]
    assert result.warnings == ["확인 필요"]


def test_structured_parse_result_v2_flags_ungrounded_evidence_fields() -> None:
    """Verify parser values unsupported by evidence are routed to user review."""
    result = SupplementStructuredParseResultV2.model_validate(
        {
            "schema_version": SUPPLEMENT_PARSER_OUTPUT_V2,
            "ingredients": [
                {
                    "display_name": "비타민 D",
                    "amount": 1000,
                    "unit": "IU",
                    "confidence": 0.8,
                    "evidence_refs": ["span:ingredient:0"],
                }
            ],
            "evidence_spans": [
                {
                    "span_id": "span:ingredient:0",
                    "source_type": "ocr_text",
                    "section_type": "nutrition_info",
                    "text_excerpt": "비타민 D 25 ug",
                }
            ],
        }
    )

    assert "ingredients.0.amount" in result.low_confidence_fields
    assert "ingredients.0.unit" in result.low_confidence_fields
    assert "evidence_grounding_mismatch" in result.warnings


def test_structured_parse_result_v2_rejects_llm_nutrient_code_and_recommendation() -> None:
    """Verify V2 rejects LLM-generated codes and recommendations."""
    with pytest.raises(ValidationError):
        SupplementStructuredParseResultV2.model_validate(
            {
                "ingredients": [
                    {
                        "display_name": "비타민 D",
                        "nutrient_code": "VITD",
                        "confidence": 0.8,
                    }
                ]
            }
        )

    with pytest.raises(ValidationError):
        SupplementStructuredParseResultV2.model_validate(
            {
                "recommendation": "매일 드세요.",
            }
        )


def test_structured_parse_result_v2_rejects_dangling_evidence_ref() -> None:
    """Verify evidence references must point to declared evidence spans."""
    with pytest.raises(ValidationError, match="Unknown evidence_refs"):
        SupplementStructuredParseResultV2.model_validate(
            {
                "ingredients": [
                    {
                        "display_name": "비타민 D",
                        "confidence": 0.8,
                        "evidence_refs": ["span:missing"],
                    }
                ],
                "evidence_spans": [],
            }
        )


def test_structured_parse_result_rejects_fake_nutrient_code() -> None:
    """Verify the LLM cannot invent internal nutrient codes during extraction."""
    with pytest.raises(ValidationError):
        SupplementStructuredParseResult.model_validate(
            {
                "parsed_product": {"product_name": "테스트 비타민"},
                "ingredient_candidates": [
                    {
                        "display_name": "비타민 D",
                        "nutrient_code": "vitamin_d_ug",
                        "amount": 25,
                        "unit": "ug",
                        "confidence": 0.9,
                    }
                ],
                "low_confidence_fields": [],
                "warnings": [],
            }
        )


def test_structured_parse_result_normalizes_warning_lists() -> None:
    """Verify repeated or blank warning strings are removed."""
    result = SupplementStructuredParseResult.model_validate(
        {
            "parsed_product": {"product_name": "테스트 비타민"},
            "ingredient_candidates": [],
            "low_confidence_fields": [" manufacturer ", "", "manufacturer"],
            "warnings": ["사용자 확인 필요", " ", "사용자 확인 필요"],
        }
    )

    assert result.low_confidence_fields == ["manufacturer"]
    assert result.warnings == ["사용자 확인 필요"]


def test_ocr_text_parse_request_bounds_provider_and_confidence() -> None:
    """Verify OCR text attach requests reject invalid provider metadata."""
    request = SupplementOCRTextParseRequest.model_validate(
        {
            "ocr_text": " 비타민 D 1000 ",
            "ocr_provider": " manual ",
            "ocr_confidence": 0.91,
        }
    )

    assert request.ocr_text == "비타민 D 1000"
    assert request.ocr_provider == "manual"
    assert request.ocr_confidence == 0.91

    with pytest.raises(ValidationError):
        SupplementOCRTextParseRequest.model_validate(
            {"ocr_text": "비타민 D", "ocr_provider": "manual", "ocr_confidence": 1.01}
        )

    with pytest.raises(ValidationError):
        SupplementOCRTextParseRequest.model_validate(
            {"ocr_text": "비타민 D", "ocr_provider": "", "ocr_confidence": None}
        )
