# HANDOFF - P1 Stabilization and Google Vision OCR Planning

작성일: 2026-05-14
로컬 경로: `/Users/yeong/99_me/00_github/03_lemon_healthcare/yeong-Lemon-Aid`
작업 브랜치: `codex/p1-5-stabilization`
반영 기준: `team/yeong-tech` 리뷰 후 반영, `main` 직접 커밋/푸시/merge 제외

## 1. 현재 상태 요약

현재 작업 트리는 커밋 전 로컬 변경 상태다. 이번 변경의 중심은 다음 네 가지다.

1. KDRIs 2025 운영 데이터 전환
2. JWT/OIDC production 인증 경로 강화
3. 만성질환자 부족 영양소 우선순위 룩업 추가
4. OCR/LLM 후속 구현 문서 정리, 특히 Google Vision OCR provider 도입 설계

커밋 전에는 코드/설정 변경과 산출물 변경을 반드시 분리해야 한다. `assets/mascot/`, `records/meetings/`, `outputs/reports/`, `outputs/generated/`, `outputs/todo-list/`, `../00_plusultra/`는 제품 산출물 또는 외부 자료 성격이므로 기능 커밋과 섞지 않는다.

## 2. 주요 변경 묶음

### 2.1 KDRIs 2025 데이터

- `data/nutrition_reference/kdris/kdris_2025.csv`
  - 2025 KDRIs approved row 1,795개 반영.
  - 줄끝은 LF로 정규화했다.
- `data/nutrition_reference/kdris/kdris_source_manifest.json`
  - `local_dataset_status=official_2025_approved`
  - `candidate_dataset_status=promoted_to_production`
  - `kdris_2025.csv` checksum 갱신.
- `data/nutrition_reference/kdris/kdris_dataset_schema.md`
  - `condition_detail`, `source_variant`, dual UL fields 문서화.
- `data/nutrition_reference/kdris/review/2025/*`
  - source artifact, candidate rows/issues, schema decisions, source text 보관.
- `data/nutrition_reference/kdris/raw/2025/*`
  - KNS 2025 KDRI source PDFs/errata 보관.

### 2.2 KDRIs 관련 코드와 테스트

- `backend/src/nutrition/kdris.py`
  - 2025 row schema 확장 필드 parsing.
  - condition/source variant별 age overlap 병합 보정.
- `backend/scripts/validate_kdris_dataset.py`
  - 확장 schema와 dual UL 검증.
  - source manifest checksum 검증.
- 신규 scripts
  - `backend/scripts/prepare_kdris_2025_digitization.py`
  - `backend/scripts/digitize_kdris_2025_summary.py`
  - `backend/scripts/validate_kdris_candidate_rows.py`
- 관련 tests
  - `backend/tests/unit/nutrition/test_kdris_2025_dataset.py`
  - `backend/tests/unit/nutrition/test_kdris_source_manifest.py`
  - `backend/tests/unit/scripts/*`

### 2.3 JWT/OIDC production 인증 경로

- `backend/src/security/auth.py`
  - JWT JOSE header의 `alg`, `typ`, `kid`를 JWKS 조회 전에 검증.
  - missing `kid`와 disallowed `alg`는 JWKS fetch 없이 401.
  - JWKS provider connection failure는 503으로 분리.
- `backend/src/security/oidc.py`
  - OIDC discovery metadata fetch 로직을 테스트 가능한 client 주입 구조로 분리.
- `backend/scripts/check_oidc_discovery.py`
  - 운영 전 discovery preflight JSON 출력.
- 관련 tests
  - `backend/tests/unit/security/test_auth.py`
  - `backend/tests/unit/security/test_oidc.py`
  - `backend/tests/integration/security/test_jwt_production_path.py`
  - `backend/tests/integration/api/test_p1_api_contract.py`

### 2.4 만성질환자 부족 영양소 우선순위

- `backend/src/nutrition/chronic_priority.py`
  - chronic disease alias를 canonical condition code로 정규화.
  - source-backed priority boost 계산.
- `data/nutrition_reference/nutrient/chronic_nutrient_priorities.json`
  - hypertension, diabetes, cardiovascular priority rules.
  - CKD potassium/phosphorus/sodium은 caution-only로 보관하고 자동 boost하지 않음.
- `backend/src/nutrition/deficiency_analysis.py`
  - 이미 `DEFICIENT` 또는 `LOW`인 영양소에만 boost 적용.
  - 사용자 문구는 "우선 확인 대상" 수준으로 제한.
