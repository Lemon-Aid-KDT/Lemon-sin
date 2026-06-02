"""Supplement-image vision labels used by gated detectors."""

from __future__ import annotations

from enum import StrEnum


class VisionLabel(StrEnum):
    """Allowed non-medical object labels for supplement image detection.

    Attributes:
        SUPPLEMENT_FACTS: Supplement facts / nutrition facts table region.
        PRECAUTIONS: Warning, caution, allergy, or precaution text region.
        INTAKE_METHOD: Suggested use / directions / dosage text region.
        INGREDIENTS: Other ingredients / ingredient declaration region.
        SUPPLEMENT_LABEL: Product label region used as OCR input.
        SUPPLEMENT_BOTTLE: Bottle, pouch, or box that contains a supplement.
        BLISTER_PACK: Blister-pack object used only as capture context.
    """

    SUPPLEMENT_FACTS = "supplement_facts"
    PRECAUTIONS = "precautions"
    INTAKE_METHOD = "intake_method"
    INGREDIENTS = "ingredients"
    SUPPLEMENT_LABEL = "supplement_label"
    SUPPLEMENT_BOTTLE = "supplement_bottle"
    BLISTER_PACK = "blister_pack"


VISION_DETECTION_LABELS = frozenset(label.value for label in VisionLabel)
VISION_SECTION_LABELS = frozenset(
    {
        VisionLabel.SUPPLEMENT_FACTS.value,
        VisionLabel.PRECAUTIONS.value,
        VisionLabel.INTAKE_METHOD.value,
        VisionLabel.INGREDIENTS.value,
    }
)
VISION_LABEL_ALIASES = {
    "nutrition_facts": VisionLabel.SUPPLEMENT_FACTS.value,
    "nutrition_facts_panel": VisionLabel.SUPPLEMENT_FACTS.value,
    "supplement_facts_panel": VisionLabel.SUPPLEMENT_FACTS.value,
    "facts": VisionLabel.SUPPLEMENT_FACTS.value,
    "nutrition_info": VisionLabel.SUPPLEMENT_FACTS.value,
    "nutrition_information": VisionLabel.SUPPLEMENT_FACTS.value,
    "nutrition_function_info": VisionLabel.SUPPLEMENT_FACTS.value,
    "warning": VisionLabel.PRECAUTIONS.value,
    "warnings": VisionLabel.PRECAUTIONS.value,
    "caution": VisionLabel.PRECAUTIONS.value,
    "cautions": VisionLabel.PRECAUTIONS.value,
    "precaution": VisionLabel.PRECAUTIONS.value,
    "allergy": VisionLabel.PRECAUTIONS.value,
    "allergies": VisionLabel.PRECAUTIONS.value,
    "allergen": VisionLabel.PRECAUTIONS.value,
    "allergens": VisionLabel.PRECAUTIONS.value,
    "allergy_warning": VisionLabel.PRECAUTIONS.value,
    "allergen_warning": VisionLabel.PRECAUTIONS.value,
    "directions": VisionLabel.INTAKE_METHOD.value,
    "direction": VisionLabel.INTAKE_METHOD.value,
    "suggested_use": VisionLabel.INTAKE_METHOD.value,
    "suggested_adult_use": VisionLabel.INTAKE_METHOD.value,
    "usage": VisionLabel.INTAKE_METHOD.value,
    "dosage": VisionLabel.INTAKE_METHOD.value,
    "how_to_take": VisionLabel.INTAKE_METHOD.value,
    "intake": VisionLabel.INTAKE_METHOD.value,
    "ingredient": VisionLabel.INGREDIENTS.value,
    "other_ingredients": VisionLabel.INGREDIENTS.value,
    "ingredient_list": VisionLabel.INGREDIENTS.value,
    "supplement_container": VisionLabel.SUPPLEMENT_BOTTLE.value,
    "bottle": VisionLabel.SUPPLEMENT_BOTTLE.value,
    "label": VisionLabel.SUPPLEMENT_LABEL.value,
    "blister": VisionLabel.BLISTER_PACK.value,
}
VISION_ROI_LABEL_PRIORITY = {
    VisionLabel.SUPPLEMENT_FACTS.value: 0,
    VisionLabel.PRECAUTIONS.value: 1,
    VisionLabel.INTAKE_METHOD.value: 2,
    VisionLabel.INGREDIENTS.value: 3,
    VisionLabel.SUPPLEMENT_LABEL.value: 4,
    VisionLabel.SUPPLEMENT_BOTTLE.value: 5,
    VisionLabel.BLISTER_PACK.value: 6,
}


def normalize_vision_label(label: str) -> str | None:
    """Normalize a detector label into the allowed supplement ROI taxonomy.

    Args:
        label: Raw model label.

    Returns:
        Canonical label when allowed, otherwise None.
    """
    normalized = label.strip().lower().replace(" ", "_").replace("-", "_")
    return (
        normalized
        if normalized in VISION_DETECTION_LABELS
        else VISION_LABEL_ALIASES.get(normalized)
    )


def normalize_vision_label_set(labels: list[str]) -> list[str]:
    """Normalize configured detector labels into stable supplement ROI labels.

    Args:
        labels: Raw configured label names or aliases.

    Returns:
        Sorted canonical labels that belong to the supplement ROI taxonomy.
    """
    return sorted(
        {
            normalized
            for label in labels
            if (normalized := normalize_vision_label(label)) is not None
        }
    )


def label_priority(label: str | None) -> int:
    """Return ROI selection priority for a canonical label.

    Args:
        label: Canonical supplement ROI label.

    Returns:
        Lower value means a stronger OCR ROI candidate.
    """
    if label is None:
        return len(VISION_ROI_LABEL_PRIORITY) + 1
    return VISION_ROI_LABEL_PRIORITY.get(label, len(VISION_ROI_LABEL_PRIORITY) + 1)
