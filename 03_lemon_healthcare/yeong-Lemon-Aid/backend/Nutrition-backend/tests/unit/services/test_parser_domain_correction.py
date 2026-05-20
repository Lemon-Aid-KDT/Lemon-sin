"""Parser/domain correction service tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from src.config import Settings
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.parser_domain_correction import (
    DomainCorrectionArtifactManifest,
    DomainCorrectionRule,
)
from src.models.schemas.supplement import SupplementAnalysisStatus, UserSupplementCreate
from src.models.schemas.supplement_parser import SupplementStructuredParseResultV2
from src.services.parser_domain_correction import (
    ParserDomainCorrectionError,
    apply_parser_domain_corrections,
    build_parser_correction_events,
    evaluate_domain_correction_promotion_gate,
    mine_domain_correction_candidates,
    reject_forbidden_correction_fields,
    with_domain_correction_artifact_checksum,
)


def _preview() -> SupplementAnalysisRun:
    """Return a preview row with a V3 parsed snapshot.

    Returns:
        Supplement analysis preview fixture.
    """
    now = datetime.now(UTC)
    return SupplementAnalysisRun(
        id=uuid4(),
        owner_subject="https://auth.example.com/::user_123",
        client_request_id="client-1",
        status=SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value,
        image_sha256="a" * 64,
        image_mime_type="image/png",
        image_size_bytes=128,
        ocr_provider="manual",
        ocr_text_hash="c" * 64,
        parsed_snapshot={
            "schema_version": "supplement-parsed-snapshot-v3",
            "requires_user_confirmation": True,
            "source": {
                "ocr_provider": "manual",
                "ocr_confidence": 0.9,
                "layout_available": False,
                "raw_image_stored": False,
                "raw_ocr_text_stored": False,
                "raw_provider_payload_stored": False,
                "raw_model_response_stored": False,
            },
            "ingredients": [
                {
                    "display_name": "Vitarnin D",
                    "amount": 2.5,
                    "unit": "㎍",
                    "confidence": 0.6,
                    "source": "ocr_llm_preview",
                    "evidence_refs": ["span:ingredient:0"],
                }
            ],
            "evidence_spans": [
                {
                    "span_id": "span:ingredient:0",
                    "source_type": "ocr_text",
                    "section_type": "nutrition_info",
                    "text_excerpt": "Vitarnin D 2.5 ㎍",
                }
            ],
        },
        match_snapshot={},
        warnings=[],
        algorithm_version="supplement-ollama-parser-v1.0.0",
        expires_at=now + timedelta(minutes=30),
        created_at=now,
        updated_at=now,
    )


def _request() -> UserSupplementCreate:
    """Return a user-confirmed supplement request.

    Returns:
        User-confirmed supplement request.
    """
    return UserSupplementCreate.model_validate(
        {
            "analysis_id": uuid4(),
            "display_name": "Vitamin D 1000",
            "ingredients": [
                {
                    "display_name": "Vitamin D",
                    "nutrient_code": "vitamin_d_ug",
                    "amount": 25,
                    "unit": "ug",
                    "confidence": 1,
                    "source": "user_confirmed",
                }
            ],
            "serving": {"amount": 1, "unit": "tablet", "daily_servings": 1},
            "user_confirmed": True,
        }
    )


def _parse_result() -> SupplementStructuredParseResultV2:
    """Return a parser result containing correctable ingredient text.

    Returns:
        Structured parser result fixture.
    """
    return SupplementStructuredParseResultV2.model_validate(
        {
            "schema_version": "supplement-parser-output-v2",
            "ingredients": [
                {
                    "display_name": "Vitarnin D",
                    "amount": 25,
                    "unit": "㎍",
                    "confidence": 0.6,
                    "evidence_refs": ["span:ingredient:0"],
                }
            ],
            "evidence_spans": [
                {
                    "span_id": "span:ingredient:0",
                    "source_type": "ocr_text",
                    "section_type": "nutrition_info",
                    "text_excerpt": "Vitarnin D 25 ㎍",
                }
            ],
        }
    )


def _artifact_path(tmp_path: Path, *, rule_status: str = "approved") -> Path:
    """Write a reviewed artifact fixture.

    Args:
        tmp_path: Pytest temporary directory.
        rule_status: Review status assigned to fixture rules.

    Returns:
        Artifact path.
    """
    artifact = with_domain_correction_artifact_checksum(
        DomainCorrectionArtifactManifest(
            domain_dictionary_version="domain-dict-v1",
            confusion_map_version="confusion-map-v1",
            created_from_manifest_checksum="manifest-checksum",
            rules=[
                DomainCorrectionRule(
                    rule_id="rule-vitd-alias",
                    rule_status=rule_status,  # type: ignore[arg-type]
                    correction_type="ingredient_alias",
                    field_path="ingredients.display_name",
                    match_value="Vitarnin D",
                    replacement_value="Vitamin D",
                    canonical_display_name="Vitamin D",
                    nutrient_code="vitamin_d_ug",
                ),
                DomainCorrectionRule(
                    rule_id="rule-microgram-unit",
                    rule_status=rule_status,  # type: ignore[arg-type]
                    correction_type="unit_normalization",
                    field_path="ingredients.unit",
                    match_value="㎍",
                    replacement_value="ug",
                ),
            ],
        )
    )
    path = tmp_path / "domain-correction.json"
    path.write_text(
        json.dumps(artifact.model_dump(mode="json"), ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def test_build_parser_correction_events_uses_only_confirmed_diffs() -> None:
    """Verify user-confirmed payloads produce redacted correction events."""
    events = build_parser_correction_events(preview=_preview(), request=_request())

    event_types = {event.correction_type for event in events}
    assert event_types == {
        "ingredient_alias",
        "unit_normalization",
        "amount_parse",
        "nutrient_code_selection",
    }
    assert all(event.ocr_text_hash == "c" * 64 for event in events)
    assert all("raw" not in event.model_dump(mode="json") for event in events)


def test_build_parser_correction_events_skips_preview_without_ocr_hash() -> None:
    """Verify preview-only rows without OCR hashes are not learning sources."""
    preview = _preview()
    preview.ocr_text_hash = None

    assert build_parser_correction_events(preview=preview, request=_request()) == ()


def test_mine_domain_correction_candidates_marks_conflicts() -> None:
    """Verify candidate mining preserves conflict review state."""
    events = list(build_parser_correction_events(preview=_preview(), request=_request()))
    conflict = events[0].model_copy(update={"confirmed_value": "Vitamin D3"})
    candidates = mine_domain_correction_candidates([events[0], conflict])

    assert {candidate.status for candidate in candidates} == {"needs_review"}
    assert all(candidate.conflict_count == 1 for candidate in candidates)


def test_apply_parser_domain_corrections_is_fail_closed_when_disabled(tmp_path: Path) -> None:
    """Verify disabled runtime settings produce no correction effects."""
    settings = Settings(
        _env_file=None,
        enable_parser_domain_correction=False,
        parser_domain_correction_artifact_path=_artifact_path(tmp_path),
    )

    result = apply_parser_domain_corrections(_parse_result(), settings)

    assert result.audit_entries == ()
    assert result.unit_overrides_by_ingredient_index == {}
    assert result.alias_catalog_by_ingredient_index == {}


def test_apply_parser_domain_corrections_reports_without_apply(tmp_path: Path) -> None:
    """Verify report-only mode keeps values unchanged but emits audit metadata."""
    settings = Settings(
        _env_file=None,
        enable_parser_domain_correction=True,
        parser_domain_correction_mode="report_only",
        parser_domain_correction_artifact_path=_artifact_path(tmp_path),
    )

    result = apply_parser_domain_corrections(_parse_result(), settings)

    assert {entry.action for entry in result.audit_entries} == {"reported"}
    assert result.unit_overrides_by_ingredient_index == {}
    assert result.alias_catalog_by_ingredient_index == {}


def test_apply_parser_domain_corrections_uses_only_approved_rules(tmp_path: Path) -> None:
    """Verify apply mode ignores unapproved artifacts."""
    settings = Settings(
        _env_file=None,
        enable_parser_domain_correction=True,
        parser_domain_correction_mode="apply_reviewed",
        parser_domain_correction_artifact_path=_artifact_path(tmp_path, rule_status="disabled"),
    )

    result = apply_parser_domain_corrections(_parse_result(), settings)

    assert result.audit_entries == ()
    assert result.unit_overrides_by_ingredient_index == {}


def test_apply_parser_domain_corrections_applies_reviewed_rules(tmp_path: Path) -> None:
    """Verify approved alias and unit rules can be applied deterministically."""
    settings = Settings(
        _env_file=None,
        enable_parser_domain_correction=True,
        parser_domain_correction_mode="apply_reviewed",
        parser_domain_correction_artifact_path=_artifact_path(tmp_path),
    )

    result = apply_parser_domain_corrections(_parse_result(), settings)

    assert result.unit_overrides_by_ingredient_index == {0: "ug"}
    assert result.alias_catalog_by_ingredient_index[0][0].nutrient_code == "vitamin_d_ug"
    assert {entry.action for entry in result.audit_entries} == {"applied"}


def test_reject_forbidden_correction_fields_blocks_raw_text() -> None:
    """Verify reports and artifacts cannot include raw OCR text."""
    with pytest.raises(ParserDomainCorrectionError, match="raw_ocr_text"):
        reject_forbidden_correction_fields({"nested": {"raw_ocr_text": "Vitamin D 25 ug"}})


def test_domain_correction_promotion_gate_requires_improvement_and_safety() -> None:
    """Verify promotion gate blocks safety regressions and no-improvement candidates."""
    decision = cast(
        dict[str, Any],
        evaluate_domain_correction_promotion_gate(
            baseline={
                "ingredient_field_exact_rate": 0.7,
                "numeric_exact_rate": 0.7,
                "unit_exact_rate": 0.7,
                "nutrient_code_candidate_hit_rate": 0.7,
                "parser_success_rate": 0.7,
            },
            candidate={
                "ingredient_field_exact_rate": 0.8,
                "numeric_exact_rate": 0.7,
                "unit_exact_rate": 0.7,
                "nutrient_code_candidate_hit_rate": 0.7,
                "parser_success_rate": 0.7,
                "fabricated_field_count": 0,
                "false_correction_count": 0,
                "raw_text_leak_count": 0,
            },
        ),
    )

    assert decision["promotable"] is True

    failed = cast(
        dict[str, Any],
        evaluate_domain_correction_promotion_gate(
            baseline={
                "ingredient_field_exact_rate": 0.7,
                "numeric_exact_rate": 0.7,
                "unit_exact_rate": 0.7,
                "nutrient_code_candidate_hit_rate": 0.7,
                "parser_success_rate": 0.7,
            },
            candidate={
                "ingredient_field_exact_rate": 0.8,
                "numeric_exact_rate": 0.7,
                "unit_exact_rate": 0.7,
                "nutrient_code_candidate_hit_rate": 0.7,
                "parser_success_rate": 0.7,
                "fabricated_field_count": 1,
            },
        ),
    )

    assert failed["promotable"] is False
    assert "safety_metric_failed:fabricated_field_count" in failed["errors"]
