"""Prepare a private PaddleOCR fine-tuning annotation queue.

The script scans an external, consented image corpus in read-only mode and
copies selected images into a gitignored private queue directory. It writes only
pseudonymous metadata: no original paths, file names, raw OCR text, provider
payloads, API headers, or image bytes appear in public reports.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from PIL import Image, UnidentifiedImageError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.learning.paddleocr_finetuning import reject_raw_manifest_fields  # noqa: E402

IMAGE_MIME_BY_FORMAT = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
QUEUE_SCHEMA_VERSION = "paddleocr-annotation-queue-v1"
PRIVATE_REPORT_SCHEMA_VERSION = "paddleocr-finetuning-queue-report-v1"
DEFAULT_MIN_PIXELS = 50_000
DEFAULT_MAX_PIXELS = 50_000_000
DEFAULT_MAX_SOURCE_IMAGES = 300
LARGE_IMAGE_PIXELS = 6_000_000
DETAIL_SOURCE_KIND = "detail"
REVIEW_SOURCE_KIND = "review"
OTHER_SOURCE_KIND = "other"


class PaddleOCRQueuePrepareError(ValueError):
    """Raised when a fine-tuning queue cannot be prepared safely."""


@dataclass(frozen=True)
class ImageCandidate:
    """Decoded image candidate eligible for private queue selection.

    Attributes:
        path: Absolute source image path. Kept in memory only; never written.
        image_sha256: SHA-256 hash of the source image bytes.
        width: Decoded image width.
        height: Decoded image height.
        mime_type: Decoded image MIME type.
        product_group_id: Pseudonymous product grouping key.
        split_group: Pseudonymous split grouping key.
        split: Deterministic split assigned from the product group.
        source_kind: Detail/review/other source category.
        extension: Safe output extension.
    """

    path: Path
    image_sha256: str
    width: int
    height: int
    mime_type: str
    product_group_id: str
    split_group: str
    split: str
    source_kind: str
    extension: str

    @property
    def pixels(self) -> int:
        """Return decoded pixel count.

        Returns:
            Width multiplied by height.
        """
        return self.width * self.height


@dataclass
class ScanStats:
    """Aggregate scanner counters.

    Attributes:
        files_seen: Number of files inspected.
        decode_failures: Decode failures.
        unsupported_mime: Files decoded to unsupported image formats.
        gif_excluded: GIF images skipped.
        too_small: Images below the minimum pixel threshold.
        too_large: Images above the maximum pixel threshold or PIL safety limit.
        duplicate_sha: Duplicate source image hashes skipped.
        candidates: Eligible candidates.
    """

    files_seen: int = 0
    decode_failures: int = 0
    unsupported_mime: int = 0
    gif_excluded: int = 0
    too_small: int = 0
    too_large: int = 0
    duplicate_sha: int = 0
    candidates: int = 0


@dataclass(frozen=True)
class QueueItem:
    """One local annotation queue item.

    Attributes:
        queue_id: Pseudonymous queue id.
        sample_id: Pseudonymous source sample id.
        source_image_id: Pseudonymous image id.
        image_path: Relative copied image path inside the queue directory.
        image_sha256: Source image SHA-256 hash.
        width: Image width.
        height: Image height.
        mime_type: Decoded image MIME type.
        product_group_id: Pseudonymous product grouping key.
        split_group: Pseudonymous split grouping key.
        split: Dataset split.
        source_kind: Detail/review/other source category.
        task_types: Fine-tuning task types requested for this image.
        human_verified: Always false at queue creation time.
        bootstrap_boxes: Optional local OCR bootstrap boxes. Empty in this script.
        quality_labels: Scanner quality tags.
    """

    queue_id: str
    sample_id: str
    source_image_id: str
    image_path: str
    image_sha256: str
    width: int
    height: int
    mime_type: str
    product_group_id: str
    split_group: str
    split: str
    source_kind: str
    task_types: list[str] = field(default_factory=lambda: ["detection", "recognition"])
    human_verified: bool = False
    bootstrap_boxes: list[dict[str, object]] = field(default_factory=list)
    quality_labels: list[str] = field(default_factory=list)


def main() -> None:
    """Run the private queue preparation CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--max-source-images", type=int, default=DEFAULT_MAX_SOURCE_IMAGES)
    parser.add_argument("--min-pixels", type=int, default=DEFAULT_MIN_PIXELS)
    parser.add_argument("--max-pixels", type=int, default=DEFAULT_MAX_PIXELS)
    args = parser.parse_args()

    summary = prepare_paddleocr_finetuning_queue(
        source_root=args.source_root,
        output_dir=args.output_dir,
        max_source_images=args.max_source_images,
        min_pixels=args.min_pixels,
        max_pixels=args.max_pixels,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def prepare_paddleocr_finetuning_queue(
    *,
    source_root: Path,
    output_dir: Path,
    max_source_images: int = DEFAULT_MAX_SOURCE_IMAGES,
    min_pixels: int = DEFAULT_MIN_PIXELS,
    max_pixels: int = DEFAULT_MAX_PIXELS,
) -> dict[str, object]:
    """Prepare a private annotation queue from an external image corpus.

    Args:
        source_root: External source directory. Read-only input.
        output_dir: Gitignored private output directory.
        max_source_images: Maximum copied source images.
        min_pixels: Minimum decoded pixel count.
        max_pixels: Maximum decoded pixel count.

    Returns:
        Redacted queue preparation summary.

    Raises:
        PaddleOCRQueuePrepareError: If inputs are invalid or no samples qualify.
    """
    if max_source_images <= 0:
        raise PaddleOCRQueuePrepareError("--max-source-images must be positive.")
    if min_pixels <= 0:
        raise PaddleOCRQueuePrepareError("--min-pixels must be positive.")
    if max_pixels <= min_pixels:
        raise PaddleOCRQueuePrepareError("--max-pixels must be greater than --min-pixels.")
    if not source_root.exists() or not source_root.is_dir():
        raise PaddleOCRQueuePrepareError(f"Source root is not a directory: {source_root}")

    stats = ScanStats()
    candidate_scan_limit = max(max_source_images * 5, max_source_images)
    candidates = list(
        scan_image_candidates(
            source_root=source_root,
            min_pixels=min_pixels,
            max_pixels=max_pixels,
            stats=stats,
            max_candidates=candidate_scan_limit,
        )
    )
    selected = select_stratified_candidates(candidates, max_source_images=max_source_images)
    if len(selected) < max_source_images:
        stats = ScanStats()
        candidates = list(
            scan_image_candidates(
                source_root=source_root,
                min_pixels=min_pixels,
                max_pixels=max_pixels,
                stats=stats,
                max_candidates=None,
            )
        )
        selected = select_stratified_candidates(candidates, max_source_images=max_source_images)
    if not selected:
        raise PaddleOCRQueuePrepareError("No eligible source images were found.")

    output_dir.mkdir(parents=True, exist_ok=True)
    image_root = output_dir / "images"
    items = copy_candidates_to_queue(selected=selected, image_root=image_root)
    queue_path = output_dir / "annotation_queue.json"
    report_path = output_dir / "public_report.json"
    html_path = output_dir / "annotation_queue.html"

    queue_payload = build_queue_payload(
        source_root=source_root,
        max_source_images=max_source_images,
        min_pixels=min_pixels,
        max_pixels=max_pixels,
        items=items,
        stats=stats,
    )
    reject_raw_manifest_fields(queue_payload)
    queue_path.write_text(
        json.dumps(queue_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    report_payload = build_public_report(items=items, stats=stats)
    reject_raw_manifest_fields(report_payload)
    report_path.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    html_path.write_text(build_static_annotation_html(), encoding="utf-8")

    return {
        "generated_at": queue_payload["generated_at"],
        "queue_dir": str(output_dir),
        "queue_path": str(queue_path),
        "public_report_path": str(report_path),
        "annotation_html_path": str(html_path),
        "selected_image_count": len(items),
        "source_root_hash": queue_payload["source_root_hash"],
        "raw_source_paths_stored": False,
        "raw_file_names_stored": False,
        "raw_ocr_text_stored": False,
        "provider_payload_stored": False,
        "image_bytes_stored_in_json": False,
    }


def scan_image_candidates(
    *,
    source_root: Path,
    min_pixels: int,
    max_pixels: int = DEFAULT_MAX_PIXELS,
    stats: ScanStats | None = None,
    max_candidates: int | None = None,
) -> Iterable[ImageCandidate]:
    """Scan source files and yield decoded, deduplicated image candidates.

    Args:
        source_root: External source directory.
        min_pixels: Minimum decoded pixel count.
        max_pixels: Maximum decoded pixel count.
        stats: Mutable aggregate counters.
        max_candidates: Optional early-stop count after eligible candidates.

    Yields:
        Eligible image candidates.
    """
    seen_hashes: set[str] = set()
    actual_stats = stats or ScanStats()
    yielded = 0
    for path in _prioritized_image_paths(source_root):
        if not path.is_file():
            continue
        actual_stats.files_seen += 1
        try:
            candidate = decode_image_candidate(path=path, source_root=source_root)
        except PaddleOCRQueuePrepareError as exc:
            if str(exc) == "gif":
                actual_stats.gif_excluded += 1
            elif str(exc) == "unsupported_mime":
                actual_stats.unsupported_mime += 1
            elif str(exc) == "too_large":
                actual_stats.too_large += 1
            else:
                actual_stats.decode_failures += 1
            continue

        if candidate.pixels < min_pixels:
            actual_stats.too_small += 1
            continue
        if candidate.pixels > max_pixels:
            actual_stats.too_large += 1
            continue
        if candidate.image_sha256 in seen_hashes:
            actual_stats.duplicate_sha += 1
            continue
        seen_hashes.add(candidate.image_sha256)
        actual_stats.candidates += 1
        yielded += 1
        yield candidate
        if max_candidates is not None and yielded >= max_candidates:
            return


def decode_image_candidate(*, path: Path, source_root: Path) -> ImageCandidate:
    """Decode one source path into an image candidate.

    Args:
        path: Source file path.
        source_root: Root used to derive pseudonymous group ids.

    Returns:
        Decoded image candidate.

    Raises:
        PaddleOCRQueuePrepareError: If the file is GIF, unsupported, or unreadable.
    """
    try:
        with Image.open(path) as image:
            image_format = (image.format or "").upper()
            if image_format == "GIF":
                raise PaddleOCRQueuePrepareError("gif")
            mime_type = IMAGE_MIME_BY_FORMAT.get(image_format)
            if mime_type is None:
                raise PaddleOCRQueuePrepareError("unsupported_mime")
            width, height = image.size
    except Image.DecompressionBombError as exc:
        raise PaddleOCRQueuePrepareError("too_large") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise PaddleOCRQueuePrepareError("decode_failure") from exc

    image_hash = sha256(path.read_bytes()).hexdigest()
    rel_parts = tuple(_normalize_part(part) for part in path.relative_to(source_root).parts)
    product_group_id = _pseudonymous_id("product", "/".join(rel_parts[:2] or rel_parts[:1]))
    split_group = _pseudonymous_id("split", product_group_id)
    return ImageCandidate(
        path=path,
        image_sha256=image_hash,
        width=width,
        height=height,
        mime_type=mime_type,
        product_group_id=product_group_id,
        split_group=split_group,
        split=split_for_group(product_group_id),
        source_kind=source_kind_from_parts(rel_parts),
        extension=extension_for_mime(mime_type),
    )


def select_stratified_candidates(
    candidates: Sequence[ImageCandidate],
    *,
    max_source_images: int,
) -> list[ImageCandidate]:
    """Select candidates by product group with detail images preferred.

    Args:
        candidates: Eligible decoded candidates.
        max_source_images: Maximum selected images.

    Returns:
        Deterministic round-robin selection.
    """
    grouped: dict[str, list[ImageCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.product_group_id].append(candidate)
    for group_candidates in grouped.values():
        group_candidates.sort(key=_candidate_sort_key)

    selected: list[ImageCandidate] = []
    group_ids = sorted(grouped)
    while len(selected) < max_source_images and group_ids:
        next_group_ids: list[str] = []
        for group_id in group_ids:
            group_candidates = grouped[group_id]
            if group_candidates and len(selected) < max_source_images:
                selected.append(group_candidates.pop(0))
            if group_candidates:
                next_group_ids.append(group_id)
        group_ids = next_group_ids
    return selected


def copy_candidates_to_queue(
    *,
    selected: Sequence[ImageCandidate],
    image_root: Path,
) -> list[QueueItem]:
    """Copy selected images into the private queue and build queue metadata.

    Args:
        selected: Selected image candidates.
        image_root: Private queue image root.

    Returns:
        Queue metadata items.
    """
    items: list[QueueItem] = []
    for index, candidate in enumerate(selected, start=1):
        queue_id = f"queue-{index:04d}-{candidate.image_sha256[:12]}"
        source_image_id = f"image-{candidate.image_sha256[:16]}"
        relative_image_path = Path("images") / candidate.split / f"{queue_id}{candidate.extension}"
        destination = image_root.parent / relative_image_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate.path, destination)
        items.append(
            QueueItem(
                queue_id=queue_id,
                sample_id=f"sample-{candidate.image_sha256[:16]}",
                source_image_id=source_image_id,
                image_path=relative_image_path.as_posix(),
                image_sha256=candidate.image_sha256,
                width=candidate.width,
                height=candidate.height,
                mime_type=candidate.mime_type,
                product_group_id=candidate.product_group_id,
                split_group=candidate.split_group,
                split=candidate.split,
                source_kind=candidate.source_kind,
                quality_labels=quality_labels_for_candidate(candidate),
            )
        )
    return items


def build_queue_payload(
    *,
    source_root: Path,
    max_source_images: int,
    min_pixels: int,
    max_pixels: int,
    items: Sequence[QueueItem],
    stats: ScanStats,
) -> dict[str, object]:
    """Build the private annotation queue payload.

    Args:
        source_root: External source directory.
        max_source_images: Maximum selected images.
        min_pixels: Minimum pixel filter.
        max_pixels: Maximum pixel filter.
        items: Queue items.
        stats: Scan counters.

    Returns:
        JSON-serializable queue payload.
    """
    return {
        "schema_version": QUEUE_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_root_hash": _pseudonymous_id("source-root", str(source_root.resolve())),
        "max_source_images": max_source_images,
        "min_pixels": min_pixels,
        "max_pixels": max_pixels,
        "scanner": asdict(stats),
        "items": [asdict(item) for item in items],
    }


def build_public_report(*, items: Sequence[QueueItem], stats: ScanStats) -> dict[str, object]:
    """Build aggregate public-safe queue report.

    Args:
        items: Queue items.
        stats: Scanner counters.

    Returns:
        Redacted aggregate report.
    """
    return {
        "schema_version": PRIVATE_REPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "selected_image_count": len(items),
        "scanner": asdict(stats),
        "split_counts": _count_values(item.split for item in items),
        "source_kind_counts": _count_values(item.source_kind for item in items),
        "product_group_count": len({item.product_group_id for item in items}),
        "contains_original_paths": False,
        "contains_original_file_names": False,
        "contains_raw_ocr_text": False,
        "contains_provider_payload": False,
        "contains_api_credentials": False,
    }


def build_static_annotation_html() -> str:
    """Build a local-only annotation helper page.

    Returns:
        Static HTML shell loaded by the annotation server.
    """
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PaddleOCR Annotation Queue</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 24px; }
    img { max-width: min(100%, 960px); border: 1px solid #ccc; }
    textarea { width: min(100%, 960px); min-height: 220px; }
    button { padding: 8px 12px; }
  </style>
</head>
<body>
  <h1>PaddleOCR Annotation Queue</h1>
  <p>Local-only helper. Save only human-verified box/transcript JSON.</p>
  <div id="app">Run serve_paddleocr_annotation_queue.py for interactive annotation.</div>
</body>
</html>
"""


def split_for_group(product_group_id: str) -> str:
    """Assign a deterministic split from a product group id.

    Args:
        product_group_id: Pseudonymous product group id.

    Returns:
        train, val, or test.
    """
    bucket = int(sha256(product_group_id.encode("utf-8")).hexdigest()[:8], 16) % 10
    if bucket == 0:
        return "test"
    if bucket == 1:
        return "val"
    return "train"


def source_kind_from_parts(parts: Sequence[str]) -> str:
    """Classify source image type from normalized path parts.

    Args:
        parts: Relative path parts.

    Returns:
        detail, review, or other.
    """
    if "상세페이지" in parts:
        return DETAIL_SOURCE_KIND
    if "리뷰" in parts:
        return REVIEW_SOURCE_KIND
    return OTHER_SOURCE_KIND


def extension_for_mime(mime_type: str) -> str:
    """Return a safe extension for a decoded MIME type.

    Args:
        mime_type: Decoded MIME type.

    Returns:
        File extension.

    Raises:
        PaddleOCRQueuePrepareError: If MIME is unsupported.
    """
    extensions = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    try:
        return extensions[mime_type]
    except KeyError as exc:
        raise PaddleOCRQueuePrepareError(f"Unsupported image MIME: {mime_type}") from exc


def quality_labels_for_candidate(candidate: ImageCandidate) -> list[str]:
    """Return coarse, non-sensitive quality labels for one candidate.

    Args:
        candidate: Image candidate.

    Returns:
        Quality label list.
    """
    labels: list[str] = []
    if candidate.pixels >= LARGE_IMAGE_PIXELS:
        labels.append("large_image")
    if candidate.width > candidate.height * 2 or candidate.height > candidate.width * 2:
        labels.append("wide_or_tall")
    if candidate.source_kind == DETAIL_SOURCE_KIND:
        labels.append("detail_page")
    return labels


def _candidate_sort_key(candidate: ImageCandidate) -> tuple[int, str]:
    source_rank = {DETAIL_SOURCE_KIND: 0, REVIEW_SOURCE_KIND: 1, OTHER_SOURCE_KIND: 2}
    return (source_rank.get(candidate.source_kind, 9), candidate.image_sha256)


def _prioritized_image_paths(source_root: Path) -> list[Path]:
    paths = [path for path in source_root.rglob("*") if path.is_file()]
    return sorted(paths, key=lambda path: (_source_rank_for_path(path, source_root), str(path)))


def _source_rank_for_path(path: Path, source_root: Path) -> int:
    try:
        parts = tuple(_normalize_part(part) for part in path.relative_to(source_root).parts)
    except ValueError:
        return 9
    source_rank = {DETAIL_SOURCE_KIND: 0, REVIEW_SOURCE_KIND: 1, OTHER_SOURCE_KIND: 2}
    return source_rank.get(source_kind_from_parts(parts), 9)


def _count_values(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _normalize_part(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _pseudonymous_id(prefix: str, value: str) -> str:
    digest = sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


if __name__ == "__main__":
    main()
