"""Privacy, consent, deletion, and audit services."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.learning.factory import build_learning_object_store
from src.learning.pipeline import delete_learning_artifacts_for_owner
from src.models.db.agent_memory import AgentMemory, AgentRun
from src.models.db.analysis_result import AnalysisResult
from src.models.db.health import HealthDailySummary, HealthSyncBatch
from src.models.db.privacy import AuditLog, ConsentRecord, DeletionRequest
from src.models.db.regulated import RegulatedDocument
from src.models.db.supplement import (
    SupplementAnalysisRun,
    UserSupplement,
    UserSupplementIngredient,
)
from src.models.schemas.privacy import (
    ConsentActionResponse,
    ConsentStateResponse,
    ConsentStatus,
    ConsentType,
    DeletionRequestResponse,
    DeletionRequestStatus,
    DeletionRequestType,
)
from src.privacy.consent_policies import ACTIVE_CONSENT_POLICIES, get_active_policy
from src.security.auth import AuthenticatedUser
from src.security.privacy import (
    hash_actor_subject,
    request_id_from_headers,
    request_privacy_hashes,
)
from src.security.subjects import build_owner_subject

SENSITIVE_HEALTH_CONSENT = ConsentType.SENSITIVE_HEALTH_ANALYSIS
AuditOutcome = Literal["success", "failed", "not_found", "blocked"]
FORBIDDEN_AUDIT_METADATA_KEYS = {
    "authorization",
    "access_token",
    "jwt",
    "owner_subject",
    "input_snapshot",
    "result_snapshot",
    "token",
}


class ConsentRequiredError(ValueError):
    """Raised when a protected operation is missing required user consent."""


def _utc_now() -> datetime:
    """Return the current UTC timestamp.

    Returns:
        Timezone-aware current datetime.
    """
    return datetime.now(UTC)


def _sanitize_event_metadata(event_metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Remove sensitive keys from audit metadata recursively.

    Args:
        event_metadata: Candidate audit metadata.

    Returns:
        Metadata dictionary with blocked keys removed.
    """
    if event_metadata is None:
        return {}
    sanitized = _sanitize_event_value(event_metadata)
    if not isinstance(sanitized, dict):
        return {}
    return sanitized


def _sanitize_event_value(value: Any) -> Any:
    """Remove sensitive keys from nested audit metadata values.

    Args:
        value: Candidate metadata value.

    Returns:
        Sanitized metadata value.
    """
    if isinstance(value, dict):
        return {
            key: _sanitize_event_value(nested_value)
            for key, nested_value in value.items()
            if isinstance(key, str) and key.lower() not in FORBIDDEN_AUDIT_METADATA_KEYS
        }
    if isinstance(value, list):
        return [_sanitize_event_value(item) for item in value]
    return value


