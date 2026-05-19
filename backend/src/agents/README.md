# agents/ — 4개 Agent + 오케스트레이터 + 메모리 (C 담당)

§3.1 / §7.3 참조. 모두 AgentInput → AgentOutput 인터페이스.

- analysis_agent.py : OCR + 영양소 산출
- personalization_agent.py : 만성질환·복약 기준
- chat_agent.py : 설명 + 알림/캘린더
- evaluation_agent.py : 점수 + 부족·과다 분석
- orchestrator.py : 4 Agent 분기 + agent_runs 로깅
- memory.py : agent_memory 갱신
