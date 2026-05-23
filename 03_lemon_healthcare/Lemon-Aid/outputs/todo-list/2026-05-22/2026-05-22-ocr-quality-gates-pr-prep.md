# 2026-05-22 OCR Quality Gates PR Prep

## Current Branch

- Branch: `feat/ocr-quality-gates`
- Internal base: `codex/p1-5-stabilization`
- Remote target: `team/develop`
- Merge rule: feature -> develop uses Squash
- Commit rule: `<type>(<scope>): <한글/영문 명령형>`, no period, max 50 chars
- Direct rebase status: `git merge-base team/develop HEAD` returns no merge base

## Team Remote Reality Check

`team/develop` is not currently synced with the working Lemon Aid code tree used by this branch.

Observed state:

- `team/develop` contains root-level skeleton folders such as `backend/src`, `backend/tests`, `mobile/lib`, and README/.gitkeep placeholders.
- `team/develop` does not contain `backend/Nutrition-backend/src/ocr/field_extractor.py`.
- `team/feat/ocr-p1-5-followup` does contain the `backend/Nutrition-backend` application tree, but it also tracks generated OCR eval artifacts under `outputs/generated/ocr-eval/`.
- A trial export of PR 1 against `team/develop` failed because the target files do not exist in that index.
- The temporary export worktree and branch created for that trial were removed.
- `backend/scripts/check_pr_export_base.py` now automates this precheck:
  - `origin/feat/ocr-quality-gates` passes as the preserved current branch baseline.
  - `team/develop` fails with missing `backend/Nutrition-backend/src/ocr/field_extractor.py`.
  - `team/feat/ocr-p1-5-followup` fails with forbidden `outputs/generated/ocr-eval/` tracked files.

Implication:

- A small patch PR directly to `team/develop` is blocked until `team/develop` is synced with the Lemon Aid application tree.
- If the team wants immediate review, first create a code-bearing base branch that removes generated OCR eval artifacts, or sync/squash that cleaned application tree into `team/develop`.
- Do not commit generated OCR eval artifacts from the existing team feature branch into new PRs.
- 2026-05-23 local cleanup branch `chore/ocr-clean-export-base` was created
  from `team/feat/ocr-p1-5-followup`, removes generated OCR/live artifacts from
  Git tracking, and passes the export base gate. It is preserved at
  `origin/chore/ocr-clean-export-base`, not pushed to `team`.

## Current Export Gate Status

Latest local evidence:

```text
git fetch team completed on 2026-05-22
origin/feat/ocr-quality-gates: pr_export_base_ok
team/develop: missing backend/Nutrition-backend OCR source/test paths
team/feat/ocr-p1-5-followup: 25 forbidden tracked outputs/generated/ocr-eval paths
chore/ocr-clean-export-base: pr_export_base_ok
git-tracked outputs/generated/ocr-eval count: 0
current branch tracked generated artifact gate: ocr_artifact_privacy_ok files=0
```

This means the current branch is now clean enough to preserve as a safe internal
baseline, but neither team target is ready for a small direct export PR:

- `team/develop` must first receive the real Lemon Aid application tree.
- `team/feat/ocr-p1-5-followup` must first drop generated OCR evaluation files
  from Git tracking while keeping local generated outputs ignored.
- `origin/chore/ocr-clean-export-base` proves that this cleanup is viable:
  generated/live OCR artifact tracking is removed and the branch passes
  `check_pr_export_base.py`.

## Branch Preservation

- Local branch: `feat/ocr-quality-gates`
- Preserved remote: `origin/feat/ocr-quality-gates`
- Clean base candidate: `origin/chore/ocr-clean-export-base`
- PR 1 export candidate: `origin/fix/ocr-field-extractor-shapes`
- PR 2a export candidate: `origin/test/ocr-artifact-privacy-gate`
- Export readiness gate candidate: `origin/test/ocr-pr-export-base-gate`
- Current generated OCR evaluation files are ignored local artifacts, not tracked
  Git content on this branch.
- Team PR not opened yet because `team/develop` is not a code-bearing base for the OCR patch slices.

## Current Recommendation

Do not open this branch as one broad PR, and do not run a direct `git rebase team/develop` on this branch.

Reason:

