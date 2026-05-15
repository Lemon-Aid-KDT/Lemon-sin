# 00. Current Branch Map

기준일: 2026-05-14

이 문서는 `Lemon-Aid-KDT/Lemon-sin` 원격 브랜치를 기준으로 현재 산출물이 어디에
흩어져 있는지 정리한다. 목적은 merge 순서를 정하는 것이 아니라, 구현 전 어떤
브랜치에서 무엇을 참고하고 무엇을 조심해야 하는지 명확히 하는 것이다.

## 원격 브랜치 스냅샷

| 브랜치 | SHA | main 대비 상태 | 주요 성격 | 1차 판정 |
|--------|-----|----------------|-----------|----------|
| `main` | `2f941020753987394ddc255746e4d3cfdebb6505` | 기준 | 상위 가이드, 골격 문서, 기본 구조 | 기준 브랜치 |
| `changmin-plan` | `7b953d70e61631f9a0986cf8826aa7b1f3492d10` | 공통 조상 없음 | 발표/기획/연구/문서 아카이브 | 문서 기준 추출 |
| `sunghoon-database` | `c6149b33a2cdc1732ca9df2fe72b31f816c1b0c6` | ahead 12 / behind 0 | DB, auth, profile, Docker, Alembic | 백엔드 기반 후보 |
| `jongpil-tech` | `41ba91c3f70881a41a03b877e1a00cb05647fecc` | ahead 28 / behind 1 | 식단 인식, RDA 매칭, dev-guides, 테스트 | 알고리즘/가이드 후보 |
| `taedong-design` | `00976143dd800ca6228646a9fe41d9ca585c915e` | ahead 9 / behind 4 | 모바일 UI, 디자인 자산, auth 화면, 일부 backend | 선별 검토 필요 |
| `yeong-tech` | `e950365f76434008c60d54ec00c5057111cedd2b` | ahead 16 / behind 4 | 별도 하위 프로젝트, API/데이터/보안/LLM/Ollama | 직접 merge 금지, 선별 흡수 |

## 브랜치별 산출물 요약

### `main`

- `PROJECT_GUIDE.md`는 본문 기준으로 `분석 알고리즘 + 3 Agent` 구조를 설명한다.
- `README.md`에는 아직 "4개 Agent" 표현이 남아 있어 수정 필요 항목이다.
- `backend/`, `mobile/`, `docs/`는 골격 README 중심이며 실제 구현은 제한적이다.

주의:
- `PROJECT_GUIDE.md`가 상위 기획 기준이지만, 실제 구현 분담과 브랜치 산출물은
  이미 다르게 진행되어 있다.
- 대형 가이드 직접 수정은 문서 파급 범위를 먼저 확인한 뒤 진행해야 한다.

### `changmin-plan`

- 기획서, 제품 가이드, 연구 근거, 발표 자료, 주간/일일 문서를 보관한다.
- `main`과 공통 조상이 없어 GitHub compare로 단순 차이 계산이 되지 않는다.

주의:
- 코드 흡수 대상이 아니라 문서 기준과 의사결정 근거를 가져오는 브랜치다.
- 새 문서 작성은 이 브랜치에서 진행하되, 실제 코드 통합 PR과 분리한다.

### `sunghoon-database`

주요 파일:
- `DATABASE_GUIDE.md`
- `docker-compose.yml`
- `backend/.env.example`
- `backend/alembic.ini`, `backend/alembic/env.py`, 초기 migration
- `backend/src/api/auth.py`, `backend/src/api/profile.py`
- `backend/src/models/user.py`, `backend/src/models/profile.py`
- `backend/src/schemas/auth.py`, `backend/src/schemas/profile.py`
- `backend/src/utils/security.py`, `backend/src/utils/deps.py`
- `mobile/lib/screens/auth/login_screen.dart`, `mobile/lib/services/auth_service.dart`

통합 가치:
- Agent 구현의 선행 조건인 사용자, 프로필, 인증, DB 세션의 첫 기반이다.
- `profiles`의 만성질환/복약 정보는 개인화 Agent 입력과 직접 연결된다.
- Docker Compose와 Alembic은 `agent_runs`, `agent_memory` 테이블 추가 전 기반이다.

주의:
- `taedong-design`에도 auth/email/backend 계열 작업이 있어 충돌 가능성이 높다.
- 환경변수, JWT, 암호화 키, profile schema는 `yeong-tech`의 보안/동의 설계와 대조해야 한다.

### `jongpil-tech`

주요 파일:
- `backend/src/meal/*`
- `backend/src/nutrition/rda_matcher.py`
- `data/meal_vision/*`
- `data/rda/*`
- `docs/dev-guides/00-setup-environment.md`부터 `29-final-deliverables-index.md`
- `backend/tests/unit/meal/*`, `backend/tests/unit/nutrition/test_rda_matcher.py`

