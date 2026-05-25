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
    P1_7_SUPPLEMENT_RECOMMENDATION_READY_STATUS,
    route_contract,
)
from src.api.v1.examples import (
    CONSENT_REQUIRED_EXAMPLE,
    INSUFFICIENT_SCOPE_EXAMPLE,
    PAYLOAD_TOO_LARGE_EXAMPLE,
    SUPPLEMENT_ANALYSIS_RESPONSE_EXAMPLES,
    SUPPLEMENT_CREATE_REQUEST_EXAMPLES,
    SUPPLEMENT_IMPACT_PREVIEW_RESPONSE_EXAMPLES,
    SUPPLEMENT_RECOMMENDATION_EXPLAIN_REQUEST_EXAMPLES,
    SUPPLEMENT_RECOMMENDATION_EXPLAIN_RESPONSE_EXAMPLES,
    TOO_MANY_REQUESTS_EXAMPLE,
    UNAUTHORIZED_EXAMPLE,
    UNPROCESSABLE_ENTITY_EXAMPLE,
    UNSUPPORTED_MEDIA_TYPE_EXAMPLE,
    USER_SUPPLEMENT_LIST_RESPONSE_EXAMPLES,
    USER_SUPPLEMENT_RESPONSE_EXAMPLES,
)
from src.config import Settings, get_settings
from src.db.dependencies import get_async_session
from src.learning.factory import build_learning_object_store
from src.learning.pipeline import (
    build_confirmed_supplement_learning_metadata,
    collect_active_learning_consents,
    enqueue_learning_embedding_job_for_confirmation,
)
from src.llm.ollama import (
    OllamaClientError,
    OllamaConfigurationError,
    OllamaStructuredOutputError,
)
from src.models.schemas.privacy import ConsentType
from src.models.schemas.supplement import (
    SupplementAnalysisPreview,
    SupplementBarcodeLookupRequest,
    SupplementBarcodeLookupResponse,
    UserSupplementCreate,
    UserSupplementListResponse,
    UserSupplementResponse,
)
from src.models.schemas.supplement_comprehensive import (
    ComprehensiveAnalysisRequest,
    SupplementComprehensiveAnalysis,
)
from src.models.schemas.supplement_parser import SupplementOCRTextParseRequest
from src.models.schemas.supplement_recommendation import (
    SupplementImpactPreviewRequest,
    SupplementImpactPreviewResponse,
    SupplementRecommendationExplainRequest,
    SupplementRecommendationExplainResponse,
)
from src.nutrition.comprehensive import compute_comprehensive
from src.ocr.factory import (
    OCRConfigurationError,
    SupplementOCRProviderSelector,
    build_supplement_image_analysis_adapters,
    build_supplement_image_analysis_adapters_for_provider,
    is_external_ocr_pipeline_enabled,
)
from src.security.auth import (
    AuthenticatedUser,
    require_scopes,
    require_supplement_delete,
    require_supplement_read,
    require_supplement_write,
)
from src.security.scopes import ApiScope
from src.services.privacy import (
    AuditOutcome,
    ConsentRequiredError,
    record_sensitive_audit_event,
    require_user_consent,
)
from src.services.supplement_barcode_lookup import (
    BarcodeLookupServiceResult,
    SupplementBarcodeLookupService,
    attach_barcode_lookup_to_analysis,
    barcode_lookup_result_to_response,
    build_supplement_barcode_lookup_service,
)
from src.services.supplement_explanation import (
    SupplementExplanationError,
    explain_supplement_recommendation,
)
from src.services.supplement_image_analysis import (
    SupplementImageAnalysisAdapters,
    analyze_supplement_image,
)
from src.services.supplement_intake import (
    SupplementImageValidationError,
    SupplementIntakeConflictError,
    supplement_analysis_run_to_preview,
)
from src.services.supplement_parser import (
    SupplementAnalysisExpiredError,
    SupplementAnalysisNotFoundError,
    SupplementAnalysisStateError,
    SupplementParserConflictError,
    SupplementParserInputError,
    parse_supplement_analysis_ocr_text,
)
from src.services.supplement_recommendation import build_supplement_impact_preview
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

require_supplement_recommendation_read = require_scopes(
    ApiScope.SUPPLEMENT_READ,
    ApiScope.ANALYSIS_READ,
)


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


