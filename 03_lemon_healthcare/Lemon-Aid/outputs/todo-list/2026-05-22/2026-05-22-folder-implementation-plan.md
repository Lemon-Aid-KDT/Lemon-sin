# 2026-05-22 Lemon-Aid 폴더 구조, 구현 상태, 향후 계획

## 1. 기준 정보

- 작업 루트: `$LEMON_HEALTHCARE_ROOT`
- 분석 대상 루트: `Lemon-Aid/`
- 팀 협업 문서 경로: `Lemon-Aid/docs/team-collaboration/`
- 현재 브랜치: `chore/ocr-next-work`
- 현재 HEAD: `e1260140 chore(lemon): stabilize P1-5 workspace snapshot`
- 현재 워킹트리 주의사항:
  - 기존 수정 파일: `Lemon-Aid/outputs/todo-list/2026-05-21/full-day-summary-2026-05-21.md`
  - 기존 미추적 항목: `../00_plusultra/`, `Lemon-Aid/outputs/todo-list/2026-05-22/`
  - `yeong-Lemon-Aid-p1-5-followup/` worktree는 `feat/ocr-p1-5-followup` 커밋 보존 후 제거했다.
  - OCR Phase 0 follow-up PR: https://github.com/Lemon-Aid-KDT/Lemon-sin/pull/3
  - 이 분석에서는 기존 변경을 되돌리지 않았다.

## 2. 앞으로의 작업 원칙

현재 폴더 구조를 크게 벗어나지 않는 것을 기본 규칙으로 둔다.

| 작업 종류 | 기본 위치 |
|---|---|
| 백엔드 애플리케이션 코드 | `Lemon-Aid/backend/Nutrition-backend/src/` |
| 백엔드 테스트 | `Lemon-Aid/backend/Nutrition-backend/tests/` |
| 백엔드 운영/검증 스크립트 | `Lemon-Aid/backend/scripts/` |
| 모바일 앱 코드 | `Lemon-Aid/mobile/lib/core/`, `Lemon-Aid/mobile/lib/features/`, `Lemon-Aid/mobile/lib/shared/` |
| 모바일 테스트 | `Lemon-Aid/mobile/test/` |
| 협업 규칙 | `Lemon-Aid/docs/team-collaboration/` |
| OCR/AI/영양 기능 문서 | `Lemon-Aid/docs/` 하위 기존 주제 폴더 |
| 날짜별 작업 산출물 | `Lemon-Aid/outputs/todo-list/YYYY-MM-DD/` |
| 평가 산출물 | `Lemon-Aid/outputs/evaluations/`, `Lemon-Aid/outputs/generated/` |
| 데이터/샘플/매니페스트 | `Lemon-Aid/data/` |

### Git 규칙

- 브랜치 이름: `<type>/<scope>-<주제>`
- 허용 type: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`, `revert`, `data`, `ops`
- 허용 scope: `mobile`, `backend`, `ai`, `ocr`, `db`, `auth`, `ux`, `infra`, `docs`, `team`, `test`, `data`
- 금지: 작업자 이름 브랜치, `--no-verify`, `--force` 단독 사용, `.env`/비밀키 커밋, 셀프 머지
- 머지:
  - feature -> develop: Squash merge
  - develop -> main: Merge commit
- 커밋 메시지: `<type>(<scope>): <한글/영문 명령형>`
  - 마침표 없음
  - 제목 50자 이내
  - 본문은 무엇을 했는지보다 왜 했는지를 설명

이번 분석 문서에 적합한 예시:

```text
docs(team): 폴더 구현 상태와 계획 정리

