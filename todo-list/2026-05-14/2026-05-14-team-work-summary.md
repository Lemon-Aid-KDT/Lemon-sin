# Lemon Healthcare 팀 공유 보고서 - 2026-05-14 작업 내용 정리

## 한 줄 요약

오늘은 Phase 1 안정화 잔여 항목을 정리하면서 KDRIs 2025 정식 데이터 전환, JWT production 검증 경로, 만성질환자 부족 영양소 우선순위 룩업, non-P1 feature flag default-off 정책을 모두 완료 상태로 맞췄습니다. 이후 Google Vision OCR provider 상세 설계와 현재 브랜치 기준 핸드오프 문서를 추가했고, KDRIs CSV 줄끝/checksum 정합성까지 보정했습니다.

## 기준 정보

- 작업 기준일: 2026-05-14
- 로컬 경로: `/Users/yeong/99_me/00_github/03_lemon_healthcare`
- 프로젝트 루트: `yeong-Vision-Nutrition`
- 현재 브랜치: `codex/p1-5-stabilization`
- 현재 상태: 로컬 작업 트리에 변경 사항이 남아 있으며, 아직 커밋/푸시는 진행하지 않았습니다.

## 오늘 작업 목적

- KDRIs 2025 정식 데이터셋을 production에서 사용할 수 있는 상태로 전환합니다.
- JWT 인증 production 경로에서 JWKS rotation, missing `kid`, invalid alg, timeout, token-use/id-token confusion을 테스트로 고정합니다.
- 만성질환자에게 부족 또는 낮음으로 판정된 영양소만 “우선 확인 대상”으로 정렬할 수 있게 합니다.
- Phase 1 안정화의 마지막 미해결 항목인 feature flag default-off 정책을 완료합니다.
- docs/22, docs/23 상태 지도를 실제 검증 결과와 일치시킵니다.
- Google Cloud Project/Billing/Vision API 활성화 이후의 Google Vision OCR provider 구현 방향을 문서화합니다.
- 커밋 전 주의사항이었던 CSV 줄끝, manifest checksum, handoff 브랜치 불일치를 현재 프로젝트 기준으로 정리합니다.

## 구현 범위 요약

### 1. KDRIs 2025 정식 데이터 전환

- `data/kdris/kdris_2025.csv`에 1,795개 approved row가 반영되었습니다.
- `data/kdris/kdris_source_manifest.json`에 `official_2025_approved`, `promoted_to_production`, checksum, source artifact 상태가 기록되었습니다.
- KDRIs schema는 trimester, folic-acid UL, niacin dual UL, water total/liquid처럼 손실 가능성이 있던 표현을 담을 수 있도록 확장되었습니다.
- raw/source/review artifact가 `data/raw/kdris/2025/`, `data/kdris/review/2025/` 아래에 정리되었습니다.
- production 설정은 `KDRIS_DATA_VERSION=2025`, `KDRIS_DATA_PATH=data/kdris/kdris_2025.csv`, `ALLOW_SAMPLE_KDRIS=false` 기준으로 정렬되었습니다.

### 2. JWT production 인증 경로 강화

- `backend/src/security/auth.py`에서 JWT header의 `kid`, `alg`, token type을 먼저 검증하도록 보강했습니다.
- missing `kid` 또는 허용되지 않은 `alg`는 JWKS fetch 전에 거부됩니다.
- JWKS key rotation, unknown `kid`, JWKS timeout, invalid alg, id-token confusion, provider token-use mismatch를 integration/unit test로 고정했습니다.
- `backend/src/security/oidc.py`와 `backend/scripts/check_oidc_discovery.py`로 OIDC discovery preflight 경로를 분리했습니다.
- OpenAPI `BearerAuth` security contract가 P1 API contract test에 포함되었습니다.

### 3. 만성질환자 부족 영양소 우선순위 룩업

