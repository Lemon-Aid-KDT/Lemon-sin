"""Parser/domain correction schema tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.models.schemas.parser_domain_correction import (
    DomainCorrectionArtifactManifest,
    DomainCorrectionCandidate,
    DomainCorrectionRule,
    ParserCorrectionEvent,
)


def test_parser_correction_event_rejects_raw_fields_and_control_text() -> None:
    """Verify correction events cannot carry raw OCR text or unsafe strings."""
    payload = {
        "analysis_id": uuid4(),
        "ocr_text_hash": "a" * 64,
        "parser_algorithm_version": "supplement-ollama-parser-v1.0.0",
        "field_path": "ingredients[0].display_name",
        "correction_type": "ingredient_alias",
        "before_value_hash": "b" * 64,
        "confirmed_value": "Vitamin D",
        "consent_scope": ["parser_domain_correction"],
    }

    event = ParserCorrectionEvent.model_validate(payload)

    assert event.confirmed_value == "Vitamin D"
    with pytest.raises(ValidationError):
        ParserCorrectionEvent.model_validate({**payload, "raw_ocr_text": "Vitamin D 25 ug"})
    with pytest.raises(ValidationError, match="confirmed_value"):
        ParserCorrectionEvent.model_validate({**payload, "confirmed_value": "Vitamin\tD"})


def test_amount_parse_event_must_target_amount_field() -> None:
    """Verify numeric correction events cannot apply outside amount fields."""
    with pytest.raises(ValidationError, match="amount_parse"):
        ParserCorrectionEvent.model_validate(
            {
                "analysis_id": uuid4(),
                "ocr_text_hash": "a" * 64,
                "parser_algorithm_version": "supplement-ollama-parser-v1.0.0",
                "field_path": "ingredients[0].display_name",
                "correction_type": "amount_parse",
                "before_value_hash": "b" * 64,
                "confirmed_value": 25,
                "consent_scope": ["parser_domain_correction"],
            }
        )


def test_domain_correction_candidate_marks_conflicts_for_review() -> None:
    """Verify conflicted candidates cannot silently remain pending."""
    candidate = DomainCorrectionCandidate(
        candidate_id="candidate-001",
        correction_type="unit_normalization",
        field_path="ingredients[0].unit",
        before_value_hash="a" * 64,
        proposed_value="ug",
        support_count=3,
        conflict_count=1,
        status="pending",
    )

    assert candidate.status == "needs_review"


def test_domain_correction_artifact_allows_only_valid_reviewed_rules() -> None:
    """Verify reviewed artifact rules validate correction-specific requirements."""
    artifact = DomainCorrectionArtifactManifest(
        domain_dictionary_version="domain-dict-v1",
        confusion_map_version="confusion-map-v1",
        created_from_manifest_checksum="manifest-checksum",
        rules=[
            DomainCorrectionRule(
                rule_id="rule-vitd-alias",
                rule_status="approved",
                correction_type="ingredient_alias",
                field_path="ingredients.display_name",
                match_value="Vitarnin D",
                replacement_value="Vitamin D",
                canonical_display_name="Vitamin D",
                nutrient_code="vitamin_d_ug",
            )
        ],
    )

    assert artifact.rules[0].rule_status == "approved"
    with pytest.raises(ValidationError, match="nutrient_code"):
        DomainCorrectionRule(
            rule_id="bad-alias",
            rule_status="approved",
            correction_type="ingredient_alias",
            field_path="ingredients.display_name",
            match_value="Vitarnin D",
            replacement_value="Vitamin D",
        )
