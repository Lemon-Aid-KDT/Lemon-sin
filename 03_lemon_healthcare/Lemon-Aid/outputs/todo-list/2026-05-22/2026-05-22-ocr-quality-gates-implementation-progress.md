# 2026-05-22 OCR Quality Gates Implementation Progress

## Scope

상세 구현 플랜 `2026-05-22-ocr-yolo-ollama-flutter-simulation-plan.md` 기준으로 진행한 구현/검증 기록이다.

이번 tranche의 목적:

- Phase 0 CLOVA baseline 결과를 남긴 뒤, 안전한 후속 PR 후보인 Phase 0-alpha parser 회귀 패치를 진행한다.
- OCR 원문, provider raw payload, request header, secret, image bytes가 코드/산출물에 노출되지 않는지 같이 점검한다.

## Implemented

### 1. Product API Local Smoke Helper

추가 파일:

- `backend/scripts/smoke_supplement_analyze_api.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_smoke_supplement_analyze_api.py`

기능:

- `POST /api/v1/supplements/analyze` multipart 업로드 경로를 local loopback 기준으로 smoke test한다.
- 기본적으로 `127.0.0.1`, `localhost`, `::1`, `10.0.2.2` API URL만 허용한다.
- `clova`, `google_vision` 같은 외부 OCR provider selector는 `--allow-external-provider` 없이는 거부한다.
- API response를 재귀 검사해서 raw OCR text, provider payload, request headers, image bytes, secret 계열 키가 있으면 실패한다.
- 출력/저장 summary는 status, provider metadata, count/boolean/latency류 bounded field만 포함한다.

### 2. CLOVA Phase 0 Baseline

산출물:

- `outputs/generated/ocr-eval/2026-05-22-stage1-clova/supplement-ocr-observations.jsonl`
- `outputs/generated/ocr-eval/2026-05-22-stage1-clova/manifest-with-clova-observations.jsonl`
- `outputs/generated/ocr-eval/2026-05-22-stage1-clova/ocr-three-tier-evaluation.json`
- `outputs/generated/ocr-eval/2026-05-22-stage1-clova/ocr-three-tier-evaluation.md`
- `outputs/todo-list/2026-05-22/2026-05-22-clova-phase0-baseline-result.md`

결과:

- 16 fixture 전송
- completed 15, error 1
- `text_non_empty_rate=0.9375`
- `parser_success_rate=0.9375`
- `ingredient_name_exact_rate=0.0`
- chronic condition accuracy는 4개 모두 `0.0`
- `raw_artifacts_stored=false`
- `raw_ocr_text_stored=false`

해석:

- CLOVA는 대부분의 fixture에서 text를 반환했지만, 현재 three-tier expected 기준으로 ingredient exact는 개선되지 않았다.
- provider 교체만으로 회귀가 해소되지 않으므로 parser/layout/LLM structured parse 분리가 필요하다.

### 3. Evaluation Error Count Fix

수정 파일:

- `backend/scripts/evaluate_ocr_three_tier.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_evaluate_ocr_three_tier.py`

변경:

- evaluator가 legacy `error: true`뿐 아니라 collector-style `status: "error"`도 provider error count에 반영한다.
- CLOVA baseline의 1건 error가 JSON report에 `errors=1`로 반영되도록 회귀 테스트를 추가했다.

### 3.5 Generated Artifact Privacy Gate

추가 파일:

- `backend/scripts/check_ocr_artifact_privacy.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_ocr_artifact_privacy.py`

변경:

- generated OCR artifact 디렉터리에서 raw OCR key, provider payload key, request header, secret key, local absolute path를 재귀 검사한다.
- `.gitignore`를 `outputs/generated/ocr-eval/` 전체 ignore로 넓혀, 새 provider observation/manifest/report가 실수로 PR에 포함되지 않게 했다.
- 기존 tracked OCR eval report 22개는 raw key는 없었지만 개발자 홈/외장 드라이브 경로가 남아 있어 `$LEMON_AID_ROOT`, `$LEMON_AID_BACKEND_ROOT`, `$NAVER_TAMPERMONKEY_SOURCE_ROOT` 또는 상대경로로 보정했다.
- 2026-05-22 CLOVA baseline 산출물 4개도 scanner로 재검사했고 통과했다.

### 3.6 PR Export Base Gate

추가 파일:

- `backend/scripts/check_pr_export_base.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_pr_export_base.py`

변경:

- PR/export base ref가 실제 Lemon Aid OCR backend tree를 포함하는지 검사한다.
- base ref가 `.env` 또는 `outputs/generated/ocr-eval/`을 이미 tracking 중이면 실패한다.
- 현재 팀 remote 검증 결과:
  - `team/develop`은 skeleton 상태라 `backend/Nutrition-backend/src/ocr/field_extractor.py` 누락으로 실패한다.
  - `team/feat/ocr-p1-5-followup`은 code-bearing branch지만 generated OCR eval artifacts를 tracking 중이라 실패한다.
  - 따라서 첫 export PR 전에 code-bearing base cleanup 또는 `team/develop` 동기화가 필요하다.

### 3.7 Backend Dev Env Doctor

추가/수정 파일:

- `backend/scripts/check_backend_dev_env.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_backend_dev_env.py`
- `docs/team-collaboration/LOCAL_SETUP.md`

변경:

- `LOCAL_SETUP.md`의 backend 설치 명령을 실제 `backend/requirements-dev.txt` 기준으로 보정했다.
- doctor는 `.env` 값을 읽지 않고 다음 항목만 확인한다.
  - 필수 backend path 존재 여부
  - `backend/pyproject.toml`의 `requires-python`과 현재 Python 버전
  - `backend/requirements-dev.txt`의 runtime include와 pytest/black/ruff/mypy/pip-audit 선언
  - 현재 interpreter에서 focused backend 검증 도구 import 가능 여부
  - `.env`, `.venv`, coverage/htmlcov 같은 local-only artifact가 Git에 tracked되어 있는지 여부
- 실제 checkout에서 `backend_dev_env_ok checks=5`를 확인했다.

보안 확인:

- doctor는 `.env`, request header, OCR artifact, provider payload, application settings를 열지 않는다.
- CLI output은 project-relative path와 count 중심으로 제한하고, 로컬 절대경로나 secret 값을 출력하지 않는다.