- `backend/src/nutrition/chronic_priority.py`를 추가해 chronic disease code alias를 canonical condition code로 정규화합니다.
- `data/reference/chronic_nutrient_priorities.json`에 source-backed priority/caution rule을 분리했습니다.
- `deficiency_analysis.py`는 이미 `DEFICIENT` 또는 `LOW`인 영양소에만 priority boost를 적용합니다.
- CKD처럼 caution-only인 영양소는 boost하지 않도록 했습니다.
- 사용자 노출 문구는 “우선 확인 대상”으로 제한했고, 진단/치료/처방/복용량 변경 표현을 금지했습니다.

### 4. Feature flag default-off 완료

- `feature_prescription_ocr_intake`, `feature_lab_result_ocr_intake`, `feature_medication_safety_alert` 기본값을 `false`로 전환했습니다.
- production에서 위 regulated flag가 `true`이면 sign-off 없이 boot되지 않도록 validator를 추가했습니다.
- `FEATURE_PRESCRIPTION_OCR_INTAKE`, `FEATURE_LAB_RESULT_OCR_INTAKE`, `FEATURE_HOSPITAL_MOCK_FHIR`, `FEATURE_MEDICATION_SAFETY_ALERT`의 readiness JSON 기본값을 `false`로 맞췄습니다.
- `.env.example`, docs/dev-guide, docs/22, docs/23의 feature flag 설명을 같은 기준으로 정리했습니다.

### 5. P1 상태 문서 갱신

- `docs/22-current-implementation-status-map.md` 상단에 Weekly Snapshot을 추가했습니다.
- KDRIs/JWT/chronic priority/feature flag default-off 상태를 모두 `done`으로 표시했습니다.
- `docs/23-p1-stabilization-plan.md`의 P1-S2 Feature Flag Default-Off Correction을 완료 상태로 갱신했습니다.
- 최신 검증 결과를 문서에 반영했습니다.

### 6. Google Vision OCR provider 상세 설계 추가

- `docs/35-google-vision-ocr-provider-implementation-plan.md`를 추가했습니다.
- 현재 프로젝트는 OCR 성능 우선 방침이므로 1차 provider를 Google Cloud Vision `DOCUMENT_TEXT_DETECTION`으로 설계했습니다.
- 기본값은 `OCR_PRIMARY_PROVIDER=none`, `ALLOW_EXTERNAL_OCR=false`로 두고, 명시 opt-in일 때만 Google Vision을 호출하는 fail-closed 구조를 제안했습니다.
- 외부 OCR 전송이므로 기존 `OCR_IMAGE_PROCESSING`과 별도로 `EXTERNAL_OCR_PROCESSING` consent를 두는 방향을 정리했습니다.
- `/api/v1/supplements/analyze`에서 OCR adapter factory를 통해 Google Vision OCR 결과를 기존 `parse_supplement_analysis_ocr_text`로 이어 OCR+parse preview를 한 번에 생성하는 구현 계획을 작성했습니다.
- 실제 Google 호출은 CI 기본 job에서 제외하고, fake client unit/integration test와 opt-in manual smoke test로 분리하는 테스트 전략을 정리했습니다.

### 7. 커밋 전 주의사항 보정

- `data/kdris/kdris_2025.csv`의 CRLF 줄끝을 LF로 정규화해 `git diff --check` 실패 원인을 제거했습니다.
- 줄끝 정규화로 바뀐 `kdris_2025.csv` SHA-256 checksum을 `data/kdris/kdris_source_manifest.json`에 반영했습니다.
- 새 checksum은 `132ea658b6c3a1c25c643d257a0af7c460eecce7e7eac984d19adab3c62a5091`입니다.
- `yeong-Vision-Nutrition/HANDOFF.md`를 현재 브랜치 `codex/p1-5-stabilization`과 `team/yeong-tech` 리뷰 기준으로 다시 작성했습니다.
- `HANDOFF.md`에서 `main` 직접 커밋/푸시/merge 제외 원칙과 커밋 포함/제외 후보를 명시했습니다.

