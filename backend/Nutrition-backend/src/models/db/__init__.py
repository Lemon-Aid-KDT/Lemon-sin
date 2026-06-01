"""Database model registry."""

from src.db.base import Base
from src.models.db.analysis_result import AnalysisResult
from src.models.db.health import (
    BodyProfileSnapshot,
    HealthDailySummary,
    HealthMetricSample,
    HealthSyncBatch,
)
from src.models.db.learning import ImageEmbeddingJob, ImageEmbeddingRecord, LearningImageObject
from src.models.db.meal import (
    FoodCatalogItem,
    FoodCourse,
    FoodCuisine,
    FoodImageAnalysisRun,
    MealFoodItem,
    MealRecord,
)
from src.models.db.media import MediaObject, MediaProcessingRun, SupplementImageEvidence
from src.models.db.medical import (
    MedicalRecordCollection,
    PatientCondition,
    PatientMedication,
    PatientStatusSnapshot,
)
from src.models.db.privacy import AuditLog, ConsentPolicy, ConsentRecord, DeletionRequest
from src.models.db.regulated import LabResultItem, PrescriptionItem, RegulatedDocument
from src.models.db.retraining import (
    AnnotationTask,
    LearningDatasetItem,
    LearningDatasetVersion,
    ModelEvalResult,
    ModelRegistryEntry,
    ModelTrainingRun,
)
from src.models.db.supplement import (
    SupplementAnalysisRun,
    SupplementCategory,
    SupplementProduct,
    SupplementProductCategory,
    SupplementProductIngredient,
    UserSupplement,
    UserSupplementIngredient,
)
from src.models.db.user import User

__all__ = [
    "AnalysisResult",
    "AnnotationTask",
    "AuditLog",
    "Base",
    "BodyProfileSnapshot",
    "ConsentPolicy",
    "ConsentRecord",
    "DeletionRequest",
    "FoodCatalogItem",
    "FoodCourse",
    "FoodCuisine",
    "FoodImageAnalysisRun",
    "HealthDailySummary",
    "HealthMetricSample",
    "HealthSyncBatch",
    "ImageEmbeddingJob",
    "ImageEmbeddingRecord",
    "LabResultItem",
    "LearningDatasetItem",
    "LearningDatasetVersion",
    "LearningImageObject",
    "MealFoodItem",
    "MealRecord",
    "MediaObject",
    "MediaProcessingRun",
    "MedicalRecordCollection",
    "ModelEvalResult",
    "ModelRegistryEntry",
    "ModelTrainingRun",
    "PatientCondition",
    "PatientMedication",
    "PatientStatusSnapshot",
    "PrescriptionItem",
    "RegulatedDocument",
    "SupplementAnalysisRun",
    "SupplementCategory",
    "SupplementImageEvidence",
    "SupplementProduct",
    "SupplementProductCategory",
    "SupplementProductIngredient",
    "User",
    "UserSupplement",
    "UserSupplementIngredient",
]