- The dirty worktree has been split into logical commits, but the accumulated branch still spans backend OCR parsing, API security, mobile release security, and operator evaluation scripts.
- The team guidance recommends small PRs near 500 lines where practical.
- Generated OCR eval artifacts were intentionally ignored via `.gitignore` and should remain out of the PR unless the team explicitly asks for them.
- `team/develop` and this monorepo branch have no merge base, so a direct rebase is not a valid PR-prep step.
- `team/develop` uses the Lemon Aid app at repository root, while this branch stores the app under `03_lemon_healthcare/Lemon-Aid/`.
- The safer review path is to export each logical slice into a fresh team-root branch based on `team/develop`.
- Public GitHub branch metadata currently reports `develop` and `main` as
  unprotected with required status checks off and no active branch rulesets, so
  repository-admin protection remains required before relying on the documented
  team merge policy.

## Actual Commit Slices

| Commit | Suggested PR | Scope |
| --- | --- | --- |
| `3d044dce fix(ocr): 성분 표 셀 파싱을 보정` | Field extractor regression | colon-less/pipe table cells, comma dosage, `mcg` normalization |
| `7a0d3d01 docs(ocr): 품질 게이트 기록을 추가` | Supporting docs | initial quality-gate progress notes |
| `4e4bc9c1 feat(backend): 분석 업로드 제한을 추가` | Analyze API security | upload rate limit, fail-closed config, arbitrary bearer bypass regression |
| `fcf7d02a feat(ocr): CLOVA primary와 토글을 추가` | Provider routing infra | CLOVA primary selector and Paddle textline orientation toggle |
| `422962c9 fix(ocr): 오류 관측치 집계를 보정` | Evaluator correctness | collector-style `status="error"` accounting |
| `473bedf9 feat(ocr): API smoke helper를 추가` | Product API smoke | loopback-only smoke helper with raw-field scan |
| `62635c63 feat(ocr): collector privacy gate를 보강` | Collector privacy | PII local-only review handling and redacted LLM summary |
| `b1b33546 docs(ocr): CLOVA baseline 결과를 기록` | Supporting docs | redacted CLOVA Phase 0 result |
| `fb9a3afd feat(ocr): 라벨 레이아웃 DTO를 추가` | Layout DTO | coordinate-bearing OCR pages and layout fixture |
| `b2603aa7 feat(ocr): 이미지 품질 관측치를 추가` | Image quality preview | deterministic capture quality report and provider observations |
| `bc2b4062 fix(ocr): 어댑터 입력 계약을 보정` | Adapter compatibility | CLOVA primary validation and multilingual adapter contract |
| `2dfe412e feat(mobile): 릴리스 보안 게이트를 추가` | Mobile release security | certificate pins, camera permission channel, local capture warning |
| `20cb69e5 feat(data): Naver OCR 평가 스크립트 추가` | Operator eval tooling | Naver manifest/runner/evaluator with external-transfer guards |
| `815190fa test(ocr): 레이아웃 snapshot fixture 추가` | Snapshot fixtures | synthetic layout snapshot fixture |
| `51e874c5 docs(ocr): 품질 게이트 진행 기록 갱신` | Supporting docs | implementation progress update |
| `1ceaefc2 docs(ocr): 구현 계획 문서를 정리` | Supporting docs | repo-local plan cleanup |
| `f4c0c98b docs(ocr): 로컬 경로 노출을 정리` | Supporting docs | private local path redaction |
| `4ee57222 docs(ocr): PR export 절차를 보정` | Supporting docs | export procedure correction |
| `4b1ecf25 docs(ocr): 팀 브랜치 동기화 조건을 기록` | Supporting docs | team branch synchronization condition |
| `176f46e1 docs(ocr): 브랜치 보존 위치를 기록` | Supporting docs | branch preservation note |
| `a2148df6 docs(ocr): 보존 브랜치 기록을 정리` | Supporting docs | preservation note cleanup |
| `5c0e6611 docs(ocr): 과거 요약 경로 노출을 정리` | Supporting docs | old summary local path redaction |
| `dbe649ee feat(ocr): artifact privacy gate를 추가` | Backend OCR quality gates | generated OCR artifact privacy scanner |
| `8b6b1def fix(backend): 운영 rate limit gate를 보강` | Analyze API security | production/staging rate-limit validation |
| `a7689938 test(ocr): PR export base gate를 추가` | Export readiness | code-bearing base and generated artifact precheck |
| `89fef092 chore(backend): dev env doctor를 추가` | Backend tooling | local dev environment doctor |
| `4b79ecf7 docs(backend): 구현 상태 map을 추가` | Supporting docs | implementation status map |
| `a43f18eb docs(team): enforcement gap을 기록` | Team governance | enforced vs documented rule gap report |
| `b32990ba fix(data): real OCR manifest 유출을 제거` | Data privacy | remove source path and label text from real manifest |
| `b0c4d0b3 fix(ocr): manifest 경로 유출을 차단` | Operator eval tooling | tokenize private source roots in generated manifests |
| `9ba4a053 fix(team): PR base 경로 검사를 보정` | Export readiness | support team-root and monorepo-prefixed path checks |
| `1e04d877 test(ocr): generated artifact 추적 검사를 추가` | Artifact privacy | fail when generated OCR eval outputs are tracked |
| `3e9cb4cf chore(ocr): generated artifact 추적을 제거` | Artifact privacy | stop tracking historical generated OCR eval outputs |
| `c186ccec chore(team): commit type 목록을 동기화` | Team governance | sync enforced commit types with team docs |
| `08860ab7 docs(ocr): PR 준비 상태를 갱신` | Supporting docs | PR prep state and export procedure update |
| `6fa42aa4 chore(team): secret scan hook을 복구` | Team governance | restore detect-secrets baseline hook behavior |
| `f68e233a test(team): secret baseline 감사를 추가` | Team governance | bounded audit for historical secret candidates |
| `8c3aed6d ci(team): team policy gate를 추가` | Team governance | standalone PR template, team policy workflow, validators |
| `7c627258 test(infra): Lemon CI 경로 감사를 추가` | CI path audit | bounded audit for stale root workflow/dependabot/template paths |
| `e219fd34 fix(backend): rate limit 운영 증거를 요구` | Analyze API security | require operational rate-limit proof in non-local environments |
| `af387877 chore(ocr): live 평가 산출물 추적을 제거` | Artifact privacy | remove tracked live OCR smoke artifacts |
| `19c9324a ci(infra): Lemon workflow 경로를 보정` | CI path audit | repair root workflow, dependabot, template, CODEOWNERS paths |
| `7e203bf7 docs(team): credential 예시를 placeholder로 보정` | Team governance | rewrite credential-looking docs placeholders and refresh baseline |
| `07abbf4e ci(infra): CI 보안 gate를 추가` | CI security | run policy, secret, OCR artifact, and path gates in backend CI |
| `d6378ba5 chore(team): 보호 브랜치 push guard를 추가` | Team governance | local pre-push guard for `main`/`develop` direct updates |
| `2febc8d4 docs(ocr): PaddleOCR baseline 결과를 기록` | Supporting docs | post-alpha PaddleOCR comparison summary without generated artifacts |

