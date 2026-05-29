"""Database model metadata tests."""

from __future__ import annotations

from decimal import Decimal
from typing import cast

from sqlalchemy import CheckConstraint, Date, Index, Numeric, String, Table, Text
from sqlalchemy.dialects import postgresql
from src.db.base import Base
from src.models.db import (
    AgentMemory,
    AgentRun,
    AnalysisResult,
    AuditLog,
    ConsentPolicy,
    ConsentRecord,
    DeletionRequest,
    HealthDailySummary,
    HealthSyncBatch,
    ImageEmbeddingJob,
    ImageEmbeddingRecord,
    LabResultItem,
    LearningImageObject,
    PrescriptionItem,
    RegulatedDocument,
    SupplementAnalysisRun,
    SupplementProduct,
    SupplementProductIngredient,
    User,
    UserSupplement,
    UserSupplementIngredient,
)


def test_user_table_is_registered_with_required_columns() -> None:
    """Verify that the users table is registered in shared ORM metadata."""
    table = cast(Table, User.__table__)

    assert "users" in Base.metadata.tables
    assert table.name == "users"
    assert set(table.c.keys()) == {
        "id",
        "sex",
        "birth_date",
        "height_cm",
        "base_weight_kg",
        "created_at",
        "updated_at",
    }
    assert table.c.id.primary_key is True
    assert table.c.sex.nullable is False
    assert table.c.created_at.nullable is False
    assert table.c.updated_at.nullable is False


def test_user_numeric_columns_use_expected_precision() -> None:
    """Verify Phase 1 body-measure columns retain predictable decimal precision."""
    table = cast(Table, User.__table__)
    height_type = cast(Numeric[Decimal], table.c.height_cm.type)
    weight_type = cast(Numeric[Decimal], table.c.base_weight_kg.type)

    assert height_type.precision == 5
    assert height_type.scale == 2
    assert weight_type.precision == 5
    assert weight_type.scale == 2


def test_user_constraints_are_named_for_alembic() -> None:
    """Verify constraints use deterministic names for migration diffs."""
    table = cast(Table, User.__table__)
    constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert {
        "ck_users_sex_allowed",
        "ck_users_height_cm_positive",
        "ck_users_base_weight_kg_positive",
    }.issubset(constraint_names)


def test_base_metadata_uses_naming_convention() -> None:
    """Verify the shared metadata has a stable naming convention."""
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"
    assert Base.metadata.naming_convention["ix"] == "ix_%(table_name)s_%(column_0_name)s"


def test_analysis_result_table_is_registered_with_required_columns() -> None:
    """Verify that the analysis results table is registered in shared ORM metadata."""
    table = cast(Table, AnalysisResult.__table__)

    assert "analysis_results" in Base.metadata.tables
    assert table.name == "analysis_results"
    assert set(table.c.keys()) == {
        "id",
        "owner_subject",
        "analysis_type",
        "algorithm_version",
        "kdris_source_manifest_version",
        "input_snapshot",
        "result_snapshot",
        "created_at",
        "updated_at",
    }
    assert table.c.id.primary_key is True
    assert table.c.owner_subject.nullable is False
    assert table.c.input_snapshot.nullable is False
    assert table.c.result_snapshot.nullable is False


def test_analysis_result_constraints_and_indexes_are_defined() -> None:
    """Verify owner-scoped result storage uses deterministic constraints and indexes."""
    table = cast(Table, AnalysisResult.__table__)
    constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    index_names = {index.name for index in table.indexes if isinstance(index, Index)}

    assert "ck_analysis_results_analysis_type_allowed" in constraint_names
    assert "ix_analysis_results_owner_created_at" in index_names
    assert "ix_analysis_results_owner_type_created_at" in index_names


