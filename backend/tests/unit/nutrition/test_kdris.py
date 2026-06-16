"""KDRIs 룩업 단위 테스트.

dev-guide 05 §"KDRIs 룩업" 명세를 검증한다.

검증 범위:
    - CSV 로딩 (성공/없음/필수 컬럼 누락/빈 파일).
    - 성별 + 연령 기본 룩업.
    - 임신부·수유부 분기 우선순위.
    - AI(충분섭취량) 폴백 (reference_value).
    - 매칭 실패 (미지원 영양소, 연령 범위 밖).
    - 실제 data/kdris/kdris_2020.csv 로딩 + 대표 값.

Reference:
    docs/dev-guides/05-kdris-lookup.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.models.schemas.nutrition import KDRIsValue, UserKDRIsContext
from src.nutrition.kdris import (
    DEFAULT_KDRIS_PATH,
    load_kdris_csv,
    lookup_kdris_for_user,
)

SAMPLE_CSV = Path(__file__).parent / "fixtures" / "kdris_sample.csv"


@pytest.fixture
def sample_rows() -> list[dict[str, str]]:
    """샘플 KDRIs CSV 로드."""
    return load_kdris_csv(SAMPLE_CSV)


class TestLoadKdrisCsv:
    """CSV 로딩 테스트."""

    def test_load_sample_returns_rows(self, sample_rows: list[dict[str, str]]) -> None:
        """샘플 CSV는 17행을 반환한다."""
        assert len(sample_rows) == 17

    def test_load_nonexistent_raises(self) -> None:
        """없는 파일은 FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_kdris_csv(Path("nonexistent_kdris.csv"))

    def test_first_row_has_expected_code(self, sample_rows: list[dict[str, str]]) -> None:
        """첫 행 code는 vitamin_c_mg."""
        assert sample_rows[0]["code"] == "vitamin_c_mg"

    def test_empty_cell_is_empty_string(self, sample_rows: list[dict[str, str]]) -> None:
        """빈 셀(ai 없음)은 빈 문자열로 로드된다."""
        assert sample_rows[0]["ai"] == ""


class TestLookupBasic:
    """기본 룩업 (성별 + 연령)."""

    def test_lookup_male_30_vitamin_c(self, sample_rows: list[dict[str, str]]) -> None:
        """30세 남성 비타민 C → 100mg RDA."""
        user = UserKDRIsContext(age=30, sex="male")
        result = lookup_kdris_for_user("vitamin_c_mg", user, rows=sample_rows)
        assert result is not None
        assert result.rda == 100.0
        assert result.unit == "mg"
        assert result.name_ko == "비타민 C"

    def test_lookup_female_50_calcium(self, sample_rows: list[dict[str, str]]) -> None:
        """50세 여성 칼슘 → 800mg."""
        user = UserKDRIsContext(age=50, sex="female")
        result = lookup_kdris_for_user("calcium_mg", user, rows=sample_rows)
        assert result is not None
        assert result.rda == 800.0

    def test_lookup_female_50_iron_absent(self, sample_rows: list[dict[str, str]]) -> None:
        """샘플에 50대 여성 철 행이 없으면 None."""
        user = UserKDRIsContext(age=50, sex="female")
        result = lookup_kdris_for_user("iron_mg", user, rows=sample_rows)
        assert result is None


class TestLookupSpecial:
    """임신부·수유부 분기."""

    def test_pregnant_vitamin_c(self, sample_rows: list[dict[str, str]]) -> None:
        """임신부 비타민 C → 110mg."""
        user = UserKDRIsContext(age=30, sex="female", is_pregnant=True)
        result = lookup_kdris_for_user("vitamin_c_mg", user, rows=sample_rows)
        assert result is not None
        assert result.rda == 110.0

    def test_lactating_vitamin_c(self, sample_rows: list[dict[str, str]]) -> None:
        """수유부 비타민 C → 140mg."""
        user = UserKDRIsContext(age=30, sex="female", is_lactating=True)
        result = lookup_kdris_for_user("vitamin_c_mg", user, rows=sample_rows)
        assert result is not None
        assert result.rda == 140.0

    def test_pregnant_priority_over_age(self, sample_rows: list[dict[str, str]]) -> None:
        """임신부 분기는 일반 연령 분기보다 우선."""
        user = UserKDRIsContext(age=30, sex="female", is_pregnant=True)
        result = lookup_kdris_for_user("iron_mg", user, rows=sample_rows)
        assert result is not None
        assert result.rda == 27.0

    def test_male_pregnancy_flag_ignored(self, sample_rows: list[dict[str, str]]) -> None:
        """남성에 is_pregnant=True를 줘도 일반 분기로 폴백."""
        user = UserKDRIsContext(age=30, sex="male", is_pregnant=True)
        result = lookup_kdris_for_user("vitamin_c_mg", user, rows=sample_rows)
        assert result is not None
        assert result.rda == 100.0

    def test_pregnant_falls_back_when_no_special_row(
        self, sample_rows: list[dict[str, str]]
    ) -> None:
        """임신부 전용 행이 없는 영양소(칼슘)는 일반 행으로 폴백."""
        user = UserKDRIsContext(age=19, sex="female", is_pregnant=True)
        result = lookup_kdris_for_user("calcium_mg", user, rows=sample_rows)
        assert result is not None
        assert result.rda == 700.0