## Suggested PR Split

### PR 1 - Field Extractor Regression Patch

This is the safest first PR because it is small, deterministic, and directly targets the chronic 0% regression symptom.

Exported branch:

```text
origin/fix/ocr-field-extractor-shapes
```

Base branch:

```text
origin/chore/ocr-clean-export-base
```

Created commit on export branch:

```text
9fac120b fix(ocr): 성분 표 셀 파싱을 보정
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
black --check passed
ruff check --ignore RUF001 passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
secret pattern scan on changed files: no matches
```

### PR 2 - Backend OCR Quality Gates

Suggested commit:

```text
feat(ocr): 품질 게이트 도구를 추가
```

Current first sub-slice:

```text
origin/test/ocr-artifact-privacy-gate
98d51c7c test(ocr): artifact privacy gate를 추가
```

This sub-slice is intentionally narrower than the whole PR 2 list. It adds only
the generated OCR artifact privacy scanner and its tests, because this gate is
needed before exporting any larger OCR evaluation tooling.

Candidate files:

- `backend/scripts/collect_supplement_ocr_observations.py`
- `backend/scripts/evaluate_ocr_three_tier.py`
- `backend/scripts/build_naver_tampermonkey_ocr_manifest.py`
- `backend/scripts/evaluate_naver_tampermonkey_ocr.py`
- `backend/scripts/run_naver_tampermonkey_ocr_eval.py`
- `backend/scripts/smoke_supplement_analyze_api.py`
- `backend/scripts/check_ocr_artifact_privacy.py`
- `backend/scripts/check_pr_export_base.py`
- `backend/Nutrition-backend/tests/unit/scripts/*`
- `outputs/todo-list/2026-05-22/2026-05-22-clova-phase0-baseline-result.md`
- `outputs/todo-list/2026-05-22/2026-05-22-ocr-quality-gates-implementation-progress.md`

Exclude:

- `outputs/generated/ocr-eval/`
- raw OCR text
- secrets, `.env`, request headers, provider payloads

PR 2a validation:

