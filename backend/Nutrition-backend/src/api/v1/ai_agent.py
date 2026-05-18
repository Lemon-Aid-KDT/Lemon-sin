"""AI Agent coaching API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from lemon_ai_agent.adapters import AgentInput, AgentOutput, DailyHealthAgentAppAdapter
from lemon_ai_agent.schemas import ReferenceRange
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.contract import P1_7_AI_AGENT_DAILY_COACHING_READY_STATUS, route_contract
from src.api.v1.examples import (
    AI_AGENT_DAILY_COACHING_REQUEST_EXAMPLES,
    AI_AGENT_DAILY_COACHING_RESPONSE_EXAMPLES,
    CONSENT_REQUIRED_EXAMPLE,
    UNAUTHORIZED_EXAMPLE,
    UNPROCESSABLE_ENTITY_EXAMPLE,
)
from src.config import Settings, get_settings
from src.db.dependencies import get_async_session
from src.models.schemas.privacy import ConsentType
from src.security.auth import AuthenticatedUser, require_analysis_write
from src.security.scopes import ApiScope
from src.services.privacy import (
    ConsentRequiredError,
    record_sensitive_audit_event,
    require_user_consent,
)

router = APIRouter(prefix="/ai-agent", tags=["ai-agent"])

DEFAULT_REFERENCE_RANGES = [
    ReferenceRange("protein", 60, "g"),
    ReferenceRange("sodium", 2000, "mg", upper_limit=2300),
    ReferenceRange("vitamin d", 15, "mcg", upper_limit=100),
    ReferenceRange("magnesium", 350, "mg", upper_limit=700),
    ReferenceRange("iron", 10, "mg", upper_limit=45),
    ReferenceRange("calcium", 800, "mg", upper_limit=2500),
    ReferenceRange("fiber", 25, "g"),
]


async def _require_sensitive_health_consent(
    session: AsyncSession,
    current_user: AuthenticatedUser,
    http_request: Request,
    settings: Settings,
) -> None:
    """Require sensitive health analysis consent for AI coaching.

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
            action="ai_agent_daily_coaching_blocked",
            resource_type="ai_agent_daily_coaching",
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
    "/daily-coaching",
    response_model=AgentOutput,
    responses={
        200: {"content": {"application/json": {"examples": AI_AGENT_DAILY_COACHING_RESPONSE_EXAMPLES}}},
        401: {"content": {"application/json": {"examples": UNAUTHORIZED_EXAMPLE}}},
        403: {"content": {"application/json": {"examples": CONSENT_REQUIRED_EXAMPLE}}},
        422: {"content": {"application/json": {"examples": UNPROCESSABLE_ENTITY_EXAMPLE}}},
    },
    openapi_extra=route_contract(
        scopes=(ApiScope.ANALYSIS_WRITE,),
        consents=(ConsentType.SENSITIVE_HEALTH_ANALYSIS,),
        contract_status=P1_7_AI_AGENT_DAILY_COACHING_READY_STATUS,
    ),
)
async def run_daily_coaching(
    http_request: Request,
    request: Annotated[
        AgentInput,
        Body(openapi_examples=AI_AGENT_DAILY_COACHING_REQUEST_EXAMPLES),
    ],
    current_user: Annotated[AuthenticatedUser, Depends(require_analysis_write)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentOutput:
    """Run deterministic daily health coaching for the authenticated user.

    Args:
        http_request: Current FastAPI request.
        request: App-facing AI Agent input. Client user_id is ignored.
        current_user: Authenticated owner.
        session: Request-scoped async database session.
        settings: Application settings.

    Returns:
        App-facing AI Agent output.
    """
    await _require_sensitive_health_consent(session, current_user, http_request, settings)
    server_owned_request = request.model_copy(update={"user_id": current_user.subject})
    output = DailyHealthAgentAppAdapter(default_references=DEFAULT_REFERENCE_RANGES).run(
        server_owned_request
    )
    await record_sensitive_audit_event(
        session,
        current_user,
        action="ai_agent_daily_coaching_completed",
        resource_type="ai_agent_daily_coaching",
        resource_id=output.request_id,
        outcome="success",
        request=http_request,
        settings=settings,
        event_metadata={
            "approval_status": output.approval_status,
            "status": output.status,
            "provider": output.provider,
            "cost_usd": output.cost_usd,
            "raw_trace_returned": bool(output.debug_trace),
        },
    )
    return output
