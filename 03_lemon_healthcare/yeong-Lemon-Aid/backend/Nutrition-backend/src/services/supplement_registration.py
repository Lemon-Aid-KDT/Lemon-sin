"""User supplement registration, lookup, and deletion services."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.models.db.supplement import (
    SupplementAnalysisRun,
    UserSupplement,
    UserSupplementIngredient,
)
from src.models.schemas.supplement import (
    SupplementAnalysisStatus,
    SupplementIngredientCandidate,
    SupplementIntakeSchedule,
    SupplementServing,
    UserSupplementCreate,
    UserSupplementListResponse,
    UserSupplementResponse,
)
from src.security.auth import AuthenticatedUser
from src.security.subjects import build_owner_subject
from src.services.parser_domain_correction import build_parser_correction_events
from src.services.supplement_matching import match_supplement_product

REFERENCE_DATA_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "nutrition_reference" / "nutrient"
)
NUTRIENT_CODES_PATH = REFERENCE_DATA_PATH / "nutrient_codes.json"


@dataclass(frozen=True)
class UserSupplementStoreResult:
    """Stored user supplement result.

    Attributes:
        supplement: Persisted user supplement row.
        ingredients: Persisted ingredient rows.
    """

    supplement: UserSupplement
    ingredients: list[UserSupplementIngredient]


class SupplementRegistrationError(ValueError):
    """Base error for user supplement registration failures."""


class SupplementRegistrationValidationError(SupplementRegistrationError):
    """Raised when a confirmed supplement payload violates server validation rules."""


class SupplementPreviewNotFoundError(SupplementRegistrationError):
    """Raised when a preview row is absent or inaccessible to the current user."""


class SupplementPreviewStateError(SupplementRegistrationError):
    """Raised when a preview row cannot be confirmed in its current state."""


class SupplementPreviewExpiredError(SupplementRegistrationError):
    """Raised when a preview row expired before user confirmation."""


async def create_user_supplement_from_confirmation(
    session: AsyncSession,
    user: AuthenticatedUser,
    request: UserSupplementCreate,
    settings: Settings | None = None,
) -> UserSupplementStoreResult:
    """Persist a user-confirmed supplement and optional preview confirmation.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        request: User-confirmed supplement creation request.
        settings: Runtime settings controlling optional learning metadata capture.

    Returns:
        Persisted supplement and ingredient rows.

    Raises:
        SupplementRegistrationValidationError: If nutrient codes are not in the allowlist.
        SupplementPreviewNotFoundError: If `analysis_id` is absent for this owner.
        SupplementPreviewExpiredError: If the linked preview has expired.
        SupplementPreviewStateError: If the linked preview was already confirmed or failed.
    """
    runtime_settings = settings or get_settings()
    _validate_nutrient_codes(request)
    owner_subject = build_owner_subject(user)
    now = datetime.now(UTC)

    preview = await _get_owned_preview_for_confirmation(
        session,
        owner_subject,
        request.analysis_id,
        now,
    )
    match = await match_supplement_product(session, request)
    supplement = UserSupplement(
        owner_subject=owner_subject,
        source_analysis_run_id=preview.id if preview is not None else None,
        matched_product_id=match.matched_product_id,
        display_name=request.display_name,
        manufacturer=request.manufacturer,
        serving_snapshot=request.serving.model_dump(mode="json", exclude_none=True),
        intake_schedule=(
            request.intake_schedule.model_dump(mode="json", exclude_none=True)
            if request.intake_schedule is not None
            else {}
        ),
        user_confirmed_at=now,
    )
    session.add(supplement)
    await session.flush()

    ingredients = [
        UserSupplementIngredient(
            user_supplement_id=supplement.id,
            display_name=ingredient.display_name,
            nutrient_code=ingredient.nutrient_code,
            amount=_decimal_or_none(ingredient.amount),
            unit=ingredient.unit,
            confidence=Decimal(str(ingredient.confidence)),
            source=ingredient.source,
            sort_order=index,
        )
        for index, ingredient in enumerate(request.ingredients)
    ]
    for ingredient in ingredients:
        session.add(ingredient)

    if preview is not None:
        preview.status = SupplementAnalysisStatus.CONFIRMED.value
        preview.confirmed_at = now
        preview.match_snapshot = {
            "matched_product_candidates": [
                candidate.model_dump(mode="json") for candidate in match.candidates
            ]
        }
        if match.matched_source_manifest_version is not None:
            preview.source_manifest_version = match.matched_source_manifest_version
        if runtime_settings.enable_parser_domain_correction:
            correction_events = build_parser_correction_events(
                preview=preview,
                request=request,
                consent_scope=("parser_domain_correction",),
            )
            if correction_events:
                preview.match_snapshot = {
                    **dict(preview.match_snapshot or {}),
                    "parser_domain_correction_events": [
                        event.model_dump(mode="json") for event in correction_events
                    ],
                }

    await session.commit()
    await session.refresh(supplement)
    return UserSupplementStoreResult(supplement=supplement, ingredients=ingredients)


async def list_user_supplement_records(
    session: AsyncSession,
    user: AuthenticatedUser,
    limit: int,
    offset: int,
) -> UserSupplementListResponse:
    """List active user supplement records visible to the current owner.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        limit: Maximum row count.
        offset: Row offset.

    Returns:
        Paginated response model.
    """
    records = await _list_owned_supplements(session, user, limit, offset)
    ingredients = await _load_ingredients_for_supplements(
        session, [record.id for record in records]
    )
    return UserSupplementListResponse(
        results=[
            user_supplement_to_response(record, ingredients.get(record.id, []))
            for record in records
        ],
        limit=limit,
        offset=offset,
    )


async def get_user_supplement_record(
    session: AsyncSession,
    user: AuthenticatedUser,
    supplement_id: UUID,
) -> UserSupplementStoreResult | None:
    """Return one active user supplement if it belongs to the current owner.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        supplement_id: Persisted user supplement identifier.

    Returns:
        Supplement and ingredients, or None when absent or inaccessible.
    """
    record = await session.scalar(
        select(UserSupplement).where(
            UserSupplement.id == supplement_id,
            UserSupplement.owner_subject == build_owner_subject(user),
            UserSupplement.deleted_at.is_(None),
        )
    )
    if record is None:
        return None
    ingredients = await _load_ingredients_for_supplements(session, [record.id])
    return UserSupplementStoreResult(
        supplement=record,
        ingredients=ingredients.get(record.id, []),
    )


async def soft_delete_user_supplement(
    session: AsyncSession,
    user: AuthenticatedUser,
    supplement_id: UUID,
) -> bool:
    """Soft-delete one active user supplement owned by the current user.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        supplement_id: Persisted user supplement identifier.

    Returns:
        True when a row was marked deleted, False when not found.
    """
    record = await session.scalar(
        select(UserSupplement).where(
            UserSupplement.id == supplement_id,
            UserSupplement.owner_subject == build_owner_subject(user),
            UserSupplement.deleted_at.is_(None),
        )
    )
    if record is None:
        return False
    record.deleted_at = datetime.now(UTC)
    await session.commit()
    return True


def user_supplement_to_response(
    supplement: UserSupplement,
    ingredients: Iterable[UserSupplementIngredient],
) -> UserSupplementResponse:
    """Convert persisted supplement rows into the public API response.

    Args:
        supplement: Persisted user supplement row.
        ingredients: Persisted ingredient rows.

    Returns:
        Public user supplement response without owner identifiers.
    """
    sorted_ingredients = sorted(ingredients, key=lambda item: item.sort_order)
    return UserSupplementResponse(
        id=supplement.id,
        display_name=supplement.display_name,
        manufacturer=supplement.manufacturer,
        ingredients=[
            SupplementIngredientCandidate(
                display_name=ingredient.display_name,
                nutrient_code=ingredient.nutrient_code,
                amount=float(ingredient.amount) if ingredient.amount is not None else None,
                unit=ingredient.unit,
                confidence=float(ingredient.confidence),
                source=ingredient.source,
            )
            for ingredient in sorted_ingredients
        ],
        serving=SupplementServing.model_validate(supplement.serving_snapshot),
        intake_schedule=(
            SupplementIntakeSchedule.model_validate(supplement.intake_schedule)
            if supplement.intake_schedule
            else None
        ),
        user_confirmed_at=supplement.user_confirmed_at,
        created_at=supplement.created_at,
    )


async def _get_owned_preview_for_confirmation(
    session: AsyncSession,
    owner_subject: str,
    analysis_id: UUID | None,
    now: datetime,
) -> SupplementAnalysisRun | None:
    """Load and validate the optional source preview for confirmation.

    Args:
        session: Request-scoped async database session.
        owner_subject: Issuer-qualified owner subject.
        analysis_id: Optional preview identifier.
        now: Current server time.

    Returns:
        Preview row or None when no analysis id is provided.

    Raises:
        SupplementPreviewNotFoundError: If the preview is absent for this owner.
        SupplementPreviewExpiredError: If the preview has expired.
        SupplementPreviewStateError: If the preview cannot be confirmed.
    """
    if analysis_id is None:
        return None
    preview = await session.scalar(
        select(SupplementAnalysisRun).where(
            SupplementAnalysisRun.id == analysis_id,
            SupplementAnalysisRun.owner_subject == owner_subject,
        )
    )
    if preview is None:
        raise SupplementPreviewNotFoundError("Supplement analysis preview was not found.")
    if preview.expires_at <= now:
        raise SupplementPreviewExpiredError("Supplement analysis preview has expired.")
    if preview.status != SupplementAnalysisStatus.REQUIRES_CONFIRMATION.value:
        raise SupplementPreviewStateError("Supplement analysis preview is not confirmable.")
    if preview.confirmed_at is not None:
        raise SupplementPreviewStateError("Supplement analysis preview was already confirmed.")
    return preview


async def _list_owned_supplements(
    session: AsyncSession,
    user: AuthenticatedUser,
    limit: int,
    offset: int,
) -> list[UserSupplement]:
    """Load active supplement rows for a current user.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        limit: Maximum row count.
        offset: Row offset.

    Returns:
        Active supplement rows.
    """
    result = await session.scalars(
        select(UserSupplement)
        .where(
            UserSupplement.owner_subject == build_owner_subject(user),
            UserSupplement.deleted_at.is_(None),
        )
        .order_by(desc(UserSupplement.created_at))
        .limit(limit)
        .offset(offset)
    )
    return list(result.all())


async def _load_ingredients_for_supplements(
    session: AsyncSession,
    supplement_ids: list[UUID],
) -> dict[UUID, list[UserSupplementIngredient]]:
    """Load ingredient rows grouped by user supplement id.

    Args:
        session: Request-scoped async database session.
        supplement_ids: User supplement identifiers.

    Returns:
        Mapping from supplement id to ingredient rows.
    """
    if not supplement_ids:
        return {}
    result = await session.scalars(
        select(UserSupplementIngredient).where(
            UserSupplementIngredient.user_supplement_id.in_(supplement_ids)
        )
    )
    grouped: dict[UUID, list[UserSupplementIngredient]] = {}
    for ingredient in result.all():
        grouped.setdefault(ingredient.user_supplement_id, []).append(ingredient)
    return grouped


def _validate_nutrient_codes(request: UserSupplementCreate) -> None:
    """Validate confirmed nutrient codes against the local allowlist.

    Args:
        request: User-confirmed supplement creation request.

    Raises:
        SupplementRegistrationValidationError: If an unknown nutrient code is present.
    """
    allowed_codes = _load_nutrient_codes()
    unknown_codes = sorted(
        {
            ingredient.nutrient_code
            for ingredient in request.ingredients
            if ingredient.nutrient_code and ingredient.nutrient_code not in allowed_codes
        }
    )
    if unknown_codes:
        raise SupplementRegistrationValidationError(
            f"Unknown nutrient_code values: {', '.join(unknown_codes)}"
        )


@lru_cache(maxsize=1)
def _load_nutrient_codes() -> frozenset[str]:
    """Load nutrient code allowlist from local reference data.

    Returns:
        Frozen set of allowed nutrient code strings.

    Raises:
        SupplementRegistrationValidationError: If reference data is unavailable or invalid.
    """
    try:
        raw = json.loads(NUTRIENT_CODES_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SupplementRegistrationValidationError(
            "Nutrient code reference data is unavailable."
        ) from exc
    if not isinstance(raw, dict):
        raise SupplementRegistrationValidationError("Nutrient code reference data is invalid.")
    return frozenset(str(code) for code in raw)


def _decimal_or_none(value: float | None) -> Decimal | None:
    """Convert an optional float value to Decimal for database storage.

    Args:
        value: Optional numeric amount.

    Returns:
        Decimal amount or None.
    """
    if value is None:
        return None
    return Decimal(str(value))
