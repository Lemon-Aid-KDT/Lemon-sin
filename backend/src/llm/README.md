# llm/ — Claude / OpenAI / 프롬프트 / Tool / 스키마 (C 담당)

§7 AI 스택 참조.

- claude_client.py : Claude SDK 래퍼 (재시도·캐시·타임아웃)
- openai_client.py : OpenAI 백업
- prompts.py : 시스템 프롬프트 + 버전 태그
- schemas.py : Pydantic 출력 스키마
- tools.py : Tool Use 함수 정의 5개 (§3.3)
