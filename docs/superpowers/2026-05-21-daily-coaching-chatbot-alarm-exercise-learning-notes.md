# Daily Coaching, Chatbot, Alarm, Exercise Learning Notes

이 문서는 `2026-05-21-daily-coaching-chatbot-alarm-exercise-todo.md` 체크리스트를 진행하면서 각 완료 항목에서 배운 구현 판단을 누적한다.

## 2026-05-21 Task 2: Chat API Route

### 완료 체크리스트

- `POST /api/v1/ai-agent/chat` route를 `sensitive_health_analysis` 동의 뒤에 추가했다.
- chat route가 `agent_memory` context를 읽고 response `used_tools`에 `agent_memory`를 표시하도록 했다.
- chat route에서는 `upsert_daily_coaching_memory`와 `record_agent_run`을 호출하지 않는다. 아직 구조화된 confirmed coaching action이 없기 때문에 daily coaching run으로 저장하면 안 된다.
- fake SGLang client API 테스트로 `provider="sglang"`와 한국어 카드형 응답 구조를 검증했다.
- preview/unconfirmed chat context가 들어와도 daily coaching memory/run persistence가 발생하지 않는 API 테스트를 추가했다.

### 학습 포인트

- `daily-coaching`은 확정 입력을 기반으로 memory와 run log를 남기는 실행형 endpoint이고, `chat`은 현재 단계에서 답변형 endpoint다. 둘은 같은 안전 기준과 LLM provider를 공유하지만 persistence boundary는 다르게 둔다.
- route 계층에서 서버 소유 `current_user.subject`를 사용하고, client `user_id`는 신뢰하지 않는다.
- 메모리 컨텍스트는 raw log가 아니라 요약 컨텍스트로만 LLM grounding에 넣어야 한다. 사용자 응답에는 `trace`, `supplement totals`, `nutrition findings`, `internal_trace` 같은 내부 문자열이 나오면 안 된다.
- 동의 실패 audit action은 daily coaching과 chat을 분리해야 나중에 감사 로그에서 feature별 차단 이유를 추적하기 쉽다.

### 검증

- `python -m pytest --no-cov backend\Nutrition-backend\tests\integration\api\test_ai_agent_api.py -q`
- 결과: `10 passed`, `requests` dependency warning 1건.

## 2026-05-21 Task 2: Flutter Chat MVP

### 완료 체크리스트

- Flutter `ChatTurn`, `ChatbotRequest`, `ChatbotResponse` DTO를 추가했다.
- `ChatRepository`에서 `sensitive_health_analysis` 동의 endpoint와 `/api/v1/ai-agent/chat` endpoint를 호출하도록 연결했다.
- chat 화면에 message list, input box, send button, provider/memory badge, medical disclaimer를 추가했다.
- dashboard에서 `/chat` route로 들어가는 카드를 추가했고 `app.dart`에 `ChatScreen` route를 등록했다.

### 학습 포인트

- 모바일 chat request도 daily coaching과 동일하게 client `userId`는 placeholder로 두고, 서버가 인증된 사용자 기준으로 소유권을 정한다.
- chat 화면은 raw error를 보여주지 않고 고정된 사용자 문구만 보여준다. 네트워크나 인증 오류 세부 정보는 사용자에게 그대로 노출하지 않는다.
- provider와 memory는 작은 badge로 보여주되, trace나 내부 tool 문자열은 message body에 섞지 않는다.
- Daily Coaching 화면의 카드형 응답 구조를 chat에서도 말투 기준으로 재사용하지만, chat은 별도 endpoint와 별도 화면으로 유지한다.

### 검증

- `python -m pytest --no-cov backend\Nutrition-backend\tests\unit\mobile\test_flutter_ai_agent_contract.py -q`
- 결과: `13 passed`.
- `C:\src\flutter\bin\flutter.bat analyze`
- 결과: `No issues found`.
- `C:\src\flutter\bin\flutter.bat test`
- 결과: `All tests passed`.

