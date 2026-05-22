"""Build redacted OCR manifests for Naver Tampermonkey supplement images.

The script scans the local Tampermonkey crawl directory, classifies detail-page
and review images, and writes an allowlisted JSONL manifest for the existing
OCR observation collector. It does not run OCR, persist image bytes, or write
raw OCR/provider/model payloads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import random
import re
import unicodedata
import warnings
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from PIL import Image, UnidentifiedImageError

SOURCE_DOC_URLS = (
    "https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html",
    "https://api.ncloud-docs.com/docs/en/ai-application-service-ocr",
    "https://api.ncloud-docs.com/docs/en/ai-application-service-ocr-ocr",
    "https://cloud.google.com/vision/docs/ocr",
    "https://docs.ollama.com/capabilities/structured-outputs",
)
DEFAULT_SOURCE_ROOT = Path(
    os.environ.get(
        "NAVER_TAMPERMONKEY_SOURCE_ROOT",
        "data/private/naver_tampermonkey",
    )
)
DEFAULT_IMAGE_ROOT_ENV_VAR = "NAVER_TAMPERMONKEY_SOURCE_ROOT"
IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif"})
ALLOWED_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MAX_DECODED_PIXELS = 50_000_000
MIN_PRODUCT_PATH_PARTS = 2
SMALL_IMAGE_BYTES = 500_000
MEDIUM_IMAGE_BYTES = 5_000_000
PRODUCT_ID_PATTERN = re.compile(r"_(?P<product_id>\d{5,})$")
RAW_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "image_bytes",
        "ocr_text",
        "provider_payload",
        "raw_image",
        "raw_model_response",
        "raw_ocr_text",
        "raw_provider_payload",
        "request_headers",
        "service_key",
    }
)

Section = Literal["detail", "review", "unknown"]
ManifestSection = Literal["detail", "review", "all"]


@dataclass(frozen=True)
class NaverImageCandidate:
    """Decoded OCR candidate from the Tampermonkey crawl tree.

    Args:
        path: Absolute local image path.
        relative_path: Path relative to the source root.
        category: Top-level category directory, NFC-normalized.
        product_dir: Product-level directory, NFC-normalized.
        product_id: Parsed trailing Naver product id when present.
        section: Detail/review/unknown section classification.
        mime_type: PIL-detected image MIME type.
        width: Decoded image width in pixels.
        height: Decoded image height in pixels.
        size_bytes: File size in bytes.
    """

    path: Path
    relative_path: Path
    category: str
    product_dir: str
    product_id: str | None
    section: Section
    mime_type: str
    width: int
    height: int
    size_bytes: int


def main() -> None:
    """Build a redacted manifest and inventory from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--manifest-name", default="manifest-detail-smoke-30.jsonl")
    parser.add_argument("--inventory-name", default="inventory.json")
    parser.add_argument("--image-root-env-var", default=DEFAULT_IMAGE_ROOT_ENV_VAR)
    parser.add_argument("--section", choices=("detail", "review", "all"), default="detail")
    parser.add_argument("--sample-size", type=int, default=30)
    parser.add_argument("--scan-limit", type=int, default=200_000)
    parser.add_argument("--seed", type=int, default=20260522)
    parser.add_argument("--min-width", type=int, default=160)
    parser.add_argument("--min-height", type=int, default=120)
    parser.add_argument("--max-bytes", type=int, default=50_000_000)
    parser.add_argument(
        "--review-personal-data-cleared",
        action="store_true",
        help=(
            "Allow review images to be emitted with contains_personal_data=false. "
            "Without this flag, review rows are emitted for local-only PII screening "
            "with contains_personal_data=null and external_transfer_allowed=false."
        ),
    )
    args = parser.parse_args()
    summary = build_naver_tampermonkey_manifest(
        source_root=args.source_root,
        output_dir=args.output_dir,
        manifest_name=args.manifest_name,
        inventory_name=args.inventory_name,
        image_root_env_var=args.image_root_env_var,
        section=args.section,
        sample_size=args.sample_size,
        scan_limit=args.scan_limit,
        seed=args.seed,
        min_width=args.min_width,
        min_height=args.min_height,
        max_bytes=args.max_bytes,
        review_personal_data_cleared=args.review_personal_data_cleared,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def build_naver_tampermonkey_manifest(
    *,
    source_root: Path,
    output_dir: Path,
    manifest_name: str,
    inventory_name: str,
    image_root_env_var: str = DEFAULT_IMAGE_ROOT_ENV_VAR,
    section: ManifestSection,
    sample_size: int,
    scan_limit: int,
    seed: int,
    min_width: int,
    min_height: int,
    max_bytes: int,
    review_personal_data_cleared: bool = False,
) -> dict[str, object]:
    """Scan the crawl tree and write inventory plus a sampled manifest.

    Args:
        source_root: Local Tampermonkey crawl root.
        output_dir: Destination for generated inventory and manifest files.
        manifest_name: JSONL manifest filename.
        inventory_name: JSON inventory filename.
        image_root_env_var: Environment variable token used in ``image_path``
            instead of writing the operator's absolute local source path.
        section: Section to include in the manifest.
        sample_size: Maximum number of manifest rows.
        scan_limit: Maximum number of files to inspect.
        seed: Deterministic category-balanced sampling seed.
        min_width: Minimum decoded image width.
        min_height: Minimum decoded image height.
        max_bytes: Maximum file size in bytes.
        review_personal_data_cleared: Whether review images are cleared for external eligibility.

    Returns:
        Redacted summary with generated artifact paths and counts.

    Raises:
        ValueError: If inputs are invalid.
    """
    _validate_options(
        source_root=source_root,
        image_root_env_var=image_root_env_var,
        sample_size=sample_size,
        scan_limit=scan_limit,
        min_width=min_width,
        min_height=min_height,
        max_bytes=max_bytes,
    )
    source_root = source_root.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    candidates, inventory = scan_naver_tampermonkey_images(
        source_root=source_root,
        scan_limit=scan_limit,
        min_width=min_width,
        min_height=min_height,
        max_bytes=max_bytes,
    )
    selected = select_manifest_candidates(
        candidates,
        section=section,
        sample_size=sample_size,
        seed=seed,
    )
    rows = build_manifest_rows(
        selected,
        image_root_env_var=image_root_env_var,
        review_personal_data_cleared=review_personal_data_cleared,
    )
    inventory = {
        **inventory,
        "generated_at": datetime.now(UTC).isoformat(),
        "source_root_hash": _sha256_text(str(source_root)),
        "source_root_exists": source_root.exists(),
        "manifest_section": section,
        "manifest_sample_size": sample_size,
        "manifest_row_count": len(rows),
        "source_doc_urls": list(SOURCE_DOC_URLS),
        "raw_artifacts_stored": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
    }
    _reject_raw_fields(inventory)
    for row in rows:
        _reject_raw_fields(row)

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / manifest_name
    inventory_path = output_dir / inventory_name
    manifest_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    inventory_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "manifest": str(manifest_path),
        "inventory": str(inventory_path),
        "manifest_row_count": len(rows),
        "candidate_count": len(candidates),
        "raw_artifacts_stored": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
    }