## 검증 결과

로컬 backend 기준으로 아래 검증을 통과했습니다.

| 검증 | 명령 | 결과 |
| --- | --- | --- |
| Formatting | `.venv/bin/black --check src tests alembic` | pass, 160 files unchanged |
| Lint | `.venv/bin/ruff check src tests alembic` | pass |
| Type check | `.venv/bin/mypy src tests --strict` | pass, 155 source files |
| Unit config test | `.venv/bin/python -m pytest -o addopts='' tests/unit/test_config.py` | pass, 26 passed |
| Full pytest coverage | `.venv/bin/python -m pytest --cov-report=term-missing` | pass, `310 passed, 1 skipped`, total coverage `87.67%` |
| KDRIs validator | `.venv/bin/python scripts/validate_kdris_dataset.py --require-approved` | pass, 1,795 rows validated |
| Settings JSON parse | `.venv/bin/python -m json.tool ../config/implementation-readiness.settings.json` | pass |
| Diff whitespace | `git diff --check` | pass after KDRIs CSV LF normalization |
| KDRIs manifest/dataset targeted tests | `.venv/bin/python -m pytest -o addopts='' -q tests/unit/nutrition/test_kdris_source_manifest.py tests/unit/nutrition/test_kdris_2025_dataset.py` | pass, `13 passed` |

참고: 특정 test file만 coverage addopts를 유지한 채 실행하면 전체 coverage 80% gate 때문에 실패할 수 있습니다. 개별 테스트 정합성 확인은 `-o addopts=''`로 실행했고, 전체 coverage gate는 full pytest 실행 결과를 기준으로 봅니다.

## 주요 변경 파일 묶음

### 설정과 정책

- `backend/src/config.py`
- `backend/.env.example`
- `config/implementation-readiness.settings.json`
- `docs/dev-guides/00-setup-environment.md`

### KDRIs 2025 데이터

- `data/kdris/kdris_2025.csv`
- `data/kdris/kdris_dataset_schema.md`
- `data/kdris/kdris_source_manifest.json`
- `data/kdris/review/2025/*`
- `data/raw/kdris/2025/*`
- `backend/scripts/validate_kdris_dataset.py`
- `backend/scripts/prepare_kdris_2025_digitization.py`
- `backend/scripts/digitize_kdris_2025_summary.py`
- `backend/scripts/validate_kdris_candidate_rows.py`

### JWT/OIDC 보안

- `backend/src/security/auth.py`
- `backend/src/security/oidc.py`
- `backend/scripts/check_oidc_discovery.py`
- `backend/tests/integration/security/test_jwt_production_path.py`
- `backend/tests/unit/security/test_auth.py`
- `backend/tests/unit/security/test_oidc.py`
- `backend/tests/integration/api/test_p1_api_contract.py`

### 만성질환 우선순위

- `backend/src/nutrition/chronic_priority.py`
- `data/reference/chronic_nutrient_priorities.json`
- `backend/src/nutrition/deficiency_analysis.py`
- `backend/src/models/schemas/nutrition.py`
- `backend/tests/unit/nutrition/test_chronic_priority.py`
- `backend/tests/unit/nutrition/test_kdris_analysis.py`

### 상태 문서

- `docs/22-current-implementation-status-map.md`
- `docs/23-p1-stabilization-plan.md`
- `docs/31-backend-feature-specifications.md`
- `docs/32-paddleocr-local-fallback-plan.md`
- `docs/33-three-tier-ocr-pipeline-implementation-guide.md`
- `docs/34-llm-serving-engines-multi-environment-setup-guide.md`
- `docs/35-google-vision-ocr-provider-implementation-plan.md`
- `HANDOFF.md`
- `output/todo-list/2026-05-14/2026-05-14-team-work-summary.md`

## 현재 작업 트리 주의사항

