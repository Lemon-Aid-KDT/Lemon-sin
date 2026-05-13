"""Supplement OCR structured parsing service."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.llm.ollama import SUPPLEMENT_PARSER_SOURCE, OllamaSupplementParser
from src.models.db.supplement import SupplementAnalysisRun
from src.models.schemas.supplement import SupplementAnalysisStatus
from src.models.schemas.supplement_parser import SupplementStructuredParseResult
from src.security.auth import AuthenticatedUser
from src.security.subjects import build_owner_subject

SUPPLEMENT_PARSER_CONFIRMATION_WARNING = (
    "Structured OCR parsing is a preview. Review and confirm every field before saving."
)
SUPPLEMENT_IMAGE_ASSIST_WARNING = (
    "Image-assisted text extraction is a fallback preview. Review every field before saving."
)
SUPPLEMENT_PARSER_PROVIDER = "ollama"
OLLAMA_VISION_ASSIST_PROVIDER = "ollama_vision_assist"
OCR_PROVIDER_MAX_LENGTH = 64
OCR_LOW_CONFIDENCE_THRESHOLD = Decimal("0.80")


class SupplementOCRTextParser(Protocol):
    """Protocol for parser adapters that convert OCR text into structured facts."""

    async def parse_supplement_ocr_text(
        self,
        ocr_text: str,
    ) -> SupplementStructuredParseResult:
        """Parse OCR text into a validated supplement structure.

        Args:
            ocr_text: Normalized OCR text.

        Returns:
            Structured supplement parse result.
        """


@dataclass(frozen=True)
class SupplementParserStoreResult:
    """Stored supplement parser result.

    Attributes:
        record: Updated supplement analysis row.
        parse_result: Validated structured parse output.
    """

    record: SupplementAnalysisRun
    parse_result: SupplementStructuredParseResult


class SupplementParserInputError(ValueError):
    """Raised when OCR text or OCR metadata fails parser input validation."""


class SupplementAnalysisNotFoundError(ValueError):
    """Raised when the current user cannot access the requested analysis row."""


class SupplementAnalysisExpiredError(ValueError):
    """Raised when the analysis preview has expired before parsing."""


class SupplementAnalysisStateError(ValueError):
    """Raised when the analysis preview is not in a parseable lifecycle state."""


class SupplementParserConflictError(ValueError):
    """Raised when a preview already has a different OCR text hash."""


async def parse_supplement_analysis_ocr_text(
    session: AsyncSession,
    user: AuthenticatedUser,
    analysis_id: UUID,
    ocr_text: str,
    ocr_provider: str,
    ocr_confidence: float | None,
    settings: Settings,
    parser: SupplementOCRTextParser | None = None,
) -> SupplementParserStoreResult:
    """Parse OCR text and store the structured preview on an owned analysis row.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        analysis_id: Supplement analysis preview identifier.
        ocr_text: Raw OCR text. It is normalized, hashed, sent only to local Ollama,
            and never stored as raw text.
        ocr_provider: OCR provider label.
        ocr_confidence: Optional OCR confidence from 0.0 to 1.0.
        settings: Runtime settings.
        parser: Optional parser adapter, primarily for tests.

    Returns:
        Updated analysis row and validated parse result.

    Raises:
        SupplementParserInputError: If OCR text, provider, or confidence is invalid.
        SupplementAnalysisNotFoundError: If the row is absent or belongs to another owner.
        SupplementAnalysisExpiredError: If the preview has expired.
        SupplementAnalysisStateError: If the row is already confirmed, failed, or expired.
        SupplementParserConflictError: If a different OCR text was already attached.
    """
    normalized_text = normalize_ocr_text(ocr_text, settings.supplement_ocr_text_max_chars)
    normalized_provider = _normalize_ocr_provider(ocr_provider)
    normalized_confidence = _normalize_confidence(ocr_confidence)
    text_hash = hash_ocr_text(normalized_text, settings.privacy_hash_secret)
    owner_subject = build_owner_subject(user)

    record = await session.scalar(
        select(SupplementAnalysisRun).where(
            SupplementAnalysisRun.id == analysis_id,
            SupplementAnalysisRun.owner_subject == owner_subject,
        )
    )
    if record is None:
        raise SupplementAnalysisNotFoundError("Supplement analysis preview was not found.")
    _validate_parseable_record(record, text_hash)

    active_parser = parser or OllamaSupplementParser(settings)
    parse_result = await active_parser.parse_supplement_ocr_text(normalized_text)
    _validate_parser_result(parse_result, settings.supplement_parser_max_ingredients)

    record.ocr_provider = normalized_provider
    record.ocr_confidence = normalized_confidence
    record.ocr_text_hash = text_hash
    record.parsed_snapshot = _build_parsed_snapshot(
        parse_result=parse_result,
        previous_snapshot=record.parsed_snapshot,
        ocr_confidence=normalized_confidence,
        ocr_provider=normalized_provider,
        settings=settings,
    )
    record.warnings = _build_warning_list(parse_result.warnings, normalized_provider)
    record.algorithm_version = settings.supplement_parser_algorithm_version
    record.status = SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value

    await session.commit()
    await session.refresh(record)
    return SupplementParserStoreResult(record=record, parse_result=parse_result)


def normalize_ocr_text(ocr_text: str, max_chars: int) -> str:
    """Normalize OCR text before hashing and structured parsing.

    Args:
        ocr_text: Raw OCR text.
        max_chars: Maximum accepted character count.

    Returns:
        Normalized OCR text.

    Raises:
        SupplementParserInputError: If the OCR text is blank or too long.
    """
    normalized = "\n".join(
        line.rstrip() for line in ocr_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ).strip()
    if not normalized:
        raise SupplementParserInputError("OCR text is empty.")
    if len(normalized) > max_chars:
        raise SupplementParserInputError("OCR text exceeds the configured parser limit.")
    return normalized


def hash_ocr_text(ocr_text: str, privacy_hash_secret: SecretStr) -> str:
    """Build a privacy-preserving HMAC-SHA256 fingerprint for OCR text.

    Args:
        ocr_text: Normalized OCR text.
        privacy_hash_secret: Application HMAC secret.

    Returns:
        Hex-encoded HMAC-SHA256 OCR text fingerprint.
    """
    secret = privacy_hash_secret.get_secret_value().encode("utf-8")
    return hmac.new(secret, ocr_text.encode("utf-8"), hashlib.sha256).hexdigest()


def _validate_parseable_record(record: SupplementAnalysisRun, ocr_text_hash: str) -> None:
    """Validate a preview row before parsing updates are applied.

    Args:
        record: Existing supplement analysis row.
        ocr_text_hash: HMAC fingerprint of the incoming OCR text.

    Raises:
        SupplementAnalysisExpiredError: If the preview TTL has elapsed.
        SupplementAnalysisStateError: If the row cannot be parsed in its current state.
        SupplementParserConflictError: If a different OCR text hash is already present.
    """
    if record.expires_at <= datetime.now(UTC):
        raise SupplementAnalysisExpiredError("Supplement analysis preview has expired.")
    if record.status != SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value:
        raise SupplementAnalysisStateError("Supplement analysis preview is not parseable.")
    if record.ocr_text_hash is not None and record.ocr_text_hash != ocr_text_hash:
        raise SupplementParserConflictError("Supplement analysis preview already has OCR text.")


def _validate_parser_result(
    parse_result: SupplementStructuredParseResult,
    max_ingredients: int,
) -> None:
    """Validate runtime parser bounds not expressed by static JSON schema settings.

    Args:
        parse_result: Validated structured parser result.
        max_ingredients: Runtime maximum ingredient candidates.

    Raises:
        SupplementParserInputError: If the parser result exceeds runtime bounds.
    """
    if len(parse_result.ingredient_candidates) > max_ingredients:
        raise SupplementParserInputError("Parser returned too many ingredient candidates.")


def _normalize_ocr_provider(ocr_provider: str) -> str:
    """Normalize and validate OCR provider metadata.

    Args:
        ocr_provider: Raw OCR provider label.

    Returns:
        Trimmed provider label.

    Raises:
        SupplementParserInputError: If the provider label is invalid.
    """
    normalized = ocr_provider.strip()
    if not normalized:
        raise SupplementParserInputError("OCR provider is required.")
    if len(normalized) > OCR_PROVIDER_MAX_LENGTH:
        raise SupplementParserInputError("OCR provider exceeds the storage limit.")
    return normalized


def _normalize_confidence(ocr_confidence: float | None) -> Decimal | None:
    """Validate OCR confidence and convert it for database storage.

    Args:
        ocr_confidence: Optional OCR confidence value.

    Returns:
        Decimal confidence or None.

    Raises:
        SupplementParserInputError: If confidence is outside 0.0 to 1.0.
    """
    if ocr_confidence is None:
        return None
    if ocr_confidence < 0 or ocr_confidence > 1:
        raise SupplementParserInputError("OCR confidence must be between 0 and 1.")
    return Decimal(str(ocr_confidence))


def _build_parsed_snapshot(
    *,
    parse_result: SupplementStructuredParseResult,
    previous_snapshot: dict[str, Any],
    ocr_confidence: Decimal | None,
    ocr_provider: str,
    settings: Settings,
) -> dict[str, Any]:
    """Build the sanitized JSON snapshot persisted for user confirmation.

    Args:
        parse_result: Validated structured parser result.
        previous_snapshot: Existing preview snapshot, used only to preserve intake metadata.
        ocr_confidence: Provider-level OCR confidence.
        ocr_provider: OCR-like provider that produced the parser input.
        settings: Runtime settings used for model and algorithm metadata.

    Returns:
        Sanitized parsed snapshot with no raw OCR text or model response.
    """
    low_confidence_fields = _build_low_confidence_fields(
        parse_result.low_confidence_fields,
        ocr_confidence,
    )
    snapshot: dict[str, Any] = {
        "parsed_product": parse_result.parsed_product.model_dump(exclude_none=True),
        "ingredient_candidates": [
            candidate.model_dump(exclude_none=True)
            for candidate in parse_result.ingredient_candidates
        ],
        "low_confidence_fields": low_confidence_fields,
        "parser_metadata": {
            "provider": SUPPLEMENT_PARSER_PROVIDER,
            "source": SUPPLEMENT_PARSER_SOURCE,
            "input_provider": ocr_provider,
            "model": settings.ollama_model,
            "algorithm_version": settings.supplement_parser_algorithm_version,
            "raw_ocr_text_stored": False,
            "raw_model_response_stored": False,
        },
    }
    intake = previous_snapshot.get("intake")
    if isinstance(intake, dict):
        snapshot["intake"] = intake
    return snapshot


def _build_low_confidence_fields(
    parser_fields: list[str],
    ocr_confidence: Decimal | None,
) -> list[str]:
    """Merge parser field warnings with OCR-level confidence review signals.

    Args:
        parser_fields: Field paths reported by the structured parser.
        ocr_confidence: Provider-level OCR confidence.

    Returns:
        Deduplicated field paths that require user review.
    """
    fields = list(parser_fields)
    if ocr_confidence is not None and ocr_confidence < OCR_LOW_CONFIDENCE_THRESHOLD:
        fields.append("ocr_text")

    normalized: list[str] = []
    seen: set[str] = set()
    for field in fields:
        stripped = field.strip()
        if not stripped or stripped in seen:
            continue
        normalized.append(stripped)
        seen.add(stripped)
    return normalized


def _build_warning_list(parser_warnings: list[str], ocr_provider: str) -> list[str]:
    """Merge parser warnings with the required user-confirmation warning.

    Args:
        parser_warnings: Safe parser-produced warning strings.
        ocr_provider: OCR-like provider that produced parser input.

    Returns:
        Deduplicated warning list.
    """
    warnings = [SUPPLEMENT_PARSER_CONFIRMATION_WARNING, *parser_warnings]
    if ocr_provider == OLLAMA_VISION_ASSIST_PROVIDER:
        warnings.append(SUPPLEMENT_IMAGE_ASSIST_WARNING)
    normalized: list[str] = []
    seen: set[str] = set()
    for warning in warnings:
        stripped = warning.strip()
        if not stripped or stripped in seen:
            continue
        normalized.append(stripped)
        seen.add(stripped)
    return normalized