def get_supplement_image_analysis_adapters(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SupplementImageAnalysisAdapters:
    """Build supplement image analysis adapters for the current settings.

    Args:
        settings: Application settings.

    Returns:
        Image analysis adapters.

    Raises:
        HTTPException: If OCR provider settings are incomplete or unsafe.
    """
    try:
        return build_supplement_image_analysis_adapters(settings)
    except OCRConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "ocr_provider_unconfigured",
                "message": str(exc),
            },
        ) from exc


def get_supplement_barcode_lookup_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SupplementBarcodeLookupService:
    """Build the barcode lookup service for the current settings.

    Args:
        settings: Application settings.

    Returns:
        Barcode lookup service.
    """

    return build_supplement_barcode_lookup_service(settings)


def _required_supplement_analyze_consents(
    settings: Settings,
    ocr_provider: SupplementOCRProviderSelector = "configured",
) -> tuple[ConsentType, ...]:
    """Return consent buckets required for supplement image analysis.

    Args:
        settings: Application settings.
        ocr_provider: Request-selected OCR provider.

    Returns:
        Consent buckets required by the active OCR path.
    """
    consents = [ConsentType.OCR_IMAGE_PROCESSING]
    if is_external_ocr_pipeline_enabled(settings, ocr_provider):
        consents.append(ConsentType.EXTERNAL_OCR_PROCESSING)
    return tuple(consents)


def _select_supplement_image_analysis_adapters(
    *,
    settings: Settings,
    configured_adapters: SupplementImageAnalysisAdapters,
    ocr_provider: SupplementOCRProviderSelector,
) -> SupplementImageAnalysisAdapters:
    """Return an adapter bundle constrained to the request-selected provider.

    Args:
        settings: Application settings.
        configured_adapters: Default adapters built by dependency injection.
        ocr_provider: Provider selector submitted with the multipart request.

    Returns:
        Adapter bundle for this request.

    Raises:
        HTTPException: If the requested provider cannot be configured.
    """
    try:
        return build_supplement_image_analysis_adapters_for_provider(
            settings,
            ocr_provider,
            configured_adapters=configured_adapters,
        )
    except OCRConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "ocr_provider_unconfigured",
                "message": str(exc),
                "requested_ocr_provider": ocr_provider,
            },
        ) from exc


def _ocr_provider_warning_codes(codes: tuple[str, ...]) -> list[str]:
    """Return warning codes that indicate OCR/provider/parser failure.

    Args:
        codes: Warning codes produced by the image analysis service.

    Returns:
        Warning codes excluding image-quality review hints.
    """
    return [code for code in codes if not code.startswith("image_quality:")]