### 3.8 Current Implementation Status Map

추가 파일:

- `outputs/todo-list/2026-05-22/2026-05-22-current-implementation-status-map.md`

변경:

- `src/main.py`와 `src/api/v1/router.py` 기준으로 현재 등록된 FastAPI router를 정리했다.
- OCR provider, regulated intake, supplement intake, prediction, learning/vector, YOLO ROI, Ollama/Gemma4, mobile release safety 상태를 `implemented`, `feature-gated`, `smoke-only`, `not-production-ready`로 분리했다.
- 성능 수치는 repo-local generated report에서 확인한 값만 기록했고, 없는 값은 만들지 않았다.
- raw OCR/provider payload, request header, secret, local absolute path를 commit하지 않는 보안 gate를 같은 문서에 붙였다.

### 3.9 Team Governance Enforcement Gap Report

추가 파일:

- `outputs/todo-list/2026-05-22/2026-05-22-team-governance-enforcement-gap-report.md`

변경:

- `docs/team-collaboration/` 규칙과 실제 `.pre-commit-config.yaml`, Git root `.github`, team remote branch 상태를 비교했다.
- 현재 checkout에서 `pre-commit validate-config`는 통과하지만, `detect-secrets`는 `.secrets.baseline` 부재로 실패하고 `markdownlint`는 `.markdownlint.json` 부재와 기존 markdown findings로 실패함을 기록했다.
- 현재 Git root Lemon CI workflow가 `03_lemon_healthcare/yeong-Lemon-Aid/...` 경로를 기준으로 하므로, 기본 작업 경로 `03_lemon_healthcare/Lemon-Aid/...`에는 그대로 적용되지 않는 gap을 기록했다.
- `team/docs/team-collaboration-rules`에 PR template, team-policy workflow, hook scripts가 이미 있으나, 현재 code-bearing tree와 결합하려면 별도 governance PR이 필요하다고 정리했다.

보안 확인:

- `.env` 값은 읽지 않았다.
- report에는 secret 값, raw OCR text, provider payload, request header, private image path를 포함하지 않았다.
- missing secret baseline과 stale CI path를 유출/우회 위험으로 분리해 후속 P0/P1 PR 후보에 넣었다.

### 3.10 Real OCR Manifest Privacy Redaction

수정 파일:

- `data/ocr_eval/real_manifest.json`
- `backend/scripts/check_ocr_artifact_privacy.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_ocr_artifact_privacy.py`

변경:

- tracked real manifest에서 외장 디스크 절대경로 `source_root`, item별 `source_path`, raw label/OCR text 성격의 `gt_text`를 제거했다.
- 86개 item과 7개 human-labeled flag는 유지하고, committed manifest에는 relative `image_path`, `category`, derived `gt_fields`, bootstrap metadata만 남겼다.
- real manifest top-level `privacy` block에 `source_root_stored=false`, `source_paths_stored=false`, `raw_label_text_stored=false`, `raw_ocr_text_stored=false`를 기록했다.
- artifact privacy scanner가 `kind="real"` JSON manifest에서 `source_root`, `source_path`, `gt_text` 키를 금지하도록 보강했다.
- synthetic manifest의 generated `gt_text`는 deterministic fixture text라 계속 허용하도록 회귀 테스트를 분리했다.

보안 확인:

- `data/ocr_eval/real_manifest.json`에서 developer-home path, external-volume path, `"gt_text"`, `"source_path"`, `"source_root"` exact pattern은 더 이상 발견되지 않는다.
- `check_ocr_artifact_privacy.py`가 real/synthetic manifests 3개를 모두 통과했다.
- 이 작업은 이미지 파일 자체나 derived `gt_fields`를 삭제하지 않고, private provenance path와 raw full-label text만 제거했다.

### 3.11 Naver Tampermonkey Manifest Path Tokenization

수정 파일:

- `backend/scripts/build_naver_tampermonkey_ocr_manifest.py`
- `backend/scripts/collect_supplement_ocr_observations.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_build_naver_tampermonkey_ocr_manifest.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_collect_supplement_ocr_observations.py`
- `outputs/todo-list/2026-05-22/2026-05-22-naver-tampermonkey-ocr-ollama-plan.md`

변경:

- Naver Tampermonkey manifest builder가 `image_path`에 developer-home 또는 external-volume 절대경로를 쓰지 않고 `$NAVER_TAMPERMONKEY_SOURCE_ROOT/...` 토큰 경로를 기록한다.
- collector는 allowlisted image root env var만 runtime에 해석한다.
- 허용 env var는 `NAVER_TAMPERMONKEY_SOURCE_ROOT`, `LEMON_OCR_FIXTURE_ROOT`, `SUPPLEMENT_OCR_FIXTURE_ROOT`로 제한했다.
- env path suffix는 absolute path와 `..` traversal을 거부한다.
- tracked plan 예시의 external-volume 경로도 env-token 예시로 보정했다.

보안 확인:

- manifest 자체는 operator-local absolute path를 저장하지 않는다.
- collector 오류는 env var 이름만 출력하고 실제 env 값 또는 로컬 경로를 출력하지 않는다.
- 기존 absolute image path manifest도 하위 호환을 위해 읽을 수 있지만, 새 builder 출력은 privacy scanner의 local-path rule을 통과하도록 설계했다.

### 3.12 PR Export Base Monorepo Path Guard

수정 파일:

- `backend/scripts/check_pr_export_base.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_pr_export_base.py`

변경:

- PR export base checker가 standalone team repo 형태의 `backend/...` 경로와 monorepo checkout 형태의 `03_lemon_healthcare/Lemon-Aid/backend/...` 경로를 모두 검사하도록 보강했다.
- `--project-root` 옵션을 추가해 nested project root를 명시할 수 있게 했다.
- CLI 기본 실행은 현재 directory를 project root로 보고 Git root는 `git rev-parse --show-toplevel`로 해석한다.
- required path는 standalone path와 monorepo-prefixed path 중 하나라도 존재하면 통과한다.
- forbidden prefix는 standalone path와 monorepo-prefixed path를 모두 검사해 generated OCR eval artifact tracking을 놓치지 않는다.

보안 확인:

