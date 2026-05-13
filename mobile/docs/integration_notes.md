# 팀원 브랜치 정찰 노트

> 합치기 시 mobile 측이 fromJson 만 손보면 화면 코드를 안 건드려도 되도록 — 실제 API 응답 키 / 형식을 여기 모은다.
> 기획서 (`PROJECT_GUIDE.md` / `plan.md`) 와 다른 점은 **팀원 코드가 정답**.
> 2026-05-13 기준 정찰. 브랜치는 절대 체크아웃하지 않고 `git show` 만 사용.

---

## 1. 브랜치 한눈에

| 브랜치 | 마지막 커밋 (한 줄) | 역할 |
|---|---|---|
| `origin/changmin-plan` | docs(changmin-plan): reorganize project documents | 기획 / 문서 (코드 없음) |
| `origin/sunghoon-database` | docs: DATABASE_GUIDE.md 상세화 v2.0 | 백엔드 (auth · profile · DB) |
| `origin/work-space/jongpil` | chore(gitignore): pytest basetemp 임시 폴더 제외 | AI · Vision (식단 인식 파이프라인) |
| `origin/yeong-tech` | chore(repo): remove duplicate root scaffolds | 백엔드 P1 baseline (활동 · 영양 · 체중 · 건강 · 영양제 통합) |

⚠️ `sunghoon-database` 와 `yeong-tech` 가 별도 백엔드 baseline 으로 보임. 둘이 어디서 머지될지 미정 — 모바일 통합 시 한쪽이 정본일 가능성.

---

## 2. yeong-tech — 백엔드 P1 baseline (가장 풍부, 233 파일)

루트가 `yeong-Vision-Nutrition/` 으로 한 단계 들어간 구조.

### 2.1 발견된 Pydantic 스키마 — `yeong-Vision-Nutrition/backend/src/models/schemas/`

- `analysis_result.py` — **AnalysisResultResponse 가 모바일 AnalysisResult 모델의 정본**
  - 응답 키: `id` (UUID), `analysis_type` (StrEnum), `algorithm_version` (str), `kdris_source_manifest_version` (str | None), `result_snapshot` (dict[str, Any]), `created_at` (datetime)
  - `AnalysisType` 값: `activity_score` / `weight_prediction` / `nutrition_analysis` — **3종**. 기획서 "5 종 카드 (nutrient/kdri/weight/activity/goal)" 와 다름.
- `user.py` — UserProfile
  - 키: `age` (int), `sex` ("male" | "female"), `height_cm` (float), `weight_kg` (float), `pregnancy_status` ("none"|"pregnant"|"lactating"), `chronic_diseases` (list[str])
- `dashboard.py` — DashboardSummaryResponse (홈 한눈 화면 정본)
  - 최상위: `as_of`, `nutrition`, `activity`, `weight`, `supplements`, `disclaimers` (list[str]), `algorithm_version`
  - `nutrition` 안: `data_status` ("ready"|"not_ready"), `latest_result_id` (UUID|None), `low_count`, `high_count`, `dataset_version`, `source_manifest_version`
  - `activity` 안: `data_status`, `latest_steps`, `latest_resting_heart_rate_bpm`, `latest_active_energy_kcal`, `latest_activity_score` (0~120), `measured_date`
  - `weight` 안: `data_status`, `latest_weight_kg`, `predicted_weight_kg`, `measured_date`
  - `supplements` 안: `registered_count`, `requires_review_count`
- `nutrition.py` — KDRIs 기준값. NutrientStatus = deficient | low | adequate | excessive | risky. KDRIReference 에 `nutrient_code` · `nutrient_name_ko` · `reference_amount` · `reference_unit` · `ul_amount` 등.
- `supplement.py` — SupplementAnalysisStatus: requires_confirmation | confirmed | expired | failed. Candidate 에 `display_name` · `nutrient_code` · `amount` · `unit` · `confidence` (0~1) · `source`.
- `health.py` — HealthDailyAggregate. 키: `measured_date`, `source_platform` (ios_healthkit | android_health_connect | manual), `steps`, `weight_kg`, `resting_heart_rate_bpm`, `active_energy_kcal`.
- `algorithm.py`, `privacy.py`, `errors.py`, `supplement_parser.py` — 부수.

