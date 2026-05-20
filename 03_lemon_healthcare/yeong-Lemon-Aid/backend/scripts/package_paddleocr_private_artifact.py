"""Package a private PaddleOCR fine-tuning artifact.

The packager collects the local annotation queue, exported PaddleOCR labels,
and training outputs into a gitignored full-private artifact directory. It also
writes a redacted summary sidecar that contains only aggregate counts and
privacy assertions, not source file names, raw OCR text, provider payloads,
credentials, or image bytes.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.learning.paddleocr_finetuning import (  # noqa: E402
    RAW_FORBIDDEN_MANIFEST_KEYS,
    PaddleOCRFineTuningExportError,
)

from scripts.train_paddleocr_finetuned_models import (  # noqa: E402
    DEFAULT_DET_MODEL_NAME,
    DEFAULT_REC_MODEL_NAME,
    resolve_single_config,
    validate_paddleocr_source_dir,
)

PRIVATE_ARTIFACT_SCHEMA_VERSION = "paddleocr-private-artifact-v1"
REDACTED_SUMMARY_SCHEMA_VERSION = "paddleocr-private-artifact-redacted-summary-v1"
FULL_PRIVATE_DIR_NAME = "full_private"
CHECKSUMS_FILE_NAME = "checksums.sha256"
ARTIFACT_MANIFEST_NAME = "artifact_manifest.json"
REDACTED_SUMMARY_NAME = "redacted_summary.json"
QUEUE_COPY_DIR_NAME = "queue"
EXPORT_COPY_DIR_NAME = "export"
TRAINING_COPY_DIR_NAME = "training"
ARTIFACT_PRIVACY_FORBIDDEN_KEYS = RAW_FORBIDDEN_MANIFEST_KEYS.union(
    {
        "absolute_path",
        "original_file_name",
        "original_filename",
        "original_path",
        "source_file_name",
        "source_filename",
        "source_path",
    }
)
REQUIRED_QUEUE_FILES = (
    "annotation_queue.json",
    "public_report.json",
)
REQUIRED_EXPORT_FILES = (
    "paddleocr-finetuning-manifest.json",
    "paddleocr-finetuning-distribution.json",
    "det/train.txt",
    "det/val.txt",
    "rec/train.txt",
    "rec/val.txt",
)
MODEL_FILE_SUFFIXES = frozenset(
    {
        ".pdmodel",
        ".pdiparams",
        ".pdiparams.info",
        ".pdopt",
        ".onnx",
    }
)


class PaddleOCRPrivateArtifactError(ValueError):
    """Raised when a private PaddleOCR artifact cannot be packaged safely."""


@dataclass(frozen=True)
class ChecksumEntry:
    """One SHA-256 checksum entry.

    Attributes:
        path: Artifact-relative file path.
        sha256: SHA-256 digest for the file bytes.
        size_bytes: File size in bytes.
    """

    path: str
    sha256: str
    size_bytes: int


def main() -> None:
    """Run the private artifact packager from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue-dir", required=True, type=Path)
    parser.add_argument("--export-dir", required=True, type=Path)
    parser.add_argument("--training-output-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--paddleocr-source-dir", required=True, type=Path)
    parser.add_argument("--source-dataset-id", required=True)
    args = parser.parse_args()

    summary = package_paddleocr_private_artifact(
        queue_dir=args.queue_dir,
        export_dir=args.export_dir,
        training_output_dir=args.training_output_dir,
        output_dir=args.output_dir,
        paddleocr_source_dir=args.paddleocr_source_dir,
        source_dataset_id=args.source_dataset_id,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def package_paddleocr_private_artifact(
    *,
    queue_dir: Path,
    export_dir: Path,
    training_output_dir: Path,
    output_dir: Path,
    paddleocr_source_dir: Path,
    source_dataset_id: str,
) -> dict[str, object]:
    """Package queue, export, and training outputs into a private artifact.

    Args:
        queue_dir: Private annotation queue directory.
        export_dir: Private PaddleOCR dataset export directory.
        training_output_dir: Private PaddleOCR training output directory.
        output_dir: Destination artifact directory. Must be empty or absent.
        paddleocr_source_dir: Existing PaddleOCR source checkout.
        source_dataset_id: Pseudonymous source dataset id for provenance.

    Returns:
        Redacted packaging summary.

    Raises:
        PaddleOCRPrivateArtifactError: If inputs are missing, unsafe, or output
            would recursively include itself.
    """
    if not source_dataset_id.strip():
        raise PaddleOCRPrivateArtifactError("--source-dataset-id must be non-empty.")

    queue_dir = queue_dir.resolve()
    export_dir = export_dir.resolve()
    training_output_dir = training_output_dir.resolve()
    paddleocr_source_dir = paddleocr_source_dir.resolve()
    output_dir = output_dir.resolve()

    _validate_input_tree(queue_dir, label="queue", required_files=REQUIRED_QUEUE_FILES)
    _validate_input_tree(export_dir, label="export", required_files=REQUIRED_EXPORT_FILES)
    _validate_training_output_dir(training_output_dir)
    _validate_output_dir(output_dir, input_dirs=(queue_dir, export_dir, training_output_dir))

    tools = validate_paddleocr_source_dir(paddleocr_source_dir)
    det_config = resolve_single_config(paddleocr_source_dir, DEFAULT_DET_MODEL_NAME)
    rec_config = resolve_single_config(paddleocr_source_dir, DEFAULT_REC_MODEL_NAME)

    queue_payload = _load_safe_json(queue_dir / "annotation_queue.json")
    queue_report = _load_safe_json(queue_dir / "public_report.json")
    export_manifest = _load_safe_json(export_dir / "paddleocr-finetuning-manifest.json")
    export_report = _load_safe_json(export_dir / "paddleocr-finetuning-distribution.json")
    _validate_optional_json_files(queue_dir=queue_dir, export_dir=export_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    full_private_dir = output_dir / FULL_PRIVATE_DIR_NAME
    full_private_dir.mkdir()
    copied_subtrees = _copy_private_inputs(
        queue_dir=queue_dir,
        export_dir=export_dir,
        training_output_dir=training_output_dir,
        full_private_dir=full_private_dir,
    )

    training_summary = _training_summary(training_output_dir)
    privacy_assertions = _privacy_assertions()
    redacted_summary = _build_redacted_summary(
        source_dataset_id=source_dataset_id,
        queue_payload=queue_payload,
        queue_report=queue_report,
        export_manifest=export_manifest,
        export_report=export_report,
        training_summary=training_summary,
        privacy_assertions=privacy_assertions,
    )
    _reject_artifact_privacy_fields(redacted_summary)
    redacted_summary_path = output_dir / REDACTED_SUMMARY_NAME
    redacted_summary_path.write_text(
        json.dumps(redacted_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    artifact_manifest = _build_artifact_manifest(
        source_dataset_id=source_dataset_id,
        queue_dir=queue_dir,
        export_dir=export_dir,
        training_output_dir=training_output_dir,
        output_dir=output_dir,
        paddleocr_source_dir=paddleocr_source_dir,
        copied_subtrees=copied_subtrees,
        queue_payload=queue_payload,
        queue_report=queue_report,
        export_manifest=export_manifest,
        export_report=export_report,
        training_summary=training_summary,
        tools=tools,
        det_config=det_config,
        rec_config=rec_config,
        privacy_assertions=privacy_assertions,
    )
    _reject_artifact_privacy_fields(artifact_manifest)
    artifact_manifest_path = output_dir / ARTIFACT_MANIFEST_NAME
    artifact_manifest_path.write_text(
        json.dumps(artifact_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    checksums = _write_checksums(output_dir)
    _verify_checksums(output_dir, checksums)

    return {
        "generated_at": artifact_manifest["generated_at"],
        "output_dir": str(output_dir),
        "artifact_manifest_path": str(artifact_manifest_path),
        "redacted_summary_path": str(redacted_summary_path),
        "checksums_path": str(output_dir / CHECKSUMS_FILE_NAME),
        "checksummed_file_count": len(checksums),
        "full_private_artifact": True,
        "source_dataset_id": source_dataset_id,
        "privacy_assertions": privacy_assertions,
    }


def _validate_input_tree(
    path: Path,
    *,
    label: str,
    required_files: tuple[str, ...],
) -> None:
    """Validate a required input directory and files exist.

    Args:
        path: Input directory path.
        label: Human-readable input label.
        required_files: Relative files that must exist.

    Raises:
        PaddleOCRPrivateArtifactError: If the directory or files are missing.
    """
    if not path.is_dir():
        raise PaddleOCRPrivateArtifactError(f"{label} directory does not exist: {path}")
    missing = [relative for relative in required_files if not (path / relative).is_file()]
    if missing:
        raise PaddleOCRPrivateArtifactError(
            f"{label} directory is missing required file(s): {', '.join(missing)}"
        )


def _validate_training_output_dir(training_output_dir: Path) -> None:
    """Validate training outputs exist before packaging.

    Args:
        training_output_dir: Training output directory.

    Raises:
        PaddleOCRPrivateArtifactError: If training outputs are missing or empty.
    """
    if not training_output_dir.is_dir():
        raise PaddleOCRPrivateArtifactError(
            f"training output directory does not exist: {training_output_dir}"
        )
    if not any(path.is_file() for path in training_output_dir.rglob("*")):
        raise PaddleOCRPrivateArtifactError(
            f"training output directory contains no files: {training_output_dir}"
        )


def _validate_output_dir(output_dir: Path, *, input_dirs: tuple[Path, ...]) -> None:
    """Validate the destination is safe for one-shot artifact creation.

    Args:
        output_dir: Artifact output directory.
        input_dirs: Input directories that must not contain the output.

    Raises:
        PaddleOCRPrivateArtifactError: If output exists, is non-empty, or is
            nested under an input directory.
    """
    for input_dir in input_dirs:
        if _is_relative_to(output_dir, input_dir):
            raise PaddleOCRPrivateArtifactError(
                f"output directory must not be inside input directory: {output_dir}"
            )
    if output_dir.exists() and any(output_dir.iterdir()):
        raise PaddleOCRPrivateArtifactError(f"output directory must be empty: {output_dir}")


def _is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether path is inside parent.

    Args:
        path: Candidate child path.
        parent: Candidate parent path.

    Returns:
        True when path is parent or a descendant of parent.
    """
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _load_safe_json(path: Path) -> dict[str, object]:
    """Load a JSON object and reject forbidden privacy fields.

    Args:
        path: JSON file path.

    Returns:
        Parsed JSON object.

    Raises:
        PaddleOCRPrivateArtifactError: If the file is missing, malformed, not
            an object, or contains forbidden fields.
    """
    try:
        parsed: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PaddleOCRPrivateArtifactError(f"JSON file is malformed: {path}") from exc
    if not isinstance(parsed, dict):
        raise PaddleOCRPrivateArtifactError(f"JSON file must contain an object: {path}")
    try:
        _reject_artifact_privacy_fields(parsed)
    except PaddleOCRFineTuningExportError as exc:
        raise PaddleOCRPrivateArtifactError(str(exc)) from exc
    return parsed


def _validate_optional_json_files(*, queue_dir: Path, export_dir: Path) -> None:
    """Validate optional manifest JSON files when present.

    Args:
        queue_dir: Annotation queue directory.
        export_dir: Exported dataset directory.
    """
    for json_path in (
        queue_dir / "verified_manifest.json",
        export_dir / "paddleocr-finetuning-manifest.json",
        export_dir / "paddleocr-finetuning-distribution.json",
    ):
        if json_path.exists():
            _load_safe_json(json_path)


def _reject_artifact_privacy_fields(value: object) -> None:
    """Reject raw/provider/credential/original-path fields in JSON payloads.

    Args:
        value: Candidate JSON-like value.

    Raises:
        PaddleOCRFineTuningExportError: If forbidden fields are present.
    """
    if isinstance(value, Mapping):
        forbidden = ARTIFACT_PRIVACY_FORBIDDEN_KEYS.intersection(str(key).lower() for key in value)
        if forbidden:
            raise PaddleOCRFineTuningExportError(
                f"Artifact contains forbidden raw field(s): {sorted(forbidden)}"
            )
        for nested_value in value.values():
            _reject_artifact_privacy_fields(nested_value)
    elif isinstance(value, list):
        for item in value:
            _reject_artifact_privacy_fields(item)


def _copy_private_inputs(
    *,
    queue_dir: Path,
    export_dir: Path,
    training_output_dir: Path,
    full_private_dir: Path,
) -> dict[str, str]:
    """Copy private input trees into the artifact.

    Args:
        queue_dir: Source queue directory.
        export_dir: Source export directory.
        training_output_dir: Source training output directory.
        full_private_dir: Destination full-private root.

    Returns:
        Mapping of logical input names to artifact-relative copy paths.
    """
    copies = {
        QUEUE_COPY_DIR_NAME: (queue_dir, full_private_dir / QUEUE_COPY_DIR_NAME),
        EXPORT_COPY_DIR_NAME: (export_dir, full_private_dir / EXPORT_COPY_DIR_NAME),
        TRAINING_COPY_DIR_NAME: (
            training_output_dir,
            full_private_dir / TRAINING_COPY_DIR_NAME,
        ),
    }
    copied: dict[str, str] = {}
    for name, (source, destination) in copies.items():
        shutil.copytree(source, destination)
        copied[name] = destination.relative_to(full_private_dir.parent).as_posix()
    return copied


def _build_redacted_summary(
    *,
    source_dataset_id: str,
    queue_payload: Mapping[str, object],
    queue_report: Mapping[str, object],
    export_manifest: Mapping[str, object],
    export_report: Mapping[str, object],
    training_summary: Mapping[str, object],
    privacy_assertions: Mapping[str, bool],
) -> dict[str, object]:
    """Build a public-safe aggregate artifact summary.

    Args:
        source_dataset_id: Pseudonymous dataset id.
        queue_payload: Parsed queue payload.
        queue_report: Parsed public queue report.
        export_manifest: Parsed exported manifest.
        export_report: Parsed export distribution report.
        training_summary: Aggregate training output summary.
        privacy_assertions: Redacted summary privacy assertions.

    Returns:
        JSON-serializable redacted summary.
    """
    return {
        "schema_version": REDACTED_SUMMARY_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "artifact_type": "redacted-summary",
        "source_dataset_id": source_dataset_id,
        "queue": {
            "schema_version": queue_payload.get("schema_version"),
            "source_root_hash": queue_payload.get("source_root_hash"),
            "selected_image_count": queue_report.get("selected_image_count"),
            "split_counts": queue_report.get("split_counts", {}),
            "source_kind_counts": queue_report.get("source_kind_counts", {}),
            "product_group_count": queue_report.get("product_group_count"),
        },
        "export": {
            "schema_version": export_manifest.get("schema_version"),
            "item_count": export_report.get("item_count"),
            "split_counts": export_report.get("split_counts", {}),
            "task_type_counts": export_report.get("task_type_counts", {}),
            "language_mix_counts": export_report.get("language_mix_counts", {}),
            "field_type_counts": export_report.get("field_type_counts", {}),
            "human_verified_count": export_report.get("human_verified_count"),
        },
        "training": training_summary,
        "privacy_assertions": privacy_assertions,
    }


def _build_artifact_manifest(
    *,
    source_dataset_id: str,
    queue_dir: Path,
    export_dir: Path,
    training_output_dir: Path,
    output_dir: Path,
    paddleocr_source_dir: Path,
    copied_subtrees: Mapping[str, str],
    queue_payload: Mapping[str, object],
    queue_report: Mapping[str, object],
    export_manifest: Mapping[str, object],
    export_report: Mapping[str, object],
    training_summary: Mapping[str, object],
    tools: Mapping[str, Path],
    det_config: Path,
    rec_config: Path,
    privacy_assertions: Mapping[str, bool],
) -> dict[str, object]:
    """Build the private artifact manifest.

    Args:
        source_dataset_id: Pseudonymous dataset id.
        queue_dir: Source queue directory.
        export_dir: Source export directory.
        training_output_dir: Source training output directory.
        output_dir: Artifact output directory.
        paddleocr_source_dir: PaddleOCR checkout.
        copied_subtrees: Artifact-relative copied subtree paths.
        queue_payload: Parsed queue payload.
        queue_report: Parsed public queue report.
        export_manifest: Parsed exported manifest.
        export_report: Parsed export distribution report.
        training_summary: Aggregate training output summary.
        tools: Validated PaddleOCR tool paths.
        det_config: Resolved detection config path.
        rec_config: Resolved recognition config path.
        privacy_assertions: Privacy assertions.

    Returns:
        JSON-serializable private artifact manifest.
    """
    return {
        "schema_version": PRIVATE_ARTIFACT_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "artifact_type": "full-private",
        "source_dataset_id": source_dataset_id,
        "inputs": {
            "queue_dir": str(queue_dir),
            "export_dir": str(export_dir),
            "training_output_dir": str(training_output_dir),
            "paddleocr_source_dir": str(paddleocr_source_dir),
        },
        "outputs": {
            "artifact_dir": str(output_dir),
            "full_private_dir": str(output_dir / FULL_PRIVATE_DIR_NAME),
            "artifact_manifest": ARTIFACT_MANIFEST_NAME,
            "redacted_summary": REDACTED_SUMMARY_NAME,
            "checksums": CHECKSUMS_FILE_NAME,
        },
        "copied_subtrees": dict(copied_subtrees),
        "queue": {
            "schema_version": queue_payload.get("schema_version"),
            "source_root_hash": queue_payload.get("source_root_hash"),
            "selected_image_count": queue_report.get("selected_image_count"),
            "scanner": queue_report.get("scanner", {}),
            "split_counts": queue_report.get("split_counts", {}),
            "source_kind_counts": queue_report.get("source_kind_counts", {}),
            "product_group_count": queue_report.get("product_group_count"),
        },
        "export": {
            "schema_version": export_manifest.get("schema_version"),
            "item_count": export_report.get("item_count"),
            "split_counts": export_report.get("split_counts", {}),
            "task_type_counts": export_report.get("task_type_counts", {}),
            "human_verified_count": export_report.get("human_verified_count"),
        },
        "training": training_summary,
        "paddleocr": {
            "det_model_name": DEFAULT_DET_MODEL_NAME,
            "rec_model_name": DEFAULT_REC_MODEL_NAME,
            "det_config": str(det_config),
            "rec_config": str(rec_config),
            "tools": {name: str(path) for name, path in tools.items()},
            "network_downloads_used": False,
        },
        "git": _git_state(),
        "privacy_assertions": privacy_assertions,
    }


def _training_summary(training_output_dir: Path) -> dict[str, object]:
    """Summarize training output files without reading model contents.

    Args:
        training_output_dir: Training output directory.

    Returns:
        Aggregate training output summary.
    """
    files = [path for path in training_output_dir.rglob("*") if path.is_file()]
    suffix_counts: dict[str, int] = {}
    for path in files:
        suffix = path.suffix or "[no_suffix]"
        suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
    model_file_count = sum(1 for path in files if _is_model_file(path))
    return {
        "file_count": len(files),
        "model_file_count": model_file_count,
        "contains_model_files": model_file_count > 0,
        "suffix_counts": dict(sorted(suffix_counts.items())),
    }


def _is_model_file(path: Path) -> bool:
    """Return whether a path looks like a PaddleOCR model artifact.

    Args:
        path: Candidate file path.

    Returns:
        True when the suffix is one of the Paddle/Paddle-to-ONNX model suffixes.
    """
    if path.name.endswith(".pdiparams.info"):
        return True
    return path.suffix in MODEL_FILE_SUFFIXES


def _privacy_assertions() -> dict[str, bool]:
    """Return privacy assertions for the redacted artifact summary.

    Returns:
        Privacy assertion map.
    """
    return {
        "contains_original_paths": False,
        "contains_original_file_names": False,
        "contains_raw_ocr_text": False,
        "contains_provider_payload": False,
        "contains_api_credentials": False,
        "contains_image_bytes": False,
    }


def _write_checksums(output_dir: Path) -> list[ChecksumEntry]:
    """Write artifact checksums.

    Args:
        output_dir: Artifact root.

    Returns:
        Checksum entries for every artifact file except the checksum file.
    """
    entries = [_checksum_entry(output_dir, path) for path in _iter_checksum_files(output_dir)]
    lines = [f"{entry.sha256}  {entry.path}" for entry in entries]
    (output_dir / CHECKSUMS_FILE_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return entries


def _iter_checksum_files(output_dir: Path) -> list[Path]:
    """Return files to include in checksums.

    Args:
        output_dir: Artifact root.

    Returns:
        Sorted file paths excluding the checksum file itself.
    """
    return sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file() and path.name != CHECKSUMS_FILE_NAME
    )


def _checksum_entry(output_dir: Path, path: Path) -> ChecksumEntry:
    """Build one checksum entry.

    Args:
        output_dir: Artifact root.
        path: File path to hash.

    Returns:
        Checksum entry.
    """
    digest = sha256(path.read_bytes()).hexdigest()
    return ChecksumEntry(
        path=path.relative_to(output_dir).as_posix(),
        sha256=digest,
        size_bytes=path.stat().st_size,
    )


def _verify_checksums(output_dir: Path, checksums: list[ChecksumEntry]) -> None:
    """Verify freshly written checksum entries against current files.

    Args:
        output_dir: Artifact root.
        checksums: Checksum entries to verify.

    Raises:
        PaddleOCRPrivateArtifactError: If any digest no longer matches.
    """
    for entry in checksums:
        path = output_dir / entry.path
        digest = sha256(path.read_bytes()).hexdigest()
        if digest != entry.sha256:
            raise PaddleOCRPrivateArtifactError(f"checksum mismatch: {entry.path}")


def _git_state() -> dict[str, object]:
    """Return git provenance for the backend checkout.

    Returns:
        Git state with best-effort fields when git is unavailable.
    """
    return {
        "root": _git_command(["rev-parse", "--show-toplevel"]),
        "head": _git_command(["rev-parse", "HEAD"]),
        "status_short": _git_command(["status", "--short"]),
    }


def _git_command(args: list[str]) -> str | None:
    """Run a read-only git command.

    Args:
        args: Git arguments after ``git -C BACKEND_ROOT``.

    Returns:
        Trimmed stdout, or None if git is unavailable or the command fails.
    """
    completed = subprocess.run(
        ["git", "-C", str(BACKEND_ROOT), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


if __name__ == "__main__":
    main()