팀이 새 기능을 추가하기 전에 현재 Lemon-Aid 구조, 구현 범위,
검증 공백, OCR 성능 한계를 같은 기준으로 확인할 수 있도록
날짜별 분석 산출물을 추가한다.
```

## 3. 팀 협업 문서 파악

`Lemon-Aid/docs/team-collaboration/` 안에는 Markdown 파일 10개가 존재한다.

| 파일 | 역할 | 현재 파악한 핵심 |
|---|---|---|
| `README.md` | 협업 문서 인덱스 | `develop`은 통합/테스트, `main`은 안정 브랜치로 정의한다. 작업은 브랜치, PR, 리뷰, CI를 거친다. |
| `TEAM_QUICK_REFERENCE.md` | 빠른 규칙표 | 브랜치/커밋/PR/CI 금지사항을 짧게 정리한다. 사용자 요청의 규칙과 일치한다. |
| `BRANCH_STRATEGY.md` | 브랜치 전략 | `<type>/<scope>-<subject>` 패턴, 작업자명 브랜치 금지, feature -> develop squash, develop -> main merge commit을 정의한다. |
| `COMMIT_CONVENTION.md` | 커밋 규칙 | Conventional Commits 형식, 허용 type/scope, subject/body 작성 규칙을 정의한다. |
| `DEVELOP_WORKFLOW.md` | 일일 개발 흐름 | 최신 develop 동기화, feature branch 생성, `git add -p`, PR 작성, squash merge 흐름을 정의한다. |
| `PR_GUIDELINES.md` | PR 작성 규칙 | PR 제목/본문 템플릿, 200라인 이하 권장, 검증 항목, self merge 금지를 정의한다. |
| `CI_CD_GATES.md` | CI/CD 게이트 | pre-commit, commit-msg, lint, test, build, secret scan, `--no-verify` 금지를 정의한다. |
| `CODE_REVIEW_CHECKLIST.md` | 리뷰 체크리스트 | 공통, 모바일, 백엔드, OCR, DB, 인증 영역별 리뷰 기준을 제공한다. |
| `LOCAL_SETUP.md` | 로컬 환경 구성 | Python 3.13, pre-commit, Flutter, `.env` 복사 흐름을 안내한다. 현재 로컬에는 `Lemon-Aid/backend/.venv`가 없다. |
| `MERGE_AND_CONFLICT.md` | 머지/충돌 처리 | feature에서는 rebase 기반 동기화, `--force-with-lease` 사용, 위험 명령 금지를 정리한다. |

판단: 협업 문서 자체는 팀 운영 규칙을 충분히 갖추고 있다. 다음 보완은 문서 추가가 아니라 실제 PR 템플릿, commit-msg hook, CI 설정이 이 규칙과 같은지를 점검하는 쪽이 우선이다.

## 4. 폴더별 파일 현황

현재 `git ls-files Lemon-Aid` 기준 tracked 파일 수는 다음과 같다.

| 폴더/파일 | tracked 파일 수 | 역할 |
|---|---:|---|
| `backend/` | 305 | FastAPI 백엔드, OCR/LLM/영양/예측/학습/규제 입력 기능 |
| `mobile/` | 238 | Flutter 모바일 앱 |
| `docs/` | 165 | 기능 문서, OCR 보고서, 협업 문서, 통합 문서 |
| `data/` | 195 | KDRI, chronic disease matrix, OCR 샘플/매니페스트/평가 데이터 |
| `outputs/` | 81 | 평가 결과, 생성 리포트, 날짜별 todo-list 산출물 |
| `records/` | 8 | 프로젝트 기록 |
| `config/` | 2 | 구현 준비/상태 관련 JSON 설정 |
| `assets/` | 2 | 이미지 자산 |
| `frontend/` | 1 | 현재는 README 중심의 placeholder 성격 |
| 루트 문서/설정 | 4 | `README.md`, `PROJECT_GUIDE.md`, `guide.html`, `.gitignore`, pre-commit 설정 등 |

추가 확인:

- `Lemon-Aid/backend/Nutrition-backend/src/`: Python 파일 144개
- `Lemon-Aid/backend/Nutrition-backend/tests/`: `test_*.py` 84개
- `Lemon-Aid/backend/scripts/`: Python 스크립트 15개
- `Lemon-Aid/mobile/lib/`: Dart 파일 17개
- `Lemon-Aid/mobile/test/`: `*_test.dart` 7개
- `Lemon-Aid/docs/`: Markdown 파일 147개
- `Lemon-Aid/data/`: 실제 파일 200개

주의:

- `Lemon-Aid/backend/.env`는 존재하지만 `.gitignore`에 의해 무시된다. 내용은 읽지 않았고 앞으로도 커밋 대상에서 제외해야 한다.
- `Lemon-Aid/backend/Nutrition-backend/htmlcov/`, `.coverage`, `Lemon-Aid/mobile/build/`, `Lemon-Aid/mobile/.dart_tool/`은 ignored artifact이다. 스테이징 금지 대상이다.

## 5. 기능별 구현도

| 기능 | 구현도 | 현재 구현 내용 | 보완 필요 |
|---|---|---|---|
| 팀 협업 규칙 | 높음 | 브랜치, 커밋, PR, CI, 리뷰, 충돌 처리 문서가 분리되어 있다. | 실제 hook, PR template, CI 설정과 문서 규칙의 일치 여부 확인 |
| 백엔드 API 구조 | 높음 | FastAPI `main.py`와 `/api/v1` router가 activity, nutrition, predictions, supplements, privacy, regulated inputs, health, dashboard를 분리한다. | OpenAPI 요약 문서와 현재 라우트 동기화 |
| 설정/보안 가드 | 높음 | `config.py`에서 auth, CORS, allowed hosts, external OCR/LLM, production guard를 fail-closed 방향으로 둔다. | staging/prod 실제 Secret Manager, DB, auth smoke 미검증 |
| Supplement intake | 높음 | 이미지 magic byte 검증, 크기 제한, 메타데이터 제거, owner-scoped idempotency, raw OCR text 저장 억제를 구현한다. | 운영 환경에서 consent/auth/retention 로그 검증 |
| OCR adapter | 중간 이상 | PaddleOCR local, Google Vision, CLOVA 계열 provider 파일과 factory routing이 존재한다. | 실제 real-label 기준 정확도와 provider별 latency gate가 부족 |
| OCR layout parser | 중간 이상 | `OCRResult.pages` 기반 no-network/no-LLM 휴리스틱 parser, y-band row grouping, x-gap cell splitting, keyword anchor를 사용한다. | 더 많은 실제 라벨 fixture와 parser regression test 필요 |
| Supplement parser/LLM | 중간 | local Ollama 기반 structured parser, raw OCR/model response 저장 억제, sanitization 흐름이 있다. | 모델 응답 품질, timeout, fallback, 스키마 실패율 계측 필요 |
| Nutrition/KDRI | 중간 이상 | KDRI, chronic disease matrix, supplement recommendation/explain API가 구현되어 있다. | 의료적 표현 제한, 근거 문구, 사용자 안전 UX 재검토 |
| Weight prediction | 중간 | `/predictions/weight` 경로와 Hall-lite 성격의 예측 기능이 존재한다. | 임상/통계 검증 전에는 의사결정용 성능 주장 금지 |
| Regulated OCR intake | 중간 | prescription/lab OCR intake와 confirmation endpoint가 feature gate 뒤에 존재한다. | 운영 sign-off, 법적/의료적 문구, 삭제/감사 정책 필요 |
| Learning/vector scaffolding | 낮음에서 중간 | migration, repository, vector/learning 관련 코드가 존재한다. | 실제 pgvector/object storage/embedding smoke와 데이터 거버넌스 필요 |
| Flutter mobile | 중간 이상 | `core`, `features`, `shared` 구조로 dashboard, supplement flow, API client, repository, app controller가 존재한다. | 실제 기기 카메라/권한/HTTPS/cert pin/release flavor 검증 필요 |
| OCR evaluation | 중간 | synthetic/real/live/google/paddle 평가 산출물이 존재한다. | ground truth 수량과 real-image 품질이 부족해 production accuracy 결론은 불가 |

## 6. 성능 평가와 검증 상태

이번 분석에서 실제로 실행한 검증:

| 명령 | 결과 |
|---|---|
| `git diff --check` | 통과 |
| `flutter analyze` in `Lemon-Aid/mobile` | `No issues found` |
| `flutter test` in `Lemon-Aid/mobile` | 15 tests passed |

이번 분석에서 실행하지 못한 검증:

| 항목 | 이유 |
|---|---|
| backend `pytest` | `Lemon-Aid/backend/.venv`가 없고 현재 `python3`에 `pytest`가 설치되어 있지 않다. |
| backend `ruff`, `black`, `mypy` | 현재 `python3`에 관련 패키지가 없다. |

Repo 내부 OCR 성능 문서에서 확인한 수치:

| 출처 | 데이터 | 수치 | 해석 |
|---|---|---|---|
| `docs/ocr_baseline_reports/v3/final_summary.md` | synthetic 60, v3-B server det + lightweight | avg CER 7.19%, exact 28.33%, field match 57.22% | synthetic 기준으로는 개선 흐름이 있으나 exact match는 아직 낮다. |
| `docs/ocr_baseline_reports/v3/final_summary.md` | real 7 | avg CER 38.27%, field match 9.52%, product/ingredients 0/7 | real-image 기준 OCR은 아직 production claim 불가다. |
| `outputs/evaluations/supplement-ocr/live/2026-05-17-smoke-3/paddle-only/supplement-ocr-gate.md` | live auto-seed 3 | avg latency 8103ms, parser/layout success 1.0, warning 상태 | N=3 smoke라서 회귀 감지용으로만 봐야 한다. |
| `outputs/generated/ocr-eval/2026-05-20-three-tier/ocr-three-tier-evaluation.md` | Google Vision 1 fixture | avg latency 720ms, ingredient exact 1.0, missing image 1 | N=1이고 이미지 누락 표시가 있어 일반화하면 안 된다. |

성능 판단:

- 모바일 정적 분석과 테스트는 현재 로컬에서 통과했다.
- 백엔드는 현재 환경 구성 공백 때문에 재검증되지 않았다.
- OCR은 synthetic benchmark와 실제 라벨 benchmark 간 격차가 크다. 현재 수치만으로 "실사용 정확도 확보"라고 주장하면 안 된다.
- PaddleOCR CPU/macOS 환경에서는 latency와 real-image 품질이 병목이다. capture quality gate와 real-label 확장이 먼저다.

## 7. 현재 한계와 문제점

1. 백엔드 로컬 재현성 공백
   - 문서상 `Lemon-Aid/backend/.venv`를 전제로 하지만 현재 해당 venv가 없다.
   - 이 상태에서는 `pytest`, `ruff`, `black`, `mypy`를 같은 기준으로 재실행할 수 없다.

2. 현재 상태 문서 드리프트
   - `docs/Nutrition-docs/22-current-implementation-status-map.md`는 2026-05-15 기준이라 현재 code tree와 일부 불일치한다.
   - regulated input endpoint, OCR provider 구현 상태 등은 현재 코드가 더 앞서 있다.

3. 2026-05-21 일부 산출물과 현재 local mobile tree 불일치 가능성
   - `outputs/todo-list/2026-05-21/full-day-summary-2026-05-21.md`는 `models/providers/services` 스타일의 mobile 경로를 언급한다.
   - 현재 `Lemon-Aid/mobile/lib`는 `core/features/shared` 구조다.
   - 같은 팀 export 또는 이전 app slice를 가리킨 것인지 확인이 필요하다.

4. OCR real-image 정확도 부족
   - real 7 기준 field match가 9.52%로 낮다.
   - dense Korean label, blur, angle, lighting, ROI segmentation 문제가 남아 있다.

5. 외부 OCR/LLM 사용 경계
   - Google Vision/CLOVA/Ollama remote는 개인정보와 의료 데이터 경계가 크다.
   - 현재 default fail-closed 정책은 유지해야 하며, 외부 사용은 명시 opt-in, region, audit, secret policy를 갖춰야 한다.

6. ignored artifact 관리
   - `htmlcov`, `.coverage`, `mobile/build`, `.dart_tool`이 로컬에 존재한다.
   - 실수로 강제 추가하지 않도록 `git add -p` 중심으로 유지해야 한다.

## 8. 수정 및 보완 방안

### P0: 다음 작업 전 필수 정리

1. 백엔드 재현 환경 복구
   - `Lemon-Aid/backend/.venv` 또는 팀 표준 Python 환경을 문서와 실제 명령이 일치하도록 복구한다.
   - 목표 검증 명령:
     - `pytest`
     - `ruff check`
     - `black --check`
     - `mypy`
     - `git diff --check`
   - `.env` 값은 읽거나 문서화하지 않고 `.env.example`과 secret placeholder만 사용한다.

2. 현재 상태 문서 갱신
   - `22-current-implementation-status-map.md` 또는 신규 dated status map을 현재 코드 기준으로 갱신한다.
   - "구현됨", "feature gate 뒤에 존재", "스모크만 통과", "성능 결론 불가"를 분리한다.

3. 협업 규칙 실행 장치 점검
   - PR template, commit-msg hook, pre-commit, CI workflow가 `team-collaboration` 문서와 일치하는지 점검한다.
   - 불일치가 있으면 `docs/team` 또는 `ci/team` 범위로 작은 PR을 만든다.

4. OCR 평가 ground truth 확장
   - real label 최소 30장 이상으로 확대한다.
   - product, manufacturer, ingredients, dosage, warning field별 exact/partial/F1을 분리한다.
   - OCR raw text는 저장하지 않고 hash, derived field, error class만 보존한다.

### P1: 기능 품질 개선

5. 모바일 capture quality gate
   - blur, angle, crop, glare, resolution warning을 촬영 직후 안내한다.
   - real OCR 실패의 상당 부분이 입력 품질 문제이므로 backend OCR 이전에 UX gate가 필요하다.

6. OCR provider routing 정리
   - local PaddleOCR을 기본값으로 유지한다.
   - Google Vision/CLOVA는 `ALLOW_EXTERNAL_OCR=true`와 provider-specific credential이 있을 때만 활성화한다.
   - provider별 latency/error/empty text rate를 같은 schema로 남긴다.

7. Layout parser regression 확대
   - `OCRResult -> LabelLayout` fixture를 provider raw JSON이 아닌 normalized DTO 기준으로 추가한다.
   - bounding box 누락, 좌표 scale mismatch, 빈 layout, 한글 anchor variation을 테스트한다.

8. 모바일 release safety 검증
   - `LEMON_API_BASE_URL` HTTPS 강제, certificate pin, release token embedding 금지 검증을 실제 release build에서 확인한다.
   - 카메라/갤러리 권한 플로우를 iOS/Android 실기기 또는 emulator에서 확인한다.

### P2: 운영/확장 준비

9. Learning/vector 기능 smoke
   - migration 적용, pgvector extension, embedding insert/search, object storage link를 최소 end-to-end로 검증한다.

10. Hall-lite/regulated 기능 검증 문서화
   - weight prediction과 regulated intake는 의료적 해석 오해가 생기기 쉬운 영역이다.
   - 모델 한계, preview-only 여부, confirmation gate, disclaimer를 API와 모바일 UX에서 동시에 점검한다.

11. develop/main release 운영 점검
   - feature -> develop squash와 develop -> main merge commit이 실제 GitHub branch protection과 맞는지 확인한다.
   - release note는 OCR/AI 성능 claim과 구현 claim을 분리해서 작성한다.

## 9. 앞으로의 작업 계획

| 순서 | 작업 | 산출물 | 추천 브랜치 |
|---:|---|---|---|
| 1 | 백엔드 검증 환경 복구와 로컬 명령 재실행 | 검증 로그, 필요 시 setup 문서 보완 | `chore/backend-test-env` |
| 2 | 현재 구현 상태 map 갱신 | dated status report 또는 기존 status map 업데이트 | `docs/backend-status-map` |
| 3 | 협업 문서와 실제 hooks/CI/PR template 비교 | gap report, 작은 config/docs PR | `docs/team-governance-sync` |
| 4 | OCR real-label 평가 확장 설계 | fixture schema, metrics plan, privacy rule | `test/ocr-real-baseline` |
| 5 | OCR 입력 품질 gate 구현 | mobile/backend validation, tests | `feat/ocr-capture-quality-gate` |
| 6 | provider별 OCR routing/metrics 정리 | provider metrics DTO, regression tests | `refactor/ocr-provider-routing` |
| 7 | 모바일 release safety 검증 | analyze/test/build 결과, device checklist | `test/mobile-release-safety` |
| 8 | learning/vector smoke | migration + repository smoke test | `test/ai-learning-smoke` |

## 10. 공식 문서 확인 기준

이번 분석에서 기능 판단 기준으로 확인한 공식 문서와 표준은 다음과 같다.

- FastAPI APIRouter와 큰 애플리케이션 구조: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- Pydantic Settings API: https://docs.pydantic.dev/latest/api/pydantic_settings/
- Flutter testing overview: https://docs.flutter.dev/testing/overview
- PaddleOCR 3.x General OCR Pipeline Usage: https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html
- Google Cloud Vision OCR: https://cloud.google.com/vision/docs/ocr
- Conventional Commits 1.0.0: https://www.conventionalcommits.org/en/v1.0.0/

주의: 위 공식 문서는 구조와 API 사용 방향 검증에 사용했다. OCR 성능 수치는 외부 문서에서 가져오지 않고 repo 내부 평가 산출물에 기록된 값만 사용했다.

## 11. 결론

현재 Lemon-Aid는 백엔드 기능 폭과 협업 문서 체계가 이미 넓게 구성되어 있다. 다만 새 기능을 더하기 전에 가장 큰 리스크는 코드 부재가 아니라 검증 기준의 드리프트다.

우선순위는 다음과 같다.

1. 백엔드 로컬 검증 환경 복구
2. 현재 구현 상태 문서 최신화
3. 협업 규칙의 실제 enforcement 확인
4. OCR real-image ground truth와 quality gate 강화
5. 모바일 release safety와 실제 기기 검증

이 순서로 진행하면 기존 폴더 구조를 유지하면서도 팀 협업, 기능 안정성, 성능 주장 정확도를 동시에 개선할 수 있다.

## 12. 2026-05-22 후속 상태 업데이트

이번 후속 작업에서 먼저 처리한 사항은 다음과 같다.

| 항목 | 결과 |
|---|---|
| 기존 follow-up branch 보존 | 로컬 `feat/ocr-p1-5-followup`에 `8efb52f7 feat(ocr): CLOVA Phase 0 기준선 보존` 커밋 생성 |
| standalone team repo용 이식 커밋 | `b5a9dec9 feat(ocr): CLOVA Phase 0 기준선 보존` |
| 원격 push | `team/feat/ocr-p1-5-followup` 생성 |
| PR 생성 | https://github.com/Lemon-Aid-KDT/Lemon-sin/pull/3 |
| PR base/head | base `feat/ocr-95-baseline-and-security-2026-05-20`, head `feat/ocr-p1-5-followup` |
| PR 상태 | open, mergeable |

PR #3은 `team/develop`이 아니라 기존 P1-5 snapshot branch 위에 쌓았다. 이유는 `team/develop`과 로컬 monorepo snapshot 사이에 merge base가 없고, `team/develop` 자체도 현재 P1-5 snapshot을 아직 포함하지 않기 때문이다. 이 상태에서 바로 `develop` 대상으로 PR을 만들면 리뷰 범위가 Phase 0 follow-up이 아니라 전체 snapshot으로 커진다. 따라서 PR #3은 작은 stacked PR로 두고, P1-5 snapshot PR이 통합된 뒤 팀 규칙에 맞는 최종 integration branch로 base를 조정하는 것이 안전하다.

PR #3 검증 결과:

| 검증 | 결과 |
|---|---|
| focused backend unit tests | 112 passed |
| `black --check` | 9 files unchanged |
| `ruff check --ignore RUF001` | all checks passed |
| `git diff --check` | 통과 |
| `git diff --cached --check` | 통과 |

추가로 PR #3에는 raw OCR text, provider raw payload, request header, API secret, 절대 로컬 이미지 manifest를 포함하지 않았다. 커밋된 CLOVA 산출물은 redacted observation과 aggregate evaluation JSON/Markdown으로 제한했다.

## 13. 수정 및 보완 브레인스토밍

현재 문서의 P0/P1/P2 항목과 PR #3의 Phase 0 진단 내용을 합치면, 다음 순서가 가장 안전하다.

### 13.1 가장 먼저 줄여야 할 리스크

1. 검증 재현성 리스크
   - 현재 기본 checkout에는 backend `.venv`가 없다.
   - 테스트 가능 여부가 worktree마다 달라지면 PR 리뷰에서 "내 환경에서는 통과" 상태가 반복된다.
   - 해결 방향은 기능 코드보다 먼저 backend dev env doctor, 표준 명령, 실패 시 안내 문구를 정리하는 것이다.

2. 상태 문서 드리프트 리스크
   - 현재 구현 상태 문서가 2026-05-15 기준인 반면, 코드에는 regulated intake, provider routing, layout parser, OCR evaluation script가 더 많이 들어와 있다.
   - 해결 방향은 "구현됨", "feature gate 뒤에 있음", "스모크만 통과", "성능 결론 불가"를 분리한 dated status map을 새로 만드는 것이다.

3. OCR 성능 주장 리스크
   - PR #3의 CLOVA baseline은 text non-empty/parser success는 높지만 ingredient exact와 chronic condition accuracy가 0이다.
   - 이는 OCR provider가 글자를 못 읽는 문제라기보다 field extraction/layout interpretation 문제가 섞였을 가능성이 크다.
   - 해결 방향은 곧바로 모델 교체가 아니라 `field_extractor`의 알려진 failure shape를 작은 PR로 먼저 고치는 것이다.

4. 팀 규칙 enforcement 리스크
   - 협업 문서는 충분하지만 실제 PR template, commit-msg hook, CI gate가 문서와 같은지 아직 검증되지 않았다.
   - 해결 방향은 code feature PR과 분리한 `docs/team` 또는 `ci/team` 범위의 작은 governance PR이다.

### 13.2 OCR 개선 가설

| 가설 | 근거 | 먼저 할 일 |
|---|---|---|
| H1: `field_extractor`가 표 셀 OCR을 놓친다 | 콜론 없는 `비타민 C 1000mg`, 파이프 구분자, 천단위 콤마, `mcg` 단위가 회귀 테스트로 확인됨 | `fix/ocr-field-extractor-shapes` |
| H2: layout row/column reconstruction이 부족하다 | real label은 dense table이고 provider별 line order가 다를 수 있음 | H1 패치 후에도 field match가 낮으면 `refactor/ocr-layout-parser-regression` |
| H3: 입력 품질이 OCR 이전 병목이다 | real benchmark와 synthetic benchmark 격차가 큼 | mobile capture quality gate |
| H4: provider routing 기준이 불충분하다 | PaddleOCR/CLOVA/Google Vision 결과 비교 schema가 아직 운영 metric으로 정리되지 않음 | provider metrics DTO와 evaluation summary 통합 |
| H5: fine-tune은 아직 이르다 | extraction/layout/quality gate가 정리되지 않으면 학습 데이터 라벨링 방향이 흔들림 | 30장 이상 real fixture와 error taxonomy 확정 후 판단 |

### 13.3 우선순위 결론

1. PR #3 리뷰/merge 준비를 유지한다.
2. 기본 checkout에서 `chore/backend-test-env` 성격의 재현성 보완을 먼저 한다.
3. 곧바로 `fix/ocr-field-extractor-shapes`를 작은 PR로 준비한다.
4. 그 다음 real-label evaluation과 capture quality gate를 병렬 후보로 둔다.
5. PP-StructureV3, PaddleOCR-VL, fine-tune은 H1/H2가 실패했을 때만 비용을 쓴다.

## 14. 상세 구현 계획

### PR-0: PR #3 리뷰 준비 유지

- 목적: Phase 0 인프라와 CLOVA baseline 산출물을 작은 stacked PR로 보존한다.
- 현재 상태:
  - URL: https://github.com/Lemon-Aid-KDT/Lemon-sin/pull/3
  - base: `feat/ocr-95-baseline-and-security-2026-05-20`
  - head: `feat/ocr-p1-5-followup`
  - 상태: open, mergeable
- 완료 조건:
  - PR #2 또는 P1-5 snapshot integration 상태가 바뀌면 PR #3 base를 다시 판단한다.
  - PR #3 body에는 raw OCR text, secret, local manifest를 포함하지 않는다.
  - 리뷰 요청 전 PR diff가 Phase 0 follow-up 1커밋 범위인지 다시 확인한다.

### PR-1: Backend 검증 환경 복구

- 추천 branch: `chore/backend-test-env`
- 범위:
  - `Lemon-Aid/backend/README.md` 또는 `docs/team-collaboration/LOCAL_SETUP.md`의 backend setup 명령과 실제 repo 구조를 맞춘다.
  - `backend/scripts/check_backend_dev_env.py` 같은 진단 스크립트를 추가할지 검토한다. 추가한다면 `.env` 값을 읽지 않고 Python version, import 가능성, pytest/ruff/black 존재 여부만 확인한다.
  - `.venv`는 만들 수 있지만 커밋하지 않는다.
- 구현 단계:
  1. `backend/pyproject.toml`, `backend/requirements-dev.txt`, `LOCAL_SETUP.md`를 대조한다.
  2. 표준 명령을 하나로 고정한다.
  3. backend root와 app root가 섞이지 않도록 명령 예시를 절대/상대 경로 기준으로 정리한다.
  4. 검증 실패 시 사용자가 바로 복구할 수 있는 오류 메시지와 체크리스트를 문서화한다.
- 검증:
  - `python3 -m venv .venv`
  - `.venv/bin/python -m pip install -r backend/requirements-dev.txt`
  - `PYTHONPATH=backend/Nutrition-backend .venv/bin/python -m pytest ... -q --no-cov`
  - `.venv/bin/python -m black --check ...`
  - `.venv/bin/python -m ruff check ...`
  - `git diff --check`
- 완료 조건:
  - 새 작업자가 문서 명령만으로 focused backend test를 재현할 수 있다.
  - `.env`, secret, coverage artifact, venv는 git status에 잡히지 않는다.

### PR-2: 현재 구현 상태 map 최신화

- 추천 branch: `docs/backend-status-map`
- 범위:
  - `docs/Nutrition-docs/22-current-implementation-status-map.md`를 직접 갱신하거나, `outputs/todo-list/2026-05-22/` 아래 dated status report를 추가한다.
  - 상태 구분을 네 단계로 고정한다: `implemented`, `feature-gated`, `smoke-only`, `not-production-ready`.
- 구현 단계:
  1. FastAPI router 등록 상태를 `src/main.py`, `src/api/v1/router.py` 기준으로 확인한다.
  2. OCR provider, regulated intake, supplement intake, prediction, learning/vector 영역을 파일/테스트 단위로 매핑한다.
  3. 문서의 성능 수치는 repo 내부 평가 산출물에서만 가져오고, 없는 수치는 만들지 않는다.
  4. 각 기능에 필요한 다음 검증 gate를 표로 붙인다.
- 검증:
  - 문서 내 파일 경로가 실제 존재하는지 `test -e` 또는 `rg --files`로 확인한다.
  - 성능 수치가 인용한 repo-local report와 일치하는지 재확인한다.
- 완료 조건:
  - 현재 code tree와 status document 사이의 큰 불일치가 사라진다.
  - "사용 가능"과 "검증 필요"가 같은 표현으로 섞이지 않는다.

### PR-3: 협업 규칙 enforcement 동기화

- 추천 branch: `docs/team-governance-sync`
- 범위:
  - `docs/team-collaboration/`의 규칙과 실제 `.github`, pre-commit, commit-msg, PR template, CI workflow를 비교한다.
  - 누락된 장치가 있으면 docs-only gap report로 먼저 남기고, 설정 변경은 별도 작은 PR로 분리한다.
- 구현 단계:
  1. 브랜치명/커밋명 규칙이 실제 hook으로 강제되는지 확인한다.
  2. PR template이 없다면 `PR_GUIDELINES.md`와 맞는 최소 템플릿을 제안한다.
  3. secret scan, `--no-verify` 금지, force push 정책이 CI나 branch protection에서 보완되는지 확인한다.
  4. team remote의 실제 integration branch 상태를 문서에 반영한다.
- 검증:
  - `pre-commit run --all-files`가 가능한 환경인지 확인한다.
  - GitHub PR template 적용 여부를 실제 PR 생성 화면 또는 `.github` 파일로 확인한다.
- 완료 조건:
  - 문서 규칙과 실제 자동화 사이의 gap이 표로 정리된다.
  - 설정 변경이 필요하면 위험도별로 후속 PR이 분리된다.

### PR-4: OCR field extractor failure shape 패치

- 추천 branch: `fix/ocr-field-extractor-shapes`
- 범위:
  - 콜론 없는 표 셀: `비타민 C 1000mg`
  - 파이프 구분: `비타민 C | 1000mg`
  - 천단위 콤마: `1,000mg`
  - `mcg` 단위
  - `μg RAE` 같은 unit suffix case preservation
- 구현 단계:
  1. PR #3에 들어간 회귀 진단 테스트를 "현재 failure characterization"에서 "expected pass"로 전환한다.
  2. `DOSAGE_PATTERN`을 숫자 토큰 전체와 단위 전체를 잡도록 수정한다.
  3. ingredient name과 dosage 사이 separator를 `:`, 공백, `|`, tabular spacing까지 허용한다.
  4. 기존 콜론 기반 문법이 깨지지 않는지 음성 통제 테스트를 유지한다.
  5. raw OCR text 저장 금지 정책을 건드리지 않는다.
- 검증:
  - `test_field_extractor.py`
  - OCR factory/provider/config focused tests
  - 16 fixture Phase 0 evaluation 재실행
- KPI:
  - 최소 기준: PR #3 baseline 대비 `ingredient_name_exact_rate`가 0에서 상승한다.
  - 다음 gate: field-level match ratio가 0.95에 못 미치면 layout parser 또는 provider routing 문제로 분기한다.
- 완료 조건:
  - 알려진 5개 failure shape가 단위 테스트에서 통과한다.
  - 기존 parsed ingredient 동작이 회귀하지 않는다.

### PR-5: OCR real-label 평가 확장

- 추천 branch: `test/ocr-real-baseline`
- 범위:
  - real label fixture를 최소 30장 이상으로 늘린다.
  - ground truth schema를 product/manufacturer/ingredients/dosage/warning/chronic matrix로 분리한다.
  - raw OCR text는 저장하지 않고 hash, derived field, warning/error code만 남긴다.
- 구현 단계:
  1. 현재 `data/`와 `_archive` fixture 위치를 분리해 공개/비공개 경계를 정한다.
  2. manifest schema에 private path가 커밋되지 않도록 relative id 중심 구조로 바꾼다.
  3. evaluator가 provider별 text_non_empty, parser_success, ingredient exact, field match, latency를 같은 schema로 내도록 정리한다.
  4. 보고서에는 N, missing image count, raw artifact 저장 여부를 항상 포함한다.
- 검증:
  - evaluator unit test
  - 16 fixture regression
  - 30 fixture expanded run
- 완료 조건:
  - N이 작아서 생기는 과대해석을 줄이고, provider/field별 병목을 분리할 수 있다.

### PR-6: OCR capture quality gate

- 추천 branch: `feat/ocr-capture-quality-gate`
- 범위:
  - 모바일 촬영 직후 blur, crop, angle, glare, resolution warning을 표시한다.
  - backend image safety와 mobile UX 메시지가 같은 warning code를 사용하도록 맞춘다.
- 구현 단계:
  1. 기존 `image_quality` schema와 mobile capture flow를 확인한다.
  2. backend는 deterministic warning code만 반환하고, raw image는 저장하지 않는다.
  3. mobile은 warning code별 재촬영 안내를 제공하되 의료/성능 보장 문구를 쓰지 않는다.
  4. OCR provider 호출 전에 quality gate를 통과하지 못한 이미지는 사용자 확인을 요구한다.
- 검증:
  - backend unit/integration tests
  - Flutter widget/unit tests
  - mobile camera permission smoke
- 완료 조건:
  - 품질 문제를 OCR 실패로만 기록하지 않고 사용자 입력 단계에서 줄인다.

### PR-7: OCR provider routing/metrics 정리

- 추천 branch: `refactor/ocr-provider-routing`
- 범위:
  - PaddleOCR, CLOVA, Google Vision provider 결과를 같은 metrics DTO로 수집한다.
  - external OCR은 `ALLOW_EXTERNAL_OCR=true`와 provider credential이 있을 때만 활성화한다.
- 구현 단계:
  1. provider selector와 settings validation을 다시 표로 정리한다.
  2. latency, empty text, parser success, provider error code를 공통 schema로 만든다.
  3. duplicated fallback이나 external provider accidental call을 막는 테스트를 추가한다.
  4. report generator가 provider별 비교 표를 안정적으로 출력하게 한다.
- 검증:
  - provider factory tests
  - config production validation tests
  - collector redaction tests
- 완료 조건:
  - provider 교체가 기능 코드 수정 없이 config/evaluation layer에서 비교 가능해진다.

### PR-8: Mobile release safety 검증

- 추천 branch: `test/mobile-release-safety`
- 범위:
  - release flavor, HTTPS base URL, token embedding 금지, camera/gallery permission flow를 확인한다.
- 구현 단계:
  1. `flutter analyze`, `flutter test`를 기본 gate로 둔다.
  2. Android/iOS release build에서 API endpoint와 권한 선언을 확인한다.
  3. ngrok/local/dev URL이 release artifact에 남지 않는지 검색한다.
  4. 인증/consent 화면을 OCR flow와 연결해 privacy boundary를 확인한다.
- 검증:
  - `flutter analyze`
  - `flutter test`
  - release build smoke
  - static search for dev URL/token
- 완료 조건:
  - OCR 기능을 release build로 올리기 전에 모바일 노출 리스크가 정리된다.

### PR-9: Learning/vector smoke

- 추천 branch: `test/ai-learning-smoke`
- 범위:
  - pgvector extension, embedding insert/search, object storage link, consent gate를 최소 end-to-end로 확인한다.
- 구현 단계:
  1. 현재 migration과 repository 계층이 실제 DB에 적용 가능한지 확인한다.
  2. raw health/OCR payload가 vector metadata에 들어가지 않는지 테스트한다.
  3. embedding provider unavailable 상태에서 fail-closed/fallback 동작을 확인한다.
  4. 운영 전 필요한 retention/audit 항목을 문서화한다.
- 검증:
  - DB integration smoke
  - privacy metadata unit test
  - no-secret/no-raw search
- 완료 조건:
  - learning/vector 코드를 "스캐폴딩"에서 "제한된 smoke 통과"로 승격할 수 있다.

## 15. 의사결정 트리

```text
PR #3 리뷰 유지
  |
  v
