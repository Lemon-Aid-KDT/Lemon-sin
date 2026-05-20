"""Seed V2/V3 ground-truth snapshot templates from local PaddleOCR + Ollama parser.

The helper reads a prepared live OCR manifest, picks fixtures by id or
category, runs the fully-local PaddleOCR adapter to extract text, hands the
text to the local OllamaSupplementParser to produce a redacted structured
parse result, and merges the parser output into the existing V2 and V3
expected-snapshot templates living under ``tests/fixtures/supplement_labels/
expected/``. The auto-seeded values are marked with a provisional source
(``ocr_llm_auto_seed``) and a warning so a human reviewer can verify each row
before the fixture is used for accuracy measurement.

The script never persists raw OCR text, raw Ollama responses, image bytes,
or provider payloads. PaddleOCR text stays in process memory just long
enough to feed the structured parser; only the redacted structured fields
are written to disk.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.config import Settings  # type: ignore[import-untyped]  # noqa: E402
from src.llm.ollama import OllamaSupplementParser  # type: ignore[import-untyped]  # noqa: E402
from src.models.schemas.supplement_parser import (  # type: ignore[import-untyped]  # noqa: E402
    SupplementStructuredParseResultV2,
)
from src.models.schemas.supplement_snapshot import (  # type: ignore[import-untyped]  # noqa: E402
    SupplementParsedSnapshotV2,
    SupplementParsedSnapshotV3,
)
from src.ocr.base import OCRImageInput  # type: ignore[import-untyped]  # noqa: E402
from src.ocr.providers.paddle import PaddleOCRAdapter  # type: ignore[import-untyped]  # noqa: E402

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
AUTO_SEED_SOURCE = "ocr_llm_auto_seed"
AUTO_SEED_WARNING = "auto_seeded_from_llm_requires_human_verification"


def main() -> None:
    """Run the seed helper from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--expected-dir", required=True, type=Path)
    parser.add_argument("--fixture-ids", default=None)
    parser.add_argument("--categories", default=None)
    args = parser.parse_args()

    summary = asyncio.run(
        seed_expected_snapshots(
            manifest_path=args.manifest,
            expected_dir=args.expected_dir,
            fixture_ids=_split(args.fixture_ids),
            categories=_split(args.categories),
        )
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


async def seed_expected_snapshots(
    *,
    manifest_path: Path,
    expected_dir: Path,
    fixture_ids: Sequence[str] | None,
    categories: Sequence[str] | None,
) -> dict[str, object]:
    """Seed V2/V3 expected snapshots for matching fixtures using local OCR+LLM.

    Args:
        manifest_path: Prepared live OCR manifest JSON object.
        expected_dir: Directory containing existing V2/V3 templates.
        fixture_ids: Optional fixture_id filter (overrides categories when set).
        categories: Optional category_label filter.

    Returns:
        Redacted summary of seeded and skipped fixtures.

    Raises:
        ValueError: If manifest contains forbidden raw keys or no fixtures match.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _reject_raw(manifest)
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Manifest must contain a 'cases' list.")

    manifest_root = manifest_path.parent
    settings = Settings(_env_file=None)
    paddle = PaddleOCRAdapter(settings)
    llm = OllamaSupplementParser(settings)

    seeded: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        if not _matches(case, fixture_ids=fixture_ids, categories=categories):
            continue
        fixture_id = case["fixture_id"]
        image_relative = case.get("image_path")
        if not isinstance(image_relative, str):
            skipped.append({"fixture_id": fixture_id, "reason": "image_path_missing"})
            continue
        image_path = (manifest_root / image_relative).resolve()
        if not image_path.is_file():
            skipped.append({"fixture_id": fixture_id, "reason": "image_file_missing"})
            continue

        try:
            ocr_text = await _extract_text(paddle, image_path)
        except Exception as exc:
            skipped.append({"fixture_id": fixture_id, "reason": f"ocr_error:{type(exc).__name__}"})
            continue
        if not ocr_text:
            skipped.append({"fixture_id": fixture_id, "reason": "ocr_text_empty"})
            continue
        try:
            parse_result = await llm.parse_supplement_ocr_text(ocr_text)
        except Exception as exc:
            skipped.append({"fixture_id": fixture_id, "reason": f"llm_error:{type(exc).__name__}"})
            continue

        v2_target = expected_dir / f"{fixture_id}.snapshot_v2.json"
        v3_target = expected_dir / f"{fixture_id}.snapshot_v3.json"
        if not v2_target.exists() or not v3_target.exists():
            skipped.append({"fixture_id": fixture_id, "reason": "template_missing"})
            continue

        v2_updated = _seed_v2(template_path=v2_target, parse_result=parse_result)
        v3_updated = _seed_v3(template_path=v3_target, parse_result=parse_result)
        seeded.append(
            {
                "fixture_id": fixture_id,
                "v2_ingredient_count": len(v2_updated["ingredient_candidates"]),
                "v3_ingredient_count": len(v3_updated["ingredients"]),
            }
        )

    return {
        "seeded_count": len(seeded),
        "skipped_count": len(skipped),
        "seeded": seeded,
        "skipped": skipped,
        "raw_image_stored": False,
        "raw_ocr_text_stored": False,
        "raw_provider_payload_stored": False,
        "raw_model_response_stored": False,
    }


async def _extract_text(paddle: PaddleOCRAdapter, image_path: Path) -> str:
    """Run PaddleOCR on ``image_path`` and return the redacted normalized text.

    Args:
        paddle: PaddleOCR adapter instance.
        image_path: Resolved fixture image path.

    Returns:
        OCR text. The text stays in process memory and is never persisted by
        this helper.
    """
    image_bytes = image_path.read_bytes()
    mime_type = "image/jpeg"
    if image_path.suffix.lower() == ".png":
        mime_type = "image/png"
    elif image_path.suffix.lower() == ".webp":
        mime_type = "image/webp"
    image_input = OCRImageInput(
        image_bytes=image_bytes,
        mime_type=mime_type,
        width=0,
        height=0,
        label_region=None,
    )
    result = await paddle.extract_text(image_input)
    return (result.text or "").strip()


def _seed_v2(
    *,
    template_path: Path,
    parse_result: SupplementStructuredParseResultV2,
) -> dict[str, Any]:
    """Merge parser output into an existing V2 template file and write it back.

    Args:
        template_path: V2 template file path.
        parse_result: Validated structured parser output.

    Returns:
        Updated V2 dictionary that was written to disk.

    Raises:
        ValueError: If the merged document fails V2 schema validation.
    """
    template = cast(dict[str, Any], json.loads(template_path.read_text(encoding="utf-8")))
    template["product"] = {
        "product_name": parse_result.product.product_name or "TBD",
        "manufacturer": parse_result.product.manufacturer,
        "barcode_text": None,
        "barcode_format": None,
    }
    template["serving"] = {
        "serving_size_text": parse_result.serving.serving_size_text or "TBD",
        "serving_amount": parse_result.serving.serving_amount,
        "serving_unit": parse_result.serving.serving_unit,
        "daily_servings": parse_result.serving.daily_servings,
        "evidence_refs": [],
    }
    template["ingredient_candidates"] = [
        {
            "display_name": ingredient.display_name,
            "normalized_name": ingredient.normalized_name or ingredient.display_name.lower(),
            "nutrient_code_candidates": [],
            "amount": ingredient.amount,
            "unit": ingredient.unit,
            "daily_amount": ingredient.daily_amount,
            "confidence": ingredient.confidence,
            "source": AUTO_SEED_SOURCE,
            "evidence_refs": [],
        }
        for ingredient in parse_result.ingredients
    ]
    template["intake_method"] = {
        "text": parse_result.intake_method.text,
        "structured": {
            "frequency": parse_result.intake_method.structured.frequency,
            "time_of_day": list(parse_result.intake_method.structured.time_of_day),
            "with_food": parse_result.intake_method.structured.with_food,
        },
        "evidence_refs": [],
    }
    template["precautions"] = [
        {
            "text": precaution.text,
            "category": precaution.category,
            "evidence_refs": [],
        }
        for precaution in parse_result.precautions
    ]
    template["functional_claims"] = [
        {
            "text": claim.text,
            "claim_type": claim.claim_type,
            "evidence_refs": [],
        }
        for claim in parse_result.functional_claims
    ]
    template["low_confidence_fields"] = list(parse_result.low_confidence_fields)
    warnings = list(template.get("warnings", []))
    if AUTO_SEED_WARNING not in warnings:
        warnings.append(AUTO_SEED_WARNING)
    template["warnings"] = warnings

    SupplementParsedSnapshotV2.model_validate(template)
    template_path.write_text(
        json.dumps(template, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return template


def _seed_v3(
    *,
    template_path: Path,
    parse_result: SupplementStructuredParseResultV2,
) -> dict[str, Any]:
    """Merge parser output into an existing V3 template file and write it back."""
    template = cast(dict[str, Any], json.loads(template_path.read_text(encoding="utf-8")))
    template["product"] = {
        "product_name": parse_result.product.product_name or "TBD",
        "manufacturer": parse_result.product.manufacturer,
        "barcode_candidates": [],
        "evidence_refs": [],
    }
    template["serving"] = {
        "serving_size_text": parse_result.serving.serving_size_text or "TBD",
        "serving_amount": parse_result.serving.serving_amount,
        "serving_unit": parse_result.serving.serving_unit,
        "daily_servings": parse_result.serving.daily_servings,
        "evidence_refs": [],
    }
    template["ingredients"] = [
        {
            "display_name": ingredient.display_name,
            "normalized_name": ingredient.normalized_name or ingredient.display_name.lower(),
            "amount": ingredient.amount,
            "unit": ingredient.unit,
            "daily_amount": ingredient.daily_amount,
            "daily_unit": ingredient.unit,
            "nutrient_code_candidates": [],
            "confidence": ingredient.confidence,
            "source": AUTO_SEED_SOURCE,
            "evidence_refs": [],
        }
        for ingredient in parse_result.ingredients
    ]
    template["intake_method"] = {
        "text": parse_result.intake_method.text,
        "structured": {
            "frequency": parse_result.intake_method.structured.frequency,
            "time_of_day": list(parse_result.intake_method.structured.time_of_day),
            "with_food": parse_result.intake_method.structured.with_food,
        },
        "evidence_refs": [],
    }
    template["precautions"] = [
        {
            "text": precaution.text,
            "category": precaution.category,
            "severity": "unknown",
            "evidence_refs": [],
        }
        for precaution in parse_result.precautions
    ]
    template["functional_claims"] = [
        {
            "text": claim.text,
            "claim_type": claim.claim_type,
            "evidence_refs": [],
        }
        for claim in parse_result.functional_claims
    ]
    template["evidence_spans"] = []
    template["low_confidence_fields"] = list(parse_result.low_confidence_fields)
    warnings = list(template.get("warnings", []))
    if AUTO_SEED_WARNING not in warnings:
        warnings.append(AUTO_SEED_WARNING)
    template["warnings"] = warnings

    SupplementParsedSnapshotV3.model_validate(template)
    template_path.write_text(
        json.dumps(template, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return template


def _split(value: str | None) -> list[str] | None:
    """Split a comma-separated CLI filter into a list of non-empty tokens."""
    if value is None:
        return None
    tokens = [token.strip() for token in value.split(",")]
    return [token for token in tokens if token] or None


def _matches(
    case: dict[str, Any],
    *,
    fixture_ids: Sequence[str] | None,
    categories: Sequence[str] | None,
) -> bool:
    """Return True when the case satisfies the active filter."""
    if fixture_ids:
        return case.get("fixture_id") in set(fixture_ids)
    if categories:
        category = case.get("source_metadata", {}).get("category_label")
        return category in set(categories)
    return True


def _reject_raw(value: object) -> None:
    """Recursively reject raw artifact keys to keep redaction policy intact."""
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