```text
10 passed - test_check_ocr_artifact_privacy.py
black --check passed
ruff check passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
secret pattern scan on changed source files: no matches
```

### PR 2b - PR Export Base Gate

Current sub-slice:

```text
origin/test/ocr-pr-export-base-gate
ea7a9006 test(ocr): PR export base gate를 추가
```

Candidate files:

- `backend/scripts/check_pr_export_base.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_pr_export_base.py`

Scope:

- require code-bearing OCR backend paths in the base ref
- reject `.env` tracking in the base ref
- reject `outputs/generated/ocr-eval/` tracking in the base ref
- support both team-root and monorepo-prefixed layouts
- keep CLI output bounded

Validation:

```text
6 passed - test_check_pr_export_base.py
black --check passed
ruff check passed
chore/ocr-clean-export-base: pr_export_base_ok
team/develop: missing required OCR source/test paths
team/feat/ocr-p1-5-followup: forbidden tracked outputs/generated/ocr-eval paths
secret pattern scan on changed source files: no matches
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
- production fail-closed guard requiring external ingress/API gateway/Redis rate-limit enforcement
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

PaddleOCR post-alpha:

```text
16 observations, 14 completed, 2 errors
raw_artifacts_stored=false
raw_ocr_text_stored=false
text_non_empty_rate=0.875
parser_success_rate=0.875
ingredient_name_exact_rate=0.9375
accuracy_by_condition: cardiovascular=1.0, diabetes=1.0, dyslipidemia=1.0, osteoporosis=1.0
artifact privacy scanner: ocr_artifact_privacy_ok files=4
```

Export and artifact privacy:

```text
pr_export_base_ok ref=origin/feat/ocr-quality-gates
team/develop fails with missing required OCR source/test paths
team/feat/ocr-p1-5-followup fails with tracked outputs/generated/ocr-eval files
git-tracked outputs/generated/ocr-eval count is 0 on the current branch
ocr_artifact_privacy_ok files=0 with --check-tracked-generated
```

## Export / PR Procedure

Do not directly rebase this branch onto `team/develop`.

The preferred team PR branch should be created from `team/develop` only after `team/develop` contains the real Lemon Aid application tree.

Until then, use this procedure only against a code-bearing base branch such as `team/feat/ocr-p1-5-followup`, or treat it as blocked pending team/develop synchronization.

Pre-checks:

```bash
git fetch team
git merge-base team/develop HEAD
# expected here: no output / non-zero because histories are unrelated

PYTHONPATH=backend/Nutrition-backend:backend \
  $PYTHON_BIN backend/scripts/check_pr_export_base.py \
  --repo-root $MONOREPO_ROOT \
  --base-ref $CODE_BEARING_BASE_BRANCH

PYTHONPATH=backend/Nutrition-backend:backend \
  $PYTHON_BIN backend/scripts/check_ocr_artifact_privacy.py \
  --check-tracked-generated \
  --project-root .
```

The check must pass before creating an export worktree. It rejects:

- skeleton bases missing `backend/Nutrition-backend/src/ocr/field_extractor.py`
- bases that already track `outputs/generated/ocr-eval/`
- bases that track `.env`

Example export for PR 1:

```bash
git worktree add -b feat/ocr-field-extractor-regression \
  $EXPORT_WORKTREE \
  $CODE_BEARING_BASE_BRANCH

git -C $MONOREPO_ROOT diff --binary \
  --relative=03_lemon_healthcare/Lemon-Aid \
  3d044dce^ 3d044dce \
  -- \
  03_lemon_healthcare/Lemon-Aid/backend/Nutrition-backend/src/ocr/field_extractor.py \
  03_lemon_healthcare/Lemon-Aid/backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py \
  | git -C $EXPORT_WORKTREE apply --index
```

After applying a slice:

```bash
git -C $EXPORT_WORKTREE status --short
git diff --check
PYTHONPATH=backend/Nutrition-backend:backend \
  $PYTHON_BIN -m pytest <selected backend PR test set> -q --no-cov
```

Conflict resolution must preserve:

- raw OCR text non-storage policy
- `ALLOW_EXTERNAL_OCR` and consent gates
- `ALLOW_EXTERNAL_LLM=false` local Ollama default
- production/staging security validation guards
- generated/private OCR artifacts excluded from Git
- `backend/scripts/check_ocr_artifact_privacy.py` passes on any exported artifact files
- `backend/scripts/check_pr_export_base.py` passes on the chosen base ref

Push only after the exported team-root branch passes tests and the changed-file secret/path scan is empty.
