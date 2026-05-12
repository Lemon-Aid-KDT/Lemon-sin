"""Supplement parser schema tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models.schemas.supplement_parser import SupplementStructuredParseResult


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
