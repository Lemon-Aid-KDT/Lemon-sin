"""Safety guard regression tests for medical-boundary language."""

from __future__ import annotations

import pytest
from lemon_ai_agent.guards.safety import SafetyGuard


@pytest.mark.parametrize(
    "text",
    [
        "당뇨입니다. 이 식단으로 치료하세요.",
        "혈압약은 오늘부터 약을 중단하세요.",
        "이 영양제를 먹고 약을 끊으세요.",
        "복용량을 바꾸세요.",
        "현재 약 용량을 늘리세요.",
        "Take more of this medicine.",
        "Stop taking your medicine.",
    ],
)
def test_safety_guard_blocks_diagnosis_treatment_and_medication_changes(text: str) -> None:
    """Verify user-facing LLM text cannot direct diagnosis or medication changes."""
    result = SafetyGuard().check_text(text)

    assert result.allowed is False
    assert "Forbidden medical expression detected" in result.warnings


def test_safety_guard_allows_professional_consult_boundary_language() -> None:
    """Verify safe professional-consult wording can mention medication boundaries."""
    result = SafetyGuard().check_text(
        "복용 중인 약이나 영양제 조정은 의사 또는 약사와 상담해 주세요."
    )

    assert result.allowed is True
    assert result.warnings == []


def test_safety_guard_blocks_unsupported_evidence_claims() -> None:
    """Verify evidence/effect claims must be present in the grounding context."""
    result = SafetyGuard().check_grounding(
        "연구에 따르면 오메가3는 혈압을 낮춥니다.",
        allowed_context="현재 입력 기준으로 나트륨 섭취가 높을 수 있습니다.",
    )

    assert result.allowed is False
    assert "Unsupported medical fact detected" in result.warnings


def test_safety_guard_allows_grounded_evidence_terms() -> None:
    """Verify evidence terms are allowed when already present in context."""
    result = SafetyGuard().check_grounding(
        "현재 메모에 따르면 임상시험 관련 자료는 사용하지 않습니다.",
        allowed_context="임상시험 관련 자료는 사용하지 않습니다.",
    )

    assert result.allowed is True
    assert result.warnings == []
