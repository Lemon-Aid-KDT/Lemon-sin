"""AI Agent coaching API routes."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from lemon_ai_agent.adapters import AgentInput, AgentOutput, DailyHealthAgentAppAdapter
from lemon_ai_agent.agents.chatbot import ChatbotAgent
from lemon_ai_agent.chat_session import (
    ChatbotRequest as AgentChatbotRequest,
)
from lemon_ai_agent.chat_session import (
    ChatTurn as AgentChatTurn,
)
from lemon_ai_agent.llm import LocalLLMClient, OllamaClient, SGLangClient
from lemon_ai_agent.schemas import ReferenceRange
from lemon_ai_agent.user_health_context import ContextResolver
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
from src.services.app_health_analysis import (
    build_analysis_run_confirmation,
    build_health_analysis_snapshot,
    build_today_analysis_snapshot,
    detect_analysis_run_intent,
    store_app_health_analysis_result,
)
from src.services.chatbot_evidence_retriever import build_chatbot_medical_knowledge_retriever
from src.services.chatbot_unknown_backlog import (
    build_unknown_knowledge_event,
    record_unknown_knowledge_event,
)
from src.services.food_records import load_recent_user_food_record_context
from src.services.medical_source_readiness import build_medical_source_readiness_from_db
from src.services.privacy import (
    ConsentRequiredError,
    record_sensitive_audit_event,
    require_user_consent,
)
from src.services.supplement_registration import load_active_supplement_context
from src.services.user_health_context_snapshot import build_user_health_context_snapshot
from src.services.user_medications import load_active_user_medication_context

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
    source_families: list[str] = Field(default_factory=list)
    answerability: str = "answerable"
    sources: list[dict[str, str]] = Field(default_factory=list)
    requires_user_approval: bool = False
    ctas: list[str] = Field(default_factory=list)


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


async def _production_medical_source_gate(
    session: AsyncSession,
    settings: Settings,
) -> tuple[bool, list[str]]:
    """Fail closed for production chat if reviewed source governance is unavailable."""
    if settings.environment != "production":
        return True, []

    readiness = await build_medical_source_readiness_from_db(
        session,
        settings,
        allow_registry_fallback=False,
    )
    if readiness.ready:
        return True, []

    error_codes = [
        source.error_code or source.status
        for source in readiness.sources
        if not source.ready
    ]
    return False, list(dict.fromkeys(error_codes or ["no_reviewed_sources"]))


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
    sources_ready, source_warnings = await _production_medical_source_gate(session, settings)
    if not sources_ready:
        return ChatbotApiResponse(
            request_id=request.request_id,
            message=(
                "요약\n"
                "- 현재 검수된 의료 지식 출처가 준비되지 않아 답변할 수 없습니다.\n"
                "현재 답할 수 없는 이유\n"
                "- production 환경에서는 reviewed source governance DB가 준비된 경우에만 "
                "건강 답변을 생성합니다.\n"
                "필요한 검수 지식\n"
                "- reviewed source, source version, expiry, user-facing 허용 상태가 필요합니다.\n"
                "지금 할 수 있는 안전한 행동\n"
                "- 긴급 증상이 있으면 119 또는 가까운 응급실을 이용하고, 복약·치료 판단은 "
                "의사 또는 약사에게 확인하세요."
            ),
            provider="deterministic",
            used_tools=["medical_source_readiness"],
            safety_warnings=source_warnings,
            source_families=[],
            answerability="unknown_no_reviewed_source",
            sources=[],
            requires_user_approval=False,
        )

    memory_context = await load_agent_memory_context(session, current_user, settings)
    medication_context = await load_active_user_medication_context(session, current_user, settings)
    food_record_context = await load_recent_user_food_record_context(
        session,
        current_user,
        settings,
    )
    active_supplement_context = await load_active_supplement_context(session, current_user)
    context = dict(request.context)
    context["agent_memory"] = memory_context
    context = _merge_user_medication_context(context, medication_context)
    context.setdefault("daily_coaching_summary", _memory_summary_for_chat(memory_context))
    user_health_snapshot = build_user_health_context_snapshot(
        request_context=context,
        memory_context=memory_context,
        medication_context=medication_context,
        food_record_context=food_record_context,
        active_supplement_context=active_supplement_context,
    )
    context_resolution = ContextResolver().resolve(request.message, user_health_snapshot)
    context["user_health_context_snapshot"] = user_health_snapshot.to_safe_context()
    context["user_health_context_resolution"] = {
        "status": context_resolution.status,
        "required_records": list(context_resolution.required_records),
        "lookup_filters": context_resolution.lookup_filters,
        "reason": context_resolution.reason,
    }
    analysis_response = await _maybe_handle_chat_analysis_run(
        session=session,
        current_user=current_user,
        request=request,
        user_health_snapshot=context["user_health_context_snapshot"],
    )
    if analysis_response is not None:
        await record_sensitive_audit_event(
            session,
            current_user,
            action="ai_agent_chat_analysis_confirmation",
            resource_type="ai_agent_chat",
            resource_id=request.request_id,
            outcome="success",
            request=http_request,
            settings=settings,
            event_metadata={
                "requires_user_approval": analysis_response.requires_user_approval,
            },
        )
        return analysis_response

    llm_client = _build_llm_client(settings)
    retriever = await build_chatbot_medical_knowledge_retriever(session, settings)
    chatbot_response = ChatbotAgent(llm_client=llm_client, retriever=retriever).answer(
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
    if chatbot_response.answerability == "unknown_no_reviewed_source":
        record_unknown_knowledge_event(
            session,
            build_unknown_knowledge_event(
                message=request.message,
                answerability=chatbot_response.answerability,
                retrieval_warnings=chatbot_response.safety_warnings,
            ),
        )

    used_tools = list(
        dict.fromkeys(
            [
                *chatbot_response.used_tools,
                "agent_memory",
                "user_health_context_snapshot",
            ]
        )
    )
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
        source_families=chatbot_response.source_families,
        answerability=chatbot_response.answerability,
        sources=chatbot_response.sources,
        requires_user_approval=chatbot_response.requires_user_approval,
    )


async def _maybe_handle_chat_analysis_run(
    *,
    session: AsyncSession,
    current_user: AuthenticatedUser,
    request: ChatbotApiRequest,
    user_health_snapshot: dict[str, Any],
) -> ChatbotApiResponse | None:
    analysis_kind = detect_analysis_run_intent(request.message)
    if analysis_kind is None:
        return None

    result_snapshot = (
        build_today_analysis_snapshot(user_health_snapshot)
        if analysis_kind == "today_analysis"
        else build_health_analysis_snapshot(user_health_snapshot)
    )
    approval = _analysis_run_approval(request.context)
    approved_kind = approval.get("analysis_kind")
    approved = approval.get("approved") is True and approved_kind == analysis_kind
    if not approved:
        confirmation = build_analysis_run_confirmation(analysis_kind, result_snapshot)
        return ChatbotApiResponse(
            request_id=request.request_id,
            message=(
                "요약\n"
                "- 분석을 실행하려면 현재 기록으로 분석을 저장해도 되는지 먼저 확인이 필요합니다.\n"
                "오늘 행동\n"
                "- 분석 실행을 승인하거나, 부족한 기록을 먼저 보완해 주세요.\n"
                "출처 기준\n"
                "- 사용자 확인 기록과 현재 앱 컨텍스트"
            ),
            provider="deterministic",
            used_tools=["app_health_analysis_confirmation"],
            answerability="needs_more_info",
            requires_user_approval=True,
            ctas=list(confirmation["ctas"]),
        )

    await store_app_health_analysis_result(
        session,
        current_user,
        analysis_kind=analysis_kind,
        input_snapshot={
            "context_sections": list(user_health_snapshot.keys()),
            "request_id": request.request_id,
        },
        result_snapshot=result_snapshot,
        user_confirmed=True,
    )
    return ChatbotApiResponse(
        request_id=request.request_id,
        message=(
            "요약\n"
            "- 승인된 현재 앱 기록을 기준으로 분석 snapshot을 저장했습니다.\n"
            "오늘 행동\n"
            "- 분석 탭에서 저장된 결과를 확인하고, 이 결과로 이어서 질문할 수 있습니다.\n"
            "출처 기준\n"
            "- 사용자 확인 기록과 현재 앱 컨텍스트"
        ),
        provider="deterministic",
        used_tools=["app_health_analysis"],
        answerability="answerable",
        requires_user_approval=False,
        ctas=["ask_about_this_result"],
    )


def _analysis_run_approval(context: dict[str, Any]) -> dict[str, Any]:
    value = context.get("analysis_run_approval")
    return dict(value) if isinstance(value, dict) else {}


def _merge_user_medication_context(
    context: dict[str, Any],
    medication_context: dict[str, object],
) -> dict[str, Any]:
    """Merge DB-confirmed medication profile context without raw free text."""
    profile = dict(context.get("profile") or {})
    existing_names = [
        str(name).strip()
        for name in profile.get("medications", [])
        if str(name).strip()
    ]
    medication_names = [
        str(name).strip()
        for name in medication_context.get("medications", [])
        if str(name).strip()
    ]
    profile["medications"] = list(dict.fromkeys([*existing_names, *medication_names]))
    medication_details = medication_context.get("medication_details", [])
    if medication_details:
        profile["medication_details"] = medication_details
    context["profile"] = profile
    return context
