# 2026-05-22 OCR Quality Gates PR Prep

## Current Branch

- Branch: `feat/ocr-quality-gates`
- Remote target: `team/develop`
- Merge rule: feature -> develop uses Squash
- Commit rule: `<type>(<scope>): <한글/영문 명령형>`, no period, max 50 chars

## Current Recommendation

Do not open this branch as one broad PR without an explicit reviewer agreement.

Reason:

- The dirty worktree has been split into logical commits, but the accumulated branch still spans backend OCR parsing, API security, mobile release security, and operator evaluation scripts.
- The team guidance recommends small PRs near 500 lines where practical.
- Generated OCR eval artifacts were intentionally ignored via `.gitignore` and should remain out of the PR unless the team explicitly asks for them.
- A single integration PR is possible for end-to-end traceability, but the safer review path is cherry-picking grouped commits into smaller branches.

## Actual Commit Slices

| Commit | Suggested PR | Scope |
| --- | --- | --- |
| `3d044dce fix(ocr): 성분 표 셀 파싱을 보정` | Field extractor regression | colon-less/pipe table cells, comma dosage, `mcg` normalization |
| `4e4bc9c1 feat(backend): 분석 업로드 제한을 추가` | Analyze API security | upload rate limit, fail-closed config, arbitrary bearer bypass regression |
| `fcf7d02a feat(ocr): CLOVA primary와 토글을 추가` | Provider routing infra | CLOVA primary selector and Paddle textline orientation toggle |
| `473bedf9 feat(ocr): API smoke helper를 추가` | Product API smoke | loopback-only smoke helper with raw-field scan |
| `62635c63 feat(ocr): collector privacy gate를 보강` | Collector privacy | PII local-only review handling and redacted LLM summary |
| `fb9a3afd feat(ocr): 라벨 레이아웃 DTO를 추가` | Layout DTO | coordinate-bearing OCR pages and layout fixture |
| `b2603aa7 feat(ocr): 이미지 품질 관측치를 추가` | Image quality preview | deterministic capture quality report and provider observations |
| `bc2b4062 fix(ocr): 어댑터 입력 계약을 보정` | Adapter compatibility | CLOVA primary validation and multilingual adapter contract |
| `2dfe412e feat(mobile): 릴리스 보안 게이트를 추가` | Mobile release security | certificate pins, camera permission channel, local capture warning |
| `20cb69e5 feat(data): Naver OCR 평가 스크립트 추가` | Operator eval tooling | Naver manifest/runner/evaluator with external-transfer guards |
| `815190fa test(ocr): 레이아웃 snapshot fixture 추가` | Snapshot fixtures | synthetic layout snapshot fixture |

## Suggested PR Split

### PR 1 - Backend OCR Quality Gates

Suggested commit:

```text
feat(ocr): 품질 게이트 도구를 추가
```

Candidate files:

- `backend/scripts/collect_supplement_ocr_observations.py`
- `backend/scripts/evaluate_ocr_three_tier.py`
- `backend/scripts/build_naver_tampermonkey_ocr_manifest.py`
- `backend/scripts/evaluate_naver_tampermonkey_ocr.py`
- `backend/scripts/run_naver_tampermonkey_ocr_eval.py`
- `backend/scripts/smoke_supplement_analyze_api.py`
- `backend/Nutrition-backend/tests/unit/scripts/*`
- `outputs/todo-list/2026-05-22/2026-05-22-clova-phase0-baseline-result.md`
- `outputs/todo-list/2026-05-22/2026-05-22-ocr-quality-gates-implementation-progress.md`

Exclude:

- `outputs/generated/ocr-eval/2026-05-22-*`
- raw OCR text
- secrets, `.env`, request headers, provider payloads

### PR 2 - Field Extractor Regression Patch

Created commit:

```text
3d044dce fix(ocr): 성분 표 셀 파싱을 보정
```

Candidate files:

- `backend/Nutrition-backend/src/ocr/field_extractor.py`
- `backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py`

Scope:

- colon-less table rows
- pipe-separated rows
- thousand comma dosage
- `mcg`/`µg` normalization
- unit suffix case canonicalization

Validation:

```text
27 passed - backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py
```

### PR 3 - Analyze API Security Gate

Suggested commit:

```text
feat(backend): 분석 업로드 제한을 추가
```

Candidate files:

- `backend/Nutrition-backend/src/middleware/rate_limit.py`
- `backend/Nutrition-backend/src/main.py`
- `backend/Nutrition-backend/src/config.py`
- `backend/Nutrition-backend/tests/integration/api/test_supplement_intake_api.py`
- `backend/Nutrition-backend/tests/unit/test_config.py`

Scope:

- process-local fixed-window limiter for `POST /api/v1/supplements/analyze`
- 429 response with `Retry-After`
- staging/production fail-closed guard for disabled rate limit
- hashed client-derived subject keys only
- regression test that changing arbitrary `Authorization` headers cannot bypass the upload limit

### PR 4 - Mobile Release Security

Suggested commit:

```text
feat(mobile): 릴리스 보안 게이트를 추가
```

Candidate files:

- `mobile/lib/core/config/app_config.dart`
- `mobile/lib/core/api/api_client.dart`
- `mobile/lib/core/api/certificate_pin_verifier.dart`
- `mobile/android/app/src/main/AndroidManifest.xml`
- `mobile/android/app/src/main/kotlin/com/lemonaid/mobile/MainActivity.kt`
- `mobile/ios/Runner/AppDelegate.swift`
- `mobile/test/unit/app_config_test.dart`
- `mobile/test/unit/api_client_certificate_pin_test.dart`
- `mobile/test/unit/release_security_config_test.dart`
- `mobile/scripts/verify_release_artifact.py`

Scope:

- release HTTPS enforcement
- embedded token rejection
- certificate pin validation before API traffic
- Android hostname verification before certificate pin match
- iOS SSL hostname policy before certificate pin match
- Android cleartext block
- iOS ATS arbitrary-load block

## Validation Already Run

Backend:

```text
153 passed - OCR/script/security/supplement analyze integration set
71 passed - focused rate-limit/config/security-header set
104 passed - YOLO/ROI/image-analysis/config gate set
42 passed - Ollama parser/vision/factory set
Black check passed on latest backend security files
Ruff check passed on latest backend security files with --ignore RUF001
git diff --check passed
```

Mobile:

```text
23 passed - app config, certificate pin, release security, supplement model tests
Dart format checked 7 files, 0 changed
Android dev debug flavor build passed
iOS simulator debug build passed
```

Ollama:

```text
parser_ready=True parser_model=gemma4:e4b parser_error=None
vision_ready=True vision_model=gemma4:e4b vision_error=None
parse_ok=true ingredient_count=2 product_name_present=True
```

CLOVA:

```text
16 observations, 15 completed, 1 error
raw_artifacts_stored=false
raw_ocr_text_stored=false
ingredient_name_exact_rate=0.0
```

## Rebase / PR Procedure

Before pushing:

```bash
git fetch team
git rebase team/develop
```

If conflicts appear, resolve by preserving:

- raw OCR text non-storage policy
- `ALLOW_EXTERNAL_OCR` and consent gates
- `ALLOW_EXTERNAL_LLM=false` local Ollama default
- production/staging security validation guards

After rebase:

```bash
git diff --check
PYTHONPATH=backend/Nutrition-backend:backend /private/tmp/lemon-p1-quality-venv/bin/python -m pytest <selected backend PR test set> -q --no-cov
cd mobile && flutter test <selected mobile PR test set>
```

Push only after generated/private artifacts are excluded.
