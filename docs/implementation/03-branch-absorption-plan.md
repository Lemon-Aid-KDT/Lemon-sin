# 03. Branch Absorption Plan

이 문서는 원격 브랜치 산출물을 어떤 순서와 방식으로 흡수할지 정한다. 현재 단계의
목표는 코드 통합이 아니라, 통합 PR을 만들기 전에 "무엇을 그대로 가져오고, 무엇을
재작성하고, 무엇을 참고만 할지" 판정하는 것이다.

## 흡수 판정 타입

| 판정 | 의미 | 사용 조건 |
|------|------|-----------|
| 그대로 merge | 파일 구조와 정책이 기준 브랜치와 맞아 충돌이 작음 | 작은 문서/설정/독립 파일 |
| 부분 cherry-pick | 특정 파일 또는 commit만 가치가 있음 | 기능은 맞지만 주변 구조가 다름 |
| 재작성 | 아이디어는 좋지만 위치, schema, 보안 정책이 다름 | 하위 프로젝트, 중복 구현 |
| 문서만 참고 | 코드보다 설계 설명이 가치 있음 | 가이드, 보고서, 상태 문서 |
| 보류 | 대용량, 중복, 불확실성이 큼 | 자산, 0 byte 파일, provider 정책 미합의 |

## 전체 순서

### Step 0. 문서/용어 정리

목표:
- `분석 알고리즘 + 3 Agent` 기준을 공식화한다.
- README와 하위 README의 "4 Agent" 표현을 정리할 수정 목록을 만든다.
- `docs/implementation`을 중간 기준 위치로 유지한다.

흡수 대상:
- `changmin-plan`의 기획/가이드 문서
- `main`의 `PROJECT_GUIDE.md`
- `yeong-tech`와 `jongpil-tech`의 구현 상태/개발 가이드 문서

판정:
- 문서만 참고 또는 재작성.

### Step 1. DB/auth/profile 기반 검토

목표:
- Agent context와 사용자 데이터 격리의 기반을 고른다.

후보:
- `sunghoon-database`: 간결한 DB/auth/profile 기반
- `taedong-design`: email verification, rate limit, mobile auth 포함
- `yeong-tech`: OIDC/JWT, privacy, consent, richer schema

판정 기준:
- 민감정보 동의와 audit가 있는가
- profile에 만성질환/복약 정보가 들어가는가
- migration이 재실행 가능한가
- mobile auth와 API 계약이 맞는가
- secret이 코드/모바일에 노출되지 않는가

권장:
- `sunghoon-database`를 최소 기반 후보로 보고, `yeong-tech`의 consent/security 정책을
  선별 반영한다.
- `taedong-design`의 UI/auth 흐름은 모바일 단계에서 따로 검토한다.

### Step 2. 식단/RDA/알고리즘 검토

목표:
- evaluation Agent 입력이 될 결정론적 분석 결과를 만든다.

후보:
- `jongpil-tech`: meal pipeline, RDA matcher, mock-first 식단 인식
- `yeong-tech`: KDRIs 2025, chronic priority, deficiency analysis

판정 기준:
- API와 독립된 순수 함수 테스트가 있는가
- 결과 schema가 Agent 입력으로 쓰기 쉬운가
- 데이터 출처와 version이 명시되어 있는가
- 의료 표현을 직접 단정하지 않는가

권장:
- `jongpil-tech`의 식단 인식 구조는 부분 cherry-pick 후보.
- `yeong-tech`의 KDRIs 2025와 chronic priority는 재작성 또는 선별 흡수 후보.

### Step 3. 영양제 preview/API 검토

목표:
- 영양제 이미지/OCR 분석이 사용자 승인 전 preview 상태로 멈추게 한다.

후보:
- `yeong-tech`: supplement analyze, OCR text attach, registration, confirmation flow
- `sunghoon-database`: DB 기반과 profile 연동

판정 기준:
- raw OCR text를 저장하지 않는가
- preview와 confirmed 상태가 분리되는가
- 사용자 동의를 확인하는가
- supplement ingredient schema가 KDRIs/UL 판단과 연결 가능한가

권장:
- `yeong-tech`의 preview/confirmation 정책은 우선 참고한다.
- 루트 프로젝트 구조와 맞지 않으므로 직접 merge가 아니라 재작성 또는 부분 흡수한다.

### Step 4. Agent mock-first 계약 문서화

목표:
- 실제 LLM 호출 없이 3 Agent 흐름을 API와 테스트로 검증한다.

선행:
- Step 1의 user/profile/consent
- Step 2의 meal/nutrition result
- Step 3의 supplement preview
- safety filter

산출:
- Agent schema
- orchestrator mock
- agent_runs logging
- agent_memory summary
- Tool preview contract

판정:
- 새 코드 작성. 기존 브랜치에는 완성된 3 Agent 구현이 없으므로 직접 흡수하지 않는다.

### Step 5. 모바일 preview와 Tool 승인 흐름

목표:
- Agent 제안을 사용자가 확인하고 승인하는 UI를 연결한다.

후보:
- `taedong-design`: mobile app, auth, placeholders, design tokens
- `sunghoon-database`: login mobile sample

판정 기준:
- API client와 token storage가 백엔드 계약과 맞는가
- preview/approval UI가 있는가
- 알림/캘린더 권한 요청이 명확한가
- 건강 고지와 안전 문구가 화면에 포함되는가

권장:
- `taedong-design`은 자산과 코드가 크므로 mobile 전용 PR로 분리한다.
- Agent Tool 실행은 처음에는 수동 승인 mock UI로 연결한다.

## 브랜치별 권장 판정

| 브랜치 | 권장 판정 | 이유 |
|--------|-----------|------|
| `changmin-plan` | 문서만 참고 | 문서 아카이브이며 코드 흡수 대상 아님 |
| `sunghoon-database` | 부분 cherry-pick | DB/auth 기반이 작고 비교적 명확함 |
| `jongpil-tech` | 부분 cherry-pick + 문서 참고 | 식단/RDA와 테스트 가치가 큼 |
| `taedong-design` | 분리 PR, 일부 재작성 | UI/자산/백엔드가 섞여 있어 대형 merge 위험 |
| `yeong-tech` | 재작성 + 선별 흡수 | 별도 하위 프로젝트 구조라 직접 merge 위험 |

## 금지 사항

- `yeong-Vision-Nutrition/` 하위 프로젝트를 루트에 그대로 합치지 않는다.
- Agent 기능 구현 전에 실제 외부 LLM 호출을 붙이지 않는다.
- raw OCR text, raw LLM response, 개인 건강 원문을 로그에 남기지 않는다.
- `guide.html`을 직접 편집하지 않는다.
- 모바일 앱에 API key를 넣지 않는다.

## 통합 PR 분할안

1. docs-only: 용어 정리와 구현 문서 추가
2. backend-foundation: DB/auth/profile/consent 최소 기반
3. nutrition-core: KDRIs/RDA/deficiency 결정론 로직
4. supplement-preview: 영양제 preview/confirmation API
5. meal-pipeline: 식단 입력/인식 mock pipeline
6. agent-contract: 3 Agent schema, mock orchestrator, logging
7. mobile-preview: preview/approval UI와 chat Tool mock
8. provider-integration: Claude/OpenAI/Ollama 중 결정된 provider adapter

