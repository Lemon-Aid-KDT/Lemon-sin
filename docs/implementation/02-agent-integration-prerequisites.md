# 02. Agent Integration Prerequisites

Agent 기능은 LLM 호출 파일부터 만드는 작업이 아니다. Lemon Aid의 Agent는 건강,
복약, 식단, 영양제, 동의, 개인정보를 함께 다루므로 사전 기반이 없으면 응답을
저장하거나 설명하는 순간 위험해진다.

## 구현 기준

- Agent는 `personalization`, `evaluation`, `chat` 3개다.
- 분석/OCR/음식/영양제 매칭은 Agent 밖의 결정론적 파이프라인이다.
- 첫 구현은 mock-first다.
- 실제 Claude/OpenAI/Ollama 연결은 schema, 안전 필터, preview/approval, logging이
  먼저 통과한 뒤 붙인다.

## 선행 조건 요약

| 선행 조건 | 필요한 이유 | 후보 브랜치 |
|-----------|-------------|-------------|
| 사용자/auth/profile | 개인화 Agent 입력, user_id 격리, 복약/질환 조회 | `sunghoon-database`, `taedong-design`, `yeong-tech` |
| 동의/개인정보 gate | OCR, 건강 데이터, 민감정보 분석 전 법적 동의 확인 | `yeong-tech` |
| DB/Alembic | `agent_runs`, `agent_memory`, preview 상태 저장 | `sunghoon-database`, `yeong-tech` |
| 영양제 preview | AI 결과를 바로 저장하지 않고 사용자가 확인 | `yeong-tech` |
| 식단 인식/영양소 산출 | evaluation Agent 입력 | `jongpil-tech` |
| KDRIs/영양 기준 | 부족/과다 판단의 결정론 기반 | `jongpil-tech`, `yeong-tech` |
| 안전 문구 필터 | 진단/처방/치료 단정 표현 차단 | guide, `jongpil-tech`, `yeong-tech` |
| 모바일 preview UI | 사용자가 승인해야 Tool 실행 가능 | `taedong-design` |

## 백엔드 사전 작업

### 1. 공통 schema

먼저 Pydantic 계약을 확정한다.

필수 모델:
- `AgentInput`
- `AgentOutput`
- `AgentMemorySnap`
- `PersonalizationContext`
- `EvaluationResult`
- `ChatAgentResult`
- `ToolPreview`
- `AgentRunLog`

정책:
- `AgentOutput.agent_name`은 `personalization`, `evaluation`, `chat`만 허용한다.
- `result`는 Agent별 전용 schema를 사용한다.
- raw OCR text, raw LLM response, 개인 건강 원문은 기본 로그에 저장하지 않는다.

### 2. 오케스트레이터

초기 흐름:

1. 분석 파이프라인 결과를 받는다.
2. `AgentMemorySnap`을 조회한다.
3. 개인화 Agent mock을 실행한다.
4. 평가 Agent mock을 실행한다.
5. 챗봇 Agent는 사용자가 질문하거나 설명이 필요한 경우에만 실행한다.
6. 각 실행을 `agent_runs`에 기록한다.
7. 평가 결과 후 `agent_memory` 갱신 후보를 만든다.

초기 구현에서는 모든 Agent가 deterministic mock 응답을 반환해야 한다.

### 3. 저장 모델

필수 테이블:
- `agent_runs`: request_id, user_id, agent_name, status, latency_ms, cost_usd, error_code, created_at
- `agent_memory`: user_id, summary_json, updated_at

선택 테이블:
- `tool_previews`: chat Tool 실행 전 preview 상태를 서버에 보관할 때 사용

주의:
- `agent_runs`에는 PHI 원문을 저장하지 않는다.
- `agent_memory`는 전체 원본이 아니라 요약만 저장한다.
- 삭제/동의 철회 정책과 연결되어야 한다.

### 4. Tool Use

Tool은 초기부터 실제 실행이 아니라 preview를 반환한다.

| Tool | 초기 동작 | 승인 후 연결 |
|------|-----------|--------------|
| `extract_supplement_facts` | OCR text를 schema로 구조화한 preview 생성 | supplement 분석 preview 갱신 |
| `add_reminder` | 알림 등록 preview 생성 | reminders API 저장 + mobile local notification |
| `add_calendar_event` | 일정 등록 preview 생성 | calendar API 저장 + mobile calendar |
| `log_supplement_intake` | 섭취 기록 preview 생성 | user supplement intake 저장 + raffle |
| `explain_deficiency` | 안전 필터를 통과한 설명 생성 | chat response에 표시 |

## 프론트엔드 사전 작업

필수 화면/상태:
- 분석 결과 미리보기
- 사용자 수정
- 승인 버튼
- 챗봇 메시지
- Tool 실행 preview 카드
- 알림/캘린더 권한 요청
- 안전 고지 배너

정책:
- 사용자가 승인하기 전 DB 저장 또는 시스템 알림/캘린더 등록을 하면 안 된다.
- 챗봇이 제안한 실행은 "등록 예정 내용"으로 먼저 보여준다.
- 모바일 앱에는 LLM/OCR/API secret을 넣지 않는다.

## 안전/컴플라이언스 사전 작업

필수 규칙:
- "진단", "처방", "치료 보장", 특정 의약품 추천 표현 차단
- "가능성", "주의", "전문가 상담 권장", "입력 기준" 표현 선호
- 복약/영양제 상호작용은 최종 판단이 아니라 상담 필요 이유로만 안내
- OCR/LLM 추출 결과는 틀릴 수 있음을 preview에서 드러냄

테스트:
- 금지 표현이 포함된 Agent mock 응답 차단
- 안전 문구가 포함된 정상 응답 통과
- Tool 실행 전 승인 상태 확인
- 동의 철회 사용자에 대한 Agent 실행 차단

## Provider 결정 보류 사항

현재 문서와 브랜치 사이에 provider 정책 차이가 있다.

| 기준 | 내용 |
|------|------|
| guide | Claude 주력, OpenAI 폴백 |
| `yeong-tech` | local Ollama parser, `ALLOW_EXTERNAL_LLM=false`, production guard |

1차 구현은 provider 독립 adapter 계약만 만든다. 실제 provider 선택은 다음 중 하나로
별도 결정한다.

- Claude-first: guide와 일치, 외부 비용/시크릿 관리 필요
- Local-first: 개인정보 노출 감소, 로컬 모델 품질/운영 부담 증가
- Hybrid: 기본 local, 특정 구조화/챗봇만 외부 LLM, 정책 복잡도 증가

## Agent 구현 시작 조건

아래 조건이 준비되기 전에는 실제 LLM 호출을 붙이지 않는다.

- user/profile/consent 조회 가능
- 분석 결과 preview schema 존재
- `agent_runs`와 `agent_memory` 저장 정책 확정
- 금지어 필터와 안전 문구 테스트 존재
- Tool preview/approval 계약 존재
- provider secret이 백엔드 환경변수로만 관리됨

