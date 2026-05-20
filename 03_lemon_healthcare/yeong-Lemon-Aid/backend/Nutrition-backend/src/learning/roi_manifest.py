"""Consent-gated ROI training manifest helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from src.config import Settings
from src.learning.consent_gate import evaluate_image_learning_gate
from src.models.schemas.image_quality import (
    ROI_TRAINING_CLASS_NAMES,
    ROITrainingManifest,
    ROITrainingManifestItem,
)
from src.models.schemas.privacy import ConsentType

RAW_FORBIDDEN_MANIFEST_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "exif",
        "filename",
        "gps",
        "image_bytes",
        "ocr_text",
        "raw_image",
        "raw_ocr_text",
        "raw_provider_payload",
        "request_headers",
        "service_key",
        "user_id",
    }
)


class ROIManifestExportError(ValueError):
    """Raised when ROI training manifest export is not allowed or invalid."""


@dataclass(frozen=True)
class SplitValidationResult:
    """Summary of ROI dataset split validation.

    Attributes:
        item_count: Number of manifest rows inspected.
        train_count: Number of training rows.
        val_count: Number of validation rows.
        test_count: Number of test rows.
    """

    item_count: int
    train_count: int
    val_count: int
    test_count: int


def build_consent_gated_manifest(
    *,
    settings: Settings,
    granted_consents: Iterable[ConsentType],
    items: Sequence[ROITrainingManifestItem],
) -> ROITrainingManifest:
    """Build a redacted ROI manifest only when the learning gate passes.

    Args:
        settings: Runtime settings used by the image-learning gate.
        granted_consents: Consent buckets granted by the current user/export context.
        items: Already redacted ROI manifest items.

    Returns:
        ROI training manifest.

    Raises:
        ROIManifestExportError: If consent/retention flags do not allow export.
    """
    decision = evaluate_image_learning_gate(settings, granted_consents)
    if not decision.allowed:
        raise ROIManifestExportError(decision.reason)
    manifest = ROITrainingManifest(items=list(items))
    validate_manifest_splits(manifest.items)
    return manifest


def validate_manifest_splits(items: Sequence[ROITrainingManifestItem]) -> SplitValidationResult:
    """Validate product/hash/session groups do not cross dataset splits.

    Args:
        items: Manifest items.

    Returns:
        Split validation summary.

    Raises:
        ROIManifestExportError: If a split group or image hash appears in multiple splits.
    """
    split_by_group: dict[str, str] = {}
    split_by_hash: dict[str, str] = {}
    split_counts = {"train": 0, "val": 0, "test": 0}
    for item in items:
        split_counts[item.split] += 1
        _register_split(
            split_by_group,
            key=item.split_group,
            split=item.split,
            kind="split_group",
        )
        _register_split(
            split_by_group,
            key=item.product_group_id,
            split=item.split,
            kind="product_group_id",
        )
        _register_split(split_by_hash, key=item.image_hash, split=item.split, kind="image_hash")
    return SplitValidationResult(
        item_count=len(items),
        train_count=split_counts["train"],
        val_count=split_counts["val"],
        test_count=split_counts["test"],
    )


def render_ultralytics_data_yaml(
    *,
    dataset_root: str | Path,
    class_names: Sequence[str] = ROI_TRAINING_CLASS_NAMES,
) -> str:
    """Render a minimal Ultralytics detection dataset YAML.

    Args:
        dataset_root: Dataset root path written into the YAML.
        class_names: Ordered class names.

    Returns:
        YAML text.
    """
    root = str(dataset_root)
    names = "\n".join(f"  {index}: {name}" for index, name in enumerate(class_names))
    return (
        f"path: {root}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        "names:\n"
        f"{names}\n"
    )


def yolo_label_lines(
    item: ROITrainingManifestItem,
    *,
    class_names: Sequence[str] = ROI_TRAINING_CLASS_NAMES,
) -> list[str]:
    """Convert one manifest item into YOLO label-file lines.

    Args:
        item: Manifest item.
        class_names: Ordered class names.

    Returns:
        YOLO label lines.

    Raises:
        ROIManifestExportError: If an annotation class is unknown.
    """
    class_index = {name: index for index, name in enumerate(class_names)}
    lines: list[str] = []
    for box in item.boxes:
        if box.class_name not in class_index:
            raise ROIManifestExportError(f"Unknown ROI class: {box.class_name}")
        lines.append(
            " ".join(
                (
                    str(class_index[box.class_name]),
                    _format_normalized_float(box.x_center),
                    _format_normalized_float(box.y_center),
                    _format_normalized_float(box.width),
                    _format_normalized_float(box.height),
                )
            )
        )
    return lines


def reject_raw_manifest_fields(value: object) -> None:
    """Reject raw images, OCR text, credentials, and direct user identifiers.

    Args:
        value: Candidate manifest object.

    Raises:
        ROIManifestExportError: If forbidden raw-data fields are present.
    """
    if isinstance(value, Mapping):
        forbidden = RAW_FORBIDDEN_MANIFEST_KEYS.intersection(str(key).lower() for key in value)
        if forbidden:
            raise ROIManifestExportError(
                f"Manifest contains forbidden raw field(s): {sorted(forbidden)}"
            )
        for nested_value in value.values():
            reject_raw_manifest_fields(nested_value)
    elif isinstance(value, list):
        for item in value:
            reject_raw_manifest_fields(item)


def _register_split(
    split_by_key: dict[str, str],
    *,
    key: str,
    split: str,
    kind: str,
) -> None:
    """Register one split grouping key.

    Args:
        split_by_key: Mutable split map.
        key: Grouping key.
        split: Dataset split.
        kind: Key kind for error messages.

    Raises:
        ROIManifestExportError: If the key crosses splits.
    """
    previous = split_by_key.get(key)
    if previous is None:
        split_by_key[key] = split
        return
    if previous != split:
        raise ROIManifestExportError(f"{kind} crosses splits: {key}")


def _format_normalized_float(value: float) -> str:
    """Format normalized YOLO coordinates deterministically.

    Args:
        value: Normalized coordinate.

    Returns:
        Six-decimal formatted value.
    """
    return f"{value:.6f}".rstrip("0").rstrip(".")
