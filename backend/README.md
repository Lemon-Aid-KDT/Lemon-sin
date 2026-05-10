# backend/ — FastAPI

> 담당: **D 백엔드** (메인) + **C AI 엔지니어** (llm/, agents/, ocr/)
> 참조: §5 백엔드, §13 파일 구조, §부록 A.1~A.6

## D1 셋업

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
# Docker는 루트에서 docker compose up -d
alembic init -t async alembic   # 첫 사람만
alembic revision --autogenerate -m "init"
alembic upgrade head
uvicorn src.main:app --reload --port 8000
```

## 핵심 파일 (D1 코드 시그니처는 §부록 A.6)

- src/main.py : FastAPI 진입점 (D)
- src/config.py : 환경변수 로딩 (D)
- src/agents/orchestrator.py : 4 Agent 분기 + agent_runs 로깅 (C)
- src/llm/prompts.py : 시스템 프롬프트 + 버전 태그 (C)
- src/llm/tools.py : Tool Use 함수 정의 5개 (C, §3.3)
- src/utils/regex_filter.py : 의료법 표현 검수 (C)
- src/services/email.py : 이메일 인증 발송 (D)
