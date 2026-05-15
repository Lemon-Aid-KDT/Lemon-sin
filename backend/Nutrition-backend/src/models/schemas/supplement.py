"""Supplement intake API contract schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SupplementAnalysisStatus(StrEnum):
    """Supplement analysis contract states.

    Attributes:
        REQUIRES_CONFIRMATION: Preview must be reviewed by the user before storage.
        CONFIRMED: Preview was confirmed into a user supplement.
        EXPIRED: Preview can no longer be confirmed.
        FAILED: Preview analysis failed before confirmation.
    """

    REQUIRES_CONFIRMATION = "requires_confirmation"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    FAILED = "failed"


class SupplementIngredientCandidate(BaseModel):
    """Ingredient candidate extracted from a supplement label.

    Attributes:
        display_name: Ingredient name shown to the user for confirmation.
        nutrient_code: Internal nutrient code when mapped.
        amount: Ingredient amount per serving.
        unit: Ingredient unit.
        confidence: Extraction confidence from 0.0 to 1.0.
        source: Source that produced the candidate.
    """

    display_name: str = Field(min_length=1, max_length=120)
    nutrient_code: str | None = Field(default=None, max_length=80)
    amount: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=40)
    confidence: float = Field(ge=0, le=1)
    source: str = Field(min_length=1, max_length=80)


class MatchedSupplementCandidate(BaseModel):
    """Product candidate matched from a supplement reference source.

    Attributes:
        source_id: Reference source identifier.
        product_name: Matched product name.
        manufacturer: Product manufacturer when available.
        match_score: Matching score from 0.0 to 1.0.
    """

    source_id: str = Field(min_length=1, max_length=120)
    product_name: str = Field(min_length=1, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=160)
    match_score: float = Field(ge=0, le=1)


class SupplementParsedProduct(BaseModel):
    """Parsed supplement product fields from OCR and structured parsing.

    Attributes:
        product_name: Product name candidate.
        manufacturer: Manufacturer candidate.
        serving_size: Serving size text from the label.
        daily_servings: Suggested daily serving count from the label.
    """

    product_name: str | None = Field(default=None, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=160)
    serving_size: str | None = Field(default=None, max_length=120)
    daily_servings: float | None = Field(default=None, ge=0, le=20)


class SupplementAnalysisPreview(BaseModel):
    """Supplement OCR and parsing preview before user confirmation.

    Attributes:
        analysis_id: Temporary analysis identifier.
        status: Preview status.
        parsed_product: Product-level parsed fields.
        ingredient_candidates: Ingredient candidates requiring user review.
        matched_product_candidates: Product reference matches.
        low_confidence_fields: Field names that require extra user attention.
        warnings: Safe warnings for the preview screen.
        algorithm_version: Parsing contract version.
        source_manifest_version: Reference source manifest version.
        expires_at: Time when this preview should no longer be used.
    """

    analysis_id: UUID
    status: SupplementAnalysisStatus
    parsed_product: SupplementParsedProduct
    ingredient_candidates: list[SupplementIngredientCandidate]
    matched_product_candidates: list[MatchedSupplementCandidate] = Field(default_factory=list)
    low_confidence_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    algorithm_version: str
    source_manifest_version: str | None
    expires_at: datetime


class SupplementServing(BaseModel):
    """User-confirmed supplement serving values.

    Attributes:
        amount: Serving amount.
        unit: Serving unit.
        daily_servings: Daily serving count confirmed by the user.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    amount: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=40)
    daily_servings: float = Field(ge=0, le=20)


class SupplementIntakeSchedule(BaseModel):
    """User-confirmed supplement intake schedule.

    Attributes:
        frequency: Human-readable frequency.
        time_of_day: Optional time labels such as morning or evening.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    frequency: str = Field(min_length=1, max_length=80)
    time_of_day: list[str] = Field(default_factory=list, max_length=8)


class UserSupplementIngredientInput(BaseModel):
    """User-confirmed supplement ingredient input.

    Attributes:
        display_name: User-confirmed ingredient name.
        nutrient_code: Internal nutrient code when deterministically mapped.
        amount: User-confirmed ingredient amount per serving.
        unit: User-confirmed ingredient unit.
        confidence: Retained extraction confidence, or 1.0 for manual confirmation.
        source: Source marker for the confirmed ingredient row.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str = Field(min_length=1, max_length=120)
    nutrient_code: str | None = Field(default=None, max_length=80)
    amount: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=40)
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: Literal["user_confirmed", "ocr_llm_preview"] = "user_confirmed"


class UserSupplementCreate(BaseModel):
    """Request to store a user-confirmed supplement record.

    Attributes:
        analysis_id: Temporary preview identifier used for traceability.
        display_name: User-confirmed supplement name.
        manufacturer: User-confirmed manufacturer.
        ingredients: User-confirmed ingredient list.
        serving: User-confirmed serving values.
        intake_schedule: User-confirmed intake schedule.
        user_confirmed: Must be true because preview values cannot be stored as final data.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    analysis_id: UUID | None = None
    display_name: str = Field(min_length=1, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=160)
    ingredients: list[UserSupplementIngredientInput] = Field(min_length=1, max_length=80)
    serving: SupplementServing
    intake_schedule: SupplementIntakeSchedule | None = None
    user_confirmed: Literal[True] = True


class UserSupplementResponse(BaseModel):
    """Persisted current-user supplement response.

    Attributes:
        id: Persisted supplement identifier.
        display_name: User-confirmed supplement name.
        manufacturer: User-confirmed manufacturer.
        ingredients: Stored ingredient list.
        serving: Stored serving values.
        intake_schedule: Stored intake schedule.
        user_confirmed_at: Time when the user confirmed the values.
        created_at: Server-side record creation time.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    manufacturer: str | None
    ingredients: list[SupplementIngredientCandidate]
    serving: SupplementServing
    intake_schedule: SupplementIntakeSchedule | None
    user_confirmed_at: datetime
    created_at: datetime


class UserSupplementListResponse(BaseModel):
    """Paginated current-user supplement list response.

    Attributes:
        results: Supplement records visible to the current owner.
        limit: Maximum requested row count.
        offset: Requested row offset.
    """

    results: list[UserSupplementResponse]
    limit: int
    offset: int
