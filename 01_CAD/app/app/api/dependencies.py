"""
CAD Vision API — FastAPI 의존성 주입.

core/dependencies.py의 싱글톤을 FastAPI Depends()로 래핑한다.
"""

from __future__ import annotations

from core.dependencies import get_pipeline as _get_pipeline
from core.feedback_store import FeedbackStore

_feedback_store: FeedbackStore | None = None


def get_pipeline():
    """FastAPI Depends()용 Pipeline 의존성."""
    return _get_pipeline()


def get_feedback_store() -> FeedbackStore:
    """FeedbackStore 싱글톤 (lazy init)."""
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStore()
    return _feedback_store
