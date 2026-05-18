from __future__ import annotations

from dataclasses import dataclass


FORBIDDEN_TERMS = (
    "diagnose",
    "cure",
    "treats",
    "prescribe",
    "take this medicine",
    "진단",
    "치료",
    "처방",
    "복용해도 됩니다",
    "당뇨입니다",
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
                warnings.append(f"Forbidden medical expression detected: {term}")

        for term in PRODUCT_PROMOTION_TERMS:
            if term.lower() in lowered:
                warnings.append(f"Product-promotion expression detected: {term}")

        return SafetyCheckResult(allowed=not warnings, warnings=warnings)

    def sanitize_or_raise(self, text: str) -> str:
        result = self.check_text(text)
        if not result.allowed:
            raise ValueError("; ".join(result.warnings))
        return text

