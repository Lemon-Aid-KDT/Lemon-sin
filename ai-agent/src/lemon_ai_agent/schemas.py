from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


MealType = Literal["breakfast", "lunch", "dinner", "snack"]
ActionType = Literal["supplement_reminder", "daily_mission"]


class FindingLevel(str, Enum):
    LOW = "low"
    ADEQUATE = "adequate"
    HIGH = "high"
    RISKY = "risky"


@dataclass(frozen=True)
class NutrientAmount:
    name: str
    amount: float
    unit: str


@dataclass(frozen=True)
class FoodIntake:
    name: str
    meal_type: MealType
    serving_label: str
    nutrients: list[NutrientAmount]


@dataclass(frozen=True)
class SupplementIntake:
    product_name: str
    ingredients: list[NutrientAmount]
    times_per_day: int = 1


@dataclass(frozen=True)
class DailyIntake:
    user_id: str
    date: str
    foods: list[FoodIntake] = field(default_factory=list)
    supplements: list[SupplementIntake] = field(default_factory=list)


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    age: int
    gender: Literal["male", "female", "other"]
    goals: list[str] = field(default_factory=list)
    chronic_conditions: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HealthTrend:
    metric: str
    direction: Literal["up", "down", "flat", "unknown"]
    severity: Literal["info", "watch", "attention"]
    summary: str


@dataclass(frozen=True)
class ReferenceRange:
    nutrient: str
    target: float
    unit: str
    upper_limit: float | None = None


@dataclass(frozen=True)
class NutrientFinding:
    nutrient: str
    total_amount: float
    unit: str
    ratio_to_target: float | None
    level: FindingLevel
    message: str


@dataclass(frozen=True)
class PersonalizationContext:
    user_id: str
    goals: list[str]
    caution_tags: list[str]
    health_trend_notes: list[str]
    medication_notes: list[str]


@dataclass(frozen=True)
class CoachingRecommendation:
    category: Literal["reduce", "add_food", "consider_ingredient", "mission", "reminder"]
    title: str
    rationale: str
    priority: int
    requires_professional_consult: bool = False


@dataclass(frozen=True)
class ProposedAction:
    action_type: ActionType
    title: str
    payload: dict[str, str]
    requires_user_approval: bool = True


@dataclass(frozen=True)
class DailyCoachingResult:
    user_id: str
    date: str
    findings: list[NutrientFinding]
    recommendations: list[CoachingRecommendation]
    actions: list[ProposedAction]
    safety_warnings: list[str]