backend 검증 환경이 재현되는가?
  |-- 아니오 -> PR-1 먼저 완료
  |-- 예 ----> 현재 구현 상태 문서가 최신인가?
                 |-- 아니오 -> PR-2 완료
                 |-- 예 ----> OCR 16 fixture에서 ingredient exact가 0인가?
                                |-- 예 -> PR-4 field_extractor 패치
                                |-- 아니오 -> provider/layout별 error taxonomy 작성

PR-4 이후 16 fixture field match가 0.95 이상인가?
  |-- 예 -> PR-5 real-label 30장 확장 후 capture gate로 이동
  |-- 아니오 -> layout parser regression 또는 PP-StructureV3 PoC 검토

real-label 30장에서도 입력 품질 warning 비중이 높은가?
  |-- 예 -> PR-6 mobile capture quality gate 우선
  |-- 아니오 -> PR-7 provider routing/metrics 정리

provider/layout/quality gate 이후에도 0.95 미달인가?
  |-- 예 -> PP-OCRv5 server, PP-StructureV3, PaddleOCR-VL, fine-tune 순서로 비용 평가
  |-- 아니오 -> mobile release safety와 운영 gate로 이동
```

## 16. 공통 검증 게이트

모든 후속 PR은 다음 원칙을 따른다.

| 영역 | 필수 게이트 |
|---|---|
| Git | 브랜치명 규칙 준수, Conventional Commit, `--no-verify` 금지, `--force-with-lease` 외 force 금지 |
| Secret/privacy | `.env`, API key, raw OCR text, provider payload, request header, absolute private image path 커밋 금지 |
| Backend | focused pytest, 관련 unit/integration test, `black --check`, `ruff check`, `git diff --check` |
| Mobile | `flutter analyze`, `flutter test`, release/dev URL static search |
| OCR evaluation | N, missing image count, raw artifact 저장 여부, provider별 latency/error/field metrics 표시 |
| Docs | 구현 claim과 성능 claim 분리, 공식 문서 또는 repo-local report만 근거로 사용 |

## 17. 바로 다음 실행 순서

1. PR #3은 reviewer가 보기 쉬운 상태로 유지한다.
2. 임시 PR worktree는 PR 생성 후 제거하고, 기본 작업은 `$LEMON_AID_ROOT`에서 진행한다.
3. 다음 실제 코드 작업은 `chore/backend-test-env` 또는 현재 `chore/ocr-next-work`에서 backend 검증 환경 복구를 먼저 수행한다.
4. 그 다음 `fix/ocr-field-extractor-shapes`를 별도 작은 PR로 진행한다.
5. OCR 모델 교체나 fine-tune은 field extractor/layout/parser의 낮은 비용 개선이 실패했다는 증거가 생긴 뒤 판단한다.
