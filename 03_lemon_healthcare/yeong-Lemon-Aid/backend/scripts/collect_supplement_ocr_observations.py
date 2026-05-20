"""Collect redacted supplement OCR provider observations.

The collector is an explicit operator tool. It validates a consented fixture
manifest and writes provider observations without raw image bytes, raw OCR text,
provider payloads, credentials, or request headers. External providers only run
when their opt-in smoke-test environment variables are set.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal, cast

from PIL import Image

BACKEND_ROOT = Path(__file__).resolve().parents[1]
NUTRITION_BACKEND_ROOT = BACKEND_ROOT / "Nutrition-backend"
if str(NUTRITION_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(NUTRITION_BACKEND_ROOT))

from src.config import Settings  # noqa: E402
from src.llm.ollama import (  # noqa: E402
    OllamaClientError,
    OllamaConfigurationError,
    OllamaStructuredOutputError,
    OllamaSupplementParser,
)
from src.ocr.base import OCRAdapter, OCRImageInput, OCRResult  # noqa: E402
from src.ocr.factory import (  # noqa: E402
    OCRConfigurationError,
    build_supplement_image_analysis_adapters_for_provider,
)
from src.ocr.providers.clova import ClovaOCRAdapter  # noqa: E402
from src.ocr.providers.paddle import PaddleOCRAdapter  # noqa: E402
from src.parsing.layout_parser import parse_label_layout  # noqa: E402

ProviderName = Literal["google_vision_document", "paddleocr_local", "clova_ocr"]
ObservationStatus = Literal["completed", "error", "not_run"]

SUPPORTED_PROVIDERS: tuple[ProviderName, ...] = (
    "google_vision_document",
    "paddleocr_local",
    "clova_ocr",
)
PROVIDER_OPT_IN_ENV: dict[ProviderName, str] = {
    "google_vision_document": "RUN_GOOGLE_VISION_SMOKE",
    "paddleocr_local": "RUN_PADDLEOCR_PROBE",
    "clova_ocr": "RUN_CLOVA_OCR_LIVE_SMOKE",
}
OPERATOR_ENV_ALLOWLIST = frozenset(
    {
        "ALLOW_EXTERNAL_OCR",
        "ENABLE_CLOVA_OCR",
        "ENABLE_LOCAL_OCR",
        "GOOGLE_CLOUD_API_KEY",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_VISION_AUTH_MODE",
        "GOOGLE_VISION_FEATURE",
        "GOOGLE_VISION_LANGUAGE_HINTS",
        "GOOGLE_VISION_LOCATION",
        "GOOGLE_VISION_MAX_RETRIES",
        "GOOGLE_VISION_TIMEOUT_SECONDS",
        "OCR_PRIMARY_PROVIDER",
        "RUN_CLOVA_OCR_LIVE_SMOKE",
        "RUN_GOOGLE_VISION_SMOKE",
        "RUN_PADDLEOCR_PROBE",
    }
)
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
ALLOWED_LICENSE_STATUS = frozenset({"public", "team_approved", "consented", "synthetic"})
ALLOWED_CONSENT_STATUS = frozenset({"not_required", "team_approved", "consented"})
SHA256_HEX_LENGTH = 64
MIN_QUOTED_DOTENV_VALUE_CHARS = 2
AUTO_EXPECTED_SOURCE = "google_vision_auto_seed"
AUTO_EXPECTED_VERIFICATION_STATUS = "provisional"
AUTO_EXPECTED_WARNING = "auto_expected_requires_human_verification"
AUTO_EXPECTED_NO_INGREDIENTS_WARNING = "auto_expected_no_ingredient_candidates"
AUTO_EXPECTED_MAX_INGREDIENTS = 40
AUTO_EXPECTED_MIN_PRODUCT_NAME_CHARS = 3
AUTO_EXPECTED_MAX_PRODUCT_NAME_CHARS = 160
AUTO_EXPECTED_MIN_INGREDIENT_NAME_CHARS = 2
AUTO_EXPECTED_MAX_INGREDIENT_NAME_CHARS = 80
TRAILING_INGREDIENT_PUNCTUATION = " -_/.,:\uff1a|·•"
INGREDIENT_AMOUNT_PATTERN = re.compile(
    r"(?P<name>[A-Za-z가-힣][A-Za-z가-힣0-9\s()/+\-.,]{1,80}?)"
    r"\s*(?P<amount>\d+(?:[,.]\d+)?)\s*"
    r"(?P<unit>mg|g|mcg|μg|ug|㎍|iu|IU|%)\b"
)


@dataclass(frozen=True)
class FixtureCase:
    """One consented supplement OCR fixture.

    Attributes:
        fixture_id: Stable fixture identifier.
        image_path: Path to the committed non-sensitive image, relative to manifest.
        expected: Redacted expected field summary.
        manifest_row: Original allowlisted manifest row.
    """

    fixture_id: str
    image_path: Path
    expected: dict[str, object]
    manifest_row: dict[str, object]

    def with_expected(self, expected: dict[str, object]) -> FixtureCase:
        """Return a copy with a different expected field summary.

        Args:
            expected: Replacement expected field summary.

        Returns:
            Fixture copy carrying the new expected object.
        """
        return FixtureCase(
            fixture_id=self.fixture_id,
            image_path=self.image_path,
            expected=expected,
            manifest_row=self.manifest_row,
        )


@dataclass(frozen=True)
class ProviderObservationResult:
    """One provider observation with transient OCR result for in-memory seeding.

    Attributes:
        row: Redacted observation row.
        ocr_result: OCR result kept only in process memory.
    """

    row: dict[str, object]
    ocr_result: OCRResult | None = None


@dataclass(frozen=True)
class CollectionResult:
    """Redacted collection output and optional auto-expected manifest.

    Attributes:
        observations: Redacted observation rows.
        auto_expected_manifest: Optional manifest seeded from a live provider.
    """

    observations: list[dict[str, object]]
    auto_expected_manifest: dict[str, object] | None = None


def main() -> None:
    """Run the redacted observation collector from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help=(
            "Optional operator dotenv file. Only OCR allowlisted keys are loaded, "
            "and existing process environment values take precedence."
        ),
    )
    parser.add_argument(
        "--providers",
        default=",".join(SUPPORTED_PROVIDERS),
        help="Comma-separated provider names to observe.",
    )
    parser.add_argument(
        "--auto-expected-provider",
        choices=SUPPORTED_PROVIDERS,
        default=None,
        help=(
            "Provider used to seed provisional expected fields in memory. "
            "Use google_vision_document for live seed baselines."
        ),
    )
    parser.add_argument(
        "--llm-parse",
        action="store_true",
        help=(
            "Opt-in: send each non-empty OCR text to the local OllamaSupplementParser "
            "and record redacted llm_parsed_ingredients on each completed observation. "
            "Raw OCR text and raw model responses are never written; only structured "
            "ingredient display_name/normalized_name/amount/unit are stored."
        ),
    )
    parser.add_argument(
        "--auto-expected-manifest",
        type=Path,
        default=None,
        help="Optional output manifest with provisional provider-seeded expected fields.",
    )
    args = parser.parse_args()
    if args.auto_expected_manifest is not None and args.auto_expected_provider is None:
        parser.error("--auto-expected-manifest requires --auto-expected-provider")

    collection = asyncio.run(
        collect_observations_with_auto_expected(
            manifest_path=args.manifest,
            providers=_parse_providers(args.providers),
            auto_expected_provider=cast(ProviderName | None, args.auto_expected_provider),
            auto_expected_manifest_path=args.auto_expected_manifest,
            env_file=args.env_file or _default_operator_env_file(),
            llm_parse_enabled=bool(args.llm_parse),
        )
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "supplement-ocr-observations.jsonl"
    output_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in collection.observations),
        encoding="utf-8",
    )
    summary: dict[str, object] = {
        "observation_count": len(collection.observations),
        "output": str(output_path),
    }
    if collection.auto_expected_manifest is not None and args.auto_expected_manifest is not None:
        args.auto_expected_manifest.parent.mkdir(parents=True, exist_ok=True)
        args.auto_expected_manifest.write_text(
            json.dumps(collection.auto_expected_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        summary["auto_expected_manifest"] = str(args.auto_expected_manifest)
    print(json.dumps(summary, ensure_ascii=False))


async def collect_observations(
    *,
    manifest_path: Path,
    providers: tuple[ProviderName, ...],
) -> list[dict[str, object]]:
    """Collect redacted observations for all fixture/provider pairs.

    Args:
        manifest_path: JSON or JSONL fixture manifest path.
        providers: Provider ids to observe.

    Returns:
        Redacted observation dictionaries.
    """
    return (
        await collect_observations_with_auto_expected(
            manifest_path=manifest_path,
            providers=providers,
        )
    ).observations


async def collect_observations_with_auto_expected(
    *,
    manifest_path: Path,
    providers: tuple[ProviderName, ...],
    auto_expected_provider: ProviderName | None = None,
    auto_expected_manifest_path: Path | None = None,
    env_file: Path | None = None,
    llm_parse_enabled: bool = False,
    llm_parser: OllamaSupplementParser | None = None,
) -> CollectionResult:
    """Collect observations and optionally seed provisional expected fields.

    Args:
        manifest_path: JSON or JSONL fixture manifest path.
        providers: Provider ids to observe.
        auto_expected_provider: Provider id whose OCR text seeds expected fields.
        auto_expected_manifest_path: Destination path used to calculate image paths
            relative to the seeded manifest. The file is written by ``main``.
        env_file: Optional operator dotenv file for live OCR opt-in settings.

    Returns:
        Collection result containing redacted observations and optional manifest.
    """
    fixtures = _read_fixture_manifest(manifest_path)
    operator_env = _load_operator_env_file(env_file)
    with _temporary_operator_env(operator_env):
        settings = (
            Settings(_env_file=env_file) if env_file is not None else Settings(_env_file=None)
        )
        active_llm_parser: OllamaSupplementParser | None = llm_parser
        if llm_parse_enabled and active_llm_parser is None:
            active_llm_parser = OllamaSupplementParser(settings)
        observations: list[dict[str, object]] = []
        seeded_expected: dict[str, dict[str, object]] = {}
        for fixture in fixtures:
            active_fixture = fixture
            for provider in providers:
                observed = await _observe_provider(
                    active_fixture,
                    provider,
                    settings,
                    llm_parser=active_llm_parser if llm_parse_enabled else None,
                )
                observations.append(observed.row)
                if provider == auto_expected_provider and observed.ocr_result is not None:
                    expected = _auto_expected_from_result(
                        fixture=fixture,
                        provider=provider,
                        result=observed.ocr_result,
                    )
                    seeded_expected[fixture.fixture_id] = expected
                    active_fixture = fixture.with_expected(expected)
        auto_manifest = None
        if auto_expected_provider is not None:
            auto_manifest = _build_auto_expected_manifest(
                fixtures=fixtures,
                seeded_expected=seeded_expected,
                auto_expected_provider=auto_expected_provider,
                output_manifest_path=auto_expected_manifest_path or manifest_path,
            )
        return CollectionResult(observations=observations, auto_expected_manifest=auto_manifest)


async def _observe_provider(
    fixture: FixtureCase,
    provider: ProviderName,
    settings: Settings,
    *,
    llm_parser: OllamaSupplementParser | None = None,
) -> ProviderObservationResult:
    """Collect one provider observation or a safe not-run/error record.

    Args:
        fixture: Fixture case.
        provider: Provider id.
        settings: Runtime settings read from the operator environment.

    Returns:
        Redacted observation row and transient OCR result when completed.
    """
    opt_in_env = PROVIDER_OPT_IN_ENV[provider]
    if os.getenv(opt_in_env) != "1":
        return ProviderObservationResult(
            row=_observation(
                fixture_id=fixture.fixture_id,
                provider=provider,
                status="not_run",
                error_code=f"opt_in_env_missing:{opt_in_env}",
            )
        )
    try:
        adapter = _build_provider_adapter(provider, settings)
        image = _load_image_input(fixture.image_path)
        start = time.perf_counter()
        result = await adapter.extract_text(image)
        latency_ms = int((time.perf_counter() - start) * 1000)
    except Exception as exc:
        return ProviderObservationResult(
            row=_observation(
                fixture_id=fixture.fixture_id,
                provider=provider,
                status="error",
                error_code=_safe_error_code(exc),
            )
        )
    row = _completed_observation(
        fixture=fixture,
        provider=provider,
        result=result,
        latency_ms=latency_ms,
    )
    if llm_parser is not None and row.get("text_non_empty"):
        await _attach_llm_parse(row=row, ocr_result=result, llm_parser=llm_parser)
    return ProviderObservationResult(row=row, ocr_result=result)


def _build_provider_adapter(provider: ProviderName, settings: Settings) -> OCRAdapter:
    """Build the requested provider adapter.

    Args:
        provider: Provider id.
        settings: Runtime settings.

    Returns:
        OCR adapter.

    Raises:
        OCRConfigurationError: If settings do not permit the provider.
    """
    if provider == "google_vision_document":
        adapter = build_supplement_image_analysis_adapters_for_provider(
            settings,
            "google_vision",
        ).ocr
        if adapter is None:
            raise OCRConfigurationError("Google Vision adapter is not configured.")
        return adapter
    if provider == "paddleocr_local":
        if not settings.enable_local_ocr:
            raise OCRConfigurationError("ENABLE_LOCAL_OCR=true is required for PaddleOCR.")
        return PaddleOCRAdapter(settings)
    if provider == "clova_ocr":
        if not settings.allow_external_ocr:
            raise OCRConfigurationError("ALLOW_EXTERNAL_OCR=true is required for CLOVA OCR.")
        if not settings.enable_clova_ocr:
            raise OCRConfigurationError("ENABLE_CLOVA_OCR=true is required for CLOVA OCR.")
        return ClovaOCRAdapter(settings)
    raise OCRConfigurationError(f"Unsupported provider: {provider}")


async def _attach_llm_parse(
    *,
    row: dict[str, object],
    ocr_result: OCRResult,
    llm_parser: OllamaSupplementParser,
) -> None:
    """Run the local LLM parser on OCR text and attach a redacted ingredient list.

    Args:
        row: Completed observation row to mutate in place.
        ocr_result: PaddleOCR/CLOVA/Google Vision result with in-memory text.
        llm_parser: Local OllamaSupplementParser instance.

    Notes:
        Raw OCR text and raw Ollama responses are never persisted. Only the
        structured ingredient display_name/normalized_name/amount/unit and the
        ingredient_count are written to ``row``. Failure modes are recorded as a
        safe ``llm_parse_error_code`` token only.
    """
    text = (ocr_result.text or "").strip()
    if not text:
        row["llm_parse_status"] = "skipped_empty_text"
        return
    try:
        parse_result = await llm_parser.parse_supplement_ocr_text(text)
    except OllamaConfigurationError:
        row["llm_parse_status"] = "error"
        row["llm_parse_error_code"] = "ollama_configuration"
        return
    except OllamaStructuredOutputError:
        row["llm_parse_status"] = "error"
        row["llm_parse_error_code"] = "ollama_structured_output"
        return
    except OllamaClientError:
        row["llm_parse_status"] = "error"
        row["llm_parse_error_code"] = "ollama_client"
        return
    except Exception as exc:  # pragma: no cover - defensive
        row["llm_parse_status"] = "error"
        row["llm_parse_error_code"] = f"unexpected:{type(exc).__name__}"
        return

    ingredients: list[dict[str, object]] = []
    for ingredient in parse_result.ingredients:
        ingredients.append(
            {
                "display_name": ingredient.display_name,
                "normalized_name": ingredient.normalized_name or ingredient.display_name.lower(),
                "amount": ingredient.amount,
                "unit": ingredient.unit,
                "daily_amount": ingredient.daily_amount,
                "confidence": ingredient.confidence,
            }
        )
    row["llm_parse_status"] = "completed"
    row["llm_parsed_ingredients"] = ingredients
    row["llm_parsed_ingredient_count"] = len(ingredients)
    if parse_result.product.product_name:
        row["llm_parsed_product_name_present"] = True
    if parse_result.serving.serving_size_text:
        row["llm_parsed_serving_size_text_present"] = True


def _completed_observation(
    *,
    fixture: FixtureCase,
    provider: ProviderName,
    result: OCRResult,
    latency_ms: int,
) -> dict[str, object]:
    """Build a redacted completed observation.

    Args:
        fixture: Fixture case.
        provider: Provider id.
        result: OCR result.
        latency_ms: Provider call latency in milliseconds.

    Returns:
        Redacted observation row.
    """
    normalized_text = _normalize_text(result.text)
    parsed_ingredients = _matched_expected_ingredients(normalized_text, fixture.expected)
    layout = parse_label_layout(result) if result.pages else None
    evidence_grounded = _parsed_values_grounded(normalized_text, parsed_ingredients)
    warning_codes: list[str] = []
    layout_available = bool(layout and layout.sections)
    if not layout_available:
        warning_codes.append("layout_unavailable")
    return _observation(
        fixture_id=fixture.fixture_id,
        provider=provider,
        status="completed",
        latency_ms=latency_ms,
        text_non_empty=bool(normalized_text),
        text_hash=(
            hashlib.sha256(normalized_text.encode("utf-8")).hexdigest() if normalized_text else None
        ),
        char_count=len(normalized_text),
        layout_available=layout_available,
        parser_success=(
            bool(parsed_ingredients)
            if _expected_ingredients(fixture.expected)
            else bool(normalized_text)
        ),
        parsed_ingredients=parsed_ingredients,
        evidence_grounded=evidence_grounded,
        warning_codes=warning_codes,
    )


def _observation(
    *,
    fixture_id: str,
    provider: ProviderName,
    status: ObservationStatus,
    error_code: str | None = None,
    latency_ms: int | None = None,
    text_non_empty: bool = False,
    text_hash: str | None = None,
    char_count: int = 0,
    layout_available: bool = False,
    parser_success: bool = False,
    parsed_ingredients: list[dict[str, object]] | None = None,
    evidence_grounded: bool = False,
    warning_codes: list[str] | None = None,
) -> dict[str, object]:
    """Build one redacted observation record.

    Args:
        fixture_id: Fixture id.
        provider: Provider id.
        status: Observation status.
        error_code: Optional safe error code.
        latency_ms: Optional latency in milliseconds.
        text_non_empty: Whether OCR text was non-empty.
        text_hash: SHA-256 hash of normalized OCR text, never the text itself.
        char_count: Normalized OCR character count.
        layout_available: Whether provider layout metadata was usable.
        parser_success: Whether expected fields were recoverable from OCR text.
        parsed_ingredients: Redacted parsed ingredient summary.
        evidence_grounded: Whether parsed values are visible in OCR text.
        warning_codes: Safe warning codes.

    Returns:
        Observation row.
    """
    row: dict[str, object] = {
        "fixture_id": fixture_id,
        "provider": provider,
        "status": status,
        "text_non_empty": text_non_empty,
        "char_count": char_count,
        "layout_available": layout_available,
        "parser_success": parser_success,
        "parsed_ingredients": parsed_ingredients or [],
        "evidence_grounded": evidence_grounded,
        "warning_codes": warning_codes or [],
    }
    if text_hash is not None:
        row["text_hash"] = text_hash
    if latency_ms is not None:
        row["latency_ms"] = latency_ms
    if error_code is not None:
        row["error_code"] = error_code
    return row


def _default_operator_env_file() -> Path | None:
    """Return the default backend dotenv file when present.

    Returns:
        Backend-level dotenv path or None.
    """
    env_file = BACKEND_ROOT / ".env"
    return env_file if env_file.exists() else None


def _load_operator_env_file(env_file: Path | None) -> dict[str, str]:
    """Read allowlisted OCR operator env vars without leaking secret values.

    Existing process environment values take precedence over dotenv entries so
    CI or shell-level overrides remain authoritative.

    Args:
        env_file: Optional dotenv path.

    Returns:
        Allowlisted dotenv values to apply temporarily.
    """
    if env_file is None:
        return {}
    resolved = env_file.expanduser().resolve()
    if not resolved.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in resolved.read_text(encoding="utf-8").splitlines():
        parsed = _parse_dotenv_assignment(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        if not value or key not in OPERATOR_ENV_ALLOWLIST or key in os.environ:
            continue
        values[key] = value
    return values


@contextmanager
def _temporary_operator_env(values: dict[str, str]) -> Iterator[None]:
    """Temporarily expose operator dotenv values to provider opt-in checks.

    Args:
        values: Environment values returned by ``_load_operator_env_file``.

    Yields:
        None while the temporary environment overlay is active.
    """
    applied_keys: list[str] = []
    for key, value in values.items():
        if key in os.environ:
            continue
        os.environ[key] = value
        applied_keys.append(key)
    try:
        yield
    finally:
        for key in applied_keys:
            os.environ.pop(key, None)


def _parse_dotenv_assignment(raw_line: str) -> tuple[str, str] | None:
    """Parse one simple dotenv assignment.

    Args:
        raw_line: Raw dotenv line.

    Returns:
        Key and value, or None for comments/unsupported lines.
    """
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    return key, _strip_dotenv_value(value.strip())


def _strip_dotenv_value(value: str) -> str:
    """Strip quotes and inline comments from a dotenv value.

    Args:
        value: Raw dotenv value.

    Returns:
        Parsed value.
    """
    if (
        len(value) >= MIN_QUOTED_DOTENV_VALUE_CHARS
        and value[0] == value[-1]
        and value[0] in {'"', "'"}
    ):
        return value[1:-1]
    return value.split(" #", 1)[0].strip()


def _auto_expected_from_result(
    *,
    fixture: FixtureCase,
    provider: ProviderName,
    result: OCRResult,
) -> dict[str, object]:
    """Build a provisional expected summary from one live OCR result.

    The generated object contains only structured candidates and hashes/counts.
    It intentionally does not include raw OCR text or provider payloads.

    Args:
        fixture: Source fixture.
        provider: Provider used to seed the expected summary.
        result: OCR result kept only in memory.

    Returns:
        Provisional expected object for agreement analysis.
    """
    normalized_text = _normalize_text(result.text)
    ingredients = _extract_ingredient_candidates(result.text)
    warnings = [AUTO_EXPECTED_WARNING]
    if not ingredients:
        warnings.append(AUTO_EXPECTED_NO_INGREDIENTS_WARNING)
    expected: dict[str, object] = {
        "expected_source": AUTO_EXPECTED_SOURCE,
        "verification_status": AUTO_EXPECTED_VERIFICATION_STATUS,
        "seed_provider": provider,
        "seed_fixture_id": fixture.fixture_id,
        "seed_text_hash": (
            hashlib.sha256(normalized_text.encode("utf-8")).hexdigest() if normalized_text else None
        ),
        "seed_char_count": len(normalized_text),
        "product_name": _extract_product_name_candidate(result.text),
        "ingredients": ingredients,
        "warnings": warnings,
    }
    return expected


def _build_auto_expected_manifest(
    *,
    fixtures: list[FixtureCase],
    seeded_expected: dict[str, dict[str, object]],
    auto_expected_provider: ProviderName,
    output_manifest_path: Path,
) -> dict[str, object]:
    """Build a manifest with provisional provider-seeded expected fields.

    Args:
        fixtures: Original fixture cases.
        seeded_expected: Expected objects keyed by fixture id.
        auto_expected_provider: Provider selected as the seed source.
        output_manifest_path: Manifest path used for relative image paths.

    Returns:
        JSON-serializable manifest object.
    """
    output_parent = output_manifest_path.parent.resolve()
    cases: list[dict[str, object]] = []
    for fixture in fixtures:
        row = dict(fixture.manifest_row)
        row["image_path"] = os.path.relpath(fixture.image_path, output_parent)
        row["expected"] = seeded_expected.get(
            fixture.fixture_id,
            {
                "expected_source": f"{auto_expected_provider}_auto_seed_not_completed",
                "verification_status": AUTO_EXPECTED_VERIFICATION_STATUS,
                "seed_provider": auto_expected_provider,
                "ingredients": [],
                "warnings": ["auto_expected_provider_not_completed"],
            },
        )
        cases.append(row)
    return {
        "version": "supplement-ocr-live-google-seed-v1",
        "expected_policy": "google_vision_auto_seed_provisional",
        "seed_provider": auto_expected_provider,
        "full_text_artifact_stored": False,
        "provider_artifact_stored": False,
        "image_bytes_in_manifest": False,
        "cases": cases,
    }


def _extract_ingredient_candidates(ocr_text: str) -> list[dict[str, object]]:
    """Extract bounded ingredient candidates from OCR text.

    Args:
        ocr_text: Raw OCR text kept only in process memory.

    Returns:
        Structured ingredient candidates safe for provisional expected snapshots.
    """
    ingredients: list[dict[str, object]] = []
    seen: set[tuple[str, object, str]] = set()
    for line in _ocr_lines(ocr_text):
        for match in INGREDIENT_AMOUNT_PATTERN.finditer(line):
            name = _clean_ingredient_name(match.group("name"))
            if not name:
                continue
            amount = _parse_amount(match.group("amount"))
            unit = _normalize_unit(match.group("unit"))
            key = (_normalize_text(name), amount, unit)
            if key in seen:
                continue
            seen.add(key)
            ingredients.append(
                {
                    "name": name,
                    "amount": amount,
                    "unit": unit,
                    "expected_source": AUTO_EXPECTED_SOURCE,
                    "verification_status": AUTO_EXPECTED_VERIFICATION_STATUS,
                }
            )
            if len(ingredients) >= AUTO_EXPECTED_MAX_INGREDIENTS:
                return ingredients
    return ingredients


def _extract_product_name_candidate(ocr_text: str) -> str | None:
    """Extract a short product-name candidate from OCR text.

    Args:
        ocr_text: Raw OCR text kept only in process memory.

    Returns:
        Product name candidate or None.
    """
    for line in _ocr_lines(ocr_text):
        stripped = line.strip()
        if not (
            AUTO_EXPECTED_MIN_PRODUCT_NAME_CHARS
            <= len(stripped)
            <= AUTO_EXPECTED_MAX_PRODUCT_NAME_CHARS
        ):
            continue
        if INGREDIENT_AMOUNT_PATTERN.search(stripped):
            continue
        if _looks_like_non_product_heading(stripped):
            continue
        return stripped
    return None


def _ocr_lines(ocr_text: str) -> list[str]:
    """Return bounded non-empty OCR lines.

    Args:
        ocr_text: Raw OCR text kept only in process memory.

    Returns:
        Non-empty lines.
    """
    return [line.strip() for line in ocr_text.splitlines() if line.strip()][:300]


def _clean_ingredient_name(value: str) -> str:
    """Clean an ingredient name candidate.

    Args:
        value: Regex-captured ingredient prefix.

    Returns:
        Cleaned ingredient name or an empty string when unsuitable.
    """
    cleaned = re.sub(r"^[^A-Za-z가-힣]+", "", value)
    cleaned = re.sub(r"[:\uff1a|·•]+$", "", cleaned).strip(TRAILING_INGREDIENT_PUNCTUATION)
    cleaned = " ".join(cleaned.split())
    if not (
        AUTO_EXPECTED_MIN_INGREDIENT_NAME_CHARS
        <= len(cleaned)
        <= AUTO_EXPECTED_MAX_INGREDIENT_NAME_CHARS
    ):
        return ""
    if _looks_like_non_product_heading(cleaned):
        return ""
    if not re.search(r"[A-Za-z가-힣]", cleaned):
        return ""
    return cleaned


def _parse_amount(value: str) -> int | float:
    """Parse a numeric amount without inventing units or conversions.

    Args:
        value: OCR amount text.

    Returns:
        Integer or float amount.
    """
    numeric_text = value.replace(",", "")
    numeric_value = float(numeric_text)
    return int(numeric_value) if numeric_value.is_integer() else numeric_value


def _normalize_unit(value: str) -> str:
    """Normalize common OCR unit variants.

    Args:
        value: OCR unit text.

    Returns:
        Normalized unit string.
    """
    normalized = value.strip()
    if normalized in {"μg", "㎍"}:
        return "ug"
    if normalized.casefold() == "iu":
        return "IU"
    return normalized.casefold() if normalized != "%" else "%"


def _looks_like_non_product_heading(value: str) -> bool:
    """Return whether text is a generic label heading, not a product/ingredient.

    Args:
        value: Candidate text.

    Returns:
        True when the text looks like a generic section heading.
    """
    normalized = _normalize_text(value)
    heading_tokens = (
        "nutrition facts",
        "supplement facts",
        "영양 정보",
        "영양정보",
        "섭취 방법",
        "섭취방법",
        "주의 사항",
        "주의사항",
        "원재료명",
        "기능 정보",
        "기능정보",
    )
    return any(token in normalized for token in heading_tokens)


def _read_fixture_manifest(manifest_path: Path) -> list[FixtureCase]:
    """Read and validate fixture manifest rows.

    Args:
        manifest_path: JSON or JSONL manifest path.

    Returns:
        Fixture cases.

    Raises:
        ValueError: If the manifest contains raw or unsafe fields.
    """
    rows = _manifest_rows(manifest_path)
    fixtures: list[FixtureCase] = []
    for row in rows:
        _reject_raw_fields(row)
        fixture_id = row.get("fixture_id")
        image_path = row.get("image_path")
        if not isinstance(fixture_id, str) or not fixture_id.strip():
            raise ValueError("Each OCR fixture requires fixture_id.")
        if not isinstance(image_path, str) or not image_path.strip():
            raise ValueError(f"OCR fixture requires image_path: {fixture_id}")
        image_sha256 = row.get("image_sha256")
        if not isinstance(image_sha256, str) or len(image_sha256) != SHA256_HEX_LENGTH:
            raise ValueError(f"OCR fixture requires image_sha256: {fixture_id}")
        if row.get("license_status") not in ALLOWED_LICENSE_STATUS:
            raise ValueError(f"OCR fixture has unsupported license_status: {fixture_id}")
        if row.get("consent_status") not in ALLOWED_CONSENT_STATUS:
            raise ValueError(f"OCR fixture has unsupported consent_status: {fixture_id}")
        if row.get("contains_personal_data") is not False:
            raise ValueError(f"OCR fixture must set contains_personal_data=false: {fixture_id}")
        expected = row.get("expected", {})
        if not isinstance(expected, dict):
            raise ValueError(f"OCR fixture expected must be an object: {fixture_id}")
        resolved_image_path = (manifest_path.parent / image_path).resolve()
        if not resolved_image_path.exists():
            raise ValueError(f"OCR fixture image is missing: {fixture_id}")
        actual_sha = hashlib.sha256(resolved_image_path.read_bytes()).hexdigest()
        if actual_sha != image_sha256:
            raise ValueError(f"OCR fixture image_sha256 mismatch: {fixture_id}")
        fixtures.append(
            FixtureCase(
                fixture_id=fixture_id.strip(),
                image_path=resolved_image_path,
                expected=expected,
                manifest_row=dict(row),
            )
        )
    return fixtures


def _manifest_rows(manifest_path: Path) -> list[dict[str, object]]:
    """Return manifest objects from JSON or JSONL input.

    Args:
        manifest_path: Manifest path.

    Returns:
        Parsed rows.
    """
    text = manifest_path.read_text(encoding="utf-8")
    if manifest_path.suffix == ".jsonl":
        rows: list[dict[str, object]] = []
        for line_number, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parsed = json.loads(stripped)
            if not isinstance(parsed, dict):
                raise ValueError(f"Manifest line {line_number} must be an object.")
            rows.append(parsed)
        return rows
    parsed_json = json.loads(text)
    if isinstance(parsed_json, dict) and isinstance(parsed_json.get("cases"), list):
        return [cast(dict[str, object], row) for row in parsed_json["cases"]]
    if isinstance(parsed_json, list):
        return [cast(dict[str, object], row) for row in parsed_json]
    raise ValueError("Manifest must be JSONL, a JSON list, or a JSON object with cases.")


def _load_image_input(image_path: Path) -> OCRImageInput:
    """Load a fixture image for an explicitly opted-in provider call.

    Args:
        image_path: Local fixture image path.

    Returns:
        OCR image DTO.

    Raises:
        RuntimeError: If the image cannot be decoded.
    """
    image_bytes = image_path.read_bytes()
    with Image.open(BytesIO(image_bytes)) as image:
        width, height = image.size
        mime_type = Image.MIME.get(image.format or "", "image/png")
    return OCRImageInput(
        image_bytes=image_bytes,
        mime_type=mime_type,
        width=width,
        height=height,
    )


def _reject_raw_fields(value: object) -> None:
    """Reject raw OCR/image fields recursively.

    Args:
        value: Candidate manifest or observation value.

    Raises:
        ValueError: If a forbidden raw field is present.
    """
    if isinstance(value, dict):
        forbidden = RAW_FORBIDDEN_KEYS.intersection(str(key).lower() for key in value)
        if forbidden:
            raise ValueError(f"Payload contains forbidden raw field(s): {sorted(forbidden)}")
        for nested_value in value.values():
            _reject_raw_fields(nested_value)
    elif isinstance(value, list):
        for item in value:
            _reject_raw_fields(item)


def _expected_ingredients(expected: dict[str, object]) -> list[dict[str, object]]:
    """Return expected ingredients from a fixture expected object.

    Args:
        expected: Expected fixture summary.

    Returns:
        Ingredient dictionaries.
    """
    ingredients = expected.get("ingredients")
    if not isinstance(ingredients, list):
        return []
    return [item for item in ingredients if isinstance(item, dict)]


def _matched_expected_ingredients(
    normalized_text: str,
    expected: dict[str, object],
) -> list[dict[str, object]]:
    """Return expected ingredients whose values are visible in OCR text.

    Args:
        normalized_text: Normalized OCR text.
        expected: Expected fixture summary.

    Returns:
        Redacted parsed ingredient summaries.
    """
    parsed: list[dict[str, object]] = []
    for ingredient in _expected_ingredients(expected):
        name = ingredient.get("name")
        if not isinstance(name, str) or _normalize_text(name) not in normalized_text:
            continue
        observed: dict[str, object] = {"name": name}
        amount = ingredient.get("amount")
        unit = ingredient.get("unit")
        if amount is not None and _normalize_text(amount) in normalized_text:
            observed["amount"] = amount
        if isinstance(unit, str) and _normalize_text(unit) in normalized_text:
            observed["unit"] = unit
        parsed.append(observed)
    return parsed


def _parsed_values_grounded(normalized_text: str, ingredients: list[dict[str, object]]) -> bool:
    """Return whether all parsed ingredient values are present in OCR text.

    Args:
        normalized_text: Normalized OCR text.
        ingredients: Parsed ingredient summaries.

    Returns:
        True when every emitted value is visible in normalized OCR text.
    """
    for ingredient in ingredients:
        for value in ingredient.values():
            if _normalize_text(value) not in normalized_text:
                return False
    return True


def _normalize_text(value: object) -> str:
    """Normalize text for redacted fixture matching.

    Args:
        value: Candidate text-like value.

    Returns:
        Case-folded whitespace-normalized text.
    """
    raw = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value or "")
    return " ".join(raw.casefold().split())


def _safe_error_code(exc: Exception) -> str:
    """Map an exception to a stable non-sensitive error code.

    Args:
        exc: Provider exception.

    Returns:
        Safe error code.
    """
    if isinstance(exc, OCRConfigurationError):
        return "provider_configuration_error"
    return f"{exc.__class__.__name__.casefold()}".replace(" ", "_")


def _parse_providers(value: str) -> tuple[ProviderName, ...]:
    """Parse a comma-separated provider list.

    Args:
        value: CLI provider list.

    Returns:
        Provider tuple.

    Raises:
        ValueError: If a provider is unsupported.
    """
    parsed: list[ProviderName] = []
    for item in value.split(","):
        provider = item.strip()
        if not provider:
            continue
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")
        parsed.append(provider)
    return tuple(parsed or SUPPORTED_PROVIDERS)


if __name__ == "__main__":
    main()
