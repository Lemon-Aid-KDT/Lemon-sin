"""PaddleOCR fine-tuning manifest, export, and promotion-gate helpers."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256

from src.config import Settings
from src.learning.consent_gate import evaluate_image_learning_gate
from src.models.schemas.paddleocr_finetuning import (
    PaddleOCRDetectionBox,
    PaddleOCRFineTuningManifest,
    PaddleOCRFineTuningSample,
)
from src.models.schemas.privacy import ConsentType

RAW_FORBIDDEN_MANIFEST_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "exif",
        "file_name",
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
PRIMARY_PROMOTION_METRICS = (
    "numeric_exact_rate",
    "unit_exact_rate",
    "line_exact_rate",
    "parser_success_rate",
    "field_exact_rate",
)


class PaddleOCRFineTuningExportError(ValueError):
    """Raised when PaddleOCR fine-tuning dataset export is unsafe or invalid."""


@dataclass(frozen=True)
class FineTuningSplitValidationResult:
    """Summary of PaddleOCR fine-tuning split validation.

    Attributes:
        item_count: Number of samples inspected.
        train_count: Number of training samples.
        val_count: Number of validation samples.
        test_count: Number of test samples.
    """

    item_count: int
    train_count: int
    val_count: int
    test_count: int


def build_consent_gated_finetuning_manifest(
    *,
    settings: Settings,
    granted_consents: Iterable[ConsentType],
    items: Sequence[PaddleOCRFineTuningSample],
) -> PaddleOCRFineTuningManifest:
    """Build a redacted fine-tuning manifest only when learning gates pass.

    Args:
        settings: Runtime settings used by the image-learning gate.
        granted_consents: Consent buckets granted by the current export context.
        items: Already validated fine-tuning samples.

    Returns:
        Fine-tuning manifest.

    Raises:
        PaddleOCRFineTuningExportError: If consent, retention, split, or sample gates fail.
    """
    decision = evaluate_image_learning_gate(settings, granted_consents)
    if not decision.allowed:
        raise PaddleOCRFineTuningExportError(decision.reason)
    _validate_samples_are_exportable(items)
    manifest = PaddleOCRFineTuningManifest(items=list(items))
    validate_finetuning_splits(manifest.items)
    return manifest


def validate_finetuning_splits(
    items: Sequence[PaddleOCRFineTuningSample],
) -> FineTuningSplitValidationResult:
    """Validate source groups and augmented variants do not cross splits.

    Args:
        items: Fine-tuning samples.

    Returns:
        Split validation summary.

    Raises:
        PaddleOCRFineTuningExportError: If a leakage key appears in multiple splits.
    """
    split_counts = {"train": 0, "val": 0, "test": 0}
    split_by_key: dict[tuple[str, str], str] = {}
    for item in items:
        split_counts[item.split] += 1
        _register_split(split_by_key, kind="product_group_id", key=item.product_group_id, item=item)
        _register_split(split_by_key, kind="image_hash", key=item.image_hash, item=item)
        _register_split(split_by_key, kind="split_group", key=item.split_group, item=item)
        if item.session_group_id:
            _register_split(
                split_by_key,
                kind="session_group_id",
                key=item.session_group_id,
                item=item,
            )
        if item.augmented_source_id:
            _register_split(
                split_by_key,
                kind="augmented_source_id",
                key=item.augmented_source_id,
                item=item,
            )
    return FineTuningSplitValidationResult(
        item_count=len(items),
        train_count=split_counts["train"],
        val_count=split_counts["val"],
        test_count=split_counts["test"],
    )


def recognition_label_lines(
    items: Sequence[PaddleOCRFineTuningSample],
) -> dict[str, list[str]]:
    """Render PaddleOCR text-recognition label lines by split.

    Args:
        items: Fine-tuning samples.

    Returns:
        Mapping from split to PaddleOCR label lines.

    Raises:
        PaddleOCRFineTuningExportError: If a recognition sample is not human verified.
    """
    lines = _empty_split_map()
    for item in items:
        if item.task_type != "recognition":
            continue
        _validate_human_verified(item)
        if not item.verified_transcript:
            raise PaddleOCRFineTuningExportError(
                f"Recognition sample requires verified_transcript: {item.sample_id}"
            )
        lines[item.split].append(f"{item.image_path}\t{item.verified_transcript}")
    return lines


def detection_label_lines(
    items: Sequence[PaddleOCRFineTuningSample],
) -> dict[str, list[str]]:
    """Render PaddleOCR text-detection label lines by split.

    Args:
        items: Fine-tuning samples.

    Returns:
        Mapping from split to PaddleOCR detection label lines.

    Raises:
        PaddleOCRFineTuningExportError: If a detection sample is not human verified.
    """
    lines = _empty_split_map()
    for item in items:
        if item.task_type != "detection":
            continue
        _validate_human_verified(item)
        if not item.boxes:
            raise PaddleOCRFineTuningExportError(
                f"Detection sample requires at least one box: {item.sample_id}"
            )
        annotation_json = json.dumps(
            [_detection_box_label(box) for box in item.boxes],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        lines[item.split].append(f"{item.image_path}\t{annotation_json}")
    return lines


def distribution_report(items: Sequence[PaddleOCRFineTuningSample]) -> dict[str, object]:
    """Build a redacted dataset distribution report.

    Args:
        items: Fine-tuning samples.

    Returns:
        Aggregate counts by split, task, language mix, field type, and issue labels.
    """
    return {
        "item_count": len(items),
        "split_counts": _count_by(items, "split"),
        "task_type_counts": _count_by(items, "task_type"),
        "language_mix_counts": _count_by(items, "language_mix"),
        "field_type_counts": _count_by(items, "field_type"),
        "badcase_category_counts": _count_many(items, "badcase_categories"),
        "quality_label_counts": _count_many(items, "quality_labels"),
        "synthetic_count": sum(1 for item in items if item.synthetic),
        "human_verified_count": sum(1 for item in items if item.human_verified),
    }


def redacted_manifest_dict(manifest: PaddleOCRFineTuningManifest) -> dict[str, object]:
    """Build a metadata sidecar without transcript labels.

    Args:
        manifest: Fine-tuning manifest.

    Returns:
        Redacted manifest dictionary safe for metadata/audit artifacts.
    """
    return {
        "schema_version": manifest.schema_version,
        "items": [_redacted_sample_dict(item) for item in manifest.items],
    }


def reject_raw_manifest_fields(value: object) -> None:
    """Reject raw images, raw OCR, provider payloads, and direct identifiers.

    Args:
        value: Candidate manifest object.

    Raises:
        PaddleOCRFineTuningExportError: If forbidden raw-data keys are present.
    """
    if isinstance(value, Mapping):
        forbidden = RAW_FORBIDDEN_MANIFEST_KEYS.intersection(str(key).lower() for key in value)
        if forbidden:
            raise PaddleOCRFineTuningExportError(
                f"Manifest contains forbidden raw field(s): {sorted(forbidden)}"
            )
        for nested_value in value.values():
            reject_raw_manifest_fields(nested_value)
    elif isinstance(value, list):
        for item in value:
            reject_raw_manifest_fields(item)


def evaluate_promotion_gate(
    *,
    baseline: Mapping[str, object],
    candidate: Mapping[str, object],
) -> dict[str, object]:
    """Evaluate whether a fine-tuned model can be a promotion candidate.

    Args:
        baseline: Baseline model evaluation report.
        candidate: Fine-tuned model evaluation report.

    Returns:
        Redacted promotion decision with metric deltas.
    """
    baseline_split = baseline.get("frozen_test_split_id")
    candidate_split = candidate.get("frozen_test_split_id")
    if not baseline_split or baseline_split != candidate_split:
        return _promotion_result(False, "frozen_test_split_mismatch", {})

    deltas: dict[str, float] = {}
    improved = False
    for metric in PRIMARY_PROMOTION_METRICS:
        baseline_value = _metric_value(baseline.get(metric))
        candidate_value = _metric_value(candidate.get(metric))
        if baseline_value is None or candidate_value is None:
            return _promotion_result(False, f"missing_metric:{metric}", deltas)
        delta = candidate_value - baseline_value
        deltas[metric] = delta
        if delta < 0:
            return _promotion_result(False, f"metric_regressed:{metric}", deltas)
        improved = improved or delta > 0
    if not improved:
        return _promotion_result(False, "no_primary_metric_improved", deltas)
    return _promotion_result(True, "promotion_candidate", deltas)


def dataset_checksum(
    *, recognition_lines: Mapping[str, list[str]], detection_lines: Mapping[str, list[str]]
) -> str:
    """Return a deterministic checksum for exported label files.

    Args:
        recognition_lines: Recognition label lines by split.
        detection_lines: Detection label lines by split.

    Returns:
        SHA-256 checksum over split-qualified label lines.
    """
    digest = sha256()
    for task_name, split_lines in (
        ("recognition", recognition_lines),
        ("detection", detection_lines),
    ):
        for split in ("train", "val", "test"):
            for line in split_lines.get(split, []):
                digest.update(f"{task_name}/{split}:{line}\n".encode())
    return digest.hexdigest()


def _validate_samples_are_exportable(items: Sequence[PaddleOCRFineTuningSample]) -> None:
    """Validate all samples are eligible for dataset export.

    Args:
        items: Fine-tuning samples.

    Raises:
        PaddleOCRFineTuningExportError: If any sample lacks human verification.
    """
    for item in items:
        _validate_human_verified(item)


def _validate_human_verified(item: PaddleOCRFineTuningSample) -> None:
    """Validate a sample has human-confirmed labels.

    Args:
        item: Candidate fine-tuning sample.

    Raises:
        PaddleOCRFineTuningExportError: If the sample is not human verified.
    """
    if not item.human_verified:
        raise PaddleOCRFineTuningExportError(
            f"Fine-tuning sample requires human_verified=true: {item.sample_id}"
        )


def _register_split(
    split_by_key: dict[tuple[str, str], str],
    *,
    kind: str,
    key: str,
    item: PaddleOCRFineTuningSample,
) -> None:
    """Register one split leakage key.

    Args:
        split_by_key: Mutable leakage map.
        kind: Key type.
        key: Key value.
        item: Fine-tuning sample.

    Raises:
        PaddleOCRFineTuningExportError: If the key crosses splits.
    """
    typed_key = (kind, key)
    previous = split_by_key.get(typed_key)
    if previous is None:
        split_by_key[typed_key] = item.split
        return
    if previous != item.split:
        raise PaddleOCRFineTuningExportError(f"{kind} crosses splits: {key}")


def _detection_box_label(box: PaddleOCRDetectionBox) -> dict[str, object]:
    """Convert one detection box into PaddleOCR label JSON shape.

    Args:
        box: Detection box.

    Returns:
        PaddleOCR detection annotation object.
    """
    transcription = "###" if box.ignore else box.transcription
    return {
        "transcription": transcription,
        "points": [[x, y] for x, y in box.points],
    }


def _redacted_sample_dict(item: PaddleOCRFineTuningSample) -> dict[str, object]:
    """Return sample metadata without transcript text.

    Args:
        item: Fine-tuning sample.

    Returns:
        Redacted metadata dictionary.
    """
    return {
        "sample_id": item.sample_id,
        "source_image_id": item.source_image_id,
        "crop_id": item.crop_id,
        "image_path": item.image_path,
        "product_group_id": item.product_group_id,
        "image_hash": item.image_hash,
        "split_group": item.split_group,
        "split": item.split,
        "task_type": item.task_type,
        "language_mix": item.language_mix,
        "field_type": item.field_type,
        "human_verified": item.human_verified,
        "consent_scope": item.consent_scope,
        "transcript_hash": item.transcript_hash,
        "box_count": len(item.boxes),
        "box_point_counts": [len(box.points) for box in item.boxes],
        "session_group_id": item.session_group_id,
        "augmented_source_id": item.augmented_source_id,
        "source_provider": item.source_provider,
        "badcase_categories": item.badcase_categories,
        "quality_labels": item.quality_labels,
        "synthetic": item.synthetic,
    }


def _empty_split_map() -> dict[str, list[str]]:
    """Return empty train/validation/test split line buckets.

    Returns:
        Empty split-to-lines map.
    """
    return {"train": [], "val": [], "test": []}


def _count_by(items: Sequence[PaddleOCRFineTuningSample], attribute: str) -> dict[str, int]:
    """Count samples by one scalar attribute.

    Args:
        items: Fine-tuning samples.
        attribute: Attribute name.

    Returns:
        Count dictionary sorted by key.
    """
    counter = Counter(str(getattr(item, attribute)) for item in items)
    return dict(sorted(counter.items()))


def _count_many(items: Sequence[PaddleOCRFineTuningSample], attribute: str) -> dict[str, int]:
    """Count samples by values in one list attribute.

    Args:
        items: Fine-tuning samples.
        attribute: Attribute name.

    Returns:
        Count dictionary sorted by key.
    """
    counter: Counter[str] = Counter()
    for item in items:
        for value in getattr(item, attribute):
            counter[str(value)] += 1
    return dict(sorted(counter.items()))


def _metric_value(value: object) -> float | None:
    """Return a bounded metric value.

    Args:
        value: Candidate metric value.

    Returns:
        Float metric or None.
    """
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    if value < 0 or value > 1:
        return None
    return float(value)


def _promotion_result(
    promotable: bool,
    reason: str,
    deltas: Mapping[str, float],
) -> dict[str, object]:
    """Build a promotion-gate result.

    Args:
        promotable: Whether promotion is allowed.
        reason: Stable decision reason.
        deltas: Metric deltas.

    Returns:
        Promotion gate result.
    """
    return {
        "promotable": promotable,
        "reason": reason,
        "primary_metric_deltas": dict(deltas),
    }