### 2.2 발견된 API 라우터 — `yeong-Vision-Nutrition/backend/src/api/v1/`

- `analysis_results.py` (389줄) — 저장된 분석 결과 CRUD
- `dashboard.py` — 홈 한눈 요약
- `activity.py` — 활동 점수 계산
- `nutrition.py` — 영양 분석
- `health.py` — 건강 데이터 sync
- `supplements.py` — 영양제
- `predictions.py` — 체중 예측
- `privacy.py` — 동의 / 감사
- `examples.py` — OpenAPI 응답 샘플 (모바일 fromJson 작성 시 가장 유용)
- `router.py` — v1 통합 라우터
- `contract.py` — 계약 검증

### 2.3 응답 샘플 (examples.py 에서 추출)

**활동 점수 응답:**
```json
{
  "bmi": {"bmi": 26.6, "category": "obese_1", "evidence_level": "A", "note": "..."},
  "recommended_steps": 7524,
  "target_hr_range": {"low_bpm": 85, "high_bpm": 119, "formula": "guide_220_age"},
  "v1_score": 77.53, "v2_score": 69.78, "v3_score": 69.78, "v4_score": 83.74,
  "note": "..."
}
```

**체중 예측 응답:**
```json
{
  "predictions": [
    {"days": 7, "estimated_bmr": 1269.0, "estimated_tdee": 1745.0,
     "daily_balance_kcal": -245.0, "theoretical_change_kg": -0.223,
     "corrected_change_kg": -0.189, "predicted_weight_kg": 67.81, "warning": null},
    {"days": 30, "...": "..."}
  ]
}
```

### 2.4 Alembic Migrations

- 0001 users / 0002 analysis_results / 0003 privacy_consent_audit / 0004 P1 supplement·health

---

## 3. sunghoon-database — auth · profile 백엔드 (70 파일)

루트 바로 아래 `backend/` 구조 (yeong-tech 와 다른 layout).

### 3.1 인증 스키마 — `backend/src/schemas/auth.py`

- `SignupRequest`: `email` (EmailStr), `password` (min 8), `display_name` (str | None, max 100)
- `LoginRequest`: `email`, `password`
- `TokenResponse`: `access_token`, `refresh_token`, `token_type` ("bearer")
- `RefreshRequest`: `refresh_token`
- `AccessTokenResponse`: `access_token`, `token_type`

### 3.2 프로필 스키마 — `backend/src/schemas/profile.py`

- `ProfileUpdate` / `ProfileResponse`
  - `user_id`: **int** (yeong-tech 는 UUID — 충돌 가능)
  - `age`, `gender` ("M" | "F"), `height_cm`, `weight_kg`
  - `chronic_diseases: list[str]`, `medications: list[str]`, `goals: list[str]`

### 3.3 API 라우터 — `backend/src/api/`

- `auth.py` — 회원가입 / 로그인 / refresh
- `profile.py` — 프로필 조회 / 갱신

### 3.4 DB / 보안 / DI

- `backend/src/db/init.sql`, `backend/src/db/base.py`, `backend/src/db/session.py`
- `backend/src/utils/security.py` (JWT)
- `backend/src/utils/deps.py` (FastAPI 의존성)
- `backend/src/main.py` — FastAPI app 진입점
- `docker-compose.yml`

---

## 4. work-space/jongpil — 식단 인식 파이프라인 (142 파일)

루트 바로 아래 `backend/` 구조.

### 4.1 Meal DTO — `backend/src/meal/base.py`

- `BoundingBox`: `x_min` · `y_min` · `x_max` · `y_max` (float, 픽셀)
- `MealDetection`: `class_name_ko` · `confidence` (0~1) · `bbox` (Optional) · `source` ("yolo_v8" | "google_vision")
- `RecognizedMealItem` (최종):
  - `name_ko`, `food_code` (농진청 코드 또는 None), `estimated_grams`, `estimated_amount` (예: "1공기"), `confidence` (0~1), `portion_confidence` (0~1), `needs_user_review` (bool), `sources` (list), `alternatives` (list)

