"""Persisted analysis result API schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnalysisType(StrEnum):
    """Supported persisted analysis result types.

    Attributes:
        ACTIVITY_SCORE: Activity score analysis.
        WEIGHT_PREDICTION: Weight prediction analysis.
        NUTRITION_ANALYSIS: Nutrition intake analysis.
    """

    ACTIVITY_SCORE = "activity_score"
    WEIGHT_PREDICTION = "weight_prediction"
    NUTRITION_ANALYSIS = "nutrition_analysis"


class AnalysisResultResponse(BaseModel):
    """Persisted analysis result response.

    Attributes:
        id: Persisted result identifier.
        analysis_type: Type of stored analysis.
        algorithm_version: Version of the server algorithm used for the result.
        kdris_source_manifest_version: KDRIs source manifest schema version for nutrition results.
        result_snapshot: Server-computed result snapshot.
        created_at: Server-side record creation timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_type: AnalysisType
    algorithm_version: str
    kdris_source_manifest_version: str | None
    result_snapshot: dict[str, Any]
    created_at: datetime


class AnalysisResultSummary(BaseModel):
    """Persisted analysis result list item.

    Attributes:
        id: Persisted result identifier.
        analysis_type: Type of stored analysis.
        algorithm_version: Version of the server algorithm used for the result.
        kdris_source_manifest_version: KDRIs source manifest schema version for nutrition results.
        created_at: Server-side record creation timestamp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_type: AnalysisType
    algorithm_version: str
    kdris_source_manifest_version: str | None
    created_at: datetime


class AnalysisResultListResponse(BaseModel):
    """Paginated persisted analysis result list response.

    Attributes:
        results: Analysis result summaries visible to the current owner.
        limit: Maximum requested row count.
        offset: Requested row offset.
    """

    results: list[AnalysisResultSummary]
    limit: int
    offset: int