- skeleton base를 code-bearing base로 오판하는 false positive를 줄인다.
- monorepo-origin branch의 code path를 missing으로 오판하는 false negative를 줄인다.
- generated OCR eval artifact는 standalone/team branch와 monorepo/origin branch 양쪽에서 모두 차단된다.

### 3.13 Current Branch Tracked Generated Artifact Gate

수정 파일:

- `backend/scripts/check_ocr_artifact_privacy.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_ocr_artifact_privacy.py`

변경:

- artifact privacy checker에 `--check-tracked-generated` 옵션을 추가했다.
- 기본 forbidden tracked prefix는 `outputs/generated/ocr-eval/`이다.
- 검사는 `git ls-files -- <prefix>` 기준으로 project-root에서 현재 index가 generated OCR artifact를 추적하는지 확인한다.
- 공식 근거: Git `ls-files` 문서의 tracked/index file listing 동작을 기준으로 했다. https://git-scm.com/docs/git-ls-files.html
- ignored/untracked generated artifact는 로컬 산출물로 허용하지만, Git-tracked 상태이면 `tracked_generated_artifact git_tracked`로 실패한다.
- 이 gate는 파일 내용을 출력하지 않고 project-relative path와 bounded code만 출력한다.

현재 브랜치 확인:

- `git ls-files outputs/generated/ocr-eval` 결과는 비어 있다.
- `git rm -r --cached outputs/generated/ocr-eval`로 22개 historical generated artifact의 Git 추적만 제거했다.
- 공식 근거: Git `rm --cached` 문서는 working tree 파일을 유지하고 index에서만 제거하는 용도다. https://git-scm.com/docs/git-rm.html
- `find outputs/generated/ocr-eval -type f | wc -l` 결과 로컬 generated artifact 62개는 작업 디스크에 남아 있다.
- `check_ocr_artifact_privacy.py --check-tracked-generated --project-root .`는 이제 통과한다.
- 이후 PR/export branch에서는 generated OCR evaluation artifact가 Git에 포함되지 않으며, 필요한 수치와 해석은 repo-local todo report에 redacted summary로만 남긴다.

### 3.14 Commit Type Enforcement Sync

수정 파일:

- `.pre-commit-config.yaml`
- `outputs/todo-list/2026-05-22/2026-05-22-team-governance-enforcement-gap-report.md`

변경:

- 팀 문서 `COMMIT_CONVENTION.md`의 허용 type 목록과 local `conventional-pre-commit` hook args를 맞췄다.
- 기존 local hook은 `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`만 허용했다.
- `build`, `revert`, `data`, `ops`를 추가해 문서상 유효한 커밋이 local hook에서 거부되지 않게 했다.
- 공식 근거: `conventional-pre-commit`은 hook args로 허용 type 목록을 전달한다. https://github.com/compilerla/conventional-pre-commit
- 공식 근거: pre-commit config의 `args`는 hook에 전달되는 static arguments다. https://pre-commit.com/

보안/운영 확인:

- documented valid commit type이 local hook에서 막히면 `--no-verify` 사용 압력이 생긴다.
- 이번 변경은 type allow-list mismatch만 닫는다.
- scope allow-list, subject 길이, 마침표 금지는 별도 team-policy validator에서 계속 다뤄야 한다.

### 3.15 Secret Scan and Markdownlint Bootstrap

수정 파일:

- `.pre-commit-config.yaml`
- `.secrets.baseline`
- `.markdownlint.json`
- `outputs/todo-list/2026-05-22/2026-05-22-team-governance-enforcement-gap-report.md`

변경:

- `detect-secrets` baseline을 추가해 local secret hook이 missing baseline
  error로 즉시 실패하던 상태를 닫았다.
- baseline은 현재 Lemon-Aid tracked files에서 나온 33 files / 87 historical
  candidates를 detector type, filename, line number, hashed secret 형태로만
  기록한다.
- `.markdownlint.json`을 low-noise bootstrap rules로 추가해 configured hook이
  missing config error로 실패하지 않게 했다.
- `.pre-commit-config.yaml`의 file hooks가 현재 상위 Git root의 다른
  프로젝트가 아니라 Lemon-Aid 경로만 보도록 path filter를 추가했다.
- hook entry는 현재 monorepo path와 향후 standalone team-root export path에서
  Lemon-Aid root로 이동한 뒤 project-relative file path로 검사하게 했다.

검증:

```text
pre-commit validate-config .pre-commit-config.yaml
pre-commit run detect-secrets --all-files
pre-commit run markdownlint --all-files
```

보안 확인:

- baseline/config 변경분에서 local absolute path prefix, auth header,
  private key, explicit secret assignment 패턴은 발견되지 않았다.
- baseline은 cleartext candidate value를 저장하지 않는 hash 기반 gate다.
- 다만 baseline이 모든 historical candidate가 안전하다는 증명은 아니므로,
  87개 후보의 별도 audit은 후속 governance PR로 남긴다.
- 공식 근거: `detect-secrets scan > .secrets.baseline`은 baseline 생성
  quickstart로 문서화되어 있다. https://github.com/Yelp/detect-secrets
- 공식 근거: `markdownlint-cli`는 `.markdownlint.json` 등 config file을
  지원한다. https://www.npmjs.com/package/markdownlint-cli

### 3.16 Detect-Secrets Baseline Audit

추가 파일:

- `backend/scripts/audit_detect_secrets_baseline.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_audit_detect_secrets_baseline.py`

변경:

- `.secrets.baseline` 후보를 값 출력 없이 detector type, file, line,
  category, severity로 분류하는 bounded audit helper를 추가했다.
- 분류 로직은 test fixture, env example, content hash, design asset,
  framework identifier, local dev sentinel, sample key parameter, docs
  placeholder를 구분한다.
- report renderer는 candidate line content를 출력하지 않는다.

현재 감사 결과:

```text
detect_secrets_baseline_audit files=33 findings=87 manual_review=0 cleartext_values_printed=false
low=72 medium=15 high=0
content_hash=18
design_asset=36
documented_placeholder=15
env_example_placeholder=1
framework_identifier=3
local_dev_default=3
sample_key_parameter=1
test_fixture=10
```

검증:

```text
4 passed - test_audit_detect_secrets_baseline.py
pre-commit run detect-secrets --files audit script/test
```

