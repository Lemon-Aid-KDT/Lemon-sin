# 01. Role And Ownership Sync

이 문서는 `PROJECT_GUIDE.md`의 팀 분담과 원격 브랜치에서 실제 진행된 작업의 차이를
정렬한다. 목적은 누구의 작업을 덮어쓸지 정하는 것이 아니라, 구현 전 리뷰 경계와
문서 책임을 명확히 하는 것이다.

## 기준 원칙

- 기능 책임은 브랜치 이름보다 실제 산출물과 파일 경계를 우선한다.
- `PROJECT_GUIDE.md`와 실제 브랜치가 다르면 이 문서에 먼저 차이를 기록하고,
  합의된 내용만 가이드에 반영한다.
- `main` 직접 수정은 피하고, 작업 브랜치에서 작게 나눈 PR로 반영한다.
- 건강 로직, 복약, 영양제, 개인정보, 동의, 면책 문구는 안전 리뷰를 별도 트리거로 둔다.

## 실제 작업 축

| 축 | 실제 산출물 위치 | 관련 브랜치 | 연결 파트 | 우선 리뷰어 |
|----|------------------|-------------|-----------|-------------|
| 기획/중심 가이드 | `PROJECT_GUIDE.md`, `docs/planning/guide/*` | `main`, `changmin-plan` | 전체 | 문서 담당 + 기능 담당 |
| DB/auth/profile | `backend/src/db/*`, `models/*`, `api/auth.py`, `api/profile.py` | `sunghoon-database`, `taedong-design`, `yeong-tech` | Agent context, consent, audit | 백엔드 담당 |
| 식단 인식/RDA | `backend/src/meal/*`, `nutrition/rda_matcher.py`, `data/rda/*` | `jongpil-tech` | meal analysis, evaluation Agent | 알고리즘/데이터 담당 |
| 영양제 분석/등록 | `supplements.py`, supplement models/schemas/services | `yeong-tech`, `sunghoon-database` | supplement preview, chat Tool | 백엔드 + 데이터 담당 |
| 개인정보/동의/보안 | `privacy/*`, `security/*`, consent policies | `yeong-tech` | 모든 Agent 입력과 저장 | 백엔드 + 안전 담당 |
| 모바일 UI | `mobile/lib/screens/*`, `widgets/*`, `services/*` | `taedong-design`, `sunghoon-database` | preview, chat, dashboard | 프론트/UI 담당 |
| Agent/LLM | `backend/src/llm/*`, `backend/src/agents/*` | guide 중심, 일부 yeong-tech | Agent orchestration | AI 담당 |
| CI/협업 규칙 | `.github/*`, sync scripts, CODEOWNERS | `yeong-tech`, `jongpil-tech`, `main` | PR 검증, guide sync | 인프라/문서 담당 |

## Agent 책임 기준

`분석 알고리즘 + 3 Agent`를 공식 구현 기준으로 둔다.

| 구성 | 책임 | 담당 코드 경계 | Agent 여부 |
|------|------|----------------|------------|
| 분석 알고리즘 | OCR, 이미지/텍스트 구조화, 음식/영양제 매칭, 영양소 산출 | `ocr/`, `meal/`, `nutrition/`, `supplements/`, `algorithms/` | 아님 |
| 개인화 Agent | 프로필, 만성질환, 복약, 검사값을 기준 정보로 요약 | `agents/personalization_agent.py` | 맞음 |
| 평가 Agent | 분석 결과와 개인화 기준으로 점수, 부족/과다, 개선 피드백 생성 | `agents/evaluation_agent.py` | 맞음 |
| 챗봇 Agent | 설명, 알림/캘린더/섭취 기록 preview 생성 | `agents/chat_agent.py` | 맞음 |

정리 필요 표현:
- "4개 Agent"
- `analysis_agent.py`
- "OCR + 영양소 산출 Agent"
- "AI가 바로 저장"

대체 표현:
- "분석 알고리즘"
- "OCR/식단/영양제 파이프라인"
- "3개 Agent"
- "사용자 미리보기 후 승인"

## 문서 책임

| 변경 | 반드시 같이 봐야 할 문서 |
|------|--------------------------|
| 새 API | API 표, 호출 흐름, 데이터 모델, 구현 문서 |
| 새 Agent/Tool | Agent 표, Tool 표, Agent 흐름, 안전 필터, 구현 문서 |
| 새 DB 테이블/컬럼 | 데이터 모델, 보안/동의, migration 문서 |
| 새 화면 | 화면 표, mobile 구조, 사용자 승인/미리보기 흐름 |
| 새 외부 SDK | 기술 스택, 환경변수, 시크릿, CI |
| 새 의료/복약 표현 | 안전선, 금지어 필터, 테스트/golden 문구 |

## 충돌 처리 기준

1. 같은 기능이 여러 브랜치에 있으면 먼저 schema와 API 계약을 비교한다.
2. 보안/동의/민감정보 처리 수준이 높은 쪽을 기준 후보로 삼는다.
3. 모바일 UI와 백엔드 API는 한 PR에 섞지 않는다.
4. 대형 하위 프로젝트는 직접 merge하지 않고 필요한 파일과 패턴만 재작성 또는 선별 흡수한다.
5. 문서에서 3 Agent 기준을 벗어난 표현은 구현 전 정리한다.

## 현재 확정 사항

- Agent 수는 3개다.
- Agent 도입은 mock-first로 시작한다.
- `yeong-tech`의 local Ollama 정책은 유용한 참고지만, 기존 Claude/OpenAI 정책을
  바꾸려면 별도 의사결정 문서가 필요하다.
- `docs/implementation`은 실제 코드 통합 전 중간 기준 문서 위치다.