async def _commit_consent_read_transaction(session: AsyncSession) -> None:
    """Close an implicit consent-read transaction before service-level writes.

    Args:
        session: Request-scoped async database session.
    """
    in_transaction = getattr(session, "in_transaction", None)
    if callable(in_transaction) and in_transaction():
        await session.commit()


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
        conditional_consents=(ConsentType.EXTERNAL_OCR_PROCESSING,),
        contract_status=P1_2_INTAKE_READY_STATUS,
    ),
)
async def analyze_supplement_label(
    http_request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(require_supplement_write)],
    image: Annotated[UploadFile, File(description="Supplement label image file.")],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    adapters: Annotated[
        SupplementImageAnalysisAdapters,
        Depends(get_supplement_image_analysis_adapters),
    ],
    barcode_service: Annotated[
        SupplementBarcodeLookupService,
        Depends(get_supplement_barcode_lookup_service),
    ],
    client_request_id: Annotated[str | None, Form(max_length=80)] = None,
    ocr_provider: Annotated[SupplementOCRProviderSelector, Form()] = "configured",
    barcode_text: Annotated[str | None, Form(max_length=256)] = None,
    barcode_format: Annotated[str | None, Form(max_length=40)] = None,
) -> SupplementAnalysisPreview:
    """Create a supplement label preview that must be confirmed by the user.

    Args:
        http_request: Current FastAPI request.
        current_user: Authenticated owner.
        image: Uploaded supplement label image.
        session: Request-scoped async database session.
        settings: Application settings.
        client_request_id: Optional idempotency key generated by the client.
        ocr_provider: Request-level OCR provider selector for comparison testing.
        barcode_text: Optional mobile-scanned barcode text.
        barcode_format: Optional mobile scanner format label.

    Returns:
        Supplement parsing preview.

    Raises:
        HTTPException: If consent is missing, image validation fails, or idempotency conflicts.
    """
    selected_adapters = _select_supplement_image_analysis_adapters(
        settings=settings,
        configured_adapters=adapters,
        ocr_provider=ocr_provider,
    )
    required_consents = _required_supplement_analyze_consents(settings, ocr_provider)
    missing_consents: list[ConsentType] = []
    last_consent_error: ConsentRequiredError | None = None
    for consent_type in required_consents:
        try:
            await require_user_consent(session, current_user, consent_type)
        except ConsentRequiredError as exc:
            missing_consents.append(consent_type)
            last_consent_error = exc

    await _commit_consent_read_transaction(session)

    if missing_consents:
        missing_values = [consent.value for consent in missing_consents]
        await record_sensitive_audit_event(
            session,
            current_user,
            action=(
                "supplement_external_ocr_blocked"
                if ConsentType.EXTERNAL_OCR_PROCESSING in missing_consents
                else "supplement_image_intake_blocked"
            ),
            resource_type="supplement_analysis_run",
            resource_id=None,
            outcome="blocked",
            request=http_request,
            settings=settings,
            event_metadata={"missing_consents": missing_values},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "consent_required",
                "message": str(last_consent_error),
                "required_consents": missing_values,
            },
        ) from last_consent_error

    try:
        learning_consents = await _collect_learning_consents_if_enabled(
            session,
            current_user,
            settings,
        )
        await _commit_consent_read_transaction(session)
        result = await analyze_supplement_image(
            session=session,
            user=current_user,
            image=image,
            client_request_id=client_request_id,
            settings=settings,
            adapters=selected_adapters,
            learning_consents=learning_consents,
            learning_object_store=build_learning_object_store(settings),
        )
        barcode_lookup_result: BarcodeLookupServiceResult | None = None
        if barcode_text and barcode_text.strip():
            barcode_lookup_result = await barcode_service.lookup(
                barcode_text,
                barcode_format=barcode_format,
            )
            result_record = await attach_barcode_lookup_to_analysis(
                session,
                result.record,
                barcode_lookup_result,
            )
        else:
            result_record = result.record
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

    if result.ocr_attempted:
        provider_warning_codes = _ocr_provider_warning_codes(result.ocr_warning_codes)
        await record_sensitive_audit_event(
            session,
            current_user,
            action=(
                "supplement_ocr_provider_failed"
                if provider_warning_codes
                else "supplement_ocr_provider_completed"
            ),
            resource_type="supplement_analysis_run",
            resource_id=str(result.record.id),
            outcome="failed" if provider_warning_codes else "success",
            request=http_request,
            settings=settings,
            event_metadata={
                "ocr_provider": result.ocr_result.provider if result.ocr_result else None,
                "ocr_confidence_present": (
                    result.ocr_result.confidence is not None if result.ocr_result else False
                ),
                "warning_codes": provider_warning_codes,
                "raw_image_stored": False,
                "raw_ocr_text_stored": False,
            },
        )

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
            "image_mime_type": result.image_metadata.mime_type,
            "image_size_bytes": result.image_metadata.size_bytes,
            "reused_existing": result.reused_existing,
            "ocr_provider": result.ocr_result.provider if result.ocr_result else None,
            "parser_used": result.parser_used,
            "vision_roi_used": result.vision_region is not None,
            "image_quality_status": (
                result.image_quality_report.status if result.image_quality_report else None
            ),
            "image_quality_retake_reasons": (
                list(result.image_quality_report.retake_reasons)
                if result.image_quality_report
                else []
            ),
            "learning_image_object_created": result.learning_image_object_created,
            "barcode_text_present": bool(barcode_text and barcode_text.strip()),
            "barcode_lookup_status": (
                barcode_lookup_result.status if barcode_lookup_result is not None else None
            ),
        },
    )
    return supplement_analysis_run_to_preview(result_record)


