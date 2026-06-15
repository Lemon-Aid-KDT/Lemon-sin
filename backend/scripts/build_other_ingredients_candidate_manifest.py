"""Build the full other-ingredients candidate set for OCR proposal mining.

The panel merge artifact intentionally truncates operator-facing rare-class
targets to a small review list. This script rebuilds the complete train-split
candidate set from the panelized export and creates two outputs:

* a Label Studio-compatible task list without private paths, and
* a worker manifest with relative image filenames for local/A100 OCR scans.

No raw OCR text, provider payloads, absolute paths, or image bytes are written
to JSON artifacts. Image copies are optional and are limited to the selected
candidate files.

References:
    https://docs.ultralytics.com/datasets/detect/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.learning.retraining import (  # noqa: E402
    SUPPLEMENT_SECTION_CLASS_NAMES,
    SUPPLEMENT_SECTION_YOLO_EXPORT_SCHEMA_VERSION,
)

SCHEMA_VERSION = "other-ingredients-candidate-manifest-v1"
TASK_SCHEMA_VERSION = "other-ingredients-label-studio-targets-v1"
SUMMARY_SCHEMA_VERSION = "other-ingredients-candidate-summary-v1"
TARGET_CLASS = "other_ingredients"
REQUIRED_CONTEXT_CLASSES = frozenset({"ingredient_amounts", "supplement_facts"})
SOURCE_DOC_URLS = ("https://docs.ultralytics.com/datasets/detect/",)


class CandidateManifestError(ValueError):
    """Raised when candidate manifest input is malformed or unsafe."""


@dataclass(frozen=True)
class SourceImage:
    """Resolved source image metadata.

    Args:
        source_ref: Private source reference token.
        image_path: Local image file path.
    """

    source_ref: str
    image_path: Path


@dataclass(frozen=True)
class Candidate:
    """Candidate fixture for other-ingredients proposal mining.

    Args:
        source_ref: Private source reference token.
        source_ref_hash: Redacted source reference hash.
        fixture_id: Stable fixture id parsed from the source ref.
        image_filename: Candidate image file name.
        split: Dataset split. Only train is selected.
        existing_class_count: Number of section classes already present.
    """

    source_ref: str
    source_ref_hash: str
    fixture_id: str
    image_filename: str
    split: str
    existing_class_count: int

    def manifest_row(self) -> dict[str, Any]:
        """Return the private worker manifest row.

        Returns:
            Row with only relative image filename, source token, and counts.
        """
        return {
            "source_ref": self.source_ref,
            "source_ref_hash": self.source_ref_hash,
            "fixture_id": self.fixture_id,
            "image_filename": self.image_filename,
            "split": self.split,
            "target_class": TARGET_CLASS,
            "existing_class_count": self.existing_class_count,
        }

    def task_row(self, *, task_id: int, image_url_template: str) -> dict[str, Any]:
        """Return a Label Studio-compatible review task.

        Args:
            task_id: Stable task id for the generated list.
            image_url_template: URL template containing ``{fixture_id}``.

        Returns:
            Redacted task row without local paths or private source refs.
        """
        return {
            "id": task_id,
            "data": {
                "fixture_id": self.fixture_id,
                "image": image_url_template.format(fixture_id=self.fixture_id),
            },
            "meta": {
                "annotation_task_type": "supplement_roi_box",
                "target_class": TARGET_CLASS,
                "source_ref_hash": self.source_ref_hash,
                "candidate_reason": (
                    "train image has nutrition sections but no other_ingredients panel"
                ),
                "existing_class_count": self.existing_class_count,
                "coordinate_space": "source_image",
                "human_review_required": True,
            },
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Optional argument list for tests.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-export", required=True, type=Path)
    parser.add_argument("--source-map", required=True, type=Path)
    parser.add_argument("--output-manifest", required=True, type=Path)
    parser.add_argument("--output-tasks", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--image-copy-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=0, help="0 means all candidates.")
    parser.add_argument(
        "--image-url-template",
        default="http://localhost:8090/{fixture_id}.jpg",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the candidate manifest builder.

    Args:
        argv: Optional argument list for tests.
    """
    args = parse_args(argv)
    try:
        manifest, tasks, summary = build_candidate_manifest(
            panel_export_path=args.panel_export,
            source_map_path=args.source_map,
            image_copy_dir=args.image_copy_dir,
            limit=args.limit,
            image_url_template=args.image_url_template,
        )
        _write_json(args.output_manifest, manifest)
        _write_json(args.output_tasks, tasks)
        _write_json(args.summary, summary)
        print(json.dumps(_cli_summary(summary), ensure_ascii=False, sort_keys=True))
    except (CandidateManifestError, OSError, json.JSONDecodeError) as exc:
        failure = {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "status": "failed",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "raw_ocr_text_stored": False,
            "raw_provider_payload_stored": False,
            "absolute_paths_stored": False,
        }
        _write_json(args.summary, failure)
        print(json.dumps(_cli_summary(failure), ensure_ascii=False, sort_keys=True))
        raise SystemExit(1) from None