class TestLookupAiFallback:
    """AI(충분섭취량) 폴백."""

    def test_water_uses_ai(self, sample_rows: list[dict[str, str]]) -> None:
        """수분은 RDA 없고 AI만 → reference_value는 AI."""
        user = UserKDRIsContext(age=25, sex="male")
        result = lookup_kdris_for_user("water_ml", user, rows=sample_rows)
        assert result is not None
        assert result.rda is None
        assert result.ai == 2600.0
        assert result.reference_value == 2600.0


class TestLookupNotFound:
    """매칭 실패 케이스."""

    def test_unknown_nutrient(self, sample_rows: list[dict[str, str]]) -> None:
        """존재하지 않는 영양소 → None."""
        user = UserKDRIsContext(age=30, sex="male")
        result = lookup_kdris_for_user("unobtainium_mg", user, rows=sample_rows)
        assert result is None

    def test_age_out_of_range(self, sample_rows: list[dict[str, str]]) -> None:
        """연령 범위 밖(샘플은 19~64) → None."""
        user = UserKDRIsContext(age=80, sex="male")
        result = lookup_kdris_for_user("vitamin_c_mg", user, rows=sample_rows)
        assert result is None


class TestKDRIsValueModel:
    """KDRIsValue 모델."""

    def test_reference_value_uses_rda(self) -> None:
        """RDA가 있으면 reference_value는 RDA."""
        value = KDRIsValue(
            code="test_mg", name_ko="테스트", name_en="Test", unit="mg", rda=100.0, ai=80.0
        )
        assert value.reference_value == 100.0

    def test_reference_value_falls_back_to_ai(self) -> None:
        """RDA가 없으면 AI."""
        value = KDRIsValue(
            code="test_mg", name_ko="테스트", name_en="Test", unit="mg", rda=None, ai=80.0
        )
        assert value.reference_value == 80.0

    def test_reference_value_none_when_neither(self) -> None:
        """RDA·AI 둘 다 없으면 None."""
        value = KDRIsValue(
            code="test_mg", name_ko="테스트", name_en="Test", unit="mg", rda=None, ai=None
        )
        assert value.reference_value is None

    def test_invalid_code_pattern_raises(self) -> None:
        """코드 패턴 위반은 ValidationError."""
        with pytest.raises(ValueError):
            KDRIsValue(code="InvalidCode", name_ko="x", name_en="x", unit="mg")

    def test_frozen_is_immutable(self) -> None:
        """frozen=True라 속성 변경 불가."""
        value = KDRIsValue(code="test_mg", name_ko="테스트", name_en="Test", unit="mg", rda=100.0)
        with pytest.raises(ValueError):
            value.rda = 200.0  # type: ignore[misc]


class TestRealKdrisData:
    """실제 data/kdris/kdris_2020.csv 로딩 검증."""

    def test_default_file_exists(self) -> None:
        """기본 KDRIs CSV가 존재한다."""
        assert DEFAULT_KDRIS_PATH.exists()

    def test_real_calcium_female_50(self) -> None:
        """[실데이터] 50대 여성 칼슘 권장 800mg, UL 2000mg."""
        rows = load_kdris_csv(DEFAULT_KDRIS_PATH)
        user = UserKDRIsContext(age=52, sex="female")
        result = lookup_kdris_for_user("calcium_mg", user, rows=rows)
        assert result is not None
        assert result.rda == 800.0
        assert result.ul == 2000.0

    def test_real_sodium_uses_ai_and_cdrr(self) -> None:
        """[실데이터] 나트륨은 AI 기준값 + 과잉 경계(CDRR 2300)."""
        rows = load_kdris_csv(DEFAULT_KDRIS_PATH)
        user = UserKDRIsContext(age=40, sex="male")
        result = lookup_kdris_for_user("sodium_mg", user, rows=rows)
        assert result is not None
        assert result.reference_value == 1500.0
        assert result.ul == 2300.0

    def test_real_energy_male_30(self) -> None:
        """[실데이터] 30대 남성 에너지필요추정량 2500kcal."""
        rows = load_kdris_csv(DEFAULT_KDRIS_PATH)
        user = UserKDRIsContext(age=35, sex="male")
        result = lookup_kdris_for_user("energy_kcal", user, rows=rows)
        assert result is not None
        assert result.reference_value == 2500.0
