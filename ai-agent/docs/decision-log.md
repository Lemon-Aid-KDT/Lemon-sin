# 의사결정 기록

## 2026-05-18: AI Agent 방향

- 작업 브랜치는 `changmin-aiagent`입니다.
- 새 Agent 작업은 `ai-agent/` 아래에 격리합니다.
- 여기서 말하는 MVP는 버리는 데모가 아니라, 상용화를 향한 최소 제품 경로입니다.
- 혈당과 CGM 연동은 MVP 구현 범위에서 제외합니다.
- Agent 인터페이스에는 범용 건강 흐름 입력을 유지합니다. 이후 혈당, CGM, 체중,
  활동량, 식단 점수 흐름을 추가할 수 있게 하기 위함입니다.
- 민감한 건강 데이터를 다루므로 외부 LLM API는 선호하는 운영 경로가 아닙니다.
  아키텍처는 서버 운영 또는 self-hosted LLM 사용을 전제로 둡니다.
- OCR 저신뢰 대응은 이번 작업의 중심이 아닙니다. 핵심 문제는 신뢰 가능한 OCR
  섭취 데이터를 안전한 건강관리 코칭으로 바꾸는 것입니다.
- MVP에서 영양제 제안은 성분 중심으로 제한합니다. 특정 제품 추천은 법무, 약사,
  광고, 이해상충 검토가 끝나기 전까지 범위 밖입니다.
- LLM 출력은 건강 판단의 최종 권위가 아닙니다. 공식 데이터, 결정론적 영양 로직,
  사용자 맥락, Safety Guard 정책이 최종 기준입니다.
- Chat Agent는 독립 판단자가 아니라 `DailyCoachingResult`와 trace를 설명하는
  얇은 레이어로 둡니다.
- Chat Agent의 LLM 연결은 생성자 주입으로 분리합니다. 테스트에서는
  `FakeLLMClient`를 기본으로 사용해 네트워크 의존성을 제거합니다.
- 로컬 개발용 LLM runtime 1차 후보는 Ollama입니다. 개발자는 필요한 모델을 직접
  준비하고 `OllamaClient(model=...)`를 주입합니다. 공식 문서는
  [Ollama Chat API](https://docs.ollama.com/api/chat)를 기준으로 확인합니다.
- 운영용 고성능 serving 후보는 vLLM 같은 OpenAI-compatible endpoint입니다.
  `OpenAICompatibleClient`는 `/v1/chat/completions` 호환 서버에 연결합니다.
  공식 문서는
  [vLLM OpenAI-Compatible Server](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/)와
  [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)를
  기준으로 확인합니다.
- provider 선택은 이번 단계에서 설정 파일이나 환경변수 로딩으로 묶지 않습니다.
  앱 통합 시 별도 설정 계층에서 주입합니다.
- 외부 LLM API로 실제 건강 데이터, 원본 OCR 전체, 이미지, 시크릿을 보내지 않는
  원칙을 유지합니다. prompt에는 설명에 필요한 최소 findings, recommendations,
  trace 요약만 포함합니다.
- LLM 응답은 `SafetyGuard`를 통과해야만 노출합니다. 실패하거나 안전하지 않으면
  deterministic fallback 답변을 반환하고 건강 판단 결과는 그대로 둡니다.
- 공식 문서가 있는 LLM runtime, provider, serving API를 추가하거나 바꿀 때는
  구현과 문서에 공식 문서 URL을 함께 남깁니다. 2차 자료는 보조 근거로만 봅니다.
- 미승인 OCR source는 deterministic 평가로 넘기지 않고 preview-only 결과로
  멈춥니다. 사용자 승인 후 다시 실행해야 recommendations와 actions가 생성됩니다.
- trace는 Chat fallback과 LLM prompt에 그대로 노출될 수 있으므로 `SafetyGuard`로
  검사합니다. 위험 문구가 포함된 trace line은 원문을 숨기고 차단 문구로 대체합니다.
- 영양소 합산은 최소 alias/unit 정규화를 먼저 적용합니다. 현재 범위는
  비타민 D alias, `g/mg/mcg`, 비타민 D `IU -> mcg` 변환이며 전체 OCR alias와
  confidence 처리는 후속 OCR/DB 통합 범위로 둡니다.
- 기존 기획 문서의 `AgentInput`/`AgentOutput`, `agent_runs`, `agent_memory`
  계약은 `DailyHealthAgent` 내부 모델에 직접 섞지 않고 FastAPI/DB 통합 adapter에서
  맞춥니다.
- 영양제 성분 총량은 Supplement Engine에서 별도 계산해 UI와 검토 흐름에서
  음식+영양제 합산 결과와 구분해 볼 수 있게 합니다.
- Intake 결과에는 OCR 원본 이미지 ID, OCR 텍스트, 사용자 확인 여부를 보존합니다.