@router.post(
    "/barcode/lookup",
    response_model=SupplementBarcodeLookupResponse,
    status_code=status.HTTP_200_OK,
    responses={
        **SUPPLEMENT_AUTH_RESPONSES,
        200: {"description": "Review-only official barcode lookup result."},
        422: {"content": {"application/json": {"examples": UNPROCESSABLE_ENTITY_EXAMPLE}}},
    },
    openapi_extra=route_contract(
        scopes=(ApiScope.SUPPLEMENT_WRITE,),
        contract_status=P1_2_INTAKE_READY_STATUS,
    ),
)
async def lookup_supplement_barcode(
    http_request: Request,
    request: Annotated[SupplementBarcodeLookupRequest, Body()],
    current_user: Annotated[AuthenticatedUser, Depends(require_supplement_write)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    barcode_service: Annotated[
        SupplementBarcodeLookupService,
        Depends(get_supplement_barcode_lookup_service),
    ],
) -> SupplementBarcodeLookupResponse:
    """Look up review-only official product candidates by barcode.

    Args:
        http_request: Current FastAPI request.
        request: Barcode lookup request.
        current_user: Authenticated owner.
        session: Request-scoped async database session.
        settings: Application settings.
        barcode_service: Barcode lookup service.

    Returns:
        Barcode lookup response requiring user confirmation.

    Raises:
        HTTPException: If the barcode value is syntactically invalid.
    """

    result = await barcode_service.lookup(
        request.barcode_text,
        barcode_format=request.barcode_format,
    )
    response = barcode_lookup_result_to_response(result)
    await _record_barcode_lookup_audit(
        session,
        current_user,
        http_request,
        settings,
        response,
    )
    if result.status == "invalid_request":
        raise _supplement_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            code=result.error_code or "invalid_barcode",
            message=result.error_message or "Barcode value is invalid.",
        )
    return response


async def _record_barcode_lookup_audit(
    session: AsyncSession,
    current_user: AuthenticatedUser,
    http_request: Request,
    settings: Settings,
    response: SupplementBarcodeLookupResponse,
) -> None:
    """Record sanitized barcode lookup audit metadata.

    Args:
        session: Request-scoped async database session.
        current_user: Authenticated actor.
        http_request: Current FastAPI request.
        settings: Application settings.
        response: Barcode lookup response. Raw barcode values are not logged.

    Returns:
        None.
    """

    outcome: AuditOutcome = "success"
    if response.status == "invalid_request":
        outcome = "blocked"
    elif response.status == "provider_error":
        outcome = "failed"
    await record_sensitive_audit_event(
        session,
        current_user,
        action="supplement_barcode_lookup",
        resource_type="supplement_barcode",
        resource_id=None,
        outcome=outcome,
        request=http_request,
        settings=settings,
        event_metadata={
            "lookup_status": response.status,
            "barcode_hash": response.barcode_hash,
            "barcode_format": response.barcode_format,
            "barcode_symbology": response.barcode_symbology,
            "candidate_count": response.candidate_count,
            "provider_observations": [
                observation.model_dump(mode="json")
                for observation in response.provider_observations
            ],
            "raw_barcode_stored": False,
            "raw_provider_payload_stored": False,
            "auto_confirmed": False,
        },
    )