## 2026-05-21 Task 3: Alarm and Reminder Planning Layer

### 완료 체크리스트

- 리마인더 카테고리를 `supplement_reminder`, `meal_check_in`, `daily_coaching_prompt`, `safety_follow_up`으로 정의했다.
- `reminder_preferences` 테이블과 SQLAlchemy model을 추가해 사용자 알림 선호도를 push delivery token과 분리했다.
- health-related reminder 생성/수정/비활성화는 `sensitive_health_analysis` 동의 뒤에만 가능하도록 했다.
- `/api/v1/notifications/reminders` list/create/update/disable API를 추가했다.
- 실제 FCM/APNs push 발송은 구현하지 않았다.
- disabled reminder가 dispatch 후보에서 제외되는 테스트를 추가했다.
- reminder 문구가 diagnosis/treatment/prescription 표현을 포함하면 schema validation에서 거부되도록 했다.
- Flutter 알림 설정 화면에 category dropdown, time input, enabled switch, disclaimer를 추가했다.

### 학습 포인트

- 알림 기능은 push token 저장보다 먼저 user preference boundary를 잡는 것이 안전하다. 이 단계에서는 "무엇을 언제 받고 싶은지"만 저장하고, 실제 발송 infra는 다음 단계로 남겼다.
- 리마인더 문구도 건강 문구이므로 backend schema에서 금지 표현을 막아야 한다. UI 문구만 조심하면 API 직접 호출에서 우회될 수 있다.
- 비활성화는 삭제가 아니라 `enabled=false`와 `disabled_at` 기록으로 처리했다. 나중에 사용자의 설정 이력과 재활성화 흐름을 만들 수 있다.
- API 테스트는 route가 현재 인증 사용자만 사용하고 client-supplied owner 필드를 받지 않는 패턴을 유지했다.

### 검증

- `python -m pytest --no-cov backend\Nutrition-backend\tests\integration\api\test_notifications_api.py backend\Nutrition-backend\tests\unit\mobile\test_flutter_ai_agent_contract.py -q`
- 결과: `18 passed`, `requests` dependency warning 1건.
- `C:\src\flutter\bin\flutter.bat analyze`
- 결과: `No issues found`.
- `C:\src\flutter\bin\flutter.bat test`
- 결과: `All tests passed`.

## 2026-05-21 Task 4: Exercise App Integration Context

### 완료 체크리스트

- MVP source를 manual activity entry first로 결정하고, HealthKit/Health Connect는 disabled placeholder로 남겼다.
- activity context 필드를 steps, active minutes, activity energy kcal, workout type, source, date, user confirmation으로 정의했다.
- `ConfirmedActivityEntry`를 추가하고 confirmed activity만 Daily Coaching `payload.health_trends`에 직렬화되도록 했다.
- sleep, route/location, blood glucose, blood pressure, menstrual/cycle data는 수집하지 않았다.
- Flutter activity 화면에 수동 입력과 비활성 HealthKit/Health Connect placeholder를 추가했다.
- confirmed-only activity context 테스트를 추가했다.
- 화면/문구는 activity recommendation 범위에 머물고 medical prescription 성격의 표현을 넣지 않았다.

### 학습 포인트

- HealthKit/Health Connect는 OS 권한, 별도 동의, platform 설정이 붙는 작업이라 이번 단계에서는 자동 연동을 켜지 않는 것이 맞다.
- Daily Coaching에 연결되는 health context는 반드시 user-confirmed 데이터만 넣어야 한다. preview source는 `health_trends`에 들어가면 memory/run log 경계가 흐려진다.
- activity context는 backend activity score 계산을 대체하지 않는다. 현재는 코칭 grounding에 필요한 최소 요약만 제공한다.
- 민감 건강 데이터 범위를 넓힐 때는 수집하지 않는 항목을 코드와 테스트에서 명시해야 추후 확장 시 scope creep을 막기 쉽다.

### 검증

