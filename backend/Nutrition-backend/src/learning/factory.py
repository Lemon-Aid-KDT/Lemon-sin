"""Factories for consent-gated learning adapters."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.learning.embedding_runner import SentenceTransformersImageEmbeddingProvider
from src.learning.embeddings import DisabledEmbeddingProvider, EmbeddingProvider
from src.learning.object_storage import (
    DisabledLearningImageObjectStore,
    LearningImageObjectStore,
    LocalLearningImageObjectStore,
    S3LearningImageObjectStore,
)
from src.learning.pgvector_store import PgvectorStore
from src.learning.vector_store import DisabledVectorStore, VectorStore


def build_learning_object_store(settings: Settings) -> LearningImageObjectStore:
    """Build the configured learning image object store.

    Args:
        settings: Runtime settings.

    Returns:
        Object storage adapter. Defaults to a fail-closed disabled adapter.
    """
    if settings.learning_object_storage_provider == "local":
        return LocalLearningImageObjectStore(
            root=settings.learning_object_storage_local_path,
            prefix=settings.learning_object_storage_prefix,
        )
    if settings.learning_object_storage_provider == "s3":
        assert settings.learning_object_storage_bucket is not None
        return S3LearningImageObjectStore(
            bucket=settings.learning_object_storage_bucket,
            prefix=settings.learning_object_storage_prefix,
            endpoint_url=settings.learning_object_storage_endpoint_url,
            region_name=settings.learning_object_storage_region,
            server_side_encryption=settings.learning_object_storage_sse,
        )
    return DisabledLearningImageObjectStore()


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build the configured embedding provider.

    Args:
        settings: Runtime settings.

    Returns:
        Embedding provider. Defaults to a fail-closed disabled provider.
    """
    if not settings.enable_image_learning_pipeline:
        return DisabledEmbeddingProvider()
    return SentenceTransformersImageEmbeddingProvider(
        model_name=settings.embedding_model,
        expected_dimensions=settings.embedding_dimensions,
    )


def build_vector_store(settings: Settings, session: AsyncSession) -> VectorStore:
    """Build the configured vector store.

    Args:
        settings: Runtime settings.
        session: Async database session.

    Returns:
        Vector store. Defaults to a fail-closed disabled store.
    """
    if not settings.enable_pgvector_storage:
        return DisabledVectorStore()
    return PgvectorStore(session=session, expected_dimensions=settings.embedding_dimensions)