def test_privacy_tables_are_registered_with_required_columns() -> None:
    """Verify privacy tables are registered in shared ORM metadata."""
    assert "consent_policies" in Base.metadata.tables
    assert "consent_records" in Base.metadata.tables
    assert "deletion_requests" in Base.metadata.tables
    assert "audit_logs" in Base.metadata.tables

    consent_policy = cast(Table, ConsentPolicy.__table__)
    consent_record = cast(Table, ConsentRecord.__table__)
    deletion_request = cast(Table, DeletionRequest.__table__)
    audit_log = cast(Table, AuditLog.__table__)

    assert {"consent_type", "version", "content_hash", "effective_at"}.issubset(
        set(consent_policy.c.keys())
    )
    assert {"owner_subject", "policy_version", "granted", "ip_hash"}.issubset(
        set(consent_record.c.keys())
    )
    assert {"owner_subject_hash", "request_type", "deleted_counts"}.issubset(
        set(deletion_request.c.keys())
    )
    assert {"actor_subject_hash", "action", "event_metadata", "record_hash"}.issubset(
        set(audit_log.c.keys())
    )


def test_privacy_constraints_and_indexes_are_defined() -> None:
    """Verify privacy tables expose deterministic constraints and lookup indexes."""
    deletion_request = cast(Table, DeletionRequest.__table__)
    audit_log = cast(Table, AuditLog.__table__)
    audit_index_names = {index.name for index in audit_log.indexes if isinstance(index, Index)}
    deletion_constraint_names = {
        constraint.name
        for constraint in deletion_request.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_deletion_requests_deletion_request_type_allowed" in deletion_constraint_names
    assert "ck_deletion_requests_deletion_request_status_allowed" in deletion_constraint_names
    assert "ix_audit_logs_actor_created_at" in audit_index_names
    assert "ix_audit_logs_resource_created_at" in audit_index_names


def test_regulated_document_tables_are_registered_with_required_columns() -> None:
    """Verify regulated OCR intake tables are registered in shared ORM metadata."""
    regulated_document = cast(Table, RegulatedDocument.__table__)
    prescription_item = cast(Table, PrescriptionItem.__table__)
    lab_result_item = cast(Table, LabResultItem.__table__)

    assert "regulated_documents" in Base.metadata.tables
    assert "prescription_items" in Base.metadata.tables
    assert "lab_result_items" in Base.metadata.tables
    assert {
        "owner_subject_hash",
        "document_type",
        "status",
        "image_sha256",
        "ocr_text_hash",
        "parsed_snapshot",
        "warning_codes",
        "consult_cta",
        "raw_image_deleted_at",
        "expires_at",
        "confirmed_at",
    }.issubset(set(regulated_document.c.keys()))
    assert {
        "document_id",
        "medication_name_text",
        "dose_text",
        "frequency_text",
        "period_text",
        "source",
    }.issubset(set(prescription_item.c.keys()))
    assert {
        "document_id",
        "test_name_text",
        "value_text",
        "unit_text",
        "reference_range_text",
        "source",
    }.issubset(set(lab_result_item.c.keys()))


def test_regulated_document_constraints_and_indexes_are_defined() -> None:
    """Verify regulated OCR intake tables expose deterministic safety constraints."""
    regulated_document = cast(Table, RegulatedDocument.__table__)
    prescription_item = cast(Table, PrescriptionItem.__table__)
    lab_result_item = cast(Table, LabResultItem.__table__)
    document_constraint_names = {
        constraint.name
        for constraint in regulated_document.constraints
        if isinstance(constraint, CheckConstraint)
    }
    prescription_constraint_names = {
        constraint.name
        for constraint in prescription_item.constraints
        if isinstance(constraint, CheckConstraint)
    }
    lab_constraint_names = {
        constraint.name
        for constraint in lab_result_item.constraints
        if isinstance(constraint, CheckConstraint)
    }
    document_index_names = {
        index.name for index in regulated_document.indexes if isinstance(index, Index)
    }

    assert "ck_regulated_documents_regulated_document_type_allowed" in document_constraint_names
    assert "ck_regulated_documents_regulated_document_status_allowed" in document_constraint_names
    assert "ck_regulated_documents_regulated_document_image_mime_type_allowed" in (
        document_constraint_names
    )
    assert "ck_prescription_items_prescription_item_confidence_range" in (
        prescription_constraint_names
    )
    assert "ck_lab_result_items_lab_result_item_confidence_range" in lab_constraint_names
    assert "ix_regulated_documents_owner_status_created_at" in document_index_names


def test_supplement_tables_are_registered_with_required_columns() -> None:
    """Verify P1 supplement tables are registered in shared ORM metadata."""
    supplement_product = cast(Table, SupplementProduct.__table__)
    supplement_product_ingredient = cast(Table, SupplementProductIngredient.__table__)
    supplement_analysis_run = cast(Table, SupplementAnalysisRun.__table__)
    user_supplement = cast(Table, UserSupplement.__table__)
    user_supplement_ingredient = cast(Table, UserSupplementIngredient.__table__)

    assert "supplement_products" in Base.metadata.tables
    assert "supplement_product_ingredients" in Base.metadata.tables
    assert "supplement_analysis_runs" in Base.metadata.tables
    assert "user_supplements" in Base.metadata.tables
    assert "user_supplement_ingredients" in Base.metadata.tables
    assert {
        "source_provider",
        "source_product_id",
        "product_name",
        "normalized_product_name",
        "source_payload",
        "source_manifest_version",
    }.issubset(set(supplement_product.c.keys()))
    assert {
        "product_id",
        "standard_name",
        "nutrient_code",
        "amount",
        "source_payload",
    }.issubset(set(supplement_product_ingredient.c.keys()))
    assert {
        "owner_subject",
        "client_request_id",
        "status",
        "image_sha256",
        "ocr_text_hash",
        "parsed_snapshot",
        "match_snapshot",
        "algorithm_version",
        "source_manifest_version",
        "expires_at",
    }.issubset(set(supplement_analysis_run.c.keys()))
    assert {
        "owner_subject",
        "source_analysis_run_id",
        "matched_product_id",
        "display_name",
        "serving_snapshot",
        "intake_schedule",
        "deleted_at",
    }.issubset(set(user_supplement.c.keys()))
    assert {
        "user_supplement_id",
        "display_name",
        "nutrient_code",
        "amount",
        "confidence",
        "source",
    }.issubset(set(user_supplement_ingredient.c.keys()))


def test_supplement_constraints_and_indexes_are_defined() -> None:
    """Verify P1 supplement tables expose deterministic constraints and lookup indexes."""
    supplement_product = cast(Table, SupplementProduct.__table__)
    supplement_analysis_run = cast(Table, SupplementAnalysisRun.__table__)
    user_supplement_ingredient = cast(Table, UserSupplementIngredient.__table__)
    product_constraint_names = {constraint.name for constraint in supplement_product.constraints}
    run_constraint_names = {constraint.name for constraint in supplement_analysis_run.constraints}
    ingredient_constraint_names = {
        constraint.name for constraint in user_supplement_ingredient.constraints
    }
    product_index_names = {
        index.name for index in supplement_product.indexes if isinstance(index, Index)
    }
    run_index_names = {
        index.name for index in supplement_analysis_run.indexes if isinstance(index, Index)
    }
    ingredient_index_names = {
        index.name for index in user_supplement_ingredient.indexes if isinstance(index, Index)
    }

    assert "uq_supplement_products_source_provider_product_id" in product_constraint_names
    assert "ck_supplement_products_source_provider_nonempty" in product_constraint_names
    assert "ck_supplement_analysis_runs_status_allowed" in run_constraint_names
    assert "ck_supplement_analysis_runs_ocr_confidence_range" in run_constraint_names
    assert "ck_user_supplement_ingredients_confidence_range" in ingredient_constraint_names
    assert "ix_supplement_products_normalized_name" in product_index_names
    assert "ix_supplement_analysis_runs_owner_created_at" in run_index_names
    assert "ix_supplement_analysis_runs_owner_status_created_at" in run_index_names
    assert "ix_user_supplement_ingredients_supplement_id" in ingredient_index_names


def test_health_tables_are_registered_with_required_columns() -> None:
    """Verify P1 health tables are registered in shared ORM metadata."""
    health_sync_batch = cast(Table, HealthSyncBatch.__table__)
    health_daily_summary = cast(Table, HealthDailySummary.__table__)

    assert "health_sync_batches" in Base.metadata.tables
    assert "health_daily_summaries" in Base.metadata.tables
    assert {
        "owner_subject",
        "client_batch_id",
        "source_platform",
        "record_count",
        "accepted_count",
        "rejected_count",
        "input_snapshot",
        "result_snapshot",
        "synced_at",
    }.issubset(set(health_sync_batch.c.keys()))
    assert {
        "owner_subject",
        "measured_date",
        "source_platform",
        "steps",
        "weight_kg",
        "resting_heart_rate_bpm",
        "active_energy_kcal",
        "source_record_hash",
        "synced_at",
    }.issubset(set(health_daily_summary.c.keys()))


def test_health_constraints_and_indexes_are_defined() -> None:
    """Verify P1 health tables expose deterministic constraints and lookup indexes."""
    health_sync_batch = cast(Table, HealthSyncBatch.__table__)
    health_daily_summary = cast(Table, HealthDailySummary.__table__)
    sync_constraint_names = {constraint.name for constraint in health_sync_batch.constraints}
    summary_constraint_names = {constraint.name for constraint in health_daily_summary.constraints}
    sync_index_names = {
        index.name for index in health_sync_batch.indexes if isinstance(index, Index)
    }
    summary_index_names = {
        index.name for index in health_daily_summary.indexes if isinstance(index, Index)
    }

    assert "uq_health_sync_batches_owner_client_batch" in sync_constraint_names
    assert "ck_health_sync_batches_source_platform_allowed" in sync_constraint_names
    assert "ck_health_sync_batches_accepted_rejected_count_valid" in sync_constraint_names
    assert "uq_health_daily_summaries_owner_date_platform" in summary_constraint_names
    assert "ck_health_daily_summaries_health_metric_present" in summary_constraint_names
    assert "ck_health_daily_summaries_weight_kg_range" in summary_constraint_names
    assert "ix_health_sync_batches_owner_synced_at" in sync_index_names
    assert "ix_health_daily_summaries_owner_measured_date" in summary_index_names
    assert "ix_health_daily_summaries_owner_source_date" in summary_index_names


def test_learning_tables_are_registered_without_raw_payload_columns() -> None:
    """Verify learning tables store references and embeddings without raw payloads."""
    image_object = cast(Table, LearningImageObject.__table__)
    embedding_job = cast(Table, ImageEmbeddingJob.__table__)
    embedding_record = cast(Table, ImageEmbeddingRecord.__table__)

    assert "learning_image_objects" in Base.metadata.tables
    assert "image_embedding_jobs" in Base.metadata.tables
    assert "image_embedding_records" in Base.metadata.tables
    assert {
        "owner_subject_hash",
        "analysis_id",
        "image_sha256",
        "object_uri",
        "retained_until",
        "consent_snapshot",
    }.issubset(set(image_object.c.keys()))
    assert {
        "image_object_id",
        "analysis_id",
        "owner_subject_hash",
        "embedding_model",
        "metadata_snapshot",
    }.issubset(set(embedding_job.c.keys()))
    assert {
        "owner_subject_hash",
        "analysis_id",
        "image_object_id",
        "embedding_dimensions",
        "embedding",
        "metadata",
    }.issubset(set(embedding_record.c.keys()))

    all_columns = set(image_object.c.keys()) | set(embedding_job.c.keys())
    all_columns |= set(embedding_record.c.keys())
    forbidden_columns = {"raw_image", "raw_image_bytes", "image_base64", "raw_ocr_text"}

    assert forbidden_columns.isdisjoint(all_columns)


def test_learning_constraints_and_indexes_are_defined() -> None:
    """Verify learning tables expose deterministic constraints and indexes."""
    image_object = cast(Table, LearningImageObject.__table__)
    embedding_job = cast(Table, ImageEmbeddingJob.__table__)
    embedding_record = cast(Table, ImageEmbeddingRecord.__table__)
    image_constraint_names = {constraint.name for constraint in image_object.constraints}
    job_constraint_names = {constraint.name for constraint in embedding_job.constraints}
    record_constraint_names = {constraint.name for constraint in embedding_record.constraints}
    job_index_names = {index.name for index in embedding_job.indexes if isinstance(index, Index)}
    record_index_names = {
        index.name for index in embedding_record.indexes if isinstance(index, Index)
    }

    assert "uq_learning_image_objects_owner_analysis_hash" in image_constraint_names
    assert (
        "ck_learning_image_objects_learning_image_object_status_allowed" in image_constraint_names
    )
    assert "uq_image_embedding_jobs_object_model" in job_constraint_names
    assert "ck_image_embedding_jobs_image_embedding_job_status_allowed" in job_constraint_names
    assert "uq_image_embedding_records_owner_analysis_model_hash" in record_constraint_names
    assert "ck_image_embedding_records_embedding_dimensions_positive" in record_constraint_names
    assert "ix_image_embedding_jobs_status_next_run" in job_index_names
    assert "ix_image_embedding_records_owner_created_at" in record_index_names


def test_agent_memory_tables_are_registered_without_raw_payload_columns() -> None:
    """Verify Agent memory tables store summaries and execution metadata only."""
    memory = cast(Table, AgentMemory.__table__)
    run = cast(Table, AgentRun.__table__)

    assert "agent_memory" in Base.metadata.tables
    assert "agent_runs" in Base.metadata.tables
    assert {
        "owner_subject_hash",
        "memory_type",
        "summary_json",
        "source_counters",
        "last_source_created_at",
        "algorithm_version",
    }.issubset(set(memory.c.keys()))
    assert {
        "request_id",
        "owner_subject_hash",
        "agent_name",
        "status",
        "approval_status",
        "provider",
        "model",
        "latency_ms",
        "cost_usd",
        "used_tools",
    }.issubset(set(run.c.keys()))

    forbidden_columns = {"raw_image", "raw_ocr_text", "raw_llm_response", "prompt"}
    assert forbidden_columns.isdisjoint(set(memory.c.keys()) | set(run.c.keys()))


def test_agent_memory_constraints_and_indexes_are_defined() -> None:
    """Verify Agent memory tables expose deterministic constraints and lookup indexes."""
    memory = cast(Table, AgentMemory.__table__)
    run = cast(Table, AgentRun.__table__)
    memory_constraint_names = {constraint.name for constraint in memory.constraints}
    run_constraint_names = {constraint.name for constraint in run.constraints}
    memory_index_names = {index.name for index in memory.indexes if isinstance(index, Index)}
    run_index_names = {index.name for index in run.indexes if isinstance(index, Index)}

    assert "uq_agent_memory_owner_type" in memory_constraint_names
    assert "ck_agent_memory_agent_memory_memory_type_nonempty" in memory_constraint_names
    assert "ck_agent_runs_agent_runs_status_allowed" in run_constraint_names
    assert "ck_agent_runs_agent_runs_approval_status_allowed" in run_constraint_names
    assert "ix_agent_memory_owner_type" in memory_index_names
    assert "ix_agent_runs_owner_created_at" in run_index_names


def test_medical_source_governance_tables_are_registered() -> None:
    """Verify medical source governance tables are registered in ORM metadata."""
    assert {
        "medical_sources",
        "medical_source_versions",
        "medical_evidence_items",
        "medical_policy_boundaries",
        "medical_rag_chunks",
    }.issubset(Base.metadata.tables)


def test_medical_sources_table_contract() -> None:
    """Verify medical source registry table columns and lookup index."""
    table = cast(Table, Base.metadata.tables["medical_sources"])
    id_type = cast(String, table.c.id.type)
    constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    index_names = {index.name for index in table.indexes if isinstance(index, Index)}

    assert set(table.c.keys()) == {
        "id",
        "source_family",
        "publisher",
        "title",
        "canonical_url",
        "jurisdiction",
        "source_type",
        "default_review_status",
        "owner",
        "created_at",
        "updated_at",
    }
    assert table.c.id.primary_key is True
    assert id_type.length == 80
    assert table.c.source_family.nullable is False
    assert table.c.default_review_status.nullable is False
    assert {
        "ck_medical_sources_default_review_status",
        "ck_medical_sources_source_type",
    }.issubset(constraint_names)
    assert "ix_medical_sources_family_status" in index_names


def test_medical_source_versions_table_contract() -> None:
    """Verify source version table stores review and expiry dates."""
    table = cast(Table, Base.metadata.tables["medical_source_versions"])
    constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    index_names = {index.name for index in table.indexes if isinstance(index, Index)}

    assert {
        "id",
        "source_id",
        "version_label",
        "published_at",
        "reviewed_at",
        "expires_at",
        "review_status",
        "reviewer",
        "review_note",
        "created_at",
        "updated_at",
    } == set(table.c.keys())
    assert isinstance(table.c.id.type, postgresql.UUID)
    assert table.c.id.primary_key is True
    assert isinstance(table.c.published_at.type, Date)
    assert isinstance(table.c.reviewed_at.type, Date)
    assert isinstance(table.c.expires_at.type, Date)
    assert isinstance(table.c.review_note.type, Text)
    assert "ck_medical_source_versions_review_status" in constraint_names
    assert "ix_medical_source_versions_source_status_expires" in index_names


def test_medical_evidence_items_table_contract() -> None:
    """Verify evidence items preserve reviewed claim wording boundaries."""
    table = cast(Table, Base.metadata.tables["medical_evidence_items"])
    constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    index_names = {index.name for index in table.indexes if isinstance(index, Index)}

    assert {
        "id",
        "source_version_id",
        "topic",
        "audience",
        "claim_summary",
        "allowed_user_wording",
        "blocked_wording",
        "applicability_note",
        "caution_level",
        "review_status",
        "algorithm_version",
        "created_at",
        "updated_at",
    } == set(table.c.keys())
    assert isinstance(table.c.id.type, postgresql.UUID)
    assert isinstance(table.c.claim_summary.type, Text)
    assert isinstance(table.c.allowed_user_wording.type, Text)
    assert isinstance(table.c.blocked_wording.type, Text)
    assert isinstance(table.c.applicability_note.type, Text)
    assert {
        "ck_medical_evidence_items_caution_level",
        "ck_medical_evidence_items_review_status",
    }.issubset(constraint_names)
    assert "ix_medical_evidence_items_topic_audience_status" in index_names


def test_medical_policy_boundaries_table_contract() -> None:
    """Verify safety boundaries can be shared by classifiers and contract tests."""
    table = cast(Table, Base.metadata.tables["medical_policy_boundaries"])
    constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    index_names = {index.name for index in table.indexes if isinstance(index, Index)}

    assert {
        "id",
        "boundary_code",
        "topic",
        "trigger_intent",
        "response_status",
        "required_warning_code",
        "allowed_response_pattern",
        "blocked_response_pattern",
        "source_version_id",
        "review_status",
        "created_at",
        "updated_at",
    } == set(table.c.keys())
    assert isinstance(table.c.id.type, postgresql.UUID)
    assert isinstance(table.c.allowed_response_pattern.type, Text)
    assert isinstance(table.c.blocked_response_pattern.type, Text)
    assert {
        "ck_medical_policy_boundaries_response_status",
        "ck_medical_policy_boundaries_review_status",
    }.issubset(constraint_names)
    assert "ix_medical_policy_boundaries_code_status" in index_names


def test_medical_rag_chunks_table_contract() -> None:
    """Verify RAG chunks only store reviewed snippets and indexable metadata."""
    table = cast(Table, Base.metadata.tables["medical_rag_chunks"])
    constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    index_names = {index.name for index in table.indexes if isinstance(index, Index)}

    assert {
        "id",
        "evidence_item_id",
        "source_version_id",
        "chunk_text",
        "chunk_hash",
        "embedding_status",
        "review_status",
        "expires_at",
        "created_at",
        "updated_at",
    } == set(table.c.keys())
    assert isinstance(table.c.id.type, postgresql.UUID)
    assert isinstance(table.c.chunk_text.type, Text)
    assert isinstance(table.c.expires_at.type, Date)
    assert {
        "ck_medical_rag_chunks_embedding_status",
        "ck_medical_rag_chunks_review_status",
    }.issubset(constraint_names)
    assert "ix_medical_rag_chunks_status_embedding_expires" in index_names
    assert "ix_medical_rag_chunks_chunk_hash" in index_names


def test_medical_source_governance_tables_exclude_raw_payload_columns() -> None:
    """Verify medical source governance tables do not persist raw AI or OCR payloads."""
    table_names = {
        "medical_sources",
        "medical_source_versions",
        "medical_evidence_items",
        "medical_policy_boundaries",
        "medical_rag_chunks",
    }
    forbidden_columns = {
        "raw_prompt",
        "full_prompt",
        "prompt",
        "raw_llm_response",
        "provider_payload",
        "raw_ocr_text",
        "raw_image",
        "raw_image_bytes",
        "image_base64",
        "exif",
        "file_name",
        "original_file_name",
    }
    actual_columns = {
        column_name
        for table_name in table_names
        for column_name in Base.metadata.tables[table_name].c.keys()
    }

    assert forbidden_columns.isdisjoint(actual_columns)