통합 가치:
- 식단 인식과 음식 영양소 매칭은 evaluation Agent 이전 단계의 핵심 입력이다.
- mock-first 접근이 이미 문서에 반영되어 있어 Agent mock-first 전략과 잘 맞는다.
- 테스트 구조가 비교적 명확하므로 후속 코드 흡수 시 검증 기준으로 쓰기 좋다.

주의:
- `backend/src/meal/`은 `PROJECT_GUIDE.md`의 기존 `meals/`, `nutrition/`,
  `algorithms/` 경계와 다를 수 있다.
- `docs/dev-guides`에는 0 byte 파일도 있어 그대로 공식 구현 문서로 승격하면 안 된다.

### `taedong-design`

주요 파일:
- `mobile/` Flutter 앱 전체 골격, auth 화면, splash, dashboard/chat/camera placeholder
- `mobile/lib/utils/tokens.dart`, `design_tokens_v2.dart`
- `character/`, `screenshot/`, PDF 기획 자료
- `backend/src/api/auth.py`, `email_verification.py`, `profile.py`
- `backend/src/services/email.py`, `backend/src/utils/rate_limit.py`

통합 가치:
- 모바일 UI와 디자인 토큰, 로그인/회원가입/동의 화면의 실제 구현 후보가 있다.
- 챗봇/대시보드/카메라 화면 placeholder가 Agent 연동 UI의 시작점이 될 수 있다.

주의:
- 대용량 이미지, PDF, 폰트, 생성 자산이 많아 코드 PR과 문서/자산 PR을 분리해야 한다.
- auth/backend 작업이 `sunghoon-database`와 겹친다.
- `PROJECT_GUIDE.md`, `guide.html` 변경량이 크므로 문서 동기화 충돌을 별도로 봐야 한다.

### `yeong-tech`

주요 파일:
- `yeong-Vision-Nutrition/` 하위 전체 프로젝트
- `yeong-Vision-Nutrition/backend/src/api/v1/*`
- `yeong-Vision-Nutrition/backend/src/models/db/*`
- `yeong-Vision-Nutrition/backend/src/models/schemas/*`
- `yeong-Vision-Nutrition/backend/src/nutrition/*`
- `yeong-Vision-Nutrition/backend/src/security/*`
- `yeong-Vision-Nutrition/backend/src/privacy/*`
- `yeong-Vision-Nutrition/docs/22-current-implementation-status-map.md`
- `todo-list/2026-05-14/2026-05-14-team-work-summary.md`

통합 가치:
- KDRIs 2025, supplement preview, consent gate, dashboard, health sync, JWT/OIDC,
  feature flag guard 등 실제 구현 수준이 높다.
- Agent 기능 전에 필요한 안전/동의/preview 기반 설계가 이미 존재한다.

주의:
- 코드가 `yeong-Vision-Nutrition/` 하위 별도 프로젝트로 들어가 있어 루트 프로젝트에
  그대로 merge하면 중복 구조가 생긴다.
- `ALLOW_EXTERNAL_LLM=false`, Ollama local parser, production guard는 기존
  `Claude 주력 + OpenAI 폴백` 가이드와 정책 결정을 다시 요구한다.
- 0 byte 테스트/서비스 파일이 다수 있어 구현 완료로 오해하면 안 된다.

## 통합 전 핵심 불일치

| 항목 | 현재 충돌 | 정리 방향 |
|------|-----------|-----------|
| Agent 수 | main 본문은 3 Agent, 일부 README와 파일 구조는 4 Agent | `분석 알고리즘 + 3 Agent`로 통일 |
| LLM provider | guide는 Claude 주력, yeong-tech는 local Ollama 중심 | MVP 정책 문서에서 provider 전략 재결정 |
| backend 구조 | main 골격, sunghoon DB 구조, jongpil meal 구조, yeong 하위 프로젝트 구조가 다름 | 기능별 흡수 후 루트 구조로 재배치 |
| auth/profile | sunghoon과 taedong이 모두 구현 | 한쪽을 기준으로 삼기 전에 schema와 security 차이 비교 |
| guide sync | scripts 위치가 `scripts/`와 `.github/scripts/`로 갈림 | 하나의 동기화 경로로 통일 |
| 문서 위치 | PROJECT_GUIDE, docs/planning, docs/dev-guides, yeong docs가 분산 | `docs/implementation`에서 중간 기준 유지 |

## 다음 액션

1. `01-role-and-ownership-sync.md` 기준으로 실제 담당 영역을 먼저 합의한다.
2. `03-branch-absorption-plan.md`의 판정 기준으로 브랜치별 산출물을 분류한다.
3. 코드 통합 전 `PROJECT_GUIDE.md`, README, CODEOWNERS, dev-guides의 용어를 맞춘다.

