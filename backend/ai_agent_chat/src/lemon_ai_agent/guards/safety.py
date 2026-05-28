from __future__ import annotations

import re
from dataclasses import dataclass

FORBIDDEN_TERMS = (
    "diagnose",
    "diagnosis",
    "diabetes",
    "cure",
    "treats",
    "prescribe",
    "take this medicine",
    "진단",
    "치료",
    "처방",
    "복용해도 됩니다",
    "복용량을 바꾸",
    "약을 중단",
    "약을 끊",
    "용량을 늘리",
    "용량을 줄이",
    "당뇨입니다",
    "고혈압입니다",
    "신장질환입니다",
    "완전히 금지",
    "절대 먹지",
    "절대 금지",
    "먹으면 안 된다",
    "먹으면 안 돼",
    "먹는 것은 안 돼",
    "먹으면 안 됩니다",
    "안 돼요",
    "먹지 않아야",
    "먹지 말아야",
    "먹지 마세요",
    "take more of this medicine",
    "stop taking your medicine",
)

PRODUCT_PROMOTION_TERMS = (
    "buy ",
    "purchase ",
    "brand",
    "제품을 구매",
    "브랜드",
)

UNSUPPORTED_EVIDENCE_TERMS = (
    "연구에 따르면",
    "임상시험",
    "논문",
    "입증",
    "근거가 확실",
    "혈압을 낮춥니다",
    "혈당을 낮춥니다",
    "콜레스테롤을 낮춥니다",
    "reduces blood pressure",
    "clinically proven",
    "study shows",
)

NUMERIC_MEDICAL_CLAIM_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?(?:\s*(?:-|~|\u2013|\u2014|to|에서|부터)\s*\d+(?:\.\d+)?)?"
    r"\s*(?:mg/dl|mg|mcg|µg|ug|iu|g|kcal|mmhg|%)(?=\b|[^A-Za-z0-9_]|$)",
    re.IGNORECASE,
)


def _compact_numeric_text(text: str) -> str:
    """Normalize cosmetic spacing so supplied numeric facts can be repeated."""
    return re.sub(r"\s+", "", text.casefold().replace("µ", "u"))


@dataclass(frozen=True)
class SafetyCheckResult:
    allowed: bool
    warnings: list[str]


class SafetyGuard:
    """Policy guard for health-management coaching text."""

    def check_text(self, text: str) -> SafetyCheckResult:
        lowered = text.lower()
        warnings: list[str] = []

        for term in FORBIDDEN_TERMS:
            if term.lower() in lowered:
                warnings.append("Forbidden medical expression detected")

        for term in PRODUCT_PROMOTION_TERMS:
            if term.lower() in lowered:
                warnings.append("Product-promotion expression detected")

        return SafetyCheckResult(allowed=not warnings, warnings=warnings)

    def check_grounding(self, text: str, allowed_context: str) -> SafetyCheckResult:
        """Block unsupported evidence or effect claims absent from grounding context."""
        lowered_text = text.lower()
        lowered_context = allowed_context.lower()
        warnings: list[str] = []

        for term in UNSUPPORTED_EVIDENCE_TERMS:
            lowered_term = term.lower()
            if lowered_term in lowered_text and lowered_term not in lowered_context:
                warnings.append("Unsupported medical fact detected")

        compact_context = _compact_numeric_text(lowered_context)
        for claim in NUMERIC_MEDICAL_CLAIM_PATTERN.findall(text):
            if _compact_numeric_text(claim) not in compact_context:
                warnings.append("Unsupported numeric medical claim detected")
                break

        return SafetyCheckResult(allowed=not warnings, warnings=warnings)

    def sanitize_or_raise(self, text: str) -> str:
        result = self.check_text(text)
        if not result.allowed:
            raise ValueError("; ".join(result.warnings))
        return text

    def sanitize_trace(self, trace: list[str]) -> tuple[list[str], list[str]]:
        safe_trace: list[str] = []
        warnings: list[str] = []

        for item in trace:
            result = self.check_text(item)
            if result.allowed:
                safe_trace.append(item)
                continue

            safe_trace.append("trace item withheld by policy guard")
            warnings.extend(f"Trace text blocked: {warning}" for warning in result.warnings)

        return safe_trace, warnings
