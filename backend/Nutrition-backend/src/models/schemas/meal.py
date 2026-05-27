"""Meal image analysis API schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MealType(StrEnum):
    """Supported user meal buckets.

    Attributes:
        BREAKFAST: Morning meal.
        LUNCH: Midday meal.
        DINNER: Evening meal.
        SNACK: Snack or small meal.
        UNKNOWN: User has not classified the meal yet.
    """

    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    UNKNOWN = "unknown"


class MealAnalysisStatus(StrEnum):
    """Food image analysis preview states.

    Attributes:
        REQUIRES_CONFIRMATION: Preview must be reviewed or manually completed.
        CONFIRMED: Preview was confirmed into a user meal record.
        FAILED: Preview failed before confirmation.
    """

    REQUIRES_CONFIRMATION = "requires_confirmation"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class MealFoodCandidate(BaseModel):
    """Review-only food candidate shown to the user.

    Attributes:
        display_name: Candidate food name.
        portion_amount: Estimated or user-entered portion amount.
        portion_unit: Portion unit label.
        kcal: Estimated calories.
        carb_g: Estimated carbohydrate grams.
        protein_g: Estimated protein grams.
        fat_g: Estimated fat grams.
        sodium_mg: Estimated sodium milligrams.
        confidence: Candidate confidence from 0.0 to 1.0.
        source: Source that produced the candidate.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str = Field(min_length=1, max_length=160)
    portion_amount: float | None = Field(default=None, ge=0)
    portion_unit: str | None = Field(default=None, max_length=40)
    kcal: float | None = Field(default=None, ge=0)
    carb_g: float | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)
    sodium_mg: float | None = Field(default=None, ge=0)
    confidence: float = Field(ge=0, le=1)
    source: Literal["vision", "manual", "database_match"]


class FoodImagePipelineMetadata(BaseModel):
    """Sanitized food image pipeline metadata for mobile smoke tests.

    Attributes:
        intake_completed: Whether image validation and hashing completed.
        detector_model: Detector model label when configured.
        classifier_model: Classifier model label when configured.
        detector_used: Whether a detector actually ran.
        classifier_used: Whether a classifier actually ran.
        raw_image_stored: Always false unless a future consented media object is linked.
        raw_provider_payload_stored: Always false.
        requires_manual_entry: Whether the UI should ask for manual food details.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    intake_completed: bool
    detector_model: str | None = Field(default=None, max_length=120)
    classifier_model: str | None = Field(default=None, max_length=120)
    detector_used: bool
    classifier_used: bool
    raw_image_stored: Literal[False] = False
    raw_provider_payload_stored: Literal[False] = False
    requires_manual_entry: bool


class MealImageAnalysisPreview(BaseModel):
    """Food image analysis preview response.

    Attributes:
        analysis_id: Food image analysis run identifier.
        meal_id: Linked meal preview identifier.
        status: Preview lifecycle status.
        meal_type: User-selected meal bucket.
        eaten_at: User-selected or server-defaulted meal timestamp.
        food_candidates: Review-only detected food candidates.
        nutrition_estimate_summary: Bounded nutrition estimate summary.
        warning_codes: Stable warning codes for the UI.
        pipeline_metadata: Sanitized pipeline metadata.
        algorithm_version: Backend preview algorithm contract version.
        created_at: Server-side analysis creation timestamp.
    """

    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID
    meal_id: UUID
    status: MealAnalysisStatus
    meal_type: MealType
    eaten_at: datetime
    food_candidates: list[MealFoodCandidate] = Field(default_factory=list)
    nutrition_estimate_summary: dict[str, object] = Field(default_factory=dict)
    warning_codes: list[str] = Field(default_factory=list, max_length=20)
    pipeline_metadata: FoodImagePipelineMetadata
    algorithm_version: str = Field(min_length=1, max_length=80)
    created_at: datetime | None = None
