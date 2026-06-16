"""기업 과제 Output 데모 — mock 사용자 → 통합 건강 요약.

사용자(성별·나이·키·몸무게·활동) + 하루 섭취 영양소를 넣어
①부족 영양소 추천 ②영양소 섭취량 권고 ③체중 변화 예측 ④활동 권고를 출력한다.

usage: python -u _demo_health_summary.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\Lemon-sin\backend")))
sys.stdout.reconfigure(encoding="utf-8")

from src.models.schemas.user import UserProfile  # noqa: E402
from src.services.health_summary import build_health_summary  # noqa: E402

# ── mock 입력 ──
user = UserProfile(age=52, sex="male", height_cm=168, weight_kg=78.0)
daily_steps = 7200
daily_intake = {
    "kcal": 1700.0,
    "protein_g": 45.0,
    "fiber_g": 12.0,
    "sodium_mg": 3500.0,
    "calcium_mg": 400.0,
    "iron_mg": 7.0,
    "vitamin_a_ug": 350.0,
    "vitamin_c_mg": 40.0,
}

s = build_health_summary(user, daily_steps, daily_intake)

print("# 통합 건강 요약 (기업 과제 Output 데모)\n")
print("## 입력 (mock)")
print(f"- 사용자: {user.age}세 {'남성' if user.sex == 'male' else '여성'}, "
      f"{user.height_cm}cm / {user.weight_kg}kg, 하루 {daily_steps:,}보")
print(f"- 하루 섭취: {daily_intake}\n")

print(f"## 요약\n{s.summary_message_ko}\n")

print("## ① 부족 영양소 추천 + ② 섭취량 권고")
for c in s.deficient_recommendations:
    print(f"- **{c.name_ko}**: 충족률(기여도) {c.fulfillment_pct}% "
          f"(섭취 {c.intake_amount}{c.unit} / 권장 {c.reference_amount}{c.unit}) "
          f"→ 부족 {c.shortfall_amount}{c.unit} · 추천: {c.food_suggestion}")
print()

print("## 영양소 전체 기여도(충족률)")
for c in s.nutrient_contributions:
    print(f"- {c.name_ko}: {c.fulfillment_pct}% [{c.status.value}] — {c.message_ko}")
print()

print("## ③ 체중 변화 예측")
wp = s.weight_predictions
for label, p in (("1주", wp.week_1), ("1개월", wp.month_1), ("3개월", wp.month_3)):
    print(f"- {label}({p.period_days}일): {p.starting_weight}kg → "
          f"**{p.predicted_weight}kg** ({p.corrected_change:+.2f}kg) "
          f"[BMR {p.bmr} · TDEE {p.tdee} · 일수지 {p.daily_balance}kcal]")
print()

print("## ④ 활동(운동) 권고")
a = s.activity
print(f"- {a.message_ko}")
print(f"- 권장 {a.recommended_steps:,}보 / 실제 {a.actual_steps:,}보 / 부족 {a.step_gap:,}보 / v1 {a.v1_score}점")