보안 확인:

- audit CLI output에는 hashed secret, source line content, auth header,
  provider payload, raw OCR text가 포함되지 않는다.
- `--fail-on-manual-review` 옵션으로 high-severity 미분류 후보가 생기면
  CI/수동 게이트에서 실패시킬 수 있다.
- 현재 automated audit 기준 high-severity manual review item은 0개다.
- medium documentation placeholder 15건은 문서 맥락상 값 출력 없이 남겼고,
  후속 PR에서 문서 예시값을 더 명확한 placeholder로 바꿀 수 있다.
- 공식 근거: `detect-secrets-hook --baseline .secrets.baseline`은 baseline
  기준으로 새 secret을 막는 사용법으로 문서화되어 있다.
  https://github.com/Yelp/detect-secrets

### 3.17 Standalone Team Policy Gate Assets

추가 파일:

- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/team-policy.yml`
- `scripts/git-hooks/validate_commit_msg.py`
- `scripts/git-hooks/validate_team_policy.py`
- `backend/scripts/check_team_policy_assets.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_team_policy_assets.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_validate_team_policy.py`

변경:

- `team/docs/team-collaboration-rules`의 team-policy 방향을 현재 Lemon-Aid
  code-bearing tree에 맞게 standalone export용 자산으로 옮겼다.
- PR template은 `develop` target, branch shape, Conventional Commit title,
  pre-commit, secret, raw OCR text, provider payload, generated OCR artifact
  체크를 포함한다.
- team-policy workflow는 PR/push에서 branch/title policy와 policy asset
  preflight를 실행한다.
- `validate_commit_msg.py`는 `<type>(<scope>): <subject>` 형식, 허용
  type/scope, 50자 이하 subject, 마침표 금지를 검증한다.
- `validate_team_policy.py`는 worker-name branch를 막고 protected branch
  direct push를 실패시킨다.
- `check_team_policy_assets.py`는 PR template/workflow/hook scripts가
  존재하고, stale `yeong-Lemon-Aid` 경로나 local absolute path, obvious
  secret snippet이 들어가지 않았는지 검사한다.

검증:

```text
team_policy_assets_ok files=4
valid branch/title policy smoke passed
invalid worker branch/title policy smoke failed as expected
9 passed - test_check_team_policy_assets.py + test_validate_team_policy.py
black --check and ruff check passed on policy scripts/tests
pre-commit detect-secrets passed on policy assets
check-yaml passed on team-policy workflow
```

보안 확인:

- nested monorepo의 Git root `.github`는 이번 변경에서 직접 수정하지 않았다.
- standalone team-root export 시 `.github`와 `scripts/git-hooks`가 실제 repo
  root 자산으로 동작하도록 Lemon-Aid 내부에 추가했다.
- workflow는 `permissions: contents: read`만 사용한다.
- policy asset checker는 secret files를 읽지 않고 정책 파일 4개만 검사한다.
- 공식 근거: GitHub는 `.github/PULL_REQUEST_TEMPLATE.md` 위치의 PR
  template을 지원한다. https://docs.github.com/en/enterprise-cloud@latest/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository
- 공식 근거: GitHub Actions `pull_request`/`push` branch filters and workflow
  contexts are documented by GitHub. https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/triggering-a-workflow

### 4. Phase 0-alpha Field Extractor Patch

커밋:

- `3d044dce fix(ocr): 성분 표 셀 파싱을 보정`

수정 파일:

- `backend/Nutrition-backend/src/ocr/field_extractor.py`
- `backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py`

변경:

- colon-less table cell row 지원:
  - `비타민 C  1000mg`
  - `비타민 D  25μg`
- pipe-separated table row 지원:
  - `비타민 C | 1000mg`
- thousand comma dosage normalization:
  - `1,000mg` → `1000mg`
- `mcg`/`µg` unit variant normalization:
  - `25mcg` → `25μg`
- compound unit suffix canonicalization:
  - `25 μg rae` → `25μg RAE`
- 과검출 방지:
  - 제품명처럼 보일 수 있는 `비타민 C 1000mg` 단일 공백 형태는 ingredient row로 추출하지 않는다.

주의:

- 현재 `field_extractor`는 product API orchestration path에 직접 연결된 코드가 아니라 field-level evaluation/testbed 쪽에서 주로 사용된다.
- 이 패치는 "평가/회귀 진단 정규식 보정"으로 유지하고, 실제 product API 성분 후보 개선은 `supplement_parser`/layout parser/LLM structured parse 경로를 별도로 검증해야 한다.

### 5. Backend Analyze API Security Test Hardening

수정 파일:

- `backend/Nutrition-backend/tests/integration/api/test_supplement_analyze_paddleocr_default.py`
- `backend/Nutrition-backend/tests/integration/api/test_supplement_analyze_google_vision.py`
- `backend/Nutrition-backend/tests/integration/api/test_supplement_intake_api.py`

변경:

- `/api/v1/supplements/analyze` PaddleOCR 기본 경로 response를 재귀 검사해 raw OCR/image/provider field가 노출되지 않는지 테스트한다.
- fake OCR이 parser에 넘긴 full OCR text가 API response JSON에 그대로 포함되지 않는지 확인한다.
- `provider_observations`가 `raw_ocr_text_stored=false`, `raw_provider_payload_stored=false`만 노출하는지 고정했다.
- current route의 `_commit_consent_read_transaction()` helper에 맞춰 integration test fake sessions에 `in_transaction()`을 추가했다.
- intake route tests가 repo `.env`의 외부 OCR 설정에 흔들리지 않도록 `_env_file=None` settings를 명시했다.

보안 확인:

- default PaddleOCR path는 `ocr_image_processing` consent만 요구한다.
- Google Vision external path는 `ocr_image_processing` + `external_ocr_processing` consent를 모두 요구한다.
- external OCR consent가 빠지면 fake external OCR adapter는 호출되지 않는다.
- invalid media type, oversized upload, idempotency conflict는 analysis row를 만들지 않는다.

발견한 남은 이슈:

- 이전 검사 시 `/api/v1/supplements/analyze` OpenAPI response에는 `429` 예시가 있었지만 rate-limit 구현이 없었다.
- 아래 6번에서 `supplement_image_upload` bucket 기준 process-local limiter를 추가해 현재 checkout 기준의 무제한 업로드/외부 OCR 비용폭주 구멍은 닫았다.

### 6. Supplement Analyze Rate Limit Gate

수정/추가 파일:

- `backend/Nutrition-backend/src/middleware/rate_limit.py`
- `backend/Nutrition-backend/src/main.py`
- `backend/Nutrition-backend/src/config.py`
- `backend/Nutrition-backend/tests/integration/api/test_supplement_intake_api.py`
- `backend/Nutrition-backend/tests/unit/test_config.py`

Official references:

- Starlette middleware docs: https://www.starlette.io/middleware/
- FastAPI middleware execution order docs: https://fastapi.tiangolo.com/tutorial/middleware/

변경:

- `POST /api/v1/supplements/analyze`에 `supplement_image_upload` bucket fixed-window limiter를 적용했다.
- 기본값:
  - `RATE_LIMIT_ENABLED=true`
  - `RATE_LIMIT_EXTERNAL_ENFORCEMENT=false`
  - `RATE_LIMIT_WINDOW_SECONDS=60`
  - `SUPPLEMENT_IMAGE_UPLOAD_RATE_LIMIT=10`
- staging/production에서는 `RATE_LIMIT_ENABLED=false`로 부팅하지 못하도록 `Settings.validate_runtime_security()`에 guard를 추가했다.
- production에서는 process-local limiter만으로 부팅하지 못하도록 `RATE_LIMIT_EXTERNAL_ENFORCEMENT=true`를 요구한다. 이 값은 ingress/API gateway/Redis 계층의 분산 rate limit가 별도로 강제된다는 운영 attestation이다.
- subject key는 인증 전 미들웨어에서 검증되지 않은 `Authorization` header를 신뢰하지 않고 ASGI `client.host`를 SHA-256 digest로 감싸서 만든다.
- 429 응답은 OpenAPI 예시와 맞춰 `detail.code="too_many_requests"`를 반환하고 `Retry-After` header를 포함한다.
- `SecureHeadersMiddleware`가 429 응답에도 적용되는지 통합 테스트로 고정했다.
- 서로 다른 임의 `Authorization` header를 붙여도 같은 client host에서는 limit을 우회하지 못하도록 회귀 테스트를 추가했다.

한계:

- 현재 앱 내부 구현은 process-local limiter다. 단일 local/dev worker와 첫 비용폭주 차단에는 충분하지만, 다중 worker/다중 instance production에서는 Redis 또는 API gateway/ingress rate limit가 반드시 외부에서 강제되어야 한다.
- `X-Forwarded-For`류 proxy header는 신뢰하지 않는다. proxy chain 검증이 없는 상태에서 해당 header를 신뢰하면 spoofing 위험이 커진다.
- 같은 NAT/proxy 뒤 사용자가 많은 production 환경에서는 client host 단위 제한이 거칠 수 있다. 인증 완료 후 principal 기반 limiter로 옮기거나 trusted gateway/Redis limiter를 붙이는 것이 다음 단계다.

### 7. Mobile Release Security Verification

검사 파일:

- `mobile/lib/core/config/app_config.dart`
- `mobile/lib/core/api/api_client.dart`
- `mobile/lib/core/api/certificate_pin_verifier.dart`
- `mobile/android/app/src/main/kotlin/com/lemonaid/mobile/MainActivity.kt`
- `mobile/ios/Runner/AppDelegate.swift`
- `mobile/test/unit/app_config_test.dart`
- `mobile/test/unit/api_client_certificate_pin_test.dart`
- `mobile/test/unit/release_security_config_test.dart`

Official references:

- Android HostnameVerifier docs: https://developer.android.com/reference/javax/net/ssl/HostnameVerifier
- Apple SecPolicyCreateSSL docs: https://developer.apple.com/documentation/security/secpolicycreatessl%28_%3A_%3A%29
- Apple SecTrustEvaluateWithError docs: https://developer.apple.com/documentation/security/sectrustevaluatewitherror%28_%3A_%3A%29

확인:

- release build에서 `LEMON_API_TOKEN` embedded token을 거부한다.
- release build에서 `LEMON_API_BASE_URL`은 HTTPS와 `/api/v1` suffix가 필수다.
- release build에서 `LEMON_CERTIFICATE_PINS`가 비어 있거나 `sha256/<base64>` 형식이 아니면 거부한다.
- `ApiClient`는 GET/POST/multipart 요청 전 certificate pin verifier를 먼저 호출한다.
- certificate pin mismatch 시 HTTP request가 전송되지 않는 테스트가 있다.
- Android native pin preflight는 `SSLSocket` handshake 후 `HttpsURLConnection.getDefaultHostnameVerifier()`로 hostname mismatch도 거부한다.
- iOS native pin preflight는 `SecPolicyCreateSSL(true, host)`와 `SecTrustSetPolicies`로 요청 host를 trust evaluation policy에 명시한 뒤 pin을 비교한다.
- Android network security config는 cleartext traffic을 false로 둔다.
- iOS ATS는 arbitrary loads를 false로 둔다.

추가 보안 보정:

- Android native certificate pin preflight가 raw `SSLSocket` handshake와 pin 비교만 수행하던 부분을 점검했다.
- Android 공식 `HostnameVerifier` 문서 기준으로 hostname/session match 검증을 명시해야 하므로, pin 비교 전에 `HttpsURLConnection.getDefaultHostnameVerifier().verify(host, session)`를 추가했다.
- hostname mismatch는 `certificate_hostname_mismatch` bounded error code로 실패하며, host/token/certificate raw data는 Flutter error details에 싣지 않는다.
- iOS도 `SecTrustEvaluateWithError` 전에 SSL hostname policy를 명시하도록 보강했다.
- iOS trust/hostname failure는 `certificate_trust_evaluation_failed` bounded error code로 실패하며, raw host/certificate/trust error details는 Flutter로 전달하지 않는다.

검증:

```bash
cd mobile
flutter test \
  test/unit/app_config_test.dart \
  test/unit/api_client_certificate_pin_test.dart \
  test/unit/release_security_config_test.dart \
  test/unit/supplement_models_test.dart
