"""Database model registry."""

from src.db.base import Base
from src.models.db.analysis_result import AnalysisResult
from src.models.db.health import HealthDailySummary, HealthSyncBatch
from src.models.db.privacy import AuditLog, ConsentPolicy, ConsentRecord, DeletionRequest
from src.models.db.supplement import (
    SupplementAnalysisRun,
    SupplementProduct,
    SupplementProductIngredient,
    UserSupplement,
    UserSupplementIngredient,
)
from src.models.db.user import User

__all__ = [
    "AnalysisResult",
    "AuditLog",
    "Base",
    "ConsentPolicy",
    "ConsentRecord",
    "DeletionRequest",
    "HealthDailySummary",
    "HealthSyncBatch",
    "SupplementAnalysisRun",
    "SupplementProduct",
    "SupplementProductIngredient",
    "User",
    "UserSupplement",
    "UserSupplementIngredient",
]