def build_candidate_manifest(
    *,
    panel_export_path: Path,
    source_map_path: Path,
    image_copy_dir: Path | None,
    limit: int,
    image_url_template: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Build full candidate manifest and optional image copies.

    Args:
        panel_export_path: Panelized section export.
        source_map_path: Operator-only source map resolving image files.
        image_copy_dir: Optional directory for flat candidate image copies.
        limit: Optional candidate cap. ``0`` means all.
        image_url_template: Review task image URL template.

    Returns:
        Worker manifest, Label Studio task list, and redacted summary.

    Raises:
        CandidateManifestError: If input shape or image resolution is invalid.
    """
    if limit < 0:
        raise CandidateManifestError("limit must be non-negative.")
    panel_export = _load_json_object(panel_export_path, "panel export")
    _validate_panel_export(panel_export)
    source_map = _load_source_map(source_map_path)
    candidates = _candidate_rows(panel_export=panel_export, source_map=source_map)
    if limit:
        candidates = candidates[:limit]
    copied_count = 0
    if image_copy_dir is not None:
        copied_count = _copy_candidate_images(candidates, source_map=source_map, output_dir=image_copy_dir)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "target_class": TARGET_CLASS,
        "candidate_count": len(candidates),
        "source_doc_urls": list(SOURCE_DOC_URLS),
        "human_review_required": True,
        "promotion_allowed": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
        "items": [candidate.manifest_row() for candidate in candidates],
    }
    tasks = [
        candidate.task_row(task_id=index + 1, image_url_template=image_url_template)
        for index, candidate in enumerate(candidates)
    ]
    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "ready_for_proposal_scan" if candidates else "no_candidates",
        "candidate_count": len(candidates),
        "copied_image_count": copied_count,
        "target_class": TARGET_CLASS,
        "source_doc_urls": list(SOURCE_DOC_URLS),
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "absolute_paths_stored": False,
        "private_source_refs_stored_in_summary": False,
    }
    _assert_redacted(tasks)
    _assert_redacted(summary)
    return manifest, tasks, summary


def _candidate_rows(
    *,
    panel_export: dict[str, Any],
    source_map: dict[str, SourceImage],
) -> list[Candidate]:
    """Return sorted train candidates requiring other-ingredients labels."""
    rows: list[Candidate] = []
    for item in panel_export["items"]:
        if item.get("split") != "train":
            continue
        source_ref = _string_field(item, "source_ref")
        labels = item.get("labels")
        if not isinstance(labels, list) or not labels:
            raise CandidateManifestError("panel export item labels must be a non-empty list.")
        class_names = {
            label.get("label")
            for label in labels
            if isinstance(label, dict) and isinstance(label.get("label"), str)
        }
        if TARGET_CLASS in class_names or not (REQUIRED_CONTEXT_CLASSES & class_names):
            continue
        source_image = source_map.get(source_ref)
        if source_image is None:
            raise CandidateManifestError("source map is missing a candidate image.")
        rows.append(
            Candidate(
                source_ref=source_ref,
                source_ref_hash=_source_ref_hash(source_ref),
                fixture_id=_fixture_id(source_ref),
                image_filename=source_image.image_path.name,
                split="train",
                existing_class_count=len(class_names),
            )
        )
    return sorted(rows, key=lambda row: (-row.existing_class_count, row.source_ref_hash))


def _copy_candidate_images(
    candidates: list[Candidate],
    *,
    source_map: dict[str, SourceImage],
    output_dir: Path,
) -> int:
    """Copy candidate images into a flat transfer directory.

    Args:
        candidates: Candidate rows.
        source_map: Private source map.
        output_dir: Destination directory.

    Returns:
        Number of images copied or already present.

    Raises:
        CandidateManifestError: If a source image is missing.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for candidate in candidates:
        source = source_map[candidate.source_ref].image_path
        if not source.is_file():
            raise CandidateManifestError("candidate source image does not exist.")
        destination = output_dir / candidate.image_filename
        if destination.exists():
            copied += 1
            continue
        shutil.copy2(source, destination)
        copied += 1
    return copied


def _load_json_object(path: Path, description: str) -> dict[str, Any]:
    """Load a JSON object from disk.

    Args:
        path: JSON file path.
        description: Description used in redacted errors.

    Returns:
        Parsed JSON object.

    Raises:
        CandidateManifestError: If the file is not a JSON object.
    """
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CandidateManifestError(f"{description} must be a JSON object.")
    return value


def _validate_panel_export(panel_export: dict[str, Any]) -> None:
    """Validate the panel export header and item shape."""
    if panel_export.get("schema_version") != SUPPLEMENT_SECTION_YOLO_EXPORT_SCHEMA_VERSION:
        raise CandidateManifestError("unsupported panel export schema.")
    if panel_export.get("class_names") != list(SUPPLEMENT_SECTION_CLASS_NAMES):
        raise CandidateManifestError("panel export class names do not match.")
    items = panel_export.get("items")
    if not isinstance(items, list) or panel_export.get("item_count") != len(items):
        raise CandidateManifestError("panel export item_count mismatch.")


def _load_source_map(path: Path) -> dict[str, SourceImage]:
    """Load the private source map with paths resolved relative to its file."""
    payload = _load_json_object(path, "source map")
    sources = payload.get("sources")
    if not isinstance(sources, list):
        raise CandidateManifestError("source map requires a sources list.")
    output: dict[str, SourceImage] = {}
    for row in sources:
        if not isinstance(row, dict):
            raise CandidateManifestError("source map rows must be objects.")
        source_ref = _string_field(row, "source_ref")
        image_path_value = _string_field(row, "image_path")
        image_path = Path(image_path_value)
        if not image_path.is_absolute():
            image_path = path.parent / image_path
        output[source_ref] = SourceImage(source_ref=source_ref, image_path=image_path)
    return output


def _string_field(row: dict[str, Any], key: str) -> str:
    """Return a required non-empty string field."""
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CandidateManifestError(f"{key} must be a non-empty string.")
    return value


def _fixture_id(source_ref: str) -> str:
    """Return the fixture id encoded in ``template:<fixture_id>``."""
    prefix = "template:"
    if not source_ref.startswith(prefix) or len(source_ref) <= len(prefix):
        raise CandidateManifestError("source_ref must use the template fixture contract.")
    return source_ref[len(prefix) :]


def _source_ref_hash(source_ref: str) -> str:
    """Return a short stable source-ref digest."""
    return hashlib.sha256(source_ref.encode("utf-8")).hexdigest()[:16]


def _write_json(path: Path, payload: object) -> None:
    """Write JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _cli_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Return compact CLI output."""
    return {
        "status": summary.get("status"),
        "candidate_count": summary.get("candidate_count"),
        "copied_image_count": summary.get("copied_image_count"),
    }


def _assert_redacted(payload: object) -> None:
    """Reject local paths, provider payloads, and OCR text markers."""
    dumped = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    forbidden_markers = (
        "/Users/",
        "/Volumes/",
        "/private/",
        "\\Users\\",
        "file://",
        '"raw_ocr_text":',
        '"provider_payload":',
        '"provider_raw_payload":',
        '"image_bytes":',
        "matched_keyword_lines",
    )
    if any(marker in dumped for marker in forbidden_markers):
        raise CandidateManifestError("redacted artifact contains unsafe content.")


if __name__ == "__main__":
    main()