- 관련 tests
  - `backend/tests/unit/nutrition/test_chronic_priority.py`
  - `backend/tests/unit/nutrition/test_kdris_analysis.py`

### 2.5 Feature flag default-off

- `backend/src/config.py`
  - `feature_prescription_ocr_intake=false`
  - `feature_lab_result_ocr_intake=false`
  - `feature_medication_safety_alert=false`
  - production에서 regulated flag true이면 sign-off validation error.
- `backend/.env.example`
  - KDRIs 2025 운영값과 regulated feature default-off 정렬.
- `config/implementation-readiness.settings.json`
  - regulated flags와 `FEATURE_HOSPITAL_MOCK_FHIR` default false 정렬.
- docs
  - `docs/Nutrition-docs/22-current-implementation-status-map.md`
  - `docs/Nutrition-docs/23-p1-stabilization-plan.md`
  - `docs/Nutrition-docs/dev-guides/00-setup-environment.md`

### 2.6 OCR/LLM 문서

- `docs/Nutrition-docs/31-backend-feature-specifications.md`
  - 현재 backend 구현 상태 기준 기능 명세.
- `docs/Nutrition-docs/32-paddleocr-local-fallback-plan.md`
  - 로컬 PaddleOCR fallback 후보.
- `docs/Nutrition-docs/33-three-tier-ocr-pipeline-implementation-guide.md`
  - YOLO ROI, Google Vision primary OCR, Ollama vision assist 목표 구조.
- `docs/Nutrition-docs/34-llm-serving-engines-multi-environment-setup-guide.md`
  - Ollama 기본, MLX/vLLM은 후속 Adapter 전까지 후보로 정리.
- `docs/Nutrition-docs/35-google-vision-ocr-provider-implementation-plan.md`
  - Google Cloud Project/Billing/Vision API 활성화 이후의 구현 설계.
  - `OCR_PRIMARY_PROVIDER=none`, `ALLOW_EXTERNAL_OCR=false` fail-closed 기본값.
  - Google Vision은 별도 external OCR consent와 fake-client test 뒤에 연결.

## 3. 현재 검증 상태

이 문서는 로컬 파일 상태 정리용이다. 아래 명령은 커밋 전 다시 실행해야 한다.

```bash
cd /Users/yeong/99_me/00_github/03_lemon_healthcare
git diff --check
cd yeong-Lemon-Aid/backend
.venv/bin/python -m pytest --cov-report=term-missing
.venv/bin/python scripts/validate_kdris_dataset.py --require-approved
```

현재 문서 기준으로 알려진 마지막 프로젝트 검증 기록은 다음과 같다.

- full pytest coverage: `310 passed, 1 skipped`, coverage `87.67%`
- KDRIs validator: 1,795 rows validated
- formatting/lint/type check: pass 기록

검증 기록은 로컬 환경과 파일 줄끝/checksum 정리에 따라 달라질 수 있으므로, 커밋 직전 반드시 재실행한다.

## 4. 커밋 전 선별 기준

포함 후보:

- `yeong-Lemon-Aid/backend/**`
- `yeong-Lemon-Aid/config/**`
- `yeong-Lemon-Aid/data/nutrition_reference/kdris/**`
- `yeong-Lemon-Aid/data/nutrition_reference/nutrient/chronic_nutrient_priorities.json`
- `yeong-Lemon-Aid/docs/22*`, `23*`, `31*`, `32*`, `33*`, `34*`, `35*`
- `yeong-Lemon-Aid/HANDOFF.md`

기본 제외 후보:

- `assets/mascot/`
- `records/meetings/`
- `outputs/reports/`
- `outputs/generated/`
- `outputs/todo-list/`
- `../00_plusultra/`

## 5. 다음 작업 제안

1. `git diff --check`와 KDRIs validator를 통과시킨다.
2. backend full test를 재실행한다.
3. 프로젝트 파일만 선별 staging한다.
4. 커밋 메시지는 Conventional Commits 형식으로 나눈다.
   - `feat(data): promote KDRIs 2025 approved dataset`
   - `fix(security): harden JWT JWKS production verification`
   - `feat(nutrition): add chronic condition priority lookup`
   - `docs(ocr): add Google Vision OCR provider implementation plan`
5. `main`은 건드리지 않고 `team/yeong-tech` 기준 리뷰 후 반영한다.
