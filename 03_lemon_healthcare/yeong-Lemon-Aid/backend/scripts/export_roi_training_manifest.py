"""Export a consent-gated ROI training manifest and Ultralytics dataset config.

The script consumes a redacted JSON manifest. It does not read raw image bytes,
OCR text, provider payloads, EXIF, GPS, filenames, credentials, or direct user
identifiers.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.config import Settings  # noqa: E402
from src.learning.roi_manifest import (  # noqa: E402
    ROIManifestExportError,
    build_consent_gated_manifest,
    reject_raw_manifest_fields,
    render_ultralytics_data_yaml,
    validate_manifest_splits,
    yolo_label_lines,
)
from src.models.schemas.image_quality import ROITrainingManifestItem  # noqa: E402
from src.models.schemas.privacy import ConsentType  # noqa: E402


def main() -> None:
    """Run the ROI manifest exporter from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dataset-root", default="roi-dataset")
    parser.add_argument("--enable-image-learning-pipeline", action="store_true")
    parser.add_argument("--enable-pgvector-storage", action="store_true")
    parser.add_argument("--image-retention-days", type=int, default=0)
    parser.add_argument("--consent", action="append", default=[])
    args = parser.parse_args()

    settings = Settings(
        _env_file=None,
        enable_image_learning_pipeline=args.enable_image_learning_pipeline,
        enable_pgvector_storage=args.enable_pgvector_storage,
        image_retention_days=args.image_retention_days,
    )
    summary = export_roi_training_manifest(
        input_path=args.input,
        output_dir=args.output_dir,
        dataset_root=args.dataset_root,
        settings=settings,
        granted_consents=tuple(_consent_type(value) for value in args.consent),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def export_roi_training_manifest(
    *,
    input_path: Path,
    output_dir: Path,
    dataset_root: str,
    settings: Settings,
    granted_consents: tuple[ConsentType, ...],
) -> dict[str, object]:
    """Export a redacted ROI manifest and dataset YAML.

    Args:
        input_path: Redacted input manifest path.
        output_dir: Output directory.
        dataset_root: Dataset root path written into the Ultralytics YAML.
        settings: Runtime settings for the image-learning gate.
        granted_consents: Consent grants for this export.

    Returns:
        Export summary.

    Raises:
        ROIManifestExportError: If raw data is present or consent gates fail.
    """
    parsed = json.loads(input_path.read_text(encoding="utf-8"))
    reject_raw_manifest_fields(parsed)
    raw_items = parsed.get("items") if isinstance(parsed, dict) else None
    if not isinstance(raw_items, list):
        raise ROIManifestExportError("Input manifest must contain an items list.")

    items = [ROITrainingManifestItem.model_validate(item) for item in raw_items]
    manifest = build_consent_gated_manifest(
        settings=settings,
        granted_consents=granted_consents,
        items=items,
    )
    split_summary = validate_manifest_splits(manifest.items)

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "roi-training-manifest.json"
    data_yaml_path = output_dir / "data.yaml"
    labels_dir = output_dir / "labels"
    labels_dir.mkdir(exist_ok=True)

    manifest_path.write_text(
        manifest.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    data_yaml_path.write_text(
        render_ultralytics_data_yaml(
            dataset_root=dataset_root,
            class_names=manifest.class_names,
        ),
        encoding="utf-8",
    )
    label_file_count = _write_label_files(labels_dir, manifest.items)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "input": str(input_path),
        "output_dir": str(output_dir),
        "manifest_path": str(manifest_path),
        "data_yaml_path": str(data_yaml_path),
        "item_count": split_summary.item_count,
        "train_count": split_summary.train_count,
        "val_count": split_summary.val_count,
        "test_count": split_summary.test_count,
        "label_file_count": label_file_count,
        "raw_image_stored": False,
        "raw_ocr_text_stored": False,
        "interpretation": (
            "ROI manifest export validates consent, split isolation, and redacted "
            "metadata. It does not train a model or claim OCR improvement."
        ),
    }


def _write_label_files(output_dir: Path, items: list[ROITrainingManifestItem]) -> int:
    """Write YOLO label files from manifest boxes.

    Args:
        output_dir: Label output directory.
        items: Manifest items.

    Returns:
        Number of written label files.
    """
    count = 0
    for item in items:
        lines = yolo_label_lines(item)
        (output_dir / f"{item.image_id}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        count += 1
    return count


def _consent_type(value: str) -> ConsentType:
    """Parse a consent type value.

    Args:
        value: Raw consent string.

    Returns:
        Consent type enum.

    Raises:
        ROIManifestExportError: If the value is not supported.
    """
    try:
        return ConsentType(value)
    except ValueError as exc:
        raise ROIManifestExportError(f"Unsupported consent type: {value}") from exc


if __name__ == "__main__":
    main()
