from __future__ import annotations

from lemon_ai_agent.guards.safety import SafetyGuard
from lemon_ai_agent.llm import LLMMessage, LLMRequest, LocalLLMClient
from lemon_ai_agent.schemas import DailyCoachingResult


class ChatAgent:
    """Explains recommendations from computed result traces only."""

    def __init__(self, llm_client: LocalLLMClient | None = None) -> None:
        self._llm_client = llm_client
        self._safety_guard = SafetyGuard()
        self.last_llm_warnings: list[str] = []
        self.last_llm_error: str | None = None
        self.last_provider = "deterministic"

    def answer(self, question: str, result: DailyCoachingResult) -> str:
        self.last_llm_warnings = []
        self.last_llm_error = None
        self.last_provider = "deterministic"
        fallback = self._deterministic_answer(result)

        if self._llm_client is None:
            return fallback

        try:
            response = self._llm_client.generate(self._build_llm_request(question, result))
        except Exception as exc:
            self.last_llm_error = str(exc)
            return fallback

        check = self._safety_guard.check_text(response.text)
        self.last_llm_warnings.extend(check.warnings)
        if not check.allowed:
            return fallback

        self.last_provider = response.provider
        return response.text

    def _deterministic_answer(self, result: DailyCoachingResult) -> str:
        recommendation_titles = ", ".join(
            recommendation.title for recommendation in result.recommendations[:3]
        )
        trace, warnings = self._safety_guard.sanitize_trace(result.trace[:4])
        self.last_llm_warnings.extend(warnings)
        trace_text = " / ".join(trace)

        if not recommendation_titles:
            recommendation_titles = "no coaching action was prioritized"

        return (
            "For your question, the answer is based on the current input, "
            f"recent flow, and policy checks already computed for {result.date}. "
            f"Top recommendation context: {recommendation_titles}. "
            f"Trace: {trace_text}. "
            "This is health-management coaching; review medical concerns with a "
            "qualified professional."
        )

    def _build_llm_request(
        self,
        question: str,
        result: DailyCoachingResult,
    ) -> LLMRequest:
        findings = "; ".join(
            (
                f"{finding.nutrient}: {finding.level.value}, "
                f"{finding.total_amount}{finding.unit}"
            )
            for finding in result.findings[:3]
        )
        recommendations = "; ".join(
            f"{item.title}: {item.rationale}" for item in result.recommendations[:3]
        )
        trace_lines, warnings = self._safety_guard.sanitize_trace(result.trace[:4])
        self.last_llm_warnings.extend(warnings)
        trace = " / ".join(trace_lines)

        return LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You explain Lemon Aid health-management coaching. "
                        "Do not diagnose, treat, prescribe, guarantee effects, or "
                        "promote buying a specific product. Use cautious phrasing "
                        "such as 'based on the current input', 'may need attention', "
                        "and 'consult a qualified professional'. Do not create new "
                        "health judgments beyond the supplied findings, "
                        "recommendations, and trace."
                    ),
                ),
                LLMMessage(
                    role="user",
                    content=(
                        f"Question: {question.strip()}\n"
                        f"Date: {result.date}\n"
                        f"Top findings: {findings or 'none'}\n"
                        f"Top recommendations: {recommendations or 'none'}\n"
                        f"Trace summary: {trace or 'none'}"
                    ),
                ),
            ]
        )