@router.post(
    "/analyses/{analysis_id}/ocr-text",
    response_model=SupplementAnalysisPreview,
    status_code=status.HTTP_200_OK,
    responses={
        **SUPPLEMENT_AUTH_RESPONSES,
        200: {"description": "Structured OCR text preview requiring user confirmation."},
        403: {"content": {"application/json": {"examples": CONSENT_REQUIRED_EXAMPLE}}},
        404: {"description": "Supplement analysis preview was not found for the current user."},
        409: {"description": "Supplement analysis preview is expired or not parseable."},
        502: {"description": "Local structured parser failed or returned invalid content."},
    },
    openapi_extra=route_contract(
        scopes=(ApiScope.SUPPLEMENT_WRITE,),
        consents=(ConsentType.OCR_IMAGE_PROCESSING,),
        contract_status=P1_2_INTAKE_READY_STATUS,
    ),
)
async def parse_supplement_analysis_ocr_text_preview(
    analysis_id: UUID,
    http_request: Request,
    request: Annotated[SupplementOCRTextParseRequest, Body()],
    current_user: Annotated[AuthenticatedUser, Depends(require_supplement_write)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SupplementAnalysisPreview:
    """Attach OCR text to an existing preview and return structured parse candidates.

    Args:
        analysis_id: Existing supplement analysis preview identifier.
        http_request: Current FastAPI request.
        request: OCR text and provider metadata. Raw OCR text is never persisted.
        current_user: Authenticated owner.
        session: Request-scoped async database session.
        settings: Application settings.

    Returns:
        Updated supplement preview that still requires user confirmation.

    Raises:
        HTTPException: If consent is missing, the preview is unavailable, OCR text
            is invalid, or the local parser cannot produce schema-valid output.
    """
    try:
        await require_user_consent(session, current_user, ConsentType.OCR_IMAGE_PROCESSING)
    except ConsentRequiredError as exc:
        await record_sensitive_audit_event(
            session,
            current_user,
            action="supplement_ocr_text_parse_blocked",
            resource_type="supplement_analysis_run",
            resource_id=str(analysis_id),
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
        result = await parse_supplement_analysis_ocr_text(
            session=session,
            user=current_user,
            analysis_id=analysis_id,
            ocr_text=request.ocr_text,
            ocr_provider=request.ocr_provider,
            ocr_confidence=request.ocr_confidence,
            settings=settings,
        )
    except SupplementParserInputError as exc:
        await _record_ocr_text_parse_audit(
            session,
            current_user,
            http_request,
            settings,
            analysis_id,
            outcome="blocked",
            reason="invalid_ocr_text",
            request=request,
        )
        raise _supplement_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="invalid_ocr_text",
            message=str(exc),
        ) from exc
    except SupplementAnalysisNotFoundError as exc:
        await _record_ocr_text_parse_audit(
            session,
            current_user,
            http_request,
            settings,
            analysis_id,
            outcome="not_found",
            reason="analysis_not_found",
            request=request,
        )
        raise _supplement_http_error(
            status.HTTP_404_NOT_FOUND,
            code="supplement_analysis_not_found",
            message=str(exc),
        ) from exc
    except (
        SupplementAnalysisExpiredError,
        SupplementAnalysisStateError,
        SupplementParserConflictError,
    ) as exc:
        await _record_ocr_text_parse_audit(
            session,
            current_user,
            http_request,
            settings,
            analysis_id,
            outcome="blocked",
            reason="analysis_not_parseable",
            request=request,
        )
        raise _supplement_http_error(
            status.HTTP_409_CONFLICT,
            code="supplement_analysis_not_parseable",
            message=str(exc),
        ) from exc
    except (OllamaClientError, OllamaConfigurationError) as exc:
        await _record_ocr_text_parse_audit(
            session,
            current_user,
            http_request,
            settings,
            analysis_id,
            outcome="failed",
            reason="parser_unavailable",
            request=request,
        )
        raise _supplement_http_error(
            status.HTTP_502_BAD_GATEWAY,
            code="parser_unavailable",
            message="Local supplement parser is unavailable.",
        ) from exc
    except OllamaStructuredOutputError as exc:
        await _record_ocr_text_parse_audit(
            session,
            current_user,
            http_request,
            settings,
            analysis_id,
            outcome="failed",
            reason="parser_schema_invalid",
            request=request,
        )
        raise _supplement_http_error(
            status.HTTP_502_BAD_GATEWAY,
            code="parser_schema_invalid",
            message="Local supplement parser returned invalid structured output.",
        ) from exc

    await record_sensitive_audit_event(
        session,
        current_user,
        action="supplement_ocr_text_parsed",
        resource_type="supplement_analysis_run",
        resource_id=str(result.record.id),
        outcome="success",
        request=http_request,
        settings=settings,
        event_metadata={
            "ocr_provider": result.record.ocr_provider,
            "ocr_confidence_present": result.record.ocr_confidence is not None,
            "parser_provider": settings.llm_provider,
            "parser_model": settings.ollama_model,
            "parser_schema": "SupplementStructuredParseResultV2",
            "schema_valid": True,
            "ingredient_count": len(result.parse_result.ingredient_candidates),
            "low_confidence_field_count": len(
                result.record.parsed_snapshot.get("low_confidence_fields", [])
            ),
            "raw_ocr_text_stored": False,
            "raw_llm_response_stored": False,
        },
    )
    return supplement_analysis_run_to_preview(result.record)


async def _record_ocr_text_parse_audit(
    session: AsyncSession,
    current_user: AuthenticatedUser,
    http_request: Request,
    settings: Settings,
    analysis_id: UUID,
    *,
    outcome: AuditOutcome,
    reason: str,
    request: SupplementOCRTextParseRequest,
) -> None:
    """Record a sanitized OCR text parsing audit event.

    Args:
        session: Request-scoped async database session.
        current_user: Authenticated actor.
        http_request: Current FastAPI request.
        settings: Application settings.
        analysis_id: Supplement analysis preview identifier.
        outcome: Sanitized audit outcome.
        reason: Stable failure reason.
        request: OCR text parse request. Raw OCR text is intentionally not logged.

    Returns:
        None.
    """
    await record_sensitive_audit_event(
        session,
        current_user,
        action="supplement_ocr_text_parse_failed",
        resource_type="supplement_analysis_run",
        resource_id=str(analysis_id),
        outcome=outcome,
        request=http_request,
        settings=settings,
        event_metadata={
            "reason": reason,
            "ocr_provider": request.ocr_provider,
            "ocr_confidence_present": request.ocr_confidence is not None,
            "parser_provider": settings.llm_provider,
            "parser_model": settings.ollama_model,
            "parser_schema": "SupplementStructuredParseResultV2",
            "schema_valid": False if reason == "parser_schema_invalid" else None,
            "raw_ocr_text_stored": False,
            "raw_llm_response_stored": False,
        },
    )


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
        result = await create_user_supplement_from_confirmation(
            session,
            current_user,
            request,
            settings,
        )
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

    learning_consents = await _collect_learning_consents_if_enabled(
        session,
        current_user,
        settings,
    )
    learning_job = await enqueue_learning_embedding_job_for_confirmation(
        session=session,
        user=current_user,
        analysis_id=result.supplement.source_analysis_run_id,
        metadata_snapshot=build_confirmed_supplement_learning_metadata(
            result.supplement,
            result.ingredients,
        ),
        settings=settings,
        granted_consents=learning_consents,
    )

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
            "learning_embedding_job_enqueued": learning_job is not None,
        },
    )
    return user_supplement_to_response(result.supplement, result.ingredients)