# 23 passed
```

```bash
cd mobile
dart format --set-exit-if-changed \
  lib/core/config/app_config.dart \
  lib/core/api/api_client.dart \
  lib/core/api/certificate_pin_verifier.dart \
  test/unit/app_config_test.dart \
  test/unit/api_client_certificate_pin_test.dart \
  test/unit/release_security_config_test.dart \
  test/unit/supplement_models_test.dart
# 7 files, 0 changed
```

```bash
cd mobile
flutter build apk --debug --flavor dev
# Built build/app/outputs/flutter-apk/app-dev-debug.apk
```

```bash
cd mobile
flutter build ios --debug --simulator
# Built build/ios/iphonesimulator/Runner.app
```

Note:

- `flutter build apk --debug` without a flavor produced flavor APKs but failed the wrapper lookup because no default `app-debug.apk` exists in this flavor-based project.
- Flavor-specific debug build is the reliable compile check for the native Android changes.

### 8. External-Volume Ollama/Gemma4 Verification

사용자 지정 모델 경로:

```text
$OLLAMA_MODELS_DIR/manifests/registry.ollama.ai/library
```

확인:

- `gemma4/e4b`, `gemma4/latest`, `gemma4/26b`, `gemma4/e2b` manifest가 존재한다.
- `$OLLAMA_MODELS_DIR` 전체 크기는 약 `140G`다.
- 아래 서버 실행 후 `/api/tags`에서 `gemma4:e4b`가 확인됐다.

```bash
OLLAMA_MODELS="$OLLAMA_MODELS_DIR" \
OLLAMA_HOST=127.0.0.1:11435 \
ollama serve
```

runtime readiness:

```text
parser_ready=True parser_model=gemma4:e4b parser_error=None
vision_ready=True vision_model=gemma4:e4b vision_error=None
model_count=17 external_llm=False base_url=http://127.0.0.1:11435
```

Gemma4 structured parser smoke:

```text
parse_ok=true ingredient_count=2 product_name_present=True model=gemma4:e4b external_llm=False
```

주의:

- sandbox 내부 Python/httpx는 local loopback connect에서 `Operation not permitted`가 발생했다.
- 동일 명령은 sandbox 밖 실행에서 정상 통과했다. 이 문제는 code defect가 아니라 현재 Codex sandbox network 정책 차이로 판단한다.
- `ollama list` 단독 실행은 빈 목록을 반환했지만, 외장 모델 경로로 띄운 `127.0.0.1:11435` 서버의 `/api/tags`는 모델을 정상 반환했다.

### 9. YOLO/ROI Local Gate Verification

확인:

- `ENABLE_VISION_CLASSIFIER=false`가 기본값이다.
- `OCR_ROI_PREPROCESSING_POLICY=disabled`가 기본값이다.
- YOLO adapter는 `enable_vision_classifier=True`일 때만 factory에서 생성된다.
- production에서는 `ENABLE_VISION_CLASSIFIER=true`와 ROI crop policy가 docs gate sign-off 없이 켜지지 않도록 config validation이 걸려 있다.
- Ollama vision assist도 `ENABLE_MULTIMODAL_LLM=true`와 `MULTIMODAL_OCR_ASSIST_POLICY`가 맞아야만 factory에 주입된다.

검증:

```bash
PYTHONPATH=backend/Nutrition-backend:backend \
/private/tmp/lemon-p1-quality-venv/bin/python -m pytest \
  backend/Nutrition-backend/tests/unit/vision/test_preprocessing.py \
  backend/Nutrition-backend/tests/unit/vision/test_yolo_detector.py \
  backend/Nutrition-backend/tests/unit/services/test_supplement_image_analysis.py \
  backend/Nutrition-backend/tests/unit/services/test_supplement_image_quality.py \
  backend/Nutrition-backend/tests/unit/ocr/test_ocr_factory.py \
  backend/Nutrition-backend/tests/unit/test_config.py \
  -q --no-cov
