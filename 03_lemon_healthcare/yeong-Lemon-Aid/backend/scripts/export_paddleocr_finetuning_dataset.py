"""Export consent-gated PaddleOCR fine-tuning label files.

The script consumes a redacted JSON manifest with human-verified training
labels. It writes PaddleOCR-compatible recognition and detection label files,
plus a redacted metadata sidecar and distribution report. It does not copy raw
images or store provider raw payloads.
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
from src.learning.paddleocr_finetuning import (  # noqa: E402
    PaddleOCRFineTuningExportError,
    build_consent_gated_finetuning_manifest,
    dataset_checksum,
    detection_label_lines,
    distribution_report,
    recognition_label_lines,
    redacted_manifest_dict,
    reject_raw_manifest_fields,
    validate_finetuning_splits,
)
from src.models.schemas.paddleocr_finetuning import (  # noqa: E402
    PaddleOCRFineTuningSample,
)
from src.models.schemas.privacy import ConsentType  # noqa: E402


def main() -> None:
    """Run the PaddleOCR fine-tuning exporter from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dataset-root", default="paddleocr-finetuning-dataset")
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
    summary = export_paddleocr_finetuning_dataset(
        input_path=args.input,
        output_dir=args.output_dir,
        dataset_root=args.dataset_root,
        settings=settings,
        granted_consents=tuple(_consent_type(value) for value in args.consent),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def export_paddleocr_finetuning_dataset(
    *,
    input_path: Path,
    output_dir: Path,
    dataset_root: str,
    settings: Settings,
    granted_consents: tuple[ConsentType, ...],
) -> dict[str, object]:
    """Export redacted PaddleOCR fine-tuning labels and reports.

    Args:
        input_path: Redacted input manifest path.
        output_dir: Output directory.
        dataset_root: Dataset root path documented in the summary.
        settings: Runtime settings for the image-learning gate.
        granted_consents: Consent grants for this export.

    Returns:
        Export summary.

    Raises:
        PaddleOCRFineTuningExportError: If raw data is present or gates fail.
    """
    parsed = json.loads(input_path.read_text(encoding="utf-8"))
    reject_raw_manifest_fields(parsed)
    raw_items = parsed.get("items") if isinstance(parsed, dict) else None
    if not isinstance(raw_items, list):
        raise PaddleOCRFineTuningExportError("Input manifest must contain an items list.")

    items = [PaddleOCRFineTuningSample.model_validate(item) for item in raw_items]
    manifest = build_consent_gated_finetuning_manifest(
        settings=settings,
        granted_consents=granted_consents,
        items=items,
    )
    split_summary = validate_finetuning_splits(manifest.items)
    recognition_lines = recognition_label_lines(manifest.items)
    detection_lines = detection_label_lines(manifest.items)
    checksum = dataset_checksum(
        recognition_lines=recognition_lines,
        detection_lines=detection_lines,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "paddleocr-finetuning-manifest.json"
    report_path = output_dir / "paddleocr-finetuning-distribution.json"
    manifest_path.write_text(
        json.dumps(redacted_manifest_dict(manifest), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(distribution_report(manifest.items), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    recognition_label_count = _write_split_label_files(output_dir / "rec", recognition_lines)
    detection_label_count = _write_split_label_files(output_dir / "det", detection_lines)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "input": str(input_path),
        "output_dir": str(output_dir),
        "dataset_root": dataset_root,
        "manifest_path": str(manifest_path),
        "distribution_report_path": str(report_path),
        "dataset_checksum": checksum,
        "item_count": split_summary.item_count,
        "train_count": split_summary.train_count,
        "val_count": split_summary.val_count,
        "test_count": split_summary.test_count,
        "recognition_label_count": recognition_label_count,
        "detection_label_count": detection_label_count,
        "raw_image_stored": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "verified_transcripts_in_label_files": recognition_label_count > 0,
        "interpretation": (
            "PaddleOCR fine-tuning export validates consent, human verification, "
            "split isolation, and redacted metadata. It does not train a model."
        ),
    }


def _write_split_label_files(output_dir: Path, split_lines: dict[str, list[str]]) -> int:
    """Write split label files.

    Args:
        output_dir: Output directory for one PaddleOCR task.
        split_lines: Split-to-lines map.

    Returns:
        Number of label lines written.
    """
    output_dir.mkdir(exist_ok=True)
    count = 0
    for split, lines in split_lines.items():
        label_path = output_dir / f"{split}.txt"
        label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        count += len(lines)
    return count


def _consent_type(value: str) -> ConsentType:
    """Parse a consent type value.

    Args:
        value: Raw consent string.

    Returns:
        Consent type enum.

    Raises:
        PaddleOCRFineTuningExportError: If the value is not supported.
    """
    try:
        return ConsentType(value)
    except ValueError as exc:
        raise PaddleOCRFineTuningExportError(f"Unsupported consent type: {value}") from exc


if __name__ == "__main__":
    main()