### 4.2 파이프라인 — `backend/src/meal/`

- `pipeline.py` — 통합 entry point
- `fusion.py` — YOLO + GCV 결합
- `yolo_v8.py`, `google_vision.py` — 모델별 detector
- `portion_estimator.py` — bbox → 중량 추정
- `text_parser.py` — 식단 텍스트 정규화 (사용자 입력 보정)
- `exceptions.py`

### 4.3 영양 매칭 — `backend/src/nutrition/`

- `rda_matcher.py` — 추정 음식 → KDRIs RDA 매칭 + scaling

⚠️ **참고**: jongpil 브랜치의 DTO 가 모바일 `Meal.candidates: List<FoodCandidate>` 의 fromJson 작성에 가장 유용. 키명은 `class_name_ko` / `food_code` / `confidence` / `bbox` / `source`.

---

## 5. 기획서와 다른 점 (한 줄씩)

- `AnalysisType` 3종 (activity_score / weight_prediction / nutrition_analysis) — 기획서 5 종 (nutrient/kdri/weight/activity/goal) 과 다름. **nutrient + kdri 가 nutrition_analysis 로 통합**되었고 **goal 은 별도 없음**.
- `gender` 표기 — sunghoon 은 `"M"` / `"F"`, yeong-tech 은 `"male"` / `"female"` — 두 백엔드 충돌.
- `user_id` 타입 — sunghoon `int`, yeong-tech `UUID` — 두 백엔드 충돌.
- `nickname` 키명 — 기획서 / CLAUDE.md 가안 `nickname`, sunghoon 실제 `display_name`.
- `confidence` 값 형식 — 백엔드 일관 0~1 float (확정). 화면 표시 시점에 `×100` 백분율 변환.
- `analysis_result.result_snapshot: dict[str, Any]` — yeong-tech 가 분석 결과를 dict 통째로 보냄. 모바일에서 `Map<String, dynamic>` 그대로 받아서 화면 파싱.
- Dashboard 한눈 요약은 `data_status: "ready" | "not_ready"` 로 빈 상태 분기 — 빈 화면 UI 결정에 직결.
- 응답 안에 `disclaimers: list[str]` 가 들어옴 — 화면 푸터 "건강 참고용..." 을 이걸로 갈아끼울 수 있음.

---

## 6. 확인 불가 / 추가 정찰 필요

- AuthProvider 가 sunghoon 의 `/api/auth/login` 을 쓸지, yeong-tech 통합본을 쓸지 미정.
- `Meal` / `Supplement` 의 `previewApproved` 키명 — sunghoon · jongpil 에 명시적으로 보이지 않음. yeong-tech supplement `SupplementAnalysisStatus.CONFIRMED` 로 대체될 수도.
- `daily_score` (홈 한눈 점수) 의 단일 정수 합산 키는 yeong-tech 응답 어디에도 명확히 없음 — 모바일 mock 에서 "단일 0~100 점수" 가안으로 유지하되, 실제 합치 시 dashboard 의 v4 활동점수 또는 별도 집계로 대체 가능.
- jongpil 의 `RecognizedMealItem.sources` 값 enum 미확정 (`["yolo_v8", "google_vision"]` 외 추가 가능).
- changmin-plan 은 코드 없음 — 기획서만 갱신.

---

## 7. 통합 시 작업 순서 (모바일 측)

1. 실제 API 응답 한 번 통째로 `print('[API] $rawJson')` — `raw` 보존이 핵심.
2. 이 문서 §2~§4 의 키와 비교 → 다른 부분 한 줄씩 추가.
3. 해당 모델의 `fromJson` 만 손봄. 화면 코드 / 위젯 / repository 인터페이스는 안 건드림.
4. `flutter analyze` 통과 확인.
5. `mock_repository.dart` → `api_repository.dart` 로 교체 (메서드 시그니처 동일 유지).
6. `AuthProvider` 신설 → `splash_screen.dart` 의 `_initRoute()` 안 mock 분기 실제 인증으로 교체.
