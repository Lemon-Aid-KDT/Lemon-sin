# Lemon 런타임 Agent 변경

`backend/src/agents/`, `backend/src/llm/`, OCR 파싱, 프롬프트 거버넌스,
Tool 실행 등 Lemon Aid 런타임 AI 동작을 수정할 때 이 skill을 사용합니다.

## 필수 확인 문맥

- `AGENTS.md`
- `PROJECT_GUIDE.md`가 있으면 우선 확인하고, 없으면 `docs/guide/06-ai-agents.md`
- `docs/guide/08-compliance-safety.md`
- `docs/guide/09-team-workflow.md` 17.10 섹션

## 설계 규칙

- 현재 아키텍처는 결정론적 분석 파이프라인 + 개인화, 평가, 챗봇 Agent입니다.
- 가이드가 명시적으로 바뀌지 않는 한 분석은 독립 런타임 LLM Agent가 아닙니다.
- 프롬프트는 버전 태그와 schema 검증을 유지합니다.
- Tool 호출은 사용자 출력 전에 검증과 안전 문구 검수를 통과해야 합니다.
- 영속 액션은 사용자 미리보기와 승인을 필요로 합니다.

## 검증

- schema 검증, 금지 표현, Tool 라우팅, 실패 상태에 대한 집중 테스트를 추가하거나
  갱신합니다.
- 가장 작은 관련 테스트 명령을 실행하고, 건너뛴 검증이 있으면 이유를 남깁니다.