def scan_naver_tampermonkey_images(
    *,
    source_root: Path,
    scan_limit: int,
    min_width: int,
    min_height: int,
    max_bytes: int,
) -> tuple[list[NaverImageCandidate], dict[str, object]]:
    """Scan image metadata from the crawl tree.

    Args:
        source_root: Local Tampermonkey crawl root.
        scan_limit: Maximum number of files to inspect.
        min_width: Minimum decoded image width.
        min_height: Minimum decoded image height.
        max_bytes: Maximum file size in bytes.

    Returns:
        Candidate list and redacted inventory counters.
    """
    source_root = source_root.expanduser().resolve()
    counters: Counter[str] = Counter()
    section_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    extension_counts: Counter[str] = Counter()
    mime_counts: Counter[str] = Counter()
    product_groups: set[tuple[str, str]] = set()
    candidates: list[NaverImageCandidate] = []

    for path in sorted(source_root.rglob("*")):
        if counters["files_seen"] >= scan_limit:
            break
        if not path.is_file():
            counters["non_files_skipped"] += 1
            continue
        counters["files_seen"] += 1
        suffix = path.suffix.lower()
        extension_counts[suffix or "<none>"] += 1
        if suffix not in IMAGE_SUFFIXES:
            counters["unsupported_extension_skipped"] += 1
            continue
        size_bytes = path.stat().st_size
        if size_bytes > max_bytes:
            counters["oversized_skipped"] += 1
            continue
        decoded = _decode_image_metadata(path)
        if decoded is None:
            counters["decode_failed"] += 1
            continue
        mime_type, width, height = decoded
        mime_counts[mime_type] += 1
        if mime_type not in ALLOWED_MIME_TYPES:
            counters["unsupported_mime_skipped"] += 1
            continue
        if width * height > MAX_DECODED_PIXELS:
            counters["huge_image_skipped"] += 1
            continue
        if width < min_width or height < min_height:
            counters["small_image_skipped"] += 1
            continue
        relative_path = path.relative_to(source_root)
        section = _section_from_path(relative_path)
        category = _category_from_path(relative_path)
        product_dir = _product_dir_from_path(relative_path)
        section_counts[section] += 1
        category_counts[category] += 1
        product_groups.add((category, product_dir))
        candidates.append(
            NaverImageCandidate(
                path=path,
                relative_path=relative_path,
                category=category,
                product_dir=product_dir,
                product_id=_product_id_from_dir(product_dir),
                section=section,
                mime_type=mime_type,
                width=width,
                height=height,
                size_bytes=size_bytes,
            )
        )
    inventory: dict[str, object] = {
        "files_seen": counters["files_seen"],
        "candidate_count": len(candidates),
        "section_counts": dict(sorted(section_counts.items())),
        "category_count": len(category_counts),
        "product_dir_count": len(product_groups),
        "top_categories": dict(category_counts.most_common(20)),
        "extension_counts": dict(sorted(extension_counts.items())),
        "mime_counts": dict(sorted(mime_counts.items())),
        "skip_counts": {
            key: value
            for key, value in sorted(counters.items())
            if key.endswith("_skipped") or key == "decode_failed"
        },
    }
    return candidates, inventory


