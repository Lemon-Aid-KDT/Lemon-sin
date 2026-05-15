# 04. Step By Step Implementation Roadmap

이 로드맵은 문서 정리 이후 구현을 작은 PR 단위로 나누기 위한 실행 기준이다.
각 단계는 선행 조건, 연결 파트, 검증 방법을 포함한다.

## Phase A. 문서 정렬

### A1. Agent 용어 통일

목표:
- "4 Agent"와 `analysis_agent` 표현을 `분석 알고리즘 + 3 Agent`로 정리한다.

수정 후보:
- `README.md`
- `PROJECT_GUIDE.md`
- `backend/src/agents/README.md`
- 관련 dev-guides

완료 기준:
- 공식 문서에서 Agent는 `personalization`, `evaluation`, `chat`만 Agent로 부른다.
- 분석/OCR/영양소 산출은 분석 알고리즘 또는 파이프라인으로 부른다.

검증:
- `rg -n "4개 Agent|4 Agent|analysis_agent|분석 Agent"` 결과 확인
- `PROJECT_GUIDE.md` 수정 시 guide sync check 실행

### A2. 브랜치 흡수 기준 공유

목표:
- 각 브랜치 산출물을 그대로 merge하지 않고 판정 기준으로 분류한다.

완료 기준:
- `00-current-branch-map.md`와 `03-branch-absorption-plan.md`가 최신 브랜치명과 맞다.
- 팀이 `그대로 merge`, `부분 cherry-pick`, `재작성`, `문서만 참고`, `보류`를 같은 뜻으로 쓴다.

검증:
- `git ls-remote --heads`로 브랜치명 재확인
- PR 설명에 흡수 판정 타입 명시

## Phase B. Backend foundation

### B1. DB/auth/profile 최소 기반

목표:
- Agent가 사용자별 context를 안전하게 읽을 수 있는 기반을 만든다.

선행:
- A1 완료
- `sunghoon-database`, `taedong-design`, `yeong-tech` auth/profile 차이 비교

수정 대상:
- `backend/src/config.py`
- `backend/src/db/*`
- `backend/src/models/user.py`
- `backend/src/models/profile.py`
- `backend/src/api/auth.py`
- `backend/src/api/profile.py`
- `backend/.env.example`

연결 파트:
- 개인화 Agent
- 동의/개인정보
- 모바일 auth

검증:
- auth/profile 단위 테스트
- migration 생성/적용 테스트
- secret이 repo에 없는지 확인

### B2. Consent and privacy gate

목표:
- OCR, 건강 데이터, 민감정보 분석, Agent 실행 전에 동의 상태를 확인한다.

선행:
- B1 완료

수정 대상:
- consent policy
- privacy API
- audit log model
- dependency guard

연결 파트:
- supplement analyze
- meal analyze
- health sync
- Agent orchestrator

검증:
- 동의 없음: 403 또는 명확한 차단 응답
- 동의 있음: 다음 단계 진행
- 동의 철회 후 Agent 실행 차단

## Phase C. Deterministic analysis core

### C1. KDRIs/RDA lookup

목표:
- evaluation Agent가 의존할 영양 기준을 LLM 없이 계산한다.

후보:
- `jongpil-tech`의 `rda_matcher.py`
- `yeong-tech`의 KDRIs 2025 dataset, source manifest

수정 대상:
- `backend/src/nutrition/*` 또는 기존 합의된 경로
- `data/rda/*` 또는 `data/kdris/*`

검증:
- 기준 row count와 source version 확인
- age/gender 조건별 lookup 테스트
- unknown nutrient 처리 테스트

### C2. Meal input pipeline

목표:
- 음식 사진 또는 텍스트를 nutrition result schema로 변환한다.

후보:
- `jongpil-tech`의 `backend/src/meal/*`

정책:
- MVP는 mock prediction과 텍스트 파서 우선
- 실제 YOLO/GCV는 adapter 계약만 둔다
- 자동 확정 confidence 기준은 UI review 상태와 연결한다

검증:
- sample image hash -> mock prediction
- text input -> normalized food candidates
- low confidence -> `needs_user_review`

### C3. Supplement preview pipeline

목표:
- 영양제 이미지/OCR 결과를 사용자가 승인하기 전 preview로 멈춘다.

후보:
- `yeong-tech` supplement analyze/ocr-text/registration flow

