"""5-card 종합 분석 산출 로직 단위 테스트."""

from __future__ import annotations

import pytest
from src.models.schemas.supplement_comprehensive import ComprehensiveAnalysisRequest
from src.nutrition.comprehensive import compute_comprehensive


def _make_request(
    *,
    ingredients: list[dict[str, object]],
    chronic_conditions: list[str] | None = None,
    persona: str = "B",
    age: int = 52,
    sex: str = "male",
) -> ComprehensiveAnalysisRequest:
    """테스트용 요청 생성 헬퍼."""
    return ComprehensiveAnalysisRequest.model_validate(
        {
            "analysis_id": "test-001",
            "persona": persona,
            "user_profile": {
                "age": age,
                "sex": sex,
                "chronic_conditions": chronic_conditions or [],
            },
            "ingredients": ingredients,
        }
    )


class TestComputeComprehensive:
    """compute_comprehensive 산출 로직 검증."""

    def test_empty_ingredients_returns_warning(self) -> None:
        """빈 ingredient 입력 시 모든 카드가 비고 warning 발생."""
        result = compute_comprehensive(_make_request(ingredients=[]))
        assert result.warnings == ["no_recognized_nutrient_codes"]
        assert result.deficient_nutrients  # KDRIs 권장량 0 섭취 → 모두 부족
        assert result.excessive_nutrients == []
        assert result.cautionary_components == []
        assert result.diet_score < 100

    def test_omega3_high_dose_triggers_cautions(self) -> None:
        """오메가3 + 만성질환자 페르소나 시 high-severity caution(출혈 위험) 포함."""
        result = compute_comprehensive(
            _make_request(
                ingredients=[
                    {
                        "display_name": "Omega-3 Fish Oil",
                        "nutrient_code": "omega3_mg",
                        "amount": 1800,
                        "unit": "mg",
                    },
                ],
                chronic_conditions=["cardiovascular"],
                persona="B",
            )
        )
        severities = {c.severity for c in result.cautionary_components}
        assert (
            "high" in severities
        ), f"오메가3 → bleeding risk 'high' 누락: {result.cautionary_components}"

    def test_chronic_disease_indications_auto_mapped(self) -> None:
        """오메가3 ingredient → cardiovascular/dyslipidemia 등 자동 매핑."""
        result = compute_comprehensive(
            _make_request(
                ingredients=[
                    {
                        "display_name": "오메가-3 (EPA + DHA)",
                        "nutrient_code": "omega3_mg",
                        "amount": 1800,
                        "unit": "mg",
                    },
                ],
            )
        )
        assert "cardiovascular" in result.chronic_disease_indications
        assert "dyslipidemia" in result.chronic_disease_indications

    def test_persona_b_user_condition_boosts_relevance(self) -> None:
        """사용자가 명시한 condition 의 relevance_score 가 +0.15 가중치 적용."""
        result_a = compute_comprehensive(
            _make_request(
                ingredients=[
                    {
                        "display_name": "오메가-3",
                        "nutrient_code": "omega3_mg",
                        "amount": 1800,
                        "unit": "mg",
                    },
                ],
                chronic_conditions=[],  # 사용자 미지정
            )
        )
        result_b = compute_comprehensive(
            _make_request(
                ingredients=[
                    {
                        "display_name": "오메가-3",
                        "nutrient_code": "omega3_mg",
                        "amount": 1800,
                        "unit": "mg",
                    },
                ],
                chronic_conditions=["cardiovascular"],  # 사용자 지정 → boost
            )
        )
        score_a = next(
            t.relevance_score for t in result_a.purpose_targets if t.condition == "cardiovascular"
        )
        score_b = next(
            t.relevance_score for t in result_b.purpose_targets if t.condition == "cardiovascular"
        )
        assert score_b > score_a, f"user condition boost 실패: {score_a} vs {score_b}"

    def test_diet_score_in_valid_range(self) -> None:
        """diet_score 는 0~100 범위 안에 있다."""
        result = compute_comprehensive(
            _make_request(
                ingredients=[
                    {
                        "display_name": "비타민 C",
                        "nutrient_code": "vitamin_c_mg",
                        "amount": 100,
                        "unit": "mg",
                    },
                    {
                        "display_name": "비타민 D",
                        "nutrient_code": "vitamin_d_ug",
                        "amount": 10,
                        "unit": "ug",
                    },
                ],
            )
        )
        assert 0 <= result.diet_score <= 100
        assert result.diet_score_label in {"excellent", "good", "moderate", "warning", "critical"}

    def test_excessive_nutrient_detected_when_above_upper_limit(self) -> None:
        """KDRIs 상한 초과 영양소가 excessive_nutrients 에 포함된다."""
        # 마그네슘 upper_limit 350mg → 1000mg 입력 → 약 2.86배 초과
        result = compute_comprehensive(
            _make_request(
                ingredients=[
                    {
                        "display_name": "Magnesium",
                        "nutrient_code": "magnesium_mg",
                        "amount": 1000,
                        "unit": "mg",
                    },
                ],
            )
        )
        assert any(e.nutrient_code == "magnesium_mg" for e in result.excessive_nutrients)
        mg_entry = next(e for e in result.excessive_nutrients if e.nutrient_code == "magnesium_mg")
        assert mg_entry.excess_ratio == pytest.approx(1000 / 350, abs=0.02)

    def test_unknown_ingredient_does_not_crash(self) -> None:
        """nutrient_code 가 없는 ingredient 도 안전하게 처리된다."""
        result = compute_comprehensive(
            _make_request(
                ingredients=[
                    {
                        "display_name": "Mystery Extract",
                        "nutrient_code": None,
                        "amount": 100,
                        "unit": "mg",
                    },
                ],
            )
        )
        assert isinstance(result.deficient_nutrients, list)
        assert "no_recognized_nutrient_codes" in result.warnings

    def test_algorithm_version_recorded(self) -> None:
        """algorithm_version 이 응답에 포함된다."""
        result = compute_comprehensive(_make_request(ingredients=[]))
        assert result.algorithm_version == "comprehensive-v1"