# 104 passed in 1.29s
```

### 10. Current PaddleOCR + Gemma4 Runner Evidence

기존 30장 detail smoke 산출물:

- `outputs/generated/ocr-eval/2026-05-22-naver-tampermonkey/runner-paddle-detail-smoke-30-gemma4/`

핵심 지표:

| Provider | Calls | Completed | Text non-empty | LLM success | p50 latency ms | p95 latency ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `paddleocr_local` | 30 | 0.8667 | 0.8667 | 1.0 | 2352.0 | 5142.0 |

raw storage flags:

- `raw_artifacts_stored=false`
- `raw_ocr_text_stored=false`
- `raw_provider_payload_stored=false`
- `raw_model_response_stored=false`

현재 서버로 새로 실행한 1장 smoke:

- `outputs/generated/ocr-eval/2026-05-22-naver-tampermonkey/runner-paddle-detail-smoke-1-gemma4-live/`
- 결과: PaddleOCR 단계 `ocr_error`, 따라서 LLM parse까지 진행되지 않음
- forbidden raw key grep: no matches
- raw storage flags는 모두 false

해석:

- Gemma4 local parser 자체는 정상 동작한다.
- 이미지 OCR 쪽은 fixture별 PaddleOCR 실패가 여전히 존재하므로, LLM parse 품질 이전에 provider/layout/OCR failure 분리를 계속 유지해야 한다.

## Security Review

검사 범위:

- `backend/Nutrition-backend/src/ocr/field_extractor.py`
- `backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py`
- `backend/scripts/evaluate_ocr_three_tier.py`
- `backend/scripts/smoke_supplement_analyze_api.py`
- `backend/Nutrition-backend/src/api/v1/supplements.py`
- `backend/Nutrition-backend/src/services/supplement_image_analysis.py`
- `backend/Nutrition-backend/src/models/schemas/supplement.py`
- supplement analyze integration tests
- 관련 script unit tests
- CLOVA generated observation/evaluation artifacts

검사 결과:

- `field_extractor` 변경에는 network call, file write, subprocess, auth header, secret handling, raw OCR artifact write가 없다.
- smoke helper의 `Authorization` 헤더 구성은 token 값을 출력하지 않고, summary에는 `token_configured` boolean만 사용한다.
- evaluator/smoke helper의 raw key 문자열은 금지 키 차단용 allow/deny logic 및 테스트 fixture로만 등장한다.
- CLOVA generated files 3개를 재귀 검사했고 forbidden raw key는 발견되지 않았다.
- `SupplementOCRProviderObservation` schema는 `extra="forbid"`와 `Literal[False]` raw flags로 raw provider data 저장을 막는다.
- analyze route audit metadata는 OCR provider/confidence-present/warning code/size/hash flags만 남기고 raw OCR text는 남기지 않는다.
- rate-limit middleware는 Authorization header를 subject key로 사용하지 않으며, client host, secret, raw payload를 log/response/file에 남기지 않는다.
- rate-limit 429 response에도 secure header baseline이 붙는 것을 테스트했다.
- 임의 bearer token 값을 바꿔 요청하는 우회 시나리오를 통합 테스트로 추가했고, 두 번째 요청이 429로 막히는 것을 확인했다.
- mobile release config는 embedded token, non-HTTPS, missing certificate pin을 fail-closed로 거부한다.
- Android certificate pin preflight now rejects hostname mismatch before pin comparison.
- 외장 Ollama 경로는 loopback `127.0.0.1:11435`에서만 확인했고 `ALLOW_EXTERNAL_LLM=false`를 유지했다.
- YOLO/ROI와 Ollama vision assist는 기본 off이며, production sign-off guard와 단위 테스트가 있다.
- Untracked secret-like filename scan returned no matches.
- Focused secret pattern scan found only documented placeholders/test fixtures:
  - placeholder certificate pins with `A...`/`B...`
  - `LEMON_API_TOKEN` placeholder
  - test-only `GOOGLE_CLOUD_API_KEY` placeholder

금지 키 검사 범주:

```text
image_bytes, raw_image, ocr_text, raw_ocr_text,
provider_payload, raw_provider_payload, authorization,
api_key, service_key, request_headers, secret,
clova_ocr_secret, x_ocr_secret
```

## Validation

```bash
PYTHONPATH=backend/Nutrition-backend:backend \
/private/tmp/lemon-p1-quality-venv/bin/python -m pytest \
  backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py \
  backend/Nutrition-backend/tests/unit/ocr/test_ocr_factory.py \
  backend/Nutrition-backend/tests/unit/ocr/test_paddle_provider.py \
  backend/Nutrition-backend/tests/unit/test_config.py \
  backend/Nutrition-backend/tests/unit/scripts/test_collect_supplement_ocr_observations.py \
  backend/Nutrition-backend/tests/unit/scripts/test_evaluate_ocr_three_tier.py \
  backend/Nutrition-backend/tests/unit/scripts/test_smoke_supplement_analyze_api.py \
  -q --no-cov
