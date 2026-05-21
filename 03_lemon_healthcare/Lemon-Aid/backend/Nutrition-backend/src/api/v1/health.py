"""Health data API contract routes for P1 implementation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.contract import P1_6_HEALTH_SYNC_READY_STATUS, route_contract
from src.api.v1.examples import (
    CONSENT_REQUIRED_EXAMPLE,
    HEALTH_SYNC_CONFLICT_EXAMPLE,
    HEALTH_SYNC_REQUEST_EXAMPLES,
    HEALTH_SYNC_RESPONSE_EXAMPLES,
    UNAUTHORIZED_EXAMPLE,
    UNPROCESSABLE_ENTITY_EXAMPLE,
)
from src.config import Settings, get_settings
from src.db.dependencies import get_async_session
from src.models.schemas.health import HealthSyncRequest, HealthSyncResponse
from src.models.schemas.privacy import ConsentType
from src.security.auth import AuthenticatedUser, require_health_write
from src.security.scopes import ApiScope
from src.services.health_sync import (
    HealthSyncConflictError,
    health_sync_result_audit_metadata,
    health_sync_result_to_response,
)
from src.services.health_sync import (
    sync_health_daily_aggregates as sync_health_daily_aggregates_service,
)
from src.services.privacy import (
    ConsentRequiredError,
    record_sensitive_audit_event,
    require_user_consent,
)

router = APIRouter(prefix="/health", tags=["health"])


async def _require_health_device_consent(
    session: AsyncSession,
    current_user: AuthenticatedUser,
    http_request: Request,
    settings: Settings,
) -> None:
    """Require health-device-data consent before storing aggregates.

    Args:
        session: Request-scoped async database session.
        current_user: Authenticated owner.
        http_request: Current FastAPI request.
        settings: Application settings.

    Raises:
        HTTPException: If the required consent is missing.
    """
    try:
        await require_user_consent(session, current_user, ConsentType.HEALTH_DEVICE_DATA)
    except ConsentRequiredError as exc:
        await record_sensitive_audit_event(
            session,
            current_user,
            action="health_sync_blocked",
            resource_type="health_sync_batch",
            resource_id=None,
            outcome="blocked",
            request=http_request,
            settings=settings,
            event_metadata={"missing_consent": ConsentType.HEALTH_DEVICE_DATA.value},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "consent_required",
                "message": str(exc),
                "required_consents": [ConsentType.HEALTH_DEVICE_DATA.value],
            },
        ) from exc


@router.post(
    "/sync",
    response_model=HealthSyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"content": {"application/json": {"examples": HEALTH_SYNC_RESPONSE_EXAMPLES}}},
        401: {"content": {"application/json": {"examples": UNAUTHORIZED_EXAMPLE}}},
        403: {"content": {"application/json": {"examples": CONSENT_REQUIRED_EXAMPLE}}},
        409: {"content": {"application/json": {"examples": HEALTH_SYNC_CONFLICT_EXAMPLE}}},
        422: {"content": {"application/json": {"examples": UNPROCESSABLE_ENTITY_EXAMPLE}}},
    },
    openapi_extra=route_contract(
        scopes=(ApiScope.HEALTH_WRITE,),
        consents=(ConsentType.HEALTH_DEVICE_DATA,),
        contract_status=P1_6_HEALTH_SYNC_READY_STATUS,
    ),
)
async def sync_health_daily_aggregates(
    http_request: Request,
    request: Annotated[
        HealthSyncRequest,
        Body(openapi_examples=HEALTH_SYNC_REQUEST_EXAMPLES),
    ],
    current_user: Annotated[AuthenticatedUser, Depends(require_health_write)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthSyncResponse:
    """Sync current-user health aggregates from the mobile app.

    Args:
        http_request: Current FastAPI request.
        request: Daily health aggregate records.
        current_user: Authenticated owner.
        session: Request-scoped async database session.
        settings: Application settings.

    Returns:
        Health sync acceptance summary.

    Raises:
        HTTPException: If consent is missing or the client batch id conflicts.
    """
    await _require_health_device_consent(session, current_user, http_request, settings)
    try:
        result = await sync_health_daily_aggregates_service(session, current_user, request)
    except HealthSyncConflictError as exc:
        await record_sensitive_audit_event(
            session,
            current_user,
            action="health_sync_conflict",
            resource_type="health_sync_batch",
            resource_id=None,
            outcome="blocked",
            request=http_request,
            settings=settings,
            event_metadata={"client_batch_id_present": request.client_batch_id is not None},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "idempotency_conflict", "message": str(exc)},
        ) from exc

    await record_sensitive_audit_event(
        session,
        current_user,
        action="health_sync_completed",
        resource_type="health_sync_batch",
        resource_id=str(result.batch.id),
        outcome="success",
        request=http_request,
        settings=settings,
        event_metadata=health_sync_result_audit_metadata(result),
    )
    return health_sync_result_to_response(result)
