from __future__ import annotations

from collections import defaultdict

from lemon_ai_agent.schemas import (
    DailyIntake,
    FindingLevel,
    NutrientAmount,
    NutrientFinding,
    ReferenceRange,
)


class NutritionEngine:
    """Deterministic nutrition aggregation and reference comparison."""

    def __init__(self, references: list[ReferenceRange]) -> None:
        self._references = {item.nutrient.lower(): item for item in references}

    def evaluate(self, intake: DailyIntake) -> list[NutrientFinding]:
        totals = self._aggregate(intake)
        findings: list[NutrientFinding] = []

        for nutrient_name, amount in sorted(totals.items()):
            reference = self._references.get(nutrient_name.lower())
            if reference is None:
                findings.append(
                    NutrientFinding(
                        nutrient=nutrient_name,
                        total_amount=amount.amount,
                        unit=amount.unit,
                        ratio_to_target=None,
                        level=FindingLevel.ADEQUATE,
                        message="Reference range is not configured.",
                    )
                )
                continue

            ratio = amount.amount / reference.target if reference.target > 0 else None
            level = self._classify(amount.amount, reference)
            findings.append(
                NutrientFinding(
                    nutrient=reference.nutrient,
                    total_amount=round(amount.amount, 3),
                    unit=reference.unit,
                    ratio_to_target=round(ratio, 3) if ratio is not None else None,
                    level=level,
                    message=self._message(reference.nutrient, level, ratio),
                )
            )

        return findings

    def _aggregate(self, intake: DailyIntake) -> dict[str, NutrientAmount]:
        totals: dict[tuple[str, str], float] = defaultdict(float)
        for food in intake.foods:
            for nutrient in food.nutrients:
                totals[(nutrient.name, nutrient.unit)] += nutrient.amount
        for supplement in intake.supplements:
            multiplier = max(supplement.times_per_day, 1)
            for ingredient in supplement.ingredients:
                totals[(ingredient.name, ingredient.unit)] += ingredient.amount * multiplier
        return {
            name: NutrientAmount(name=name, amount=amount, unit=unit)
            for (name, unit), amount in totals.items()
        }

    def _classify(self, amount: float, reference: ReferenceRange) -> FindingLevel:
        if reference.upper_limit is not None and amount > reference.upper_limit:
            return FindingLevel.RISKY
        ratio = amount / reference.target if reference.target > 0 else 1.0
        if ratio < 0.7:
            return FindingLevel.LOW
        if ratio > 1.3:
            return FindingLevel.HIGH
        return FindingLevel.ADEQUATE

    def _message(self, nutrient: str, level: FindingLevel, ratio: float | None) -> str:
        if ratio is None:
            return f"{nutrient} could not be compared with a target."
        pct = round(ratio * 100)
        if level == FindingLevel.LOW:
            return f"{nutrient} intake is about {pct}% of the target."
        if level == FindingLevel.HIGH:
            return f"{nutrient} intake is above the target range."
        if level == FindingLevel.RISKY:
            return f"{nutrient} intake is above the configured upper limit."
        return f"{nutrient} intake is within the target range."