# 134 passed in 0.82s
```

```bash
PYTHONPATH=backend/Nutrition-backend:backend \
/private/tmp/lemon-p1-quality-venv/bin/python -m pytest \
  backend/Nutrition-backend/tests/integration/api/test_supplement_analyze_paddleocr_default.py \
  backend/Nutrition-backend/tests/integration/api/test_supplement_analyze_google_vision.py \
  backend/Nutrition-backend/tests/integration/api/test_supplement_intake_api.py \
  -q --no-cov
# 9 passed
```

Latest combined run:

```bash
PYTHONPATH=backend/Nutrition-backend:backend \
/private/tmp/lemon-p1-quality-venv/bin/python -m pytest \
  backend/Nutrition-backend/tests/unit/ocr/test_field_extractor.py \
  backend/Nutrition-backend/tests/unit/ocr/test_ocr_factory.py \
  backend/Nutrition-backend/tests/unit/ocr/test_paddle_provider.py \
  backend/Nutrition-backend/tests/unit/test_config.py \
  backend/Nutrition-backend/tests/unit/scripts/test_collect_supplement_ocr_observations.py \
  backend/Nutrition-backend/tests/unit/scripts/test_evaluate_ocr_three_tier.py \
  backend/Nutrition-backend/tests/unit/scripts/test_smoke_supplement_analyze_api.py \
  backend/Nutrition-backend/tests/unit/test_security_middleware.py \
  backend/Nutrition-backend/tests/integration/test_secure_headers.py \
  backend/Nutrition-backend/tests/integration/api/test_supplement_analyze_paddleocr_default.py \
  backend/Nutrition-backend/tests/integration/api/test_supplement_analyze_google_vision.py \
  backend/Nutrition-backend/tests/integration/api/test_supplement_intake_api.py \
  -q --no-cov
# 153 passed in 1.59s
```

Backend dev-env doctor:

```bash
PYTHONPATH=backend/Nutrition-backend:backend \
/private/tmp/lemon-p1-quality-venv/bin/python \
  backend/scripts/check_backend_dev_env.py --repo-root .
# backend_dev_env_ok checks=5
```

```bash
PYTHONPATH=backend/Nutrition-backend:backend \
/private/tmp/lemon-p1-quality-venv/bin/python -m pytest \
  backend/Nutrition-backend/tests/unit/scripts/test_check_backend_dev_env.py \
  -q --no-cov
# 4 passed
```

```bash
/private/tmp/lemon-p1-quality-venv/bin/python -m black --check \
  backend/Nutrition-backend/src/middleware/rate_limit.py \
  backend/Nutrition-backend/tests/integration/api/test_supplement_intake_api.py \
  backend/Nutrition-backend/src/config.py \
  backend/Nutrition-backend/src/main.py \
  backend/Nutrition-backend/tests/unit/test_config.py
# 5 files would be left unchanged
```

```bash
/private/tmp/lemon-p1-quality-venv/bin/python -m ruff check --ignore RUF001 \
  backend/Nutrition-backend/src/middleware/rate_limit.py \
  backend/Nutrition-backend/tests/integration/api/test_supplement_intake_api.py \
  backend/Nutrition-backend/src/config.py \
  backend/Nutrition-backend/src/main.py \
  backend/Nutrition-backend/tests/unit/test_config.py
# All checks passed
```

```bash
git diff --check
# pass
```

```bash
rg -n --hidden --glob '!outputs/generated/**' --glob '!**/.git/**' --glob '!mobile/uiux/**' \
  '(sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|CLOVA_OCR_SECRET\s*=\s*\S+|GOOGLE_CLOUD_API_KEY\s*=\s*\S+|LEMON_API_TOKEN\s*=\s*\S+|LEMON_CERTIFICATE_PINS\s*=\s*sha256/[A-Za-z0-9+/]{43}=)' \
  backend mobile outputs/todo-list/2026-05-22 config