def select_manifest_candidates(
    candidates: list[NaverImageCandidate],
    *,
    section: ManifestSection,
    sample_size: int,
    seed: int,
) -> list[NaverImageCandidate]:
    """Select a deterministic category-balanced manifest sample.

    Args:
        candidates: Decoded candidates.
        section: Section filter.
        sample_size: Maximum selected rows.
        seed: Deterministic sampling seed.

    Returns:
        Selected candidates.
    """
    if section == "all":
        filtered = [item for item in candidates if item.section in {"detail", "review"}]
    else:
        filtered = [item for item in candidates if item.section == section]
    grouped: dict[str, list[NaverImageCandidate]] = {}
    rng = random.Random(seed)
    for candidate in filtered:
        grouped.setdefault(candidate.category, []).append(candidate)
    for group in grouped.values():
        rng.shuffle(group)
        group.sort(key=lambda item: (item.product_dir, item.relative_path.as_posix()))
    selected: list[NaverImageCandidate] = []
    seen_sha256: set[str] = set()
    while grouped and len(selected) < sample_size:
        for category in sorted(grouped):
            group = grouped[category]
            if not group:
                del grouped[category]
                continue
            candidate = group.pop(0)
            image_sha256 = _sha256_file(candidate.path)
            if image_sha256 in seen_sha256:
                continue
            seen_sha256.add(image_sha256)
            selected.append(candidate)
            if len(selected) >= sample_size:
                break
    return selected


def build_manifest_rows(
    candidates: list[NaverImageCandidate],
    *,
    image_root_env_var: str = DEFAULT_IMAGE_ROOT_ENV_VAR,
    review_personal_data_cleared: bool = False,
) -> list[dict[str, object]]:
    """Convert selected candidates into collector-compatible JSONL rows.

    Args:
        candidates: Selected candidates.
        image_root_env_var: Environment variable token used to locate the
            source root at runtime without storing its absolute path.
        review_personal_data_cleared: Whether review images are cleared as not personal data.

    Returns:
        JSON-serializable manifest rows.

    """
    rows: list[dict[str, object]] = []
    for index, candidate in enumerate(candidates, 1):
        image_sha256 = _sha256_file(candidate.path)
        section_token = "detail" if candidate.section == "detail" else "review"
        review_pending_screening = (
            candidate.section == "review" and not review_personal_data_cleared
        )
        row = {
            "fixture_id": f"naver-tm-{section_token}-{index:06d}",
            "source": "naver_tampermonkey",
            "category": candidate.category,
            "product_dir": candidate.product_dir,
            "product_id": candidate.product_id,
            "section": section_token,
            "image_path": _tokenized_image_path(image_root_env_var, candidate.relative_path),
            "image_sha256": image_sha256,
            "file_size_bytes": candidate.size_bytes,
            "mime_type": candidate.mime_type,
            "width": candidate.width,
            "height": candidate.height,
            "size_bucket": _size_bucket(candidate.size_bytes),
            "license_status": "team_approved",
            "consent_status": "team_approved",
            "contains_personal_data": None if review_pending_screening else False,
            "pii_screening_status": (
                "not_required_detail_page"
                if candidate.section == "detail"
                else (
                    "pending_local_screening"
                    if review_pending_screening
                    else "operator_cleared_review_local_only"
                )
            ),
            "external_transfer_allowed": candidate.section == "detail",
            "local_processing_allowed": True,
            "labels": [
                "naver_tampermonkey",
                section_token,
                _strip_category_brackets(candidate.category),
            ],
            "source_metadata": {
                "relative_path_hash": _sha256_text(candidate.relative_path.as_posix()),
                "category": _strip_category_brackets(candidate.category),
                "product_id_present": candidate.product_id is not None,
                "section": section_token,
            },
            "expected": {},
        }
        _reject_raw_fields(row)
        rows.append(row)
    return rows


