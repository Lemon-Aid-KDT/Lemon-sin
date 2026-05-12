"""Supplement API contract routes for P1 implementation."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.contract import (
    P1_2_INTAKE_READY_STATUS,
    P1_4_SUPPLEMENT_REGISTRATION_READY_STATUS,
    route_contract,
)
from src.api.v1.examples import (
    CONSENT_REQUIRED_EXAMPLE,
    INSUFFICIENT_SCOPE_EXAMPLE,
    PAYLOAD_TOO_LARGE_EXAMPLE,
    SUPPLEMENT_ANALYSIS_RESPONSE_EXAMPLES,
    SUPPLEMENT_CREATE_REQUEST_EXAMPLES,
    TOO_MANY_REQUESTS_EXAMPLE,
    UNAUTHORIZED_EXAMPLE,
    UNPROCESSABLE_ENTITY_EXAMPLE,
    UNSUPPORTED_MEDIA_TYPE_EXAMPLE,
    USER_SUPPLEMENT_LIST_RESPONSE_EXAMPLES,
    USER_SUPPLEMENT_RESPONSE_EXAMPLES,
)
from src.config import Settings, get_settings
from src.db.dependencies import get_async_session
from src.models.schemas.privacy import ConsentType
from src.models.schemas.supplement import (
    SupplementAnalysisPreview,
    UserSupplementCreate,
    UserSupplementListResponse,
    UserSupplementResponse,
)
from src.security.auth import (
    AuthenticatedUser,
    require_supplement_delete,
    require_supplement_read,
    require_supplement_write,
)
from src.security.scopes import ApiScope
from src.services.privacy import (
    ConsentRequiredError,
    record_sensitive_audit_event,
    require_user_consent,
)
from src.services.supplement_intake import (
    SupplementImageValidationError,
    SupplementIntakeConflictError,
    create_supplement_analysis_intake,
    read_and_validate_supplement_image,
    supplement_analysis_run_to_preview,
)
from src.services.supplement_registration import (
    SupplementPreviewExpiredError,
    SupplementPreviewNotFoundError,
    SupplementPreviewStateError,
    SupplementRegistrationValidationError,
    create_user_supplement_from_confirmation,
    get_user_supplement_record,
    list_user_supplement_records,
    soft_delete_user_supplement,
    user_supplement_to_response,
)

router = APIRouter(prefix="/supplements", tags=["supplements"])

__all__ = ["router", "user_supplement_to_response"]

SUPPLEMENT_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"content": {"application/json": {"examples": UNAUTHORIZED_EXAMPLE}}},
    403: {"content": {"application/json": {"examples": INSUFFICIENT_SCOPE_EXAMPLE}}},
    422: {"content": {"application/json": {"examples": UNPROCESSABLE_ENTITY_EXAMPLE}}},
}

COMMON_SUPPLEMENT_RESPONSES: dict[int | str, dict[str, Any]] = {
    **SUPPLEMENT_AUTH_RESPONSES,
}


def _supplement_http_error(status_code: int, *, code: str, message: str) -> HTTPException:
    """Build a stable supplement API error response.

    Args:
        status_code: HTTP status code.
        code: Stable application error code.
        message: Safe user-facing message.

    Returns:
        FastAPI HTTP exception.
    """
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


async def _require_sensitive_health_consent(
    session: AsyncSession,
    current_user: AuthenticatedUser,
    http_request: Request,
    settings: Settings,
) -> None:
    """Require sensitive-health consent for confirmed supplement storage.

    Args:
        session: Request-scoped async database session.
        current_user: Authenticated owner.
        http_request: Current FastAPI request.
        settings: Application settings.

    Raises:
        HTTPException: If the required consent is missing.
    """
    try:
        await require_user_consent(session, current_user, ConsentType.SENSITIVE_HEALTH_ANALYSIS)
    except ConsentRequiredError as exc:
        await record_sensitive_audit_event(
            session,
            current_user,
            action="supplement_registration_blocked",
            resource_type="user_supplement",
            resource_id=None,
            outcome="blocked",
            request=http_request,
            settings=settings,
            event_metadata={"missing_consent": ConsentType.SENSITIVE_HEALTH_ANALYSIS.value},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "consent_required",
                "message": str(exc),
                "required_consents": [ConsentType.SENSITIVE_HEALTH_ANALYSIS.value],
            },
        ) from exc


@router.post(
    "/analyze",
    response_model=SupplementAnalysisPreview,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        **SUPPLEMENT_AUTH_RESPONSES,
        202: {"content": {"application/json": {"examples": SUPPLEMENT_ANALYSIS_RESPONSE_EXAMPLES}}},
        413: {"content": {"application/json": {"examples": PAYLOAD_TOO_LARGE_EXAMPLE}}},
        409: {
            "description": "client_request_id was already used for different image bytes.",
        },
        415: {"content": {"application/json": {"examples": UNSUPPORTED_MEDIA_TYPE_EXAMPLE}}},
        429: {"content": {"application/json": {"examples": TOO_MANY_REQUESTS_EXAMPLE}}},
    },
    openapi_extra=route_contract(
        scopes=(ApiScope.SUPPLEMENT_WRITE,),
        consents=(ConsentType.OCR_IMAGE_PROCESSING,),
        contract_status=P1_2_INTAKE_READY_STATUS,
    ),
)
async def analyze_supplement_label(
    http_request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(require_supplement_write)],
    image: Annotated[UploadFile, File(description="Supplement label image file.")],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    client_request_id: Annotated[str | None, Form(max_length=80)] = None,
) -> SupplementAnalysisPreview:
    """Create a supplement label preview that must be confirmed by the user.

    Args:
        http_request: Current FastAPI request.
        current_user: Authenticated owner.
        image: Uploaded supplement label image.
        session: Request-scoped async database session.
        settings: Application settings.
        client_request_id: Optional idempotency key generated by the client.

    Returns:
        Supplement parsing preview.

    Raises:
        HTTPException: If consent is missing, image validation fails, or idempotency conflicts.
    """
    try:
        await require_user_consent(session, current_user, ConsentType.OCR_IMAGE_PROCESSING)
    except ConsentRequiredError as exc:
        await record_sensitive_audit_event(
            session,
            current_user,
            action="supplement_image_intake_blocked",
            resource_type="supplement_analysis_run",
            resource_id=None,
            outcome="blocked",
            request=http_request,
            settings=settings,
            event_metadata={"missing_consent": ConsentType.OCR_IMAGE_PROCESSING.value},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "consent_required",
                "message": str(exc),
                "required_consents": [ConsentType.OCR_IMAGE_PROCESSING.value],
            },
        ) from exc

    try:
        image_metadata = await read_and_validate_supplement_image(image, settings)
    except SupplementImageValidationError as exc:
        await record_sensitive_audit_event(
            session,
            current_user,
            action="supplement_image_intake_rejected",
            resource_type="supplement_analysis_run",
            resource_id=None,
            outcome="blocked",
            request=http_request,
            settings=settings,
            event_metadata={"validation_code": exc.code},
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    try:
        result = await create_supplement_analysis_intake(
            session,
            current_user,
            image_metadata,
            client_request_id,
            settings,
        )
    except SupplementIntakeConflictError as exc:
        await record_sensitive_audit_event(
            session,
            current_user,
            action="supplement_image_intake_conflict",
            resource_type="supplement_analysis_run",
            resource_id=None,
            outcome="blocked",
            request=http_request,
            settings=settings,
            event_metadata={"client_request_id_present": bool(client_request_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "idempotency_conflict",
                "message": str(exc),
            },
        ) from exc

    await record_sensitive_audit_event(
        session,
        current_user,
        action=(
            "supplement_image_intake_reused"
            if result.reused_existing
            else "supplement_image_intake_created"
        ),
        resource_type="supplement_analysis_run",
        resource_id=str(result.record.id),
        outcome="success",
        request=http_request,
        settings=settings,
        event_metadata={
            "client_request_id_present": bool(client_request_id),
            "image_mime_type": image_metadata.mime_type,
            "image_size_bytes": image_metadata.size_bytes,
            "reused_existing": result.reused_existing,
        },
    )
    return supplement_analysis_run_to_preview(result.record)


@router.post(
    "",
    response_model=UserSupplementResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        **COMMON_SUPPLEMENT_RESPONSES,
        201: {"content": {"application/json": {"examples": USER_SUPPLEMENT_RESPONSE_EXAMPLES}}},
        403: {"content": {"application/json": {"examples": CONSENT_REQUIRED_EXAMPLE}}},
    },
    openapi_extra=route_contract(
        scopes=(ApiScope.SUPPLEMENT_WRITE,),
        consents=(ConsentType.SENSITIVE_HEALTH_ANALYSIS,),
        contract_status=P1_4_SUPPLEMENT_REGISTRATION_READY_STATUS,
    ),
)
async def create_user_supplement(
    http_request: Request,
    request: Annotated[
        UserSupplementCreate,
        Body(openapi_examples=SUPPLEMENT_CREATE_REQUEST_EXAMPLES),
    ],
    current_user: Annotated[AuthenticatedUser, Depends(require_supplement_write)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserSupplementResponse:
    """Store a user-confirmed supplement record.

    Args:
        http_request: Current FastAPI request.
        request: User-confirmed supplement data.
        session: Request-scoped async database session.
        current_user: Authenticated owner.
        settings: Application settings.

    Returns:
        Persisted supplement response.

    Raises:
        HTTPException: If consent is missing, preview state is invalid, or payload is invalid.
    """
    await _require_sensitive_health_consent(session, current_user, http_request, settings)
    try:
        result = await create_user_supplement_from_confirmation(session, current_user, request)
    except SupplementRegistrationValidationError as exc:
        raise _supplement_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="invalid_supplement_confirmation",
            message=str(exc),
        ) from exc
    except SupplementPreviewNotFoundError as exc:
        raise _supplement_http_error(
            status.HTTP_404_NOT_FOUND,
            code="supplement_analysis_not_found",
            message=str(exc),
        ) from exc
    except (SupplementPreviewExpiredError, SupplementPreviewStateError) as exc:
        raise _supplement_http_error(
            status.HTTP_409_CONFLICT,
            code="supplement_analysis_not_confirmable",
            message=str(exc),
        ) from exc

    await record_sensitive_audit_event(
        session,
        current_user,
        action="supplement_registered",
        resource_type="user_supplement",
        resource_id=str(result.supplement.id),
        outcome="success",
        request=http_request,
        settings=settings,
        event_metadata={
            "analysis_id_present": request.analysis_id is not None,
            "ingredient_count": len(result.ingredients),
            "matched_product_id_present": result.supplement.matched_product_id is not None,
        },
    )
    return user_supplement_to_response(result.supplement, result.ingredients)


@router.get(
    "",
    response_model=UserSupplementListResponse,
    responses={
        **COMMON_SUPPLEMENT_RESPONSES,
        200: {
            "content": {"application/json": {"examples": USER_SUPPLEMENT_LIST_RESPONSE_EXAMPLES}}
        },
    },
    openapi_extra=route_contract(
        scopes=(ApiScope.SUPPLEMENT_READ,),
        contract_status=P1_4_SUPPLEMENT_REGISTRATION_READY_STATUS,
    ),
)
async def list_user_supplements(
    http_request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(require_supplement_read)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UserSupplementListResponse:
    """List supplement records owned by the current user.

    Args:
        http_request: Current FastAPI request.
        session: Request-scoped async database session.
        current_user: Authenticated owner.
        settings: Application settings.
        limit: Maximum result count.
        offset: Result offset.

    Returns:
        Paginated supplement list.

    Raises:
        HTTPException: If owner identity cannot be persisted safely.
    """
    try:
        response = await list_user_supplement_records(session, current_user, limit, offset)
    except ValueError as exc:
        raise _supplement_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="invalid_supplement_query",
            message=str(exc),
        ) from exc
    await record_sensitive_audit_event(
        session,
        current_user,
        action="supplement_listed",
        resource_type="user_supplement",
        resource_id=None,
        outcome="success",
        request=http_request,
        settings=settings,
        event_metadata={"count": len(response.results), "limit": limit, "offset": offset},
    )
    return response


@router.get(
    "/{supplement_id}",
    response_model=UserSupplementResponse,
    responses={
        **COMMON_SUPPLEMENT_RESPONSES,
        200: {"content": {"application/json": {"examples": USER_SUPPLEMENT_RESPONSE_EXAMPLES}}},
    },
    openapi_extra=route_contract(
        scopes=(ApiScope.SUPPLEMENT_READ,),
        contract_status=P1_4_SUPPLEMENT_REGISTRATION_READY_STATUS,
    ),
)
async def get_user_supplement(
    supplement_id: UUID,
    http_request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(require_supplement_read)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserSupplementResponse:
    """Return one supplement record owned by the current user.

    Args:
        supplement_id: Persisted supplement identifier.
        http_request: Current FastAPI request.
        session: Request-scoped async database session.
        current_user: Authenticated owner.
        settings: Application settings.

    Returns:
        Supplement detail response.

    Raises:
        HTTPException: If the supplement does not exist for this owner.
    """
    result = await get_user_supplement_record(session, current_user, supplement_id)
    if result is None:
        await record_sensitive_audit_event(
            session,
            current_user,
            action="supplement_read",
            resource_type="user_supplement",
            resource_id=str(supplement_id),
            outcome="not_found",
            request=http_request,
            settings=settings,
        )
        raise _supplement_http_error(
            status.HTTP_404_NOT_FOUND,
            code="supplement_not_found",
            message="Supplement record was not found.",
        )
    await record_sensitive_audit_event(
        session,
        current_user,
        action="supplement_read",
        resource_type="user_supplement",
        resource_id=str(supplement_id),
        outcome="success",
        request=http_request,
        settings=settings,
    )
    return user_supplement_to_response(result.supplement, result.ingredients)


@router.delete(
    "/{supplement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=COMMON_SUPPLEMENT_RESPONSES,
    openapi_extra=route_contract(
        scopes=(ApiScope.SUPPLEMENT_DELETE,),
        contract_status=P1_4_SUPPLEMENT_REGISTRATION_READY_STATUS,
    ),
)
async def delete_user_supplement(
    supplement_id: UUID,
    http_request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(require_supplement_delete)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Delete one supplement record owned by the current user.

    Args:
        supplement_id: Persisted supplement identifier.
        http_request: Current FastAPI request.
        session: Request-scoped async database session.
        current_user: Authenticated owner.
        settings: Application settings.

    Returns:
        Empty response after deletion.

    Raises:
        HTTPException: If the supplement does not exist for this owner.
    """
    deleted = await soft_delete_user_supplement(session, current_user, supplement_id)
    if not deleted:
        await record_sensitive_audit_event(
            session,
            current_user,
            action="supplement_delete",
            resource_type="user_supplement",
            resource_id=str(supplement_id),
            outcome="not_found",
            request=http_request,
            settings=settings,
        )
        raise _supplement_http_error(
            status.HTTP_404_NOT_FOUND,
            code="supplement_not_found",
            message="Supplement record was not found.",
        )
    await record_sensitive_audit_event(
        session,
        current_user,
        action="supplement_delete",
        resource_type="user_supplement",
        resource_id=str(supplement_id),
        outcome="success",
        request=http_request,
        settings=settings,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
