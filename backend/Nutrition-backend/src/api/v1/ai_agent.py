"""AI Agent coaching API routes."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from lemon_ai_agent.adapters import AgentInput, AgentOutput, DailyHealthAgentAppAdapter
from lemon_ai_agent.agents.chatbot import ChatbotAgent
from lemon_ai_agent.chat_session import (
    ChatTurn as AgentChatTurn,
    ChatbotRequest as AgentChatbotRequest,
)
from lemon_ai_agent.llm import LocalLLMClient, OllamaClient, SGLangClient
from lemon_ai_agent.schemas import ReferenceRange
from pydantic import BaseModel, ConfigDict, Field
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
from src.services.agent_memory import (
    load_agent_memory_context,
    record_agent_run,
    upsert_daily_coaching_memory,
)
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


class ChatTurnPayload(BaseModel):
    """Client-supplied chatbot conversation turn."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)
    created_at: str = Field(min_length=1, max_length=80)


class ChatbotApiRequest(BaseModel):
    """App-facing chatbot request payload."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_id: str = Field(min_length=1, max_length=120)
    user_id: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=4000)
    conversation: list[ChatTurnPayload] = Field(default_factory=list, max_length=24)
    context: dict[str, Any] = Field(default_factory=dict)


class ChatbotApiResponse(BaseModel):
    """App-facing chatbot response payload."""

    request_id: str
    message: str
    provider: str
    used_tools: list[str] = Field(default_factory=list)
    safety_warnings: list[str] = Field(default_factory=list)
    requires_user_approval: bool = False


def _build_llm_client(settings: Settings) -> LocalLLMClient:
    """Build the configured local/self-hosted explanatory LLM client."""
    if settings.llm_provider == "sglang":
        api_key = (
            settings.sglang_api_key.get_secret_value()
            if settings.sglang_api_key is not None
            else None
        )
        return SGLangClient(
            model=settings.sglang_model,
            endpoint=settings.sglang_base_url,
            api_key=api_key,
            timeout=settings.ollama_timeout_sec,
        )
    return OllamaClient(
        model=settings.ollama_model,
        endpoint=settings.ollama_base_url,
        timeout=settings.ollama_timeout_sec,
    )


async def _require_sensitive_health_consent(
    session: AsyncSession,
    current_user: AuthenticatedUser,
    http_request: Request,
    settings: Settings,
    *,
    blocked_action: str = "ai_agent_daily_coaching_blocked",
    blocked_resource_type: str = "ai_agent_daily_coaching",
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
            action=blocked_action,
            resource_type=blocked_resource_type,
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


def _memory_summary_for_chat(memory_context: dict[str, object]) -> str:
    """Return a short non-raw memory summary for chatbot grounding."""
    summaries = memory_context.get("summaries")
    if not isinstance(summaries, list) or not summaries:
        return ""

    summary = summaries[0]
    if not isinstance(summary, dict):
        return "최근 데일리 코칭 메모리를 참고했습니다."

    summary_json = summary.get("summary_json")
    if isinstance(summary_json, dict):
        repeated = summary_json.get("repeated_nutrient_patterns")
        if isinstance(repeated, dict) and repeated:
            nutrients = ", ".join(str(key) for key in list(repeated.keys())[:3])
            return f"최근 데일리 코칭 메모리에서 {nutrients} 패턴을 참고했습니다."

    return "최근 데일리 코칭 메모리를 참고했습니다."


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
    memory_context = await load_agent_memory_context(session, current_user, settings)
    context = dict(request.context)
    context["agent_memory"] = memory_context
    server_owned_request = request.model_copy(
        update={"user_id": current_user.subject, "context": context}
    )
    llm_client = _build_llm_client(settings)
    output = DailyHealthAgentAppAdapter(
        default_references=DEFAULT_REFERENCE_RANGES,
        llm_client=llm_client,
    ).run(
        server_owned_request
    )
    if output.status != "preview":
        await upsert_daily_coaching_memory(
            session,
            current_user,
            settings,
            server_owned_request,
            output,
        )
        await record_agent_run(
            session,
            current_user,
            settings,
            output,
            model=getattr(llm_client, "model", None) if output.provider != "deterministic" else None,
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


@router.post(
    "/chat",
    response_model=ChatbotApiResponse,
    responses={
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
async def run_chatbot(
    http_request: Request,
    request: ChatbotApiRequest,
    current_user: Annotated[AuthenticatedUser, Depends(require_analysis_write)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatbotApiResponse:
    """Run the safety-bounded Lemon Aid chatbot for the authenticated user."""
    await _require_sensitive_health_consent(
        session,
        current_user,
        http_request,
        settings,
        blocked_action="ai_agent_chat_blocked",
        blocked_resource_type="ai_agent_chat",
    )
    memory_context = await load_agent_memory_context(session, current_user, settings)
    context = dict(request.context)
    context["agent_memory"] = memory_context
    context.setdefault("daily_coaching_summary", _memory_summary_for_chat(memory_context))

    llm_client = _build_llm_client(settings)
    chatbot_response = ChatbotAgent(llm_client=llm_client).answer(
        AgentChatbotRequest(
            request_id=request.request_id,
            user_id=current_user.subject,
            message=request.message,
            conversation=[
                AgentChatTurn(
                    role=turn.role,
                    content=turn.content,
                    created_at=turn.created_at,
                )
                for turn in request.conversation
            ],
            context=context,
        )
    )

    used_tools = list(dict.fromkeys([*chatbot_response.used_tools, "agent_memory"]))
    await record_sensitive_audit_event(
        session,
        current_user,
        action="ai_agent_chat_completed",
        resource_type="ai_agent_chat",
        resource_id=chatbot_response.request_id,
        outcome="success",
        request=http_request,
        settings=settings,
        event_metadata={
            "provider": chatbot_response.provider,
            "requires_user_approval": chatbot_response.requires_user_approval,
        },
    )
    return ChatbotApiResponse(
        request_id=chatbot_response.request_id,
        message=chatbot_response.message,
        provider=chatbot_response.provider,
        used_tools=used_tools,
        safety_warnings=chatbot_response.safety_warnings,
        requires_user_approval=chatbot_response.requires_user_approval,
    )
