"""섭취 영양소 → KDRIs 대조 평가 단위 테스트.

검증 범위:
    - classify_status 임계값(35/70/130) + UL 초과(RISKY).
    - build_message 의료적 단정 표현 0건.
    - evaluate_intake_against_kdris: 코드 매핑·스킵·정렬·요약.
    - 실데이터 기반 현실 시나리오(고나트륨 식사).

Reference:
    docs/dev-guides/06-deficient-nutrient-diagnosis.md §상태 분류
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.models.schemas.nutrition import NutrientStatus, UserKDRIsContext
from src.nutrition.kdris import load_kdris_csv
from src.nutrition.kdris_evaluation import (
    build_message,
    classify_status,
    evaluate_intake_against_kdris,
)

SAMPLE_CSV = Path(__file__).parent / "fixtures" / "kdris_sample.csv"
REAL_CSV = Path(__file__).resolve().parents[4] / "data" / "kdris" / "kdris_2020.csv"


@pytest.fixture
def sample_rows() -> list[dict[str, str]]:
    """샘플 KDRIs CSV 로드."""
    return load_kdris_csv(SAMPLE_CSV)


@pytest.fixture
def real_rows() -> list[dict[str, str]]:
    """실제 KDRIs CSV 로드."""
    return load_kdris_csv(REAL_CSV)


class TestClassifyStatus:
    """상태 분류 임계값."""

    @pytest.mark.parametrize(
        ("intake", "expected_status", "expected_ratio"),
        [
            (20.0, NutrientStatus.DEFICIENT, 20.0),
            (50.0, NutrientStatus.LOW, 50.0),
            (100.0, NutrientStatus.ADEQUATE, 100.0),
            (200.0, NutrientStatus.EXCESSIVE, 200.0),
        ],
    )
    def test_thresholds(
        self, intake: float, expected_status: NutrientStatus, expected_ratio: float
    ) -> None:
        """기준 100 대비 비율에 따른 상태 분류."""
        status, ratio = classify_status(intake, 100.0, None)
        assert status is expected_status
        assert ratio == expected_ratio

    def test_boundary_35_is_low(self) -> None:
        """정확히 35%는 LOW (DEFICIENT 아님)."""
        status, _ = classify_status(35.0, 100.0, None)
        assert status is NutrientStatus.LOW

    def test_boundary_70_is_adequate(self) -> None:
        """정확히 70%는 ADEQUATE."""
        status, _ = classify_status(70.0, 100.0, None)
        assert status is NutrientStatus.ADEQUATE

    def test_boundary_130_is_adequate(self) -> None:
        """정확히 130%는 ADEQUATE."""
        status, _ = classify_status(130.0, 100.0, None)
        assert status is NutrientStatus.ADEQUATE

    def test_above_upper_limit_is_risky(self) -> None:
        """상한 초과는 RISKY."""
        status, _ = classify_status(2500.0, 100.0, 2000.0)
        assert status is NutrientStatus.RISKY

    def test_no_reference_returns_adequate(self) -> None:
        """기준값 없으면 ADEQUATE, 비율 0."""
        status, ratio = classify_status(100.0, None, None)
        assert status is NutrientStatus.ADEQUATE
        assert ratio == 0.0

    def test_limit_under_ul_is_adequate(self) -> None:
        """한도형 영양소는 기준값보다 낮아도 부족이 아니라 적정."""
        status, ratio = classify_status(300.0, 1500.0, 2300.0, is_limit=True)
        assert status is NutrientStatus.ADEQUATE
        assert ratio == 20.0

    def test_limit_over_ul_is_risky(self) -> None:
        """한도형 영양소도 상한 초과는 RISKY."""
        status, _ = classify_status(2600.0, 1500.0, 2300.0, is_limit=True)
        assert status is NutrientStatus.RISKY


class TestBuildMessage:
    """문구 생성 + 의료적 단정 표현 차단."""

    @pytest.mark.parametrize("status", list(NutrientStatus))
    def test_no_forbidden_terms(self, status: NutrientStatus) -> None:
        """모든 상태 문구에 금지 표현이 없다."""
        message = build_message("칼슘", status, 50.0)
        for term in ("진단", "처방", "치료", "보장", "확실히"):
            assert term not in message

    def test_message_contains_name(self) -> None:
        """문구에 영양소명이 포함된다."""
        assert "칼슘" in build_message("칼슘", NutrientStatus.ADEQUATE, 90.0)


class TestEvaluateIntake:
    """섭취 → KDRIs 대조 평가."""

    def test_calcium_adequate_female_50(self, sample_rows: list[dict[str, str]]) -> None:
        """50대 여성 칼슘 600mg / 800 기준 = 75% → ADEQUATE."""
        user = UserKDRIsContext(age=50, sex="female")
        result = evaluate_intake_against_kdris({"calcium_mg": 600.0}, user, rows=sample_rows)
        assert result.evaluated_count == 1
        evaluation = result.evaluations[0]
        assert evaluation.code == "calcium_mg"
        assert evaluation.ratio_pct == 75.0
        assert evaluation.status is NutrientStatus.ADEQUATE

    def test_vitamin_c_low(self, sample_rows: list[dict[str, str]]) -> None:
        """남성 30세 비타민 C 50mg / 100 = 50% → LOW."""
        user = UserKDRIsContext(age=30, sex="male")
        result = evaluate_intake_against_kdris({"vitamin_c_mg": 50.0}, user, rows=sample_rows)
        assert result.evaluations[0].status is NutrientStatus.LOW

    def test_unmapped_nutrient_skipped(self, sample_rows: list[dict[str, str]]) -> None:
        """KDRIs 기준이 없는 영양소(fat_g)는 스킵된다."""
        user = UserKDRIsContext(age=30, sex="male")
        result = evaluate_intake_against_kdris(
            {"fat_g": 20.0, "vitamin_c_mg": 100.0}, user, rows=sample_rows
        )
        assert "fat_g" in result.skipped_codes
        assert result.evaluated_count == 1

    def test_no_kdris_match_skipped(self, sample_rows: list[dict[str, str]]) -> None:
        """매핑은 되지만 사용자 매칭 행이 없으면 스킵."""
        user = UserKDRIsContext(age=50, sex="female")  # 샘플에 50대 여성 철 없음
        result = evaluate_intake_against_kdris({"iron_mg": 10.0}, user, rows=sample_rows)
        assert "iron_mg" in result.skipped_codes
        assert result.evaluated_count == 0

    def test_priority_sort_risky_first(self, real_rows: list[dict[str, str]]) -> None:
        """과잉(RISKY)이 적정보다 앞에 정렬된다."""
        user = UserKDRIsContext(age=40, sex="male")
        # 나트륨 3000mg(>2300 과잉경계) + 비타민C 100mg(적정)
        result = evaluate_intake_against_kdris(
            {"sodium_mg": 3000.0, "vitamin_c_mg": 100.0}, user, rows=real_rows
        )
        assert result.evaluations[0].status is NutrientStatus.RISKY
        assert result.evaluations[0].code == "sodium_mg"

    def test_empty_intake_summary(self, sample_rows: list[dict[str, str]]) -> None:
        """평가 가능한 영양소가 없으면 요약이 그 사실을 알린다."""
        user = UserKDRIsContext(age=30, sex="male")
        result = evaluate_intake_against_kdris({"fat_g": 10.0}, user, rows=sample_rows)
        assert result.evaluated_count == 0
        assert "없어요" in result.summary_message_ko


class TestRealScenario:
    """실데이터 기반 현실 시나리오."""

    def test_high_sodium_meal_flags_risky(self, real_rows: list[dict[str, str]]) -> None:
        """[시나리오] 고나트륨 식사(찌개류) → 나트륨 과잉 경계 초과."""
        user = UserKDRIsContext(age=52, sex="male")
        intake = {"kcal": 500.0, "protein_g": 20.0, "sodium_mg": 2600.0, "calcium_mg": 150.0}
        result = evaluate_intake_against_kdris(intake, user, rows=real_rows)

        sodium = next(e for e in result.evaluations if e.code == "sodium_mg")
        assert sodium.status is NutrientStatus.RISKY
        assert "전문가" in result.summary_message_ko

    def test_low_sodium_not_labeled_deficient(self, real_rows: list[dict[str, str]]) -> None:
        """[시나리오] 나트륨이 적은 식사 → 부족(더 섭취) 안내가 아니라 적정."""
        user = UserKDRIsContext(age=52, sex="male")
        result = evaluate_intake_against_kdris({"sodium_mg": 3.0}, user, rows=real_rows)
        sodium = result.evaluations[0]
        assert sodium.status is NutrientStatus.ADEQUATE
        assert "더해" not in sodium.message_ko
        assert "풍부" not in sodium.message_ko
        assert "한도" in sodium.message_ko

    def test_messages_compliance_safe(self, real_rows: list[dict[str, str]]) -> None:
        """[컴플라이언스] 모든 문구에 의료적 단정 표현 0건."""
        user = UserKDRIsContext(age=52, sex="male")
        intake = {"kcal": 500.0, "sodium_mg": 2600.0, "calcium_mg": 150.0, "iron_mg": 3.0}
        result = evaluate_intake_against_kdris(intake, user, rows=real_rows)
        for evaluation in result.evaluations:
            for term in ("진단", "처방", "치료", "보장", "확실히"):
                assert term not in evaluation.message_ko