def _audit_record_hash(
    *,
    actor_subject_hash: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    outcome: AuditOutcome,
    request_id: str | None,
    event_metadata: dict[str, Any],
    settings: Settings,
) -> str:
    """Build an HMAC over the normalized audit event payload.

    Args:
        actor_subject_hash: Hashed actor subject.
        action: Event action name.
        resource_type: Resource category.
        resource_id: Optional resource identifier.
        outcome: Event outcome.
        request_id: Optional request correlation identifier.
        event_metadata: Sanitized metadata.
        settings: Application settings containing the privacy hash secret.

    Returns:
        Hex-encoded SHA-256 HMAC for the audit payload.
    """
    payload = {
        "actor_subject_hash": actor_subject_hash,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "outcome": outcome,
        "request_id": request_id,
        "event_metadata": event_metadata,
    }
    serialized_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hmac.new(
        settings.privacy_hash_secret.get_secret_value().encode("utf-8"),
        serialized_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _build_audit_log(
    *,
    user: AuthenticatedUser,
    action: str,
    resource_type: str,
    resource_id: str | None,
    outcome: AuditOutcome,
    request: Request,
    settings: Settings,
    event_metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Build a sanitized audit log ORM object.

    Args:
        user: Authenticated actor.
        action: Event action name.
        resource_type: Resource category.
        resource_id: Optional resource identifier.
        outcome: Event outcome.
        request: Current FastAPI request.
        settings: Application settings containing the privacy hash secret.
        event_metadata: Optional sanitized metadata.

    Returns:
        Unsaved audit log ORM object.

    Raises:
        ValueError: If the authenticated subject is invalid.
    """
    actor_subject_hash = hash_actor_subject(user, settings)
    ip_hash, user_agent_hash = request_privacy_hashes(request, settings)
    request_id = request_id_from_headers(request)
    sanitized_metadata = _sanitize_event_metadata(event_metadata)
    record_hash = _audit_record_hash(
        actor_subject_hash=actor_subject_hash,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        request_id=request_id,
        event_metadata=sanitized_metadata,
        settings=settings,
    )
    return AuditLog(
        actor_subject_hash=actor_subject_hash,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        request_id=request_id,
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
        event_metadata=sanitized_metadata,
        record_hash=record_hash,
    )


def consent_record_to_action_response(record: ConsentRecord) -> ConsentActionResponse:
    """Convert a consent event row to an API response.

    Args:
        record: Persisted consent record.

    Returns:
        Consent action response.
    """
    return ConsentActionResponse(
        consent_type=ConsentType(record.consent_type),
        policy_version=record.policy_version,
        granted=record.granted,
        occurred_at=record.occurred_at,
    )


def deletion_request_to_response(record: DeletionRequest) -> DeletionRequestResponse:
    """Convert a deletion request row to an API response.

    Args:
        record: Persisted deletion request.

    Returns:
        Deletion request response.
    """
    return DeletionRequestResponse.model_validate(record)


async def _latest_consent_record(
    session: AsyncSession,
    user: AuthenticatedUser,
    consent_type: ConsentType,
) -> ConsentRecord | None:
    """Return the latest consent event for one user and bucket.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        consent_type: Consent bucket.

    Returns:
        Latest consent record or None.

    Raises:
        ValueError: If owner identity cannot be persisted safely.
    """
    statement = (
        select(ConsentRecord)
        .where(
            ConsentRecord.owner_subject == build_owner_subject(user),
            ConsentRecord.consent_type == consent_type.value,
        )
        .order_by(desc(ConsentRecord.occurred_at), desc(ConsentRecord.created_at))
        .limit(1)
    )
    record: ConsentRecord | None = await session.scalar(statement)
    return record


async def has_active_consent(
    session: AsyncSession,
    user: AuthenticatedUser,
    consent_type: ConsentType,
) -> bool:
    """Check whether a user granted the active policy version.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        consent_type: Consent bucket.

    Returns:
        True when the latest consent event grants the active policy version.

    Raises:
        ValueError: If owner identity cannot be persisted safely.
    """
    policy = get_active_policy(consent_type)
    record = await _latest_consent_record(session, user, consent_type)
    return bool(record and record.granted and record.policy_version == policy.version)


async def require_user_consent(
    session: AsyncSession,
    user: AuthenticatedUser,
    consent_type: ConsentType,
) -> None:
    """Fail if a protected operation is missing required consent.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        consent_type: Consent bucket.

    Raises:
        ConsentRequiredError: If the active consent policy is not granted.
        ValueError: If owner identity cannot be persisted safely.
    """
    if not await has_active_consent(session, user, consent_type):
        raise ConsentRequiredError(
            f"Consent '{consent_type.value}' is required for this operation."
        )


async def get_consent_state(
    session: AsyncSession,
    user: AuthenticatedUser,
) -> ConsentStateResponse:
    """Return current consent state for all active policies.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.

    Returns:
        Current consent state response.

    Raises:
        ValueError: If owner identity cannot be persisted safely.
    """
    statement = (
        select(ConsentRecord)
        .where(ConsentRecord.owner_subject == build_owner_subject(user))
        .order_by(desc(ConsentRecord.occurred_at), desc(ConsentRecord.created_at))
    )
    records = list((await session.scalars(statement)).all())
    latest_by_type: dict[str, ConsentRecord] = {}
    for record in records:
        latest_by_type.setdefault(record.consent_type, record)

    statuses = []
    for consent_type, policy in ACTIVE_CONSENT_POLICIES.items():
        latest_record = latest_by_type.get(consent_type.value)
        granted = bool(
            latest_record
            and latest_record.granted
            and latest_record.policy_version == policy.version
        )
        statuses.append(
            ConsentStatus(
                consent_type=consent_type,
                policy_version=policy.version,
                title=policy.title,
                required=policy.required,
                granted=granted,
                occurred_at=latest_record.occurred_at if latest_record else None,
                revoked_at=latest_record.revoked_at if latest_record else None,
            )
        )
    return ConsentStateResponse(consents=statuses)


async def grant_consent(
    session: AsyncSession,
    user: AuthenticatedUser,
    consent_type: ConsentType,
    request: Request,
    settings: Settings,
) -> ConsentRecord:
    """Persist a consent grant event and audit log.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        consent_type: Consent bucket.
        request: Current FastAPI request.
        settings: Application settings containing the privacy hash secret.

    Returns:
        Persisted consent record.

    Raises:
        ValueError: If owner identity cannot be persisted safely.
    """
    policy = get_active_policy(consent_type)
    now = _utc_now()
    ip_hash, user_agent_hash = request_privacy_hashes(request, settings)
    record = ConsentRecord(
        owner_subject=build_owner_subject(user),
        consent_type=consent_type.value,
        policy_version=policy.version,
        granted=True,
        occurred_at=now,
        revoked_at=None,
        request_id=request_id_from_headers(request),
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
    )
    audit_log = _build_audit_log(
        user=user,
        action="consent_granted",
        resource_type="consent",
        resource_id=consent_type.value,
        outcome="success",
        request=request,
        settings=settings,
        event_metadata={"consent_type": consent_type.value, "policy_version": policy.version},
    )

    async with session.begin():
        session.add(record)
        session.add(audit_log)
    await session.refresh(record)
    return record


async def revoke_consent(
    session: AsyncSession,
    user: AuthenticatedUser,
    consent_type: ConsentType,
    request: Request,
    settings: Settings,
) -> ConsentRecord:
    """Persist a consent revocation event and audit log.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        consent_type: Consent bucket.
        request: Current FastAPI request.
        settings: Application settings containing the privacy hash secret.

    Returns:
        Persisted consent revocation record.

    Raises:
        ValueError: If owner identity cannot be persisted safely.
    """
    policy = get_active_policy(consent_type)
    now = _utc_now()
    ip_hash, user_agent_hash = request_privacy_hashes(request, settings)
    record = ConsentRecord(
        owner_subject=build_owner_subject(user),
        consent_type=consent_type.value,
        policy_version=policy.version,
        granted=False,
        occurred_at=now,
        revoked_at=now,
        request_id=request_id_from_headers(request),
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
    )
    audit_log = _build_audit_log(
        user=user,
        action="consent_revoked",
        resource_type="consent",
        resource_id=consent_type.value,
        outcome="success",
        request=request,
        settings=settings,
        event_metadata={"consent_type": consent_type.value, "policy_version": policy.version},
    )

    async with session.begin():
        session.add(record)
        session.add(audit_log)
    await session.refresh(record)
    return record


async def record_audit_event(
    session: AsyncSession,
    user: AuthenticatedUser,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None,
    outcome: AuditOutcome,
    request: Request,
    settings: Settings,
    event_metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Persist one sanitized audit event.

    Args:
        session: Request-scoped async database session.
        user: Authenticated actor.
        action: Event action name.
        resource_type: Resource category.
        resource_id: Optional resource identifier.
        outcome: Event outcome.
        request: Current FastAPI request.
        settings: Application settings containing the privacy hash secret.
        event_metadata: Optional sanitized metadata.

    Returns:
        Persisted audit log object.

    Raises:
        ValueError: If the authenticated subject is invalid.
    """
    audit_log = _build_audit_log(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        request=request,
        settings=settings,
        event_metadata=event_metadata,
    )
    session.add(audit_log)
    await session.commit()
    return audit_log


async def record_sensitive_audit_event(
    session: AsyncSession,
    user: AuthenticatedUser,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None,
    outcome: AuditOutcome,
    request: Request,
    settings: Settings,
    event_metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Persist a sanitized audit event for sensitive health data access.

    Args:
        session: Request-scoped async database session.
        user: Authenticated actor.
        action: Event action name.
        resource_type: Resource category.
        resource_id: Optional resource identifier.
        outcome: Event outcome.
        request: Current FastAPI request.
        settings: Application settings containing the privacy hash secret.
        event_metadata: Optional sanitized metadata.

    Returns:
        Persisted audit log object.

    Raises:
        ValueError: If the authenticated subject is invalid.
    """
    return await record_audit_event(
        session=session,
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        outcome=outcome,
        request=request,
        settings=settings,
        event_metadata=event_metadata,
    )


async def delete_analysis_result_for_user(
    session: AsyncSession,
    user: AuthenticatedUser,
    result_id: UUID,
    request: Request,
    settings: Settings,
) -> bool:
    """Delete one analysis result owned by the current user.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        result_id: Persisted analysis result identifier.
        request: Current FastAPI request.
        settings: Application settings containing the privacy hash secret.

    Returns:
        True when a row was deleted, False when the row was not found for this owner.

    Raises:
        ValueError: If owner identity cannot be persisted safely.
    """
    owner_subject = build_owner_subject(user)
    async with session.begin():
        record = await session.scalar(
            select(AnalysisResult).where(
                AnalysisResult.id == result_id,
                AnalysisResult.owner_subject == owner_subject,
            )
        )
        if record is None:
            session.add(
                _build_audit_log(
                    user=user,
                    action="analysis_result_deleted",
                    resource_type="analysis_result",
                    resource_id=str(result_id),
                    outcome="not_found",
                    request=request,
                    settings=settings,
                )
            )
            return False

        await session.delete(record)
        session.add(
            _build_audit_log(
                user=user,
                action="analysis_result_deleted",
                resource_type="analysis_result",
                resource_id=str(result_id),
                outcome="success",
                request=request,
                settings=settings,
            )
        )
        return True


async def create_delete_all_user_data_request(
    session: AsyncSession,
    user: AuthenticatedUser,
    request: Request,
    settings: Settings,
) -> DeletionRequest:
    """Delete current-user health, supplement, analysis, and consent rows.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        request: Current FastAPI request.
        settings: Application settings containing the privacy hash secret.

    Returns:
        Persisted deletion request record with deleted row counts.

    Raises:
        ValueError: If owner identity cannot be persisted safely.
    """
    owner_subject = build_owner_subject(user)
    owner_subject_hash = hash_actor_subject(user, settings)
    now = _utc_now()
    deletion_request = DeletionRequest(
        id=uuid4(),
        owner_subject_hash=owner_subject_hash,
        request_type=DeletionRequestType.ALL_USER_DATA.value,
        status=DeletionRequestStatus.COMPLETED.value,
        requested_at=now,
        completed_at=now,
        deleted_counts={},
        failure_reason=None,
    )

    async with session.begin():
        health_daily_summaries = list(
            (
                await session.scalars(
                    select(HealthDailySummary).where(
                        HealthDailySummary.owner_subject == owner_subject
                    )
                )
            ).all()
        )
        health_sync_batches = list(
            (
                await session.scalars(
                    select(HealthSyncBatch).where(HealthSyncBatch.owner_subject == owner_subject)
                )
            ).all()
        )
        supplement_analysis_runs = list(
            (
                await session.scalars(
                    select(SupplementAnalysisRun).where(
                        SupplementAnalysisRun.owner_subject == owner_subject
                    )
                )
            ).all()
        )
        user_supplements = list(
            (
                await session.scalars(
                    select(UserSupplement).where(UserSupplement.owner_subject == owner_subject)
                )
            ).all()
        )
        user_supplement_ids = [record.id for record in user_supplements]
        user_supplement_ingredients: list[UserSupplementIngredient] = []
        if user_supplement_ids:
            user_supplement_ingredients = list(
                (
                    await session.scalars(
                        select(UserSupplementIngredient).where(
                            UserSupplementIngredient.user_supplement_id.in_(user_supplement_ids)
                        )
                    )
                ).all()
            )
        analysis_records = list(
            (
                await session.scalars(
                    select(AnalysisResult).where(AnalysisResult.owner_subject == owner_subject)
                )
            ).all()
        )
        regulated_documents = list(
            (
                await session.scalars(
                    select(RegulatedDocument).where(
                        RegulatedDocument.owner_subject_hash == owner_subject_hash
                    )
                )
            ).all()
        )
        agent_memories = list(
            (
                await session.scalars(
                    select(AgentMemory).where(
                        AgentMemory.owner_subject_hash == owner_subject_hash
                    )
                )
            ).all()
        )
        agent_runs = list(
            (
                await session.scalars(
                    select(AgentRun).where(AgentRun.owner_subject_hash == owner_subject_hash)
                )
            ).all()
        )
        consent_records = list(
            (
                await session.scalars(
                    select(ConsentRecord).where(ConsentRecord.owner_subject == owner_subject)
                )
            ).all()
        )
        learning_deleted_counts = await delete_learning_artifacts_for_owner(
            session=session,
            owner_subject_hash=owner_subject_hash,
            object_store=build_learning_object_store(settings),
        )

        for user_supplement_ingredient in user_supplement_ingredients:
            await session.delete(user_supplement_ingredient)
        for user_supplement in user_supplements:
            await session.delete(user_supplement)
        for supplement_analysis_run in supplement_analysis_runs:
            await session.delete(supplement_analysis_run)
        for health_daily_summary in health_daily_summaries:
            await session.delete(health_daily_summary)
        for health_sync_batch in health_sync_batches:
            await session.delete(health_sync_batch)
        for analysis_record in analysis_records:
            await session.delete(analysis_record)
        for regulated_document in regulated_documents:
            await session.delete(regulated_document)
        for agent_run in agent_runs:
            await session.delete(agent_run)
        for agent_memory in agent_memories:
            await session.delete(agent_memory)
        for consent_record in consent_records:
            await session.delete(consent_record)

        deletion_request.deleted_counts = {
            "analysis_results": len(analysis_records),
            "consent_records": len(consent_records),
            "health_daily_summaries": len(health_daily_summaries),
            "health_sync_batches": len(health_sync_batches),
            "regulated_documents": len(regulated_documents),
            "agent_memory": len(agent_memories),
            "agent_runs": len(agent_runs),
            "supplement_analysis_runs": len(supplement_analysis_runs),
            "user_supplement_ingredients": len(user_supplement_ingredients),
            "user_supplements": len(user_supplements),
            **learning_deleted_counts,
        }
        session.add(deletion_request)
        session.add(
            _build_audit_log(
                user=user,
                action="user_data_deleted",
                resource_type="user_data",
                resource_id=str(deletion_request.id),
                outcome="success",
                request=request,
                settings=settings,
                event_metadata={"deleted_counts": deletion_request.deleted_counts},
            )
        )
    return deletion_request


async def get_deletion_request(
    session: AsyncSession,
    user: AuthenticatedUser,
    deletion_request_id: UUID,
    settings: Settings,
) -> DeletionRequest | None:
    """Return a deletion request owned by the current user.

    Args:
        session: Request-scoped async database session.
        user: Authenticated owner.
        deletion_request_id: Deletion request identifier.
        settings: Application settings containing the privacy hash secret.

    Returns:
        Deletion request row or None when not found for this owner.

    Raises:
        ValueError: If owner identity cannot be persisted safely.
    """
    statement = select(DeletionRequest).where(
        DeletionRequest.id == deletion_request_id,
        DeletionRequest.owner_subject_hash == hash_actor_subject(user, settings),
    )
    record: DeletionRequest | None = await session.scalar(statement)
    return record