현재 작업 트리에는 프로젝트 관련 untracked 파일과 무관한 로컬 산출물이 함께 있습니다. 커밋 전 선별이 필요합니다.

프로젝트 포함 후보:

- `backend/scripts/check_oidc_discovery.py`
- KDRIs digitization/validation scripts
- `backend/src/nutrition/chronic_priority.py`
- `backend/tests/integration/security/test_jwt_production_path.py`
- `backend/tests/unit/nutrition/test_chronic_priority.py`
- `backend/tests/unit/scripts/*`
- `data/kdris/review/2025/*`
- `data/raw/kdris/2025/*`
- `data/reference/chronic_nutrient_priorities.json`
- `docs/31`부터 `docs/35`
- `yeong-Vision-Nutrition/HANDOFF.md`
- 이 팀 공유 보고서 파일 자체: `output/todo-list/2026-05-14/2026-05-14-team-work-summary.md`

커밋 제외 후보:

- `Brand_Character/`
- `output/` 전체. 단, 이번 팀 공유 보고서 파일은 사용자 요청으로 갱신했으므로 포함 여부를 별도 결정합니다.
- `outputs/`
- `회의록/`
- `../00_plusultra/`

## 다음 구현 필요 항목

### 1. CI hardening

현재 backend CI는 backend path 중심으로 동작합니다. KDRIs data, config, docs 상태 변경이 backend 품질에 영향을 주므로 다음 보강이 필요합니다.

- backend CI trigger에 `data/kdris/**`, `data/reference/**`, `config/**` 관련 경로 추가
- CI에 `validate_kdris_dataset.py --require-approved` 추가
- CI settings smoke에 regulated flag default-off assert 추가
- docs-only 변경과 backend/data 변경 path filter 분리 재확인

### 2. Stabilization PR gate

P1 이후 AI/OCR/YOLO/학습 기능이 기준선을 침범하지 않도록 PR checklist를 더 구체화해야 합니다.

- KDRIs validator 통과 체크
- JWT/OIDC production-path test 통과 체크
- chronic priority 금지 표현 test 통과 체크
- feature flag true 변경 시 sign-off 문서 요구
- raw image/raw OCR text 저장 금지 확인

### 3. 커밋 단위 정리

현재 변경량이 커서 커밋 단위를 나누는 것이 안전합니다.

권장 커밋:

1. `fix(config): default non-P1 regulated flags to disabled`
   - 이유: 미검증 regulated 기능이 기본 활성화되지 않도록 production guard와 문서를 맞추기 위함.
2. `data(kdris): import reviewed 2025 KDRIs reference rows`
   - 이유: production이 sample fixture 대신 approved 2025 기준값을 사용하도록 하기 위함.
3. `fix(security): harden JWT JWKS verification path`
   - 이유: key rotation, missing kid, invalid alg, token confusion을 production 경로에서 안전하게 처리하기 위함.
4. `feat(nutrition): apply chronic-condition nutrient priority lookup`
   - 이유: 만성질환 context가 있을 때 이미 부족/낮음인 영양소를 근거 기반으로 우선 확인하도록 하기 위함.
5. `docs(status): refresh P1 stabilization map`
   - 이유: 팀이 현재 구현 상태와 남은 구현 범위를 같은 문서 기준으로 보도록 하기 위함.
6. `ci(backend): add data and settings stabilization gates`
   - 이유: 로컬에서 통과한 P1 gate가 GitHub Actions에서도 동일하게 재현되도록 하기 위함.

### 4. Google Vision OCR provider 구현 착수

docs/35 기준 다음 단계입니다.

