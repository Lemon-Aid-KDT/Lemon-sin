# Appendix D1 Start Guide

> Source: PROJECT_GUIDE.md 부록 A
> 원본 대형 기획서는 PROJECT_GUIDE.md에 보존되어 있습니다.

## 부록 A. D1 즉시 시작 가이드 — 🚀 5명이 지금 바로 작업 시작

### A.0 가장 먼저 (모든 팀원 공통, 30분)

1. **이 문서를 첫 페이지부터 끝까지 한 번 읽기** (스크롤만 1회). 30분 정도 걸린다.
2. 본인의 바이브 코딩 툴(Claude Code / Codex / Cursor / Cline / Windsurf 중 하나)을 열고, 첫 명령으로 `PROJECT_GUIDE.md`를 컨텍스트에 로드한다.
3. GitHub 저장소를 fork 또는 clone하고, 본인 이름으로 `feat/<영역>-setup` 브랜치를 만든다.
4. 팀 채팅에 "🍋 [본인 역할] 시작합니다" 메시지 + 오늘 할 일 한 줄.

### A.1 저장소 클론 + 환경 셋업

```
# 1) 저장소 클론
git clone https://github.com/Lemon-Aid-KDT/Lemon-sin.git
cd Lemon-sin

# 2) 백엔드 의존성
cd backend
python -m venv .venv

# 가상환경 활성화
# macOS/Linux:  source .venv/bin/activate
# Windows cmd:  .venv\Scripts\activate.bat
# Windows PS:   .venv\Scripts\Activate.ps1

pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env

# 3) Docker Compose (timescale + redis + mailhog)
cd ..
docker compose up -d

# 4) DB 마이그레이션 (D1 첫 사람만 1회 init)
cd backend
alembic init -t async alembic
alembic revision --autogenerate -m "init"
alembic upgrade head

# 5) 백엔드 개발 서버
uvicorn src.main:app --reload --port 8000

# 6) 모바일 (별도 터미널)
cd ../mobile
flutter pub get
flutter run
```

### A.2 환경 변수 (`backend/.env`)

```
DATABASE_URL=postgresql+asyncpg://lemon:lemon@localhost:5432/lemon
REDIS_URL=redis://localhost:6379/0

ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL_ID=claude-sonnet-latest
OPENAI_API_KEY=sk-...
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
CLOVA_OCR_API_KEY=...

MFDS_API_KEY=...

JWT_SECRET=...                       # openssl rand -hex 32
ENCRYPTION_KEY=...                   # openssl rand -base64 32

EMAIL_PROVIDER=smtp                  # smtp | ses | ncp
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASS=

ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### A.3 docker-compose.yml 핵심부

```yaml
version: '3.9'

