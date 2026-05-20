"""Supplement image risk-action mapping tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from src.models.schemas.image_quality import (
    DetectedROI,
    ImageQualityReasonCode,
    ImageQualityReport,
    ImageQualitySeverity,
    ImageQualityStatus,
    QualityIssue,
)
from src.models.schemas.supplement import (
    SupplementBarcodeLookupResponse,
    SupplementBarcodeProductCandidate,
)
from src.services.supplement_image_risk_actions import build_supplement_image_risk_action

_SCENARIO_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "fixtures" / "supplement_label_image_risk_scenarios.json"
)


def _report(
    *issues: QualityIssue,
    rois: list[DetectedROI] | None = None,
) -> ImageQualityReport:
    """Build an image-quality report fixture.

    Args:
        *issues: Quality issues to include.
        rois: Optional ROI metadata.

    Returns:
        Image quality report fixture.
    """
    status: ImageQualityStatus = "acceptable"
    if any(issue.severity == "blocked" for issue in issues):
        status = "blocked"
    elif any(issue.severity == "retake" for issue in issues):
        status = "retake_recommended"
    elif issues:
        status = "needs_review"
    return ImageQualityReport(
        status=status,
        issues=list(issues),
        metrics={"image_width": 400, "image_height": 300},
        detected_rois=rois or [],
        retake_reasons=[
            issue.reason_code for issue in issues if issue.severity in {"retake", "blocked"}
        ],
    )


def _issue(reason_code: ImageQualityReasonCode, severity: ImageQualitySeverity) -> QualityIssue:
    """Build a quality issue fixture.

    Args:
        reason_code: Stable quality reason code.
        severity: Issue severity.

    Returns:
        Quality issue fixture.
    """
    return QualityIssue(
        reason_code=reason_code,
        severity=severity,
        message="Review image quality.",
        evidence={"fixture": True},
    )


def _roi(label: str, *, x: int = 10) -> DetectedROI:
    """Build a detected ROI fixture.

    Args:
        label: ROI label.
        x: Left coordinate.

    Returns:
        Detected ROI fixture.
    """
    return DetectedROI(
        label=label,
        x=x,
        y=10,
        width=120,
        height=160,
        confidence=0.91,
        area_ratio=0.16,
    )


def _scenario_report(scenario: dict[str, Any]) -> ImageQualityReport:
    """Build an image-quality report from a scenario fixture row.

    Args:
        scenario: Scenario fixture row.

    Returns:
        Image quality report fixture.
    """
    issues = [
        _issue(
            cast(ImageQualityReasonCode, item["reason_code"]),
            cast(ImageQualitySeverity, item["severity"]),
        )
        for item in scenario.get("quality_issues", [])
    ]
    rois = [
        DetectedROI(
            label=item.get("label"),
            x=item.get("x", 10),
            y=item.get("y", 10),
            width=item.get("width", 120),
            height=item.get("height", 160),
            confidence=0.91,
            area_ratio=0.16,
        )
        for item in scenario.get("rois", [])
    ]
    return _report(*issues, rois=rois)


def test_risk_scenario_fixture_maps_all_brainstormed_cases() -> None:
    """Verify brainstormed image-risk scenarios have stable expected actions."""
    fixture = json.loads(_SCENARIO_FIXTURE_PATH.read_text(encoding="utf-8"))
    scenarios = fixture["scenarios"]

    assert len(scenarios) == 15
    for scenario in scenarios:
        barcode_lookup = None
        parsed_product_name = None
        if scenario.get("barcode_conflict") is True:
            barcode_lookup = SupplementBarcodeLookupResponse(
                status="review_required",
                candidate_count=1,
                candidates=[
                    SupplementBarcodeProductCandidate(
                        source_id="foodqr:scenario",
                        product_name="Barcode Candidate",
                        match_score=0.91,
                        review_required_reason="user_confirmation_required",
                    )
                ],
            )
            parsed_product_name = "Parsed Label Candidate"
        action = build_supplement_image_risk_action(
            image_quality_report=_scenario_report(scenario),
            barcode_lookup=barcode_lookup,
            parsed_product_name=parsed_product_name,
        )

        assert action.action_required == scenario["expected_action_required"]
        assert action.analysis_scope == scenario["expected_analysis_scope"]
        assert "raw_ocr_text" not in str(action.model_dump())
        assert "raw_provider_payload" not in str(action.model_dump())


def test_risk_action_defaults_to_unknown_when_quality_report_is_absent() -> None:
    """Verify intake-only previews do not claim full-label image safety."""
    action = build_supplement_image_risk_action(image_quality_report=None)

    assert action.analysis_scope == "unknown"
    assert action.action_required == "none"
    assert action.detected_product_regions == []


def test_risk_action_requires_region_selection_for_multi_product() -> None:
    """Verify multi-product images do not select a product region automatically."""
    action = build_supplement_image_risk_action(
        image_quality_report=_report(
            _issue("multi_product", "review"),
            rois=[_roi("supplement_bottle"), _roi("supplement_bottle", x=180)],
        )
    )

    assert action.action_required == "product_region_selection_required"
    assert action.analysis_scope == "multi_product_review"
    assert action.image_role == "mixed"
    assert action.selected_region_id is None
    assert len(action.detected_product_regions) == 2
    assert not any(region.selected for region in action.detected_product_regions)


def test_risk_action_marks_cover_only_as_identity_only() -> None:
    """Verify front-label images request a supplement-facts image before reliance."""
    action = build_supplement_image_risk_action(
        image_quality_report=_report(
            _issue("cover_only", "retake"),
            rois=[_roi("brand_front_label")],
        )
    )

    assert action.action_required == "additional_label_image_required"
    assert action.analysis_scope == "identity_only"
    assert action.image_role == "front_label"
    assert action.missing_required_sections == ["supplement_facts"]


def test_risk_action_recommends_retake_for_partial_or_blurry_table() -> None:
    """Verify image quality failures become retake actions without blocking."""
    action = build_supplement_image_risk_action(
        image_quality_report=_report(
            _issue("partial_table", "retake"),
            _issue("blurred_text", "retake"),
            rois=[_roi("supplement_facts_table")],
        )
    )

    assert action.action_required == "retake_recommended"
    assert action.analysis_scope == "full_image_review"
    assert action.missing_required_sections == ["supplement_facts"]
    assert action.selected_region_id == "roi-001"


def test_risk_action_degrades_roi_not_found_to_review() -> None:
    """Verify detector misses become full-image review rather than crop selection."""
    action = build_supplement_image_risk_action(
        image_quality_report=_report(_issue("roi_not_found", "review"))
    )

    assert action.action_required == "review_required"
    assert action.analysis_scope == "full_image_review"
    assert action.selected_region_id is None


def test_risk_action_reports_barcode_identity_conflict_without_raw_names() -> None:
    """Verify barcode mismatch is surfaced with redacted evidence only."""
    barcode_lookup = SupplementBarcodeLookupResponse(
        status="review_required",
        candidate_count=1,
        candidates=[
            SupplementBarcodeProductCandidate(
                source_id="foodqr:sample",
                product_name="Different Product",
                manufacturer="Example",
                match_score=0.91,
                review_required_reason="user_confirmation_required",
            )
        ],
    )

    action = build_supplement_image_risk_action(
        image_quality_report=_report(),
        barcode_lookup=barcode_lookup,
        parsed_product_name="Vitamin D 1000",
    )

    assert action.action_required == "review_required"
    assert action.identity_conflict is not None
    assert action.identity_conflict.conflict_type == "barcode_product_mismatch"
    assert "Different Product" not in str(action.identity_conflict.evidence)
    assert "Vitamin D 1000" not in str(action.identity_conflict.evidence)


def test_risk_action_accepts_contained_barcode_product_name() -> None:
    """Verify obvious product-name containment does not create a conflict."""
    barcode_lookup = SupplementBarcodeLookupResponse(
        status="review_required",
        candidate_count=1,
        candidates=[
            SupplementBarcodeProductCandidate(
                source_id="foodqr:sample",
                product_name="Vitamin D 1000 IU",
                match_score=0.91,
                review_required_reason="user_confirmation_required",
            )
        ],
    )

    action = build_supplement_image_risk_action(
        image_quality_report=_report(),
        barcode_lookup=barcode_lookup,
        parsed_product_name="Vitamin D 1000",
    )

    assert action.action_required == "none"
    assert action.identity_conflict is None
