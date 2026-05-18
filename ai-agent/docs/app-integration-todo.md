# AI Agent 앱 통합 TODO

## Summary

`ai-agent` MVP는 deterministic Health Agent와 Local LLM 설명 레이어를 검증하는
독립 작업 공간이다. 실제 Lemon Aid 앱에 붙일 때는 이 내부 모델을 기존
FastAPI/DB/승인 흐름 계약에 맞추는 adapter 작업을 별도 단계로 진행한다.

핵심 원칙은 `DailyHealthAgent`를 앱 계약에 직접 끼워 넣지 않고, 얇은 adapter가
`AgentInput`/`AgentOutput`, `agent_runs`, `agent_memory`, preview/approval 흐름을
연결하게 하는 것이다.

## Integration TODO

### 1. 계약 확인

- [ ] `changmin-plan/docs/planning/guide/06-ai-agents.md`의 `AgentInput`,
  `AgentOutput` 계약을 실제 backend 코드와 대조한다.
- [ ] backend에 이미 존재하는 Pydantic 모델, API route, DB logging 모듈을 확인한다.
- [ ] `agent_runs`와 `agent_memory` 테이블/모듈의 현재 구현 여부를 확인한다.
- [ ] 앱의 preview/approval API 흐름이 현재 어디에 구현되어 있는지 확인한다.

### 2. Adapter 설계

- [ ] `DailyHealthAgent` 입력 adapter를 설계한다.
  - `AgentInput.user_id` -> `UserProfile.user_id`
  - `AgentInput.payload` -> `DailyIntake`, `HealthTrend`, `ReferenceRange`
  - `AgentInput.context` -> `UserProfile` 또는 personalization context source
- [ ] `DailyCoachingResult` 출력 adapter를 설계한다.
  - findings/recommendations/actions를 앱 응답 스키마로 변환
  - `approval_status="requires_confirmation"`이면 저장/액션 실행 없이 preview 응답
  - `approval_status="confirmed"`일 때만 후속 저장/액션 후보로 연결
- [ ] adapter는 `DailyHealthAgent` 내부 dataclass를 Pydantic으로 강제 교체하지
  않는다.
- [ ] adapter에서 `request_id`, `agent_name`, `used_tools`, `latency_ms`,
  `cost_usd`를 채운다.

### 3. 승인 전/후 흐름

- [ ] OCR 분석 직후에는 사용자 preview를 반환한다.
- [ ] 사용자가 수정/승인하기 전에는 DB 저장, 알림 등록, 캘린더 등록, 복용 기록
  같은 action을 실행하지 않는다.
- [ ] 승인 후 동일 request 또는 승인 payload로 `DailyHealthAgent`를 다시 실행한다.
- [ ] 미승인 OCR source가 남아 있으면 `requires_confirmation`으로 멈추는 현재
  방어선을 유지한다.

### 4. 로깅과 메모리

- [ ] adapter 호출 단위로 `agent_runs`에 성공/실패, latency, cost, provider,
  request_id를 기록한다.
- [ ] `FakeLLMClient` 사용 시 cost는 `0`으로 기록한다.
- [ ] Ollama/vLLM 같은 self-hosted provider는 API 비용 대신 runtime/provider 정보를
  기록한다.
- [ ] `agent_memory` 갱신은 평가 완료 후 별도 단계로 연결한다.

### 5. 안전성

- [ ] adapter 응답 직전에도 사용자 노출 text를 `SafetyGuard`로 검사한다.
- [ ] trace 원문은 기본 응답에 노출하지 않고, 디버그/내부 로그용으로만 제한한다.
- [ ] LLM prompt에는 원본 이미지, 전체 OCR 원문, 개인 식별 정보, 시크릿을 넣지
  않는다.
- [ ] 건강 판단은 `DailyHealthAgent` deterministic 결과를 기준으로 하고, LLM 응답은
  설명 레이어로만 유지한다.

### 6. 테스트

- [ ] adapter input mapping 테스트
- [ ] `requires_confirmation` preview 응답 테스트
- [ ] 승인 후 confirmed 응답 테스트
- [ ] unsafe trace/text 차단 테스트
- [ ] `agent_runs` logging mock 테스트
- [ ] LLM provider가 없어도 `FakeLLMClient`로 통과하는 테스트
- [ ] FastAPI route가 있다면 route-level 테스트 추가

## Assumptions

- 실제 앱 통합 전까지 `ai-agent`는 독립 패키지 형태를 유지한다.
- `AgentInput`/`AgentOutput` 호환성은 adapter에서 맞추고, 내부 dataclass 모델은
  유지한다.
- OCR/DB/CGM/혈당 API 직접 연동은 adapter 이후 별도 작업이다.
- LLM provider 변경 시 공식 문서를 먼저 확인하고 문서에 공식 URL을 남긴다.
