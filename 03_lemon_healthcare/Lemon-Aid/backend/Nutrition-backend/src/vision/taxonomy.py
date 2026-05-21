"""Supplement-image vision labels used by gated detectors."""

from __future__ import annotations

from enum import StrEnum


class VisionLabel(StrEnum):
    """Allowed non-medical object labels for supplement image detection.

    Attributes:
        SUPPLEMENT_BOTTLE: Bottle, pouch, or box that contains a supplement.
        SUPPLEMENT_LABEL: Product label region used as OCR input.
        BLISTER_PACK: Blister-pack object used only as capture context.
    """

    SUPPLEMENT_BOTTLE = "supplement_bottle"
    SUPPLEMENT_LABEL = "supplement_label"
    BLISTER_PACK = "blister_pack"


VISION_DETECTION_LABELS = frozenset(label.value for label in VisionLabel)
VISION_LABEL_ALIASES = {
    "supplement_container": VisionLabel.SUPPLEMENT_BOTTLE.value,
    "bottle": VisionLabel.SUPPLEMENT_BOTTLE.value,
    "label": VisionLabel.SUPPLEMENT_LABEL.value,
    "blister": VisionLabel.BLISTER_PACK.value,
}
VISION_ROI_LABEL_PRIORITY = {
    VisionLabel.SUPPLEMENT_LABEL.value: 0,
    VisionLabel.SUPPLEMENT_BOTTLE.value: 1,
    VisionLabel.BLISTER_PACK.value: 2,
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
