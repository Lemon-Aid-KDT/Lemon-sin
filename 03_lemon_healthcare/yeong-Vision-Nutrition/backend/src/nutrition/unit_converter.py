"""영양소 단위 환산 유틸리티."""

from __future__ import annotations

MICROGRAM_SYMBOL = "μg"
MICROGRAM_ASCII = "ug"
GRAM = "g"
MILLIGRAM = "mg"
KILOCALORIE = "kcal"
INTERNATIONAL_UNIT = "iu"
VITAMIN_D_CODE = "vitamin_d_ug"
G_TO_MG = 1000.0
MG_TO_UG = 1000.0
VITAMIN_D_IU_TO_UG = 0.025
MASS_CONVERSION_FACTORS = {
    (GRAM, MILLIGRAM): G_TO_MG,
    (MILLIGRAM, GRAM): 1 / G_TO_MG,
    (MILLIGRAM, MICROGRAM_ASCII): MG_TO_UG,
    (MICROGRAM_ASCII, MILLIGRAM): 1 / MG_TO_UG,
    (GRAM, MICROGRAM_ASCII): G_TO_MG * MG_TO_UG,
    (MICROGRAM_ASCII, GRAM): 1 / (G_TO_MG * MG_TO_UG),
}


class UnitConversionError(ValueError):
    """지원하지 않는 영양소 단위 환산 오류."""


def normalize_unit(unit: str) -> str:
    """단위 문자열을 내부 표준으로 정규화한다.

    Args:
        unit: 입력 단위.

    Returns:
        소문자 ASCII 단위.
    """
    return unit.strip().lower().replace(MICROGRAM_SYMBOL, MICROGRAM_ASCII)


def convert_amount(
    amount: float,
    from_unit: str,
    to_unit: str,
    nutrient_code: str | None = None,
) -> float:
    """영양소 섭취량을 목표 단위로 환산한다.

    Args:
        amount: 환산할 섭취량.
        from_unit: 입력 단위.
        to_unit: 목표 단위.
        nutrient_code: IU처럼 영양소별 환산이 필요한 경우의 내부 코드.

    Returns:
        목표 단위로 환산한 값.

    Raises:
        UnitConversionError: 지원하지 않는 환산 조합인 경우.
    """
    source = normalize_unit(from_unit)
    target = normalize_unit(to_unit)
    if source == target:
        return amount
    conversion_factor = MASS_CONVERSION_FACTORS.get((source, target))
    if conversion_factor is not None:
        return amount * conversion_factor
    if (
        source == INTERNATIONAL_UNIT
        and target == MICROGRAM_ASCII
        and nutrient_code == VITAMIN_D_CODE
    ):
        return amount * VITAMIN_D_IU_TO_UG
    raise UnitConversionError(f"unsupported unit conversion: {from_unit} -> {to_unit}")