- OCR 호출 전용 service account 또는 attached service account 방식 결정
- credential JSON을 repo에 두지 않는 local dev 운영 규칙 확정
- `OCR_PRIMARY_PROVIDER`, `ALLOW_EXTERNAL_OCR`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_VISION_*` settings 추가
- `EXTERNAL_OCR_PROCESSING` consent type과 active policy 추가
- `GoogleVisionOCRAdapter`와 `build_supplement_ocr_adapter(settings)` factory 구현
- `/api/v1/supplements/analyze`에서 adapter를 주입해 OCR+parse preview가 한 번에 동작하도록 연결
- fake client 기반 unit/integration test 작성
- 실제 Google smoke test는 `RUN_GOOGLE_VISION_SMOKE=1` 같은 opt-in gate 뒤에서만 실행

### 5. OCR 3-tier 확장 구현

Google Vision MVP 이후 docs/33 기준 다음 단계입니다.

- YOLO ROI 실제 추론 연결
- Ollama multimodal fallback/verification 연결
- PaddleOCR 로컬 fallback 또는 CLOVA fallback 우선순위 재검토
- 라벨 fixture 30~100장 기준 정확도/latency 리포트 작성
- 발주처 리뷰 게이트 #1, #2 산출물 준비

### 6. Learning/vector DB 구현

현재는 gate와 disabled adapter 골격만 있습니다. 실제 구현 전에는 아래 작업이 필요합니다.

- pgvector extension migration
- image embedding table
- 실제 embedding model runner
- vector upsert worker
- image object storage 연동

### 7. Prescription/lab OCR intake 구현

regulated flag는 default-off로 정리됐으므로, 다음 구현은 intake-only 흐름으로 진행해야 합니다.

- 처방전 OCR intake endpoint
- 검사표 OCR intake endpoint
- 별도 민감 동의
- 원문 이미지 자동삭제 정책
- 사용자 확인 단계
- 전문의 상담 CTA
- 직접 복용량 변경 안내 금지 테스트

## 팀원이 알아야 할 결정 사항

- KDRIs 2025는 production dataset으로 승격되었고 sample fixture는 production에서 금지됩니다.
- JWT는 HS secret 기반 개발 경로가 아니라 OAuth/OIDC Bearer access token 검증 경로를 production 기준으로 삼습니다.
- 만성질환자 우선순위는 치료/복용량 안내가 아니라 “우선 확인 대상” 정렬 보조입니다.
- regulated feature flag는 모두 default-off이며, production에서 true로 켜려면 별도 sign-off가 필요합니다.
- Google Vision OCR은 성능 우선 provider로 채택하되, 외부 OCR 전송 동의와 `ALLOW_EXTERNAL_OCR=true` gate 없이는 호출하지 않습니다.
- `main` 직접 커밋/푸시는 제외하고 `team/yeong-tech` 기준으로 팀원 리뷰 후 반영합니다.
- YOLO는 제품명/성분 추출 모델이 아니라 ROI helper입니다.
- OCR/LLM 결과는 사용자 확인 전까지 확정 데이터가 아닙니다.

## 공식 문서 참고

- PyJWT API Reference: https://pyjwt.readthedocs.io/en/stable/api.html
- OpenID Connect Discovery 1.0: https://openid.net/specs/openid-connect-discovery-1_0.html
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Pydantic validators: https://docs.pydantic.dev/latest/concepts/validators/
- pytest invocation: https://docs.pytest.org/en/stable/how-to/usage.html
- mypy command line: https://mypy.readthedocs.io/en/stable/command_line.html
- Ruff linter: https://docs.astral.sh/ruff/linter/
- Black `--check`: https://black.readthedocs.io/en/stable/usage_and_configuration/the_basics.html#check
- FastAPI `openapi_extra`: https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/#openapi-extra
- OpenAPI security schemes: https://learn.openapis.org/specification/security.html
- Cloud Vision OCR: https://cloud.google.com/vision/docs/ocr
- Cloud Vision REST `images:annotate`: https://cloud.google.com/vision/docs/reference/rest/v1/images/annotate
- Cloud Vision Data Usage FAQ: https://cloud.google.com/vision/docs/data-usage
- Google Application Default Credentials: https://cloud.google.com/docs/authentication/application-default-credentials