async def _collect_learning_consents_if_enabled(
    session: AsyncSession,
    current_user: AuthenticatedUser,
    settings: Settings,
) -> tuple[ConsentType, ...]:
    """Collect learning consents only when learning flags can use them.

    Args:
        session: Request-scoped async database session.
        current_user: Authenticated owner.
        settings: Runtime settings.

    Returns:
        Active learning consents, or an empty tuple when learning is disabled.
    """
    if not settings.enable_image_learning_pipeline and not settings.enable_pgvector_storage:
        return ()
    return await collect_active_learning_consents(session, current_user)


@router.get(
    "/recommendations/latest",
    response_model=SupplementImpactPreviewResponse,
    responses={
        **SUPPLEMENT_AUTH_RESPONSES,
        200: {
            "content": {
                "application/json": {"examples": SUPPLEMENT_IMPACT_PREVIEW_RESPONSE_EXAMPLES}
            }
        },
        403: {"content": {"application/json": {"examples": CONSENT_REQUIRED_EXAMPLE}}},
    },
    openapi_extra=route_contract(
        scopes=(ApiScope.SUPPLEMENT_READ, ApiScope.ANALYSIS_READ),
        consents=(ConsentType.SENSITIVE_HEALTH_ANALYSIS,),
        contract_status=P1_7_SUPPLEMENT_RECOMMENDATION_READY_STATUS,
    ),
)
async def get_latest_supplement_recommendations(
    http_request: Request,
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_supplement_recommendation_read),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SupplementImpactPreviewResponse:
    """Return the latest deterministic supplement impact preview.

    Args:
        http_request: Current FastAPI request.
        current_user: Authenticated owner.
        session: Request-scoped async database session.
        settings: Application settings.

    Returns:
        Deterministic supplement impact preview using all active supplements.

    Raises:
        HTTPException: If consent is missing or generated output is unsafe.
    """
    await _require_sensitive_health_consent(session, current_user, http_request, settings)
    try:
        response = await build_supplement_impact_preview(
            session,
            current_user,
            SupplementImpactPreviewRequest(),
        )
    except ValueError as exc:
        raise _supplement_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="invalid_supplement_recommendation",
            message=str(exc),
        ) from exc
    await record_sensitive_audit_event(
        session,
        current_user,
        action="supplement_recommendations_latest",
        resource_type="supplement_recommendation",
        resource_id=None,
        outcome="success",
        request=http_request,
        settings=settings,
        event_metadata={
            "data_status": response.data_status.value,
            "contribution_count": len(response.current_supplement_contributions),
            "deficiency_candidate_count": len(response.deficiency_support_candidates),
            "risk_count": len(response.excess_or_duplicate_risks),
            "warning_count": len(response.warnings),
        },
    )
    return response