- `python -m pytest --no-cov backend\Nutrition-backend\tests\unit\mobile\test_flutter_ai_agent_contract.py -q`
- 결과: `15 passed`.
- `C:\src\flutter\bin\flutter.bat test`
- 결과: `All tests passed`.
- `C:\src\flutter\bin\flutter.bat analyze`
- 결과: `No issues found`.

## 2026-05-21 Task 5: Connect Context Back Into Daily Coaching

### 완료 체크리스트

- Task 4의 confirmed activity model이 구현된 뒤 Daily Coaching `payload.health_trends`에 activity context를 연결했다.
- chatbot route가 `agent_memory`를 읽고, raw log가 아니라 안전한 summary만 LLM grounding에 전달하도록 테스트를 보강했다.
- reminder recommendation이 proposed action으로 변환될 수 있게 하고, action은 `requires_user_approval=True`를 유지하도록 했다.
- Daily Coaching API response의 `debug_trace`가 기본 빈 배열로 유지되는지 activity context 테스트에서 확인했다.
- chat, reminder, activity context가 `internal_trace`, `supplement totals`, route/location, blood pressure, sleep 같은 raw sensitive text를 노출하지 않는 테스트를 추가했다.

### 학습 포인트

- "연결"은 데이터를 많이 섞는 것이 아니라, confirmed context와 summary-memory만 통과시키는 boundary를 유지하는 일이다.
- reminder는 제안과 실행을 분리해야 한다. proposed action은 만들 수 있지만 실제 알림 enable은 사용자 승인 API를 별도로 타야 한다.
- `debug_trace`는 개발 중에는 유용하지만 제품 API 기본값에서는 비워 두는 것이 맞다. 내부 trace가 필요하면 명시 옵션으로만 열어야 한다.
- activity context는 Daily Coaching에 들어가도 raw device field를 그대로 노출하면 안 된다. 모바일에서 아예 민감 항목을 수집하지 않고, backend도 필요한 요약 필드만 읽는 구조가 안전하다.

### 검증

- `python -m pytest --no-cov backend\ai_agent_chat\tests\test_action_agent.py backend\ai_agent_chat\tests\test_chat_agent_language.py backend\Nutrition-backend\tests\integration\api\test_ai_agent_api.py -q`
- 결과: `15 passed`, `requests` dependency warning 1건.
- `C:\src\flutter\bin\flutter.bat test`
- 결과: `All tests passed`.

## Final Verification Summary

### 실행한 검증

- `python -m pytest --no-cov backend\ai_agent_chat\tests backend\Nutrition-backend\tests\integration\api\test_ai_agent_api.py backend\Nutrition-backend\tests\integration\api\test_notifications_api.py backend\Nutrition-backend\tests\unit\mobile\test_flutter_ai_agent_contract.py backend\Nutrition-backend\tests\unit\db\test_alembic_setup.py -q`
- 결과: `51 passed, 1 skipped`, `requests` dependency warning 1건.
- `python -m compileall backend\Nutrition-backend\src backend\ai_agent_chat\src`
- 결과: compile 성공.
- `C:\src\flutter\bin\flutter.bat analyze`
- 결과: `No issues found`.
- `C:\src\flutter\bin\flutter.bat test`
- 결과: `All tests passed`.

### 최종 구조 요약

- Daily Coaching은 확정된 음식/영양제/활동 context를 받아 한국어 카드형 응답과 empty `debug_trace` 기본값을 유지한다.
- Chatbot은 `/api/v1/ai-agent/chat` 별도 endpoint에서 동의, agent memory summary, SGLang/deterministic provider, 안전 fallback을 사용한다.
- Reminder는 `/api/v1/notifications/reminders` preference API와 Flutter 설정 화면까지 구현했지만 실제 push 발송은 하지 않는다.
- Activity는 manual confirmed entry first로 구현했고 HealthKit/Health Connect는 permission flow 전까지 disabled placeholder로 남겼다.
