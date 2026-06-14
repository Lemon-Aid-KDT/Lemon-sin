"""Database model registry."""

from src.db.base import Base
from src.models.db.agent_memory import AgentMemory, AgentRun
from src.models.db.analysis_result import AnalysisResult
from src.models.db.food_record import FoodRecord
from src.models.db.health import HealthDailySummary, HealthSyncBatch
from src.models.db.learning import ImageEmbeddingJob, ImageEmbeddingRecord, LearningImageObject
from src.models.db.medical_source import (
    MedicalEvidenceItem,
    MedicalPolicyBoundary,
    MedicalRagChunk,
    MedicalSource,
    MedicalSourceVersion,
    MedicalUnknownKnowledgeEvent,
)
from src.models.db.notification import ReminderPreference
from src.models.db.privacy import AuditLog, ConsentPolicy, ConsentRecord, DeletionRequest
from src.models.db.regulated import LabResultItem, PrescriptionItem, RegulatedDocument
from src.models.db.supplement import (
    SupplementAnalysisRun,
    SupplementProduct,
    SupplementProductIngredient,
    UserSupplement,
    UserSupplementIngredient,
)
from src.models.db.user import User
from src.models.db.user_medication import UserMedication

__all__ = [
    "AgentMemory",
    "AgentRun",
    "AnalysisResult",
    "AuditLog",
    "Base",
    "ConsentPolicy",
    "ConsentRecord",
    "DeletionRequest",
    "FoodRecord",
    "HealthDailySummary",
    "HealthSyncBatch",
    "ImageEmbeddingJob",
    "ImageEmbeddingRecord",
    "LabResultItem",
    "LearningImageObject",
    "MedicalEvidenceItem",
    "MedicalPolicyBoundary",
    "MedicalRagChunk",
    "MedicalSource",
    "MedicalSourceVersion",
    "MedicalUnknownKnowledgeEvent",
    "PrescriptionItem",
    "RegulatedDocument",
    "ReminderPreference",
    "SupplementAnalysisRun",
    "SupplementProduct",
    "SupplementProductIngredient",
    "User",
    "UserMedication",
    "UserSupplement",
    "UserSupplementIngredient",
]