@router.post(
    "/recommendations/explain",
    response_model=SupplementRecommendationExplainResponse,
    responses={
        **SUPPLEMENT_AUTH_RESPONSES,
        200: {
            "content": {
                "application/json": {
                    "examples": SUPPLEMENT_RECOMMENDATION_EXPLAIN_RESPONSE_EXAMPLES
                }
            }
        },
        403: {"content": {"application/json": {"examples": CONSENT_REQUIRED_EXAMPLE}}},
        422: {"content": {"application/json": {"examples": UNPROCESSABLE_ENTITY_EXAMPLE}}},
    },
    openapi_extra=route_contract(
        scopes=(ApiScope.SUPPLEMENT_READ, ApiScope.ANALYSIS_READ),
        consents=(ConsentType.SENSITIVE_HEALTH_ANALYSIS,),
        contract_status=P1_7_SUPPLEMENT_RECOMMENDATION_READY_STATUS,
    ),
)
async def explain_supplement_recommendations(
    http_request: Request,
    request: Annotated[
        SupplementRecommendationExplainRequest,
        Body(openapi_examples=SUPPLEMENT_RECOMMENDATION_EXPLAIN_REQUEST_EXAMPLES),
    ],
    current_user: Annotated[
        AuthenticatedUser,
        Depends(require_supplement_recommendation_read),
    ],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SupplementRecommendationExplainResponse:
    """Explain deterministic supplement impact output with safety guardrails.

    Args:
        http_request: Current FastAPI request.
        request: Explanation request.
        current_user: Authenticated owner.
        session: Request-scoped async database session.
        settings: Application settings.

    Returns:
        Safe explanation response.

    Raises:
        HTTPException: If consent is missing or fallback wording fails safety validation.
    """
    await _require_sensitive_health_consent(session, current_user, http_request, settings)
    try:
        response = await explain_supplement_recommendation(request, settings)
    except SupplementExplanationError as exc:
        raise _supplement_http_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="unsafe_supplement_explanation",
            message=str(exc),
        ) from exc
    await record_sensitive_audit_event(
        session,
        current_user,
        action="supplement_recommendations_explained",
        resource_type="supplement_recommendation",
        resource_id=None,
        outcome="success",
        request=http_request,
        settings=settings,
        event_metadata={
            "llm_used": response.llm_used,
            "warning_count": len(response.warnings),
            "blocked_term_count": len(response.blocked_terms_detected),
            "raw_ocr_text_stored": False,
            "raw_llm_response_stored": False,
        },
    )
    return response


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


@router.post(
    "/analyze/comprehensive",
    response_model=SupplementComprehensiveAnalysis,
    status_code=status.HTTP_200_OK,
    responses=SUPPLEMENT_AUTH_RESPONSES,
)
async def analyze_supplement_comprehensive(
    request_body: ComprehensiveAnalysisRequest,
    _current_user: Annotated[AuthenticatedUser, Depends(require_supplement_write)],
) -> SupplementComprehensiveAnalysis:
    """5-card UI 의 5종 카드 데이터를 모두 채우는 종합 분석 결과를 반환한다.

    OCR `analyze` endpoint 가 반환한 ingredient candidate 와 사용자 프로필을
    받아 KDRIs 권장량/상한과 비교하고 만성질환 매트릭스와 교차하여 부족/과다/주의/점수/목적별
    카드 데이터를 산출한다. 본 endpoint 는 별도의 OCR 또는 LLM 호출 없이 빠르게(200ms 이내)
    응답한다.

    Args:
        request_body: 분석 요청 본문 (ingredients + user_profile + persona).
        _current_user: 인증된 사용자 (dev 모드에서는 mock).

    Returns:
        [SupplementComprehensiveAnalysis] — 5-card 모두 채울 수 있는 데이터.
    """
    return compute_comprehensive(request_body)
