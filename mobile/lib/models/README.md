# lib/models/ — 느슨한 컨테이너 + raw 보존

이 폴더의 모델들은 기획서 (`plan.md` / `PROJECT_GUIDE.md`) 의 **추정 스키마** 이며 팀원 브랜치 실제 구현과 다를 수 있다.
실제 API 응답 도착 시 — 우선 `raw` 로 받아서 `print` 로 키명 확인하고, 해당 키명에 맞춰 `fromJson` 만 수정한다.
화면 코드 / 위젯은 모델 인터페이스 (getter 시그니처) 가 같으면 절대 손대지 않는다.
**이 분리가 합치기 시 충돌을 막는 핵심.**

---

## 원칙

- 필수 필드 최소화 — `id` / `userId` 같은 키만 `final` non-null.
- 나머지 모든 필드 nullable (`String?` / `int?` / `double?` / `DateTime?`).
- 모든 모델에 `final Map<String, dynamic>? raw` 필드.
- `fromJson` 시 `raw = Map<String, dynamic>.from(json)` 으로 통째 보존. 키명 차이 대응 용.
- Confidence / ID 등 형식 유동적인 값은 helper 로 흡수 (예: `AnalysisResult.parseConfidence` 가 `0.85` / `85` / `"85%"` 다 처리).

---

## 수정 절차

1. 실제 API 응답 한 번 통째로 `print('[API] $rawJson')`.
2. `mobile/docs/integration_notes.md` 에 응답 키 / 값 형식 기록.
3. 해당 모델 `fromJson` 만 손봄.
4. `flutter analyze` 통과 확인.
5. 화면은 손대지 않는다.

---

## 파일 목록

- `user.dart` — `User`, `Profile`
- `meal.dart` — `Meal`, `FoodCandidate`, `FoodNutritionProfile`
- `supplement.dart` — `Supplement`, `SupplementIngredient`
- `analysis_result.dart` — `AnalysisResult` (출력 카드 정본 + `parseConfidence` helper)
- `agent_memory.dart` — `AgentMemory`, `AgentRun`
- `daily_score.dart` — `DailyScore`
- `chat_message.dart` — 기존 셸, 추후 보강

---

## 합치기 키 차이 요약 (`integration_notes.md` 상세)

- `nickname` ↔ sunghoon `display_name`
- `gender` "M"/"F" (sunghoon) ↔ "male"/"female" (yeong-tech)
- `user_id` int (sunghoon) ↔ UUID (yeong-tech)
- `confidence` 백엔드는 일관 0~1 float. 화면 표시 시 `×100`.
- `analysis_type` 3종 (yeong-tech) vs 기획서 5종 — `kind` 는 `String?` 으로 자유롭게.
- `result_snapshot: dict[str, Any]` 통째 → `Map<String, dynamic>?` 으로 받음.