def _validate_options(
    *,
    source_root: Path,
    image_root_env_var: str,
    sample_size: int,
    scan_limit: int,
    min_width: int,
    min_height: int,
    max_bytes: int,
) -> None:
    """Validate manifest build options."""
    if not source_root.expanduser().is_dir():
        raise ValueError(f"source_root is not a directory: {source_root}")
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", image_root_env_var):
        raise ValueError("image_root_env_var must be an uppercase environment variable name.")
    if sample_size < 1 or scan_limit < 1:
        raise ValueError("sample_size and scan_limit must be positive.")
    if min_width < 1 or min_height < 1 or max_bytes < 1:
        raise ValueError("min_width, min_height, and max_bytes must be positive.")


def _decode_image_metadata(path: Path) -> tuple[str, int, int] | None:
    """Decode MIME type and dimensions without retaining image bytes."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                width, height = image.size
                mime_type = Image.MIME.get(image.format or "")
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError):
        return None
    if not mime_type:
        guessed_type, _ = mimetypes.guess_type(path.name)
        mime_type = guessed_type or "application/octet-stream"
    return mime_type, width, height


def _section_from_path(relative_path: Path) -> Section:
    """Return detail/review section from NFC-normalized path parts."""
    parts = [_normalize_path_text(part) for part in relative_path.parts]
    if any(part == "상세페이지" for part in parts):
        return "detail"
    if any(part == "리뷰" for part in parts):
        return "review"
    return "unknown"


def _category_from_path(relative_path: Path) -> str:
    """Return the top-level category segment."""
    if not relative_path.parts:
        return "unknown"
    return _normalize_path_text(relative_path.parts[0])


def _product_dir_from_path(relative_path: Path) -> str:
    """Return the product directory before the section segment."""
    parts = [_normalize_path_text(part) for part in relative_path.parts]
    for index, part in enumerate(parts):
        if part in {"상세페이지", "리뷰"} and index > 0:
            return parts[index - 1]
    if len(parts) >= MIN_PRODUCT_PATH_PARTS:
        return parts[1]
    return "unknown"


def _product_id_from_dir(product_dir: str) -> str | None:
    """Extract a trailing Naver product id from a product directory."""
    match = PRODUCT_ID_PATTERN.search(product_dir)
    return match.group("product_id") if match else None


def _strip_category_brackets(value: str) -> str:
    """Normalize category text for report labels."""
    stripped = _normalize_path_text(value).strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        return stripped[1:-1].strip() or "unknown"
    return stripped or "unknown"


def _size_bucket(size_bytes: int) -> str:
    """Return a coarse size bucket for report grouping."""
    if size_bytes < SMALL_IMAGE_BYTES:
        return "small"
    if size_bytes < MEDIUM_IMAGE_BYTES:
        return "medium"
    return "large"


def _normalize_path_text(value: str) -> str:
    """Normalize macOS decomposed Korean path segments to NFC."""
    return unicodedata.normalize("NFC", value)


def _tokenized_image_path(image_root_env_var: str, relative_path: Path) -> str:
    """Return a runtime-resolvable image path without local absolute prefixes.

    Args:
        image_root_env_var: Environment variable that points to the source root.
        relative_path: Path under the source root.

    Returns:
        ``$ENV_VAR/<relative path>`` for collector runtime expansion.
    """
    return f"${image_root_env_var}/{relative_path.as_posix()}"


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a local file."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    """Return a SHA-256 digest for path metadata."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _reject_raw_fields(value: object) -> None:
    """Reject raw OCR/image/provider/model fields before writing artifacts."""
    if isinstance(value, dict):
        forbidden = RAW_FORBIDDEN_KEYS.intersection(str(key).lower() for key in value)
        if forbidden:
            raise ValueError(f"Payload contains forbidden raw field(s): {sorted(forbidden)}")
        for nested in value.values():
            _reject_raw_fields(nested)
    elif isinstance(value, list):
        for item in value:
            _reject_raw_fields(item)


if __name__ == "__main__":
    main()
