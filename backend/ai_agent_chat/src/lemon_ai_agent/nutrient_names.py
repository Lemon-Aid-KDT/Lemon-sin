"""Korean display names for nutrient codes used in coaching output.

Daily-coaching findings carry canonical English nutrient codes (for example
``"vitamin d"``). The user-facing action list ("실천 리스트") is shown in
Korean, so titles and messages map these codes to Korean labels via
:func:`nutrient_ko`, falling back to the original code when unmapped.
"""

from __future__ import annotations

NUTRIENT_KO: dict[str, str] = {
    "protein": "단백질",
    "fiber": "식이섬유",
    "vitamin a": "비타민 A",
    "vitamin b": "비타민 B",
    "vitamin c": "비타민 C",
    "vitamin d": "비타민 D",
    "vitamin e": "비타민 E",
    "vitamin k": "비타민 K",
    "magnesium": "마그네슘",
    "omega-3": "오메가3",
    "iron": "철분",
    "calcium": "칼슘",
    "zinc": "아연",
    "sodium": "나트륨",
    "potassium": "칼륨",
    "sugar": "당류",
    "folate": "엽산",
    "cholesterol": "콜레스테롤",
}


def nutrient_ko(nutrient: str) -> str:
    """Return the Korean display name for a nutrient code.

    Args:
        nutrient: Canonical nutrient code (case-insensitive).

    Returns:
        Korean label when known, otherwise the input string unchanged.
    """
    return NUTRIENT_KO.get(nutrient.strip().lower(), nutrient)
