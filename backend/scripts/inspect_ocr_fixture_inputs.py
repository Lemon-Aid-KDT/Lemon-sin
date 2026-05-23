"""Inspect OCR fixture image inputs without exposing raw image or OCR text.

The script validates manifest fixture rows through the same privacy-aware
manifest reader used by the OCR observation collector, then reports bounded
image metadata only. It never writes local image paths, image bytes, OCR text,
provider payloads, request headers, or secrets.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from scripts.collect_supplement_ocr_observations import (  # noqa: E402
    FixtureCase,
    _read_fixture_manifest,
)


@dataclass(frozen=True)
class FixtureInputInspection:
    """Bounded fixture input inspection result.

    Attributes:
        fixture_id: Stable fixture identifier.
        status: Inspection status token.
        metadata: Redacted image metadata. Contains no local paths or bytes.
    """

    fixture_id: str
    status: str
    metadata: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable inspection row.

        Returns:
            Redacted inspection row.
        """
        return {
            "fixture_id": self.fixture_id,
            "status": self.status,
            **self.metadata,
        }


def inspect_manifest_inputs(
    *,
    manifest_path: Path,
    fixture_ids: set[str] | None = None,
) -> dict[str, object]:
    """Inspect fixture image inputs in a manifest.

    Args:
        manifest_path: OCR fixture manifest path.
        fixture_ids: Optional fixture ids to include.

    Returns:
        Redacted inspection summary.
    """
    fixtures = _read_fixture_manifest(manifest_path, providers=("paddleocr_local",))
    selected = [
        fixture for fixture in fixtures if fixture_ids is None or fixture.fixture_id in fixture_ids
    ]
    return {
        "manifest_name": manifest_path.name,
        "requested_fixture_count": len(fixture_ids or set()),
        "inspected_fixture_count": len(selected),
        "raw_artifacts_stored": False,
        "raw_ocr_text_stored": False,
        "fixtures": [_inspect_fixture(fixture).as_dict() for fixture in selected],
    }


def _inspect_fixture(fixture: FixtureCase) -> FixtureInputInspection:
    """Inspect one fixture image without serializing raw content.

    Args:
        fixture: Validated fixture case.

    Returns:
        Redacted input inspection row.
    """
    try:
        file_size = fixture.image_path.stat().st_size
    except OSError:
        return FixtureInputInspection(
            fixture_id=fixture.fixture_id,
            status="image_stat_error",
            metadata={},
        )
    try:
        with Image.open(fixture.image_path) as image:
            width, height = image.size
            image_format = image.format or "unknown"
            mime_type = Image.MIME.get(image_format, "application/octet-stream")
            mode = image.mode
    except (OSError, UnidentifiedImageError):
        return FixtureInputInspection(
            fixture_id=fixture.fixture_id,
            status="image_decode_error",
            metadata={"file_size_bytes": file_size},
        )

    return FixtureInputInspection(
        fixture_id=fixture.fixture_id,
        status="ok",
        metadata={
            "file_size_bytes": file_size,
            "format": image_format,
            "mime_type": mime_type,
            "width": width,
            "height": height,
            "mode": mode,
            "megapixels": round((width * height) / 1_000_000, 4),
            "sha256_verified": True,
        },
    )


def main(argv: list[str] | None = None) -> int:
    """Run the fixture input inspector.

    Args:
        argv: Optional CLI argument list.

    Returns:
        Process exit code. Zero means inspection completed.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--fixture-id",
        action="append",
        dest="fixture_ids",
        default=None,
        help="Fixture id to inspect. May be repeated. Defaults to all fixtures.",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    fixture_ids = set(args.fixture_ids) if args.fixture_ids else None
    summary = inspect_manifest_inputs(
        manifest_path=args.manifest,
        fixture_ids=fixture_ids,
    )
    payload = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
