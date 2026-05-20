"""Join a prepared supplement OCR live manifest with collected observations.

The ``prepare_supplement_ocr_live_manifest.py`` script emits a JSON object with
a ``cases`` list, and ``collect_supplement_ocr_observations.py`` writes a JSONL
file with one redacted observation per line. The ``evaluate_ocr_three_tier.py``
report expects a JSONL manifest where each row carries both the case metadata
(``image_path``, ``expected``) and an ``observations`` array. This helper joins
the two artifacts into the row format the three-tier evaluator consumes.

The script does not run OCR, does not read raw image bytes, and refuses any
``raw_*`` keys in either input. It only forwards redacted fields already
present in the source artifacts.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

RAW_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "image_bytes",
        "ocr_text",
        "provider_payload",
        "raw_image",
        "raw_ocr_text",
        "raw_provider_payload",
        "request_headers",
        "service_key",
    }
)


def main() -> None:
    """Run the three-tier manifest joiner from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
        help="Prepared manifest JSON (object with cases list).",
    )
    parser.add_argument(
        "--observations",
        required=True,
        type=Path,
        help="Collected observations JSONL.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Three-tier evaluator JSONL output path.",
    )
    args = parser.parse_args()

    summary = build_three_tier_manifest(
        manifest_path=args.manifest,
        observations_path=args.observations,
        output_path=args.output,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def build_three_tier_manifest(
    *,
    manifest_path: Path,
    observations_path: Path,
    output_path: Path,
) -> dict[str, object]:
    """Join manifest cases with observations and write JSONL rows.

    Args:
        manifest_path: Prepared manifest JSON object.
        observations_path: Collected observations JSONL.
        output_path: Destination JSONL.

    Returns:
        Summary with fixture and observation counts.

    Raises:
        ValueError: If either input contains forbidden raw fields or is malformed.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _reject_raw(manifest)
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Manifest must contain a 'cases' list.")

    observations_by_id: dict[str, list[dict[str, object]]] = {}
    for observation in _read_jsonl_rows(observations_path):
        _reject_raw(observation)
        fixture_id = observation.get("fixture_id")
        if not isinstance(fixture_id, str):
            raise ValueError("Observation row missing 'fixture_id'.")
        observations_by_id.setdefault(fixture_id, []).append(observation)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    matched_observation_count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for case in cases:
            if not isinstance(case, dict):
                raise ValueError("Manifest case must be a JSON object.")
            fixture_id = case.get("fixture_id")
            if not isinstance(fixture_id, str):
                raise ValueError("Manifest case missing 'fixture_id'.")
            observations = observations_by_id.get(fixture_id, [])
            row = {
                "fixture_id": fixture_id,
                "image_path": case.get("image_path"),
                "labels": case.get("labels", []),
                "expected": case.get("expected", {}),
                "observations": observations,
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
            matched_observation_count += len(observations)

    return {
        "rows_written": written,
        "matched_observation_count": matched_observation_count,
        "manifest": str(manifest_path),
        "observations": str(observations_path),
        "output": str(output_path),
        "raw_image_stored": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
    }


def _read_jsonl_rows(path: Path) -> Iterable[dict[str, object]]:
    """Yield JSONL rows as dicts, skipping blank or comment lines.

    Args:
        path: JSONL path.

    Yields:
        Decoded JSON object per non-empty line.

    Raises:
        ValueError: If a line is not a JSON object.
    """
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError(f"Observation line {line_number} must be a JSON object.")
        yield parsed


def _reject_raw(value: object) -> None:
    """Reject raw artifact keys recursively.

    Args:
        value: Candidate value.

    Raises:
        ValueError: If a forbidden raw key is present anywhere in ``value``.
    """
    if isinstance(value, dict):
        forbidden = RAW_FORBIDDEN_KEYS.intersection(value.keys())
        if forbidden:
            raise ValueError(f"Input contains forbidden raw field(s): {sorted(forbidden)}")
        for nested in value.values():
            _reject_raw(nested)
    elif isinstance(value, list):
        for item in value:
            _reject_raw(item)


if __name__ == "__main__":
    main()
