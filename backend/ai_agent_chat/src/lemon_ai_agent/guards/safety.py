from __future__ import annotations

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
    "당뇨입니다",
    "고혈압입니다",
    "신장질환입니다",
)

PRODUCT_PROMOTION_TERMS = (
    "buy ",
    "purchase ",
    "brand",
    "제품을 구매",
    "브랜드",
)


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