정책:
- raw OCR text 저장 금지
- OCR hash, provider, confidence, sanitized parsed snapshot만 저장
- confirmed 전에는 user supplement로 등록하지 않는다

검증:
- upload -> preview
- OCR text attach -> parsed preview
- confirm -> registered supplement
- revoke consent -> blocked

## Phase D. Agent contract

### D1. Agent schemas

목표:
- 3 Agent와 오케스트레이터의 입출력 계약을 만든다.

수정 대상:
- `backend/src/agents/schemas.py`
- `backend/src/llm/schemas.py`

필수:
- `AgentInput`
- `AgentOutput`
- `AgentMemorySnap`
- `PersonalizationContext`
- `EvaluationResult`
- `ChatAgentResult`
- `ToolPreview`

검증:
- valid mock payload 통과
- missing required field 실패
- `agent_name="analysis"` 실패

### D2. Mock orchestrator

목표:
- 실제 LLM 없이 `personalization -> evaluation -> optional chat` 흐름을 실행한다.

수정 대상:
- `backend/src/agents/orchestrator.py`
- `backend/src/agents/personalization_agent.py`
- `backend/src/agents/evaluation_agent.py`
- `backend/src/agents/chat_agent.py`
- `backend/src/agents/memory.py`

정책:
- deterministic mock 응답
- request_id 공유
- agent_runs 기록
- PHI 원문 로그 금지

검증:
- 같은 입력 -> 같은 mock 결과
- Agent 실패 -> fallback status
- latency/cost field 기록

### D3. Safety filter

목표:
- 모든 Agent 응답과 Tool preview가 의료/복약 금지 표현을 통과해야 사용자에게 보인다.

수정 대상:
- `backend/src/utils/regex_filter.py`
- Agent response path
- Tool preview path

검증:
- 금지 표현 차단
- 대체 문구 통과
- 최대 재생성 횟수 초과 시 안전 fallback

## Phase E. Tool preview and mobile UI

### E1. Tool preview API

목표:
- 챗봇 Agent가 알림/캘린더/섭취 기록을 바로 실행하지 않고 preview를 반환한다.

수정 대상:
- `backend/src/llm/tools.py`
- `backend/src/api/chat.py`
- `backend/src/api/reminders.py`
- `backend/src/api/calendar.py`

검증:
- chat request -> tool preview
- approve request -> 실제 저장
- reject/cancel -> 저장 없음

### E2. Mobile preview/approval

목표:
- 사용자가 Agent 제안을 확인하고 승인하는 화면을 연결한다.

후보:
- `taedong-design` mobile UI

수정 대상:
- `mobile/lib/screens/chat_screen.dart`
- `mobile/lib/widgets/supplement_preview.dart`
- `mobile/lib/services/api_client.dart`
- `mobile/lib/services/notification_service.dart`
- `mobile/lib/services/calendar_service.dart`

검증:
- preview card 표시
- 승인 전 local notification/calendar 등록 없음
- 승인 후 성공/실패 상태 표시

## Phase F. Provider integration

### F1. Provider policy decision

목표:
- Claude-first, local-first, hybrid 중 하나를 정한다.

결정 입력:
- 비용
- 개인정보 노출
- 한국어 품질
- 로컬 운영 난이도
- 발표 안정성

완료 기준:
- 환경변수 표 확정
- provider adapter contract 확정
- production guard 확정

### F2. Real LLM adapter

목표:
- mock Agent를 실제 provider adapter와 교체 가능하게 만든다.

선행:
- D1-D3 완료
- F1 결정 완료

검증:
- 네트워크 없는 테스트는 mock으로 통과
- provider integration test는 명시적 opt-in
- timeout/fallback/cost tracking 동작

## 문서 동기화 규칙

- 새 API: API 문서, 호출 흐름, roadmap 갱신
- 새 Agent/Tool: Agent 표, Tool 표, safety filter, roadmap 갱신
- 새 DB: 데이터 모델, migration, consent/audit 문서 갱신
- 새 화면: mobile 화면 목록, preview/approval 흐름 갱신
- 새 provider/env: 시크릿 표, `.env.example`, deployment 문서 갱신

## MVP 우선순위

1. 문서와 용어 정렬
2. user/profile/consent
3. deterministic nutrition/supplement/meal result
4. 3 Agent mock contract
5. safety filter
6. preview/approval
7. 실제 LLM provider

