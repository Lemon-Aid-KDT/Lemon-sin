"""Deterministic nutrient-code candidate matching for supplement labels.

This matcher uses a small project-owned alias table. It is intentionally not an
LLM step and does not make recommendation, adequacy, or clinical judgments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from src.models.schemas.supplement_snapshot import SupplementSnapshotNutrientCodeCandidate

EXACT_MATCH_CONFIDENCE = 1.0
FUZZY_MATCH_THRESHOLD = 0.88
MAX_MATCH_CANDIDATES = 3


@dataclass(frozen=True)
class NutrientAliasEntry:
    """One deterministic nutrient alias catalog entry.

    Attributes:
        nutrient_code: Project-owned internal nutrient code.
        display_name: Canonical nutrient display name.
        aliases: Label aliases that can map to this nutrient code.
        source_catalog: Deterministic catalog used for candidate metadata.
    """

    nutrient_code: str
    display_name: str
    aliases: tuple[str, ...]
    source_catalog: str = "internal_nutrient_alias"


NUTRIENT_ALIAS_CATALOG: tuple[NutrientAliasEntry, ...] = (
    NutrientAliasEntry("VITC", "Vitamin C", ("vitamin c", "비타민 c", "비타민c")),
    NutrientAliasEntry("VITD", "Vitamin D", ("vitamin d", "비타민 d", "비타민d")),
    NutrientAliasEntry("ZN", "Zinc", ("zinc", "아연")),
    NutrientAliasEntry("CA", "Calcium", ("calcium", "칼슘")),
    NutrientAliasEntry("MG", "Magnesium", ("magnesium", "마그네슘")),
    NutrientAliasEntry("EPA", "EPA", ("epa",)),
    NutrientAliasEntry("DHA", "DHA", ("dha",)),
)


def normalize_nutrient_alias(value: str) -> str:
    """Normalize an ingredient label for deterministic alias matching.

    Args:
        value: Ingredient display name from a label.

    Returns:
        Normalized ingredient alias.
    """
    normalized = value.casefold().strip()
    normalized = re.sub(r"[\s_\-]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized)


def match_nutrient_code_candidates(
    display_name: str,
    extra_catalog: tuple[NutrientAliasEntry, ...] = (),
) -> list[SupplementSnapshotNutrientCodeCandidate]:
    """Return deterministic nutrient-code candidates for a display name.

    Args:
        display_name: Ingredient name extracted from a label.
        extra_catalog: Reviewed domain-correction aliases. These are matched exactly only.

    Returns:
        Ranked deterministic nutrient-code candidates.
    """
    normalized_name = normalize_nutrient_alias(display_name)
    if not normalized_name:
        return []

    exact_matches: list[SupplementSnapshotNutrientCodeCandidate] = []
    fuzzy_matches: list[SupplementSnapshotNutrientCodeCandidate] = []
    for entry in (*NUTRIENT_ALIAS_CATALOG, *extra_catalog):
        for alias in entry.aliases:
            normalized_alias = normalize_nutrient_alias(alias)
            if normalized_name == normalized_alias:
                exact_matches.append(
                    SupplementSnapshotNutrientCodeCandidate(
                        nutrient_code=entry.nutrient_code,
                        display_name=entry.display_name,
                        source_catalog=entry.source_catalog,
                        match_method="alias_exact",
                        matched_alias=alias,
                        confidence=EXACT_MATCH_CONFIDENCE,
                    )
                )
                break
            if entry.source_catalog != "internal_nutrient_alias":
                continue
            score = SequenceMatcher(None, normalized_name, normalized_alias).ratio()
            if score >= FUZZY_MATCH_THRESHOLD:
                fuzzy_matches.append(
                    SupplementSnapshotNutrientCodeCandidate(
                        nutrient_code=entry.nutrient_code,
                        display_name=entry.display_name,
                        source_catalog=entry.source_catalog,
                        match_method="alias_fuzzy",
                        matched_alias=alias,
                        confidence=round(score, 4),
                    )
                )
                break

    if exact_matches:
        return exact_matches[:MAX_MATCH_CANDIDATES]
    fuzzy_matches.sort(key=lambda candidate: candidate.confidence, reverse=True)
    return fuzzy_matches[:MAX_MATCH_CANDIDATES]


__all__ = [
    "NUTRIENT_ALIAS_CATALOG",
    "NutrientAliasEntry",
    "match_nutrient_code_candidates",
    "normalize_nutrient_alias",
]