services:
  db:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_USER: lemon
      POSTGRES_PASSWORD: lemon
      POSTGRES_DB: lemon
    volumes:
      - ./backend/src/db/init.sql:/docker-entrypoint-initdb.d/init.sql
      - lemon-pg-data:/var/lib/postgresql/data
    ports: ["5432:5432"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes:
      - lemon-redis-data:/data

  mailhog:                          # 개발용 SMTP UI
    image: mailhog/mailhog
    ports: ["1025:1025", "8025:8025"]

volumes:
  lemon-pg-data:
  lemon-redis-data:
```

`backend/src/db/init.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

### A.4 첫 커밋 전 체크리스트

- .env 작성됐는가
- docker compose ps에 timescale + redis + mailhog 동작
- uvicorn이 8000 포트에서 뜨는가
- http://localhost:8000/docs 에 Swagger UI 나오는가
- flutter run으로 시뮬레이터 동작
- pre-commit install 완료

### A.5 W1~W2 종료 시점에 있어야 할 것

- FastAPI 빈 셸 + 인증 라우터
- PostgreSQL/TimescaleDB/Redis Docker 환경
- Alembic 초기 마이그레이션
- Flutter 빈 셸 + 라우팅 + 디자인 토큰
- 카메라 화면 + 갤러리 선택
- backend/src/llm/claude_client.py 빈 함수 시그니처 (§A.6)
- backend/src/llm/tools.py 5개 Tool 정의
- backend/src/agents/orchestrator.py + memory.py 빈 셸
- backend/src/algorithms/bmi.py + 단위 테스트
- backend/src/services/email.py SMTP 발송 PoC
- Health Connect 데이터 타입 신청 제출

### A.6 D1 코드 시그니처 (5명 공통 합의, 변경 시 PR 필수)

```python
# backend/src/llm/claude_client.py
async def call_claude(
    *,
    system: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    max_tokens: int = 1024,
    timeout_s: int = 12,
) -> ClaudeResponse: ...

# backend/src/agents/orchestrator.py
async def run_full_analysis(
    user_id: int,
    supplements: list[UploadFile],
    meal: MealInput | None,
) -> FullAnalysisResult: ...

# backend/src/agents/memory.py
async def update_memory(user_id: int, evaluation: EvaluationResult) -> None: ...

# backend/src/llm/tools.py
TOOLS = {
    "extract_supplement_facts": {...},
    "add_reminder": {...},
    "add_calendar_event": {...},
    "log_supplement_intake": {...},
    "explain_deficiency": {...},
}

# backend/src/algorithms/bmi.py
def classify_bmi(height_cm: float, weight_kg: float) -> BmiClass: ...

# backend/src/algorithms/activity.py
def compute_v4(profile: Profile, daily: DailyActivity) -> ActivityScore: ...

# backend/src/utils/regex_filter.py
def check_forbidden_terms(text: str) -> ForbiddenCheck: ...

# backend/src/services/email.py
async def send_verification_email(to: str, token: str) -> None: ...
```

### A.7 pubspec.yaml 의존성 핵심부

```yaml
name: lemon_aid
description: AI 헬스케어 / 건강관리 플랫폼
publish_to: 'none'
version: 1.0.0+1

environment:
  sdk: ">=3.4.0 <4.0.0"
  flutter: ">=3.24.0"

dependencies:
  flutter:
    sdk: flutter
  flutter_riverpod: ^2.5.1
  go_router: ^14.2.0
  dio: ^5.4.3
  retrofit: ^4.1.0
  image_picker: ^1.1.2
  camera: ^0.11.0
  health: ^11.0.0
  isar: ^3.1.0
  isar_flutter_libs: ^3.1.0
  fl_chart: ^0.68.0
  flutter_local_notifications: ^17.2.0
  add_2_calendar: ^3.0.1
  freezed_annotation: ^2.4.4
  json_annotation: ^4.9.0
  intl: ^0.19.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  build_runner: ^2.4.11
  freezed: ^2.5.7
  json_serializable: ^6.8.0
  retrofit_generator: ^8.2.0
  flutter_lints: ^4.0.0
```

### A.8 GitHub Actions CI 핵심 step

| 워크플로 | 실행 단계 |
|----------|----------|
| ci-backend.yml | `pip install -r requirements.txt -r requirements-dev.txt` → `ruff check .` → `black --check .` → `mypy src` → `pytest --cov` |
| ci-mobile.yml | `flutter pub get` → `dart format --set-exit-if-changed .` → `flutter analyze` → `flutter test` |
| ci-docs.yml | `markdownlint PROJECT_GUIDE.md README.md` → SPLIT 카운트 검증 → guide.html script 태그 균형 체크 + `python scripts/sync_guide.py --check` |

### A.9 5명별 D1 ~ D5 액션 카드

#### A — 프론트 리드 (Flutter 환경 + 라우팅)

```
D1: Flutter 프로젝트 init, pubspec.yaml 의존성 (§A.7), main.dart + app.dart 셸
D2: go_router 7화면 라우팅, Splash → Login → Onboarding → Home
D3: utils/tokens.dart 디자인 토큰 (라이트 단독), Pretendard 폰트
D4: health 패키지 권한 요청 화면 + Info.plist / AndroidManifest.xml 작성
D5: 카메라 화면 (image_picker + camera) MVP
```

#### B — UI/UX (위젯 + 미리보기)

```
D1: Figma 와이어프레임 (Splash, Login, Signup, Consent)
D2: 화면 토큰 적용, widgets/disclaimer_banner.dart, error_view.dart
D3: supplement_preview.dart 미리보기 위젯 (분석 결과 + 사용자 수정)
D4: ai_input_sheet.dart 챗봇 입력 시트
D5: insight_card.dart, raffle_screen.dart UI
```

#### C — AI 엔지니어 (Claude + Tool + 검수)

```
D1: backend/src/llm/claude_client.py 빈 시그니처 (§A.6) + 기본 호출 테스트
D2: backend/src/llm/prompts.py 3개 Agent 시스템 프롬프트 v0
D3: backend/src/llm/tools.py 5개 Tool 정의 (§3.3)
D4: backend/src/llm/schemas.py Pydantic 출력 스키마
D5: backend/src/utils/regex_filter.py 의료법 검수 + 단위 테스트
```

#### D — 백엔드 (FastAPI + DB + 인증 + 보안)

```
D1: docker-compose.yml + backend/src/db/init.sql + alembic init
D2: backend/src/main.py + config.py + db/session.py
D3: backend/src/api/auth.py (signup, login, refresh, JWT)
D4: backend/src/algorithms/bmi.py + activity.py + 단위 테스트
D5: backend/src/services/email.py SMTP PoC + RLS 정책 SQL
```

#### E — 데이터 · 도메인 (KDRIs + 식약처 + 컴플라이언스)

```
D1: data/kdris_2020.csv 임포트 스크립트 작성
D2: backend/src/algorithms/kdris.py 룩업 함수 + 단위 테스트
D3: 식약처 식품영양성분 Open API PoC (FastAPI 어댑터)
D4: data/goal_matrix.json 작성 (눈/간/피로 §8.7 표 그대로)
D5: docs/reports/medical-review.md 의료자문위 질문 초안 + Health Connect 신청 진행
```

### A.10 팀 공유 채팅 메시지 템플릿

```
🍋 Lemon Aid W1 작업 시작합니다

[저장소] https://github.com/Lemon-Aid-KDT/Lemon-sin
[가이드] PROJECT_GUIDE.md (단일 진실) / guide.html (브라우저로 열기)
[브랜치] feat/<영역>-<짧은이름> · main 직접 푸시 X · PR 1명 리뷰

작업 분담 (§A.9 D1 액션 카드 참조):
- A (프론트 리드): Flutter init + 라우팅
- B (UI/UX): Figma 와이어프레임
- C (AI 엔지니어): claude_client.py 빈 시그니처
- D (백엔드): docker-compose + alembic init
- E (데이터·도메인): KDRIs CSV 임포트 + Health Connect 신청

질문/블로커는 채팅 즉시. 매일 18시 스탠드업 10분.

⚠️  바이브 코딩 툴 사용 시 PROJECT_GUIDE.md 먼저 읽어주세요.
⚠️  guide.html은 직접 수정하지 마세요. PROJECT_GUIDE.md만 수정 → pre-commit이 자동 동기화.
⚠️  코드 시그니처(A.6)는 합의된 인터페이스. 변경 시 PR 필수.
⚠️  GitHub 협업 규칙은 §16 참조. 자동 동기화는 §17 참조.
```

### A.11 막힐 때 / 도움 받을 때

| 상황 | 어디 보기 |
|------|-----------|
| 환경 셋업이 안 됨 | §A.1 명령 순서 / Docker 로그 / 채팅에 에러 그대로 |
| API 키 받는 법 모름 | Anthropic Console / Google Cloud Console / 채팅에 멘토 호출 |
| 다른 팀원 코드와 충돌 | §16 GitHub 규칙 + 채팅에서 동기 콜 |
| 알고리즘 산식이 헷갈림 | §8 핵심 알고리즘 / 가이드 PPT 예시값과 비교 |
| 의료법 표현이 걱정 | §19.2 위반→대체 표 / E에게 검토 요청 |
| 분석 알고리즘 + 3개 Agent 흐름이 헷갈림 | §3.1 / §7.3 / §9 호출 흐름 |
| LLM 비용이 무서움 | §7.6 가드레일 / 캐시 적중률 점검 |
| 발표 직전인데 백엔드 죽음 | §20.4 / §21.5 시연 안전장치 |
| guide.html이 PG.md와 다르게 보임 | §17 기획서 자동 동기화 |

---

> 본 문서는 Lemon Aid 팀 공유용 가이드라인입니다.
> 변경 시 PROJECT_GUIDE.md만 수정하면 guide.html에 자동 반영됩니다 (§17 자동 동기화).


