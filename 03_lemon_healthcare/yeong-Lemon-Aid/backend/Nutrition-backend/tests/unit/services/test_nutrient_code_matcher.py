"""Nutrient-code matcher tests."""

from __future__ import annotations

from src.services.nutrient_code_matcher import (
    NutrientAliasEntry,
    match_nutrient_code_candidates,
    normalize_nutrient_alias,
)


def test_match_nutrient_code_candidates_returns_deterministic_exact_candidate() -> None:
    """Verify exact aliases map to project-owned nutrient code candidates."""
    candidates = match_nutrient_code_candidates(" 비타민 C ")

    assert len(candidates) == 1
    assert candidates[0].nutrient_code == "VITC"
    assert candidates[0].match_method == "alias_exact"
    assert candidates[0].confidence == 1.0


def test_match_nutrient_code_candidates_returns_empty_for_unknown_label() -> None:
    """Verify unknown labels are not forced into nutrient codes."""
    assert match_nutrient_code_candidates("알 수 없는 성분") == []


def test_normalize_nutrient_alias_is_case_and_spacing_stable() -> None:
    """Verify deterministic alias normalization is stable."""
    assert normalize_nutrient_alias(" Vitamin   D ") == "vitamin d"


def test_match_nutrient_code_candidates_uses_reviewed_extra_alias_exact_only() -> None:
    """Verify domain-correction aliases can extend matching without fuzzy auto-apply."""
    extra_catalog = (
        NutrientAliasEntry(
            nutrient_code="vitamin_d_ug",
            display_name="Vitamin D",
            aliases=("Vitarnin D",),
            source_catalog="domain_correction_artifact",
        ),
    )

    exact = match_nutrient_code_candidates("Vitarnin D", extra_catalog)
    fuzzy = match_nutrient_code_candidates("Vitarnin", extra_catalog)

    assert exact[0].nutrient_code == "vitamin_d_ug"
    assert exact[0].source_catalog == "domain_correction_artifact"
    assert fuzzy == []