# matches were placeholders/test fixtures only, no live secret value found
```

Additional validation:

```bash
PYTHONPATH=backend/Nutrition-backend:backend \
/private/tmp/lemon-p1-quality-venv/bin/python -m pytest \
  backend/Nutrition-backend/tests/integration/api/test_supplement_intake_api.py \
  backend/Nutrition-backend/tests/unit/test_config.py \
  backend/Nutrition-backend/tests/unit/test_security_middleware.py \
  backend/Nutrition-backend/tests/integration/test_secure_headers.py \
  -q --no-cov
# 71 passed in 1.42s
```

```bash
PYTHONPATH=backend/Nutrition-backend:backend \
/private/tmp/lemon-p1-quality-venv/bin/python -m pytest \
  backend/Nutrition-backend/tests/unit/llm/test_ollama_parser.py \
  backend/Nutrition-backend/tests/unit/llm/test_ollama_vision_assist.py \
  backend/Nutrition-backend/tests/unit/ocr/test_ocr_factory.py \
  -q --no-cov
# 42 passed in 1.15s
```

```bash
flutter test \
  test/unit/app_config_test.dart \
  test/unit/api_client_certificate_pin_test.dart \
  test/unit/release_security_config_test.dart \
  test/unit/supplement_models_test.dart
# 23 passed
```

```bash
flutter build apk --debug --flavor dev
# pass

flutter build ios --debug --simulator
# pass
```

## Latest Commit Split

추가로 dirty backend/mobile/script 변경분을 다음 slice로 나눠 커밋했다.

| Commit | Scope | 핵심 |
| --- | --- | --- |
| `fb9a3afd feat(ocr): 라벨 레이아웃 DTO를 추가` | backend OCR layout | `OCRResult.pages` DTO, label layout schema, layout parser regression fixture |
| `b2603aa7 feat(ocr): 이미지 품질 관측치를 추가` | backend preview quality | OCR 전 image quality report, sanitized provider observations, API raw-field regression tests |
| `bc2b4062 fix(ocr): 어댑터 입력 계약을 보정` | OCR adapters | CLOVA primary validation 보정, multilingual adapter `OCRImageInput` 계약 정리, generic exception message redaction |
| `2dfe412e feat(mobile): 릴리스 보안 게이트를 추가` | mobile release/security | certificate pin preflight, release config pin format validation, native camera permission channel, local capture quality warning |
| `20cb69e5 feat(data): Naver OCR 평가 스크립트 추가` | operator data/eval | Naver Tampermonkey manifest, provider runner, comparison evaluator, external-transfer guard |
| `815190fa test(ocr): 레이아웃 snapshot fixture 추가` | test fixture | synthetic V2 layout snapshot fixture |

추가 검증:

```bash
PYTHONPATH=backend/Nutrition-backend:backend \
/private/tmp/lemon-p1-quality-venv/bin/python -m pytest \
  backend/Nutrition-backend/tests/unit/parsing/test_layout_parser.py \
  backend/Nutrition-backend/tests/unit/services/test_supplement_image_quality.py \
  backend/Nutrition-backend/tests/unit/services/test_supplement_image_analysis.py \
  backend/Nutrition-backend/tests/unit/services/test_supplement_intake.py \
  backend/Nutrition-backend/tests/integration/api/test_supplement_analyze_paddleocr_default.py \
  backend/Nutrition-backend/tests/integration/api/test_supplement_analyze_google_vision.py \
  backend/Nutrition-backend/tests/unit/ocr/test_clova_provider.py \
  backend/Nutrition-backend/tests/unit/ocr/test_multilingual_adapter.py \
  backend/Nutrition-backend/tests/unit/scripts/test_build_naver_tampermonkey_ocr_manifest.py \
  backend/Nutrition-backend/tests/unit/scripts/test_evaluate_naver_tampermonkey_ocr.py \
  backend/Nutrition-backend/tests/unit/scripts/test_run_naver_tampermonkey_ocr_eval.py \
  backend/Nutrition-backend/tests/unit/models/test_supplement_snapshot_schema.py \
  -q --no-cov
# pass in focused runs
```

```bash
flutter test \
  test/unit/app_config_test.dart \
  test/unit/api_client_certificate_pin_test.dart \
  test/unit/release_security_config_test.dart \
  test/unit/supplement_models_test.dart \
  test/supplement_flow_image_picker_test.dart
# 31 passed

flutter analyze
# No issues found

flutter build apk --debug --flavor dev
# pass

flutter build ios --simulator --debug
# pass
```

## Remaining Work

1. Decide PR contents:
   - field_extractor Phase 0-alpha is isolated in commit `3d044dce`.
   - backend quality/layout/provider routing and mobile release security are now separate commits, but the branch as a whole is larger than the team PR-size recommendation.
   - before opening PR, decide whether to keep this branch as an integration PR or cherry-pick commits into smaller branches.
2. Do not commit generated CLOVA artifacts unless the team explicitly wants evaluation artifacts in repo.
3. Run PaddleOCR baseline again and compare before/after field-level extractor behavior where applicable.
4. Start local Ollama with external model path before LLM parse:

```bash
OLLAMA_MODELS="$OLLAMA_MODELS_DIR" \
OLLAMA_HOST=127.0.0.1:11435 \
ollama serve
```

5. Re-run the 30-row PaddleOCR + Gemma4 runner if the team wants fresh post-rate-limit timestamps; existing 30-row result already has `llm_parse_success_rate=1.0` for OCR-success rows.
6. Continue security review on the next tranche:
   - decide whether process-local rate-limit is enough for current deployment or must move to Redis/API gateway before production
   - generated OCR evaluation artifacts are now ignored by default; decide separately whether historical tracked reports should remain in Git or move to a private artifact store
   - optionally rewrite the 15 medium-severity documentation placeholders into clearer non-credential examples
   - fix stale root monorepo workflow paths or export the standalone team-policy assets into the team-root repo
   - rebase against `team/develop` only after the working tree is clean and the target PR split is decided
