# 2026-05-22 Current Implementation Status Map

## 기준

이 문서는 `2026-05-22-folder-implementation-plan.md`의 PR-2 항목을 현재 checkout 기준으로 갱신한 상태 map이다.

상태 구분:

| Status | 의미 |
| --- | --- |
| `implemented` | 라우터/서비스/테스트가 있고 기본 동작이 현재 검증 가능하다. |
| `feature-gated` | 코드가 있으나 설정, consent, 외부 provider, sign-off gate가 켜져야 동작한다. |
| `smoke-only` | smoke/evaluation harness는 있으나 production 기능으로 판단하지 않는다. |
| `not-production-ready` | 현재 성능, 운영 의존성, 보안/비용 gate 때문에 운영 사용 전 추가 작업이 필요하다. |

## FastAPI 등록 상태

근거 파일:

- `backend/Nutrition-backend/src/main.py`
- `backend/Nutrition-backend/src/api/v1/router.py`

현재 `create_app()`은 `api_router`를 포함하고, `api_router`는 아래 router를 `/api/v1` prefix 아래에 등록한다.

| Area | Routes | Status | 근거 |
| --- | --- | --- | --- |
| Activity | `POST /api/v1/activity/score` | `implemented` | `src/api/v1/activity.py`, `tests/integration/api/test_health_sync_api.py` |
| Weight prediction | `POST /api/v1/predictions/weight` | `implemented` | `src/api/v1/predictions.py`, `tests/integration/api/test_predictions_auth.py` |
| Nutrition | `GET /api/v1/nutrition/kdris`, `POST /api/v1/nutrition/analyze`, `GET /api/v1/nutrition/diagnosis/latest` | `implemented` | `src/api/v1/nutrition.py`, `tests/unit/nutrition/` |
| Analysis results | create/list/get/delete result endpoints | `implemented` | `src/api/v1/analysis_results.py`, `tests/integration/api/test_dashboard_nutrition_api.py` |
| Privacy | consent and data deletion endpoints | `implemented` | `src/api/v1/privacy.py`, `tests/integration/api/test_privacy_api.py` |
| Regulated inputs | prescription/lab OCR preview and confirm | `feature-gated` | `src/api/v1/regulated_inputs.py`, `src/regulated/ocr_intake.py`, `tests/integration/api/test_regulated_inputs_api.py` |
| Supplements | OCR analyze, OCR-text confirm, registration, recommendations | `feature-gated` | `src/api/v1/supplements.py`, `tests/integration/api/test_supplement_*` |
| Dashboard | `GET /api/v1/dashboard/summary` | `implemented` | `src/api/v1/dashboard.py`, `tests/unit/services/test_dashboard.py` |
| Health sync | `POST /api/v1/health/sync` | `implemented` | `src/api/v1/health.py`, `tests/unit/services/test_health_sync.py` |

## 기능별 구현 상태

| Feature | Status | 현재 구현 | 다음 gate |
| --- | --- | --- | --- |
| OCR provider routing | `feature-gated` | `src/ocr/factory.py`에서 `none`, `google_vision`, `paddleocr`, `clova` provider selector를 가진다. | provider별 fixture KPI를 계속 분리하고, generated artifact privacy scan을 유지한다. |
| PaddleOCR local fallback | `not-production-ready` | `src/ocr/providers/paddle.py`, `ocr-local` extra, local toggle가 있다. | 16 fixture와 30장 smoke에서 OCR 실패/latency 분리를 계속해야 한다. |
| CLOVA OCR primary | `feature-gated` | `src/ocr/providers/clova.py`, production validation, external consent/config guard가 있다. | 외부 전송 비용/동의 정책과 provider KPI가 충족될 때만 상시 primary로 올린다. |
| Field extractor regression patch | `implemented` | `src/ocr/field_extractor.py`가 colon-less row, pipe row, comma dosage, `mcg`, unit case를 처리한다. | 실제 product API 성분 후보 개선은 `supplement_parser`/layout/LLM path에서 별도 검증한다. |
| Supplement analyze API | `feature-gated` | `/supplements/analyze`는 consent, image safety, OCR routing, provider observations, rate limit gate를 가진다. | product API smoke와 real-label fixture를 함께 통과해야 한다. |
| Supplement registration | `implemented` | OCR 분석 결과에서 사용자 확인 기반 등록 flow가 있다. | 실제 DB/권한/중복 케이스 회귀 테스트를 유지한다. |
| Regulated OCR intake | `feature-gated` | 처방전/검사결과 OCR은 preview-only와 confirm 단계로 분리되어 있다. | regulated data는 외부 OCR/LLM consent와 operator review gate 없이는 확장하지 않는다. |
| Learning/vector pipeline | `feature-gated` | `src/learning/`, `src/models/db/learning.py`, pgvector/object storage abstractions가 있다. | raw health/OCR payload가 vector metadata에 들어가지 않는 테스트가 필요하다. |
| YOLO ROI preprocessing | `feature-gated` | `src/vision/`, `src/ocr/preprocessing.py`, ROI policy config가 있다. | `ENABLE_VISION_CLASSIFIER`와 docs sign-off 없이 production에서 켜지지 않는다. |
| Ollama parser/vision assist | `smoke-only` | `src/llm/ollama.py`, `src/llm/ollama_vision.py`와 local Gemma4 smoke evidence가 있다. | loopback-only, raw model response non-storage, fixture-level parse KPI가 필요하다. |
| Mobile release safety | `implemented` | release token/HTTPS/certificate pin checks와 native hostname validation이 있다. | release artifact scan과 flavor build gate를 계속 유지한다. |
| Backend dev environment | `implemented` | `backend/scripts/check_backend_dev_env.py`가 `.env`를 읽지 않고 setup/tool/Git artifact 상태를 점검한다. | 신규 작업자는 `LOCAL_SETUP.md`의 `requirements-dev` 명령과 doctor를 먼저 실행한다. |

## Repo-local 성능/품질 수치

성능 수치는 repo-local generated report에서 확인한 값만 적는다. 없는 값은 추정하지 않는다.

| Report | Provider | N | 핵심 지표 | Raw storage |
| --- | --- | ---: | --- | --- |
| `outputs/generated/ocr-eval/2026-05-22-stage1-clova/ocr-three-tier-evaluation.json` | `clova_ocr` | 16 | completed 15, error 1, text non-empty 0.9375, parser success 0.9375, ingredient exact 0.0, avg latency 1786.125ms | `raw_artifacts_stored=false`, `raw_ocr_text_stored=false` |
| `outputs/generated/ocr-eval/2026-05-22-naver-tampermonkey/runner-paddle-detail-smoke-30-gemma4/naver-ocr-provider-comparison.json` | `paddleocr_local` | 30 | text non-empty 0.8667, parser success 0.8667 | `raw_artifacts_stored=false`, `raw_ocr_text_stored=false` |
| `outputs/generated/ocr-eval/2026-05-22-naver-tampermonkey/runner-paddle-detail-smoke-1-gemma4-live/naver-ocr-provider-comparison.json` | `paddleocr_local` | 1 | text non-empty 0.0, parser success 0.0 | `raw_artifacts_stored=false`, `raw_ocr_text_stored=false` |

## 보안/유출 관찰

- Public supplement analyze response는 raw OCR text, provider raw payload, request header, image bytes를 반환하지 않는 방향으로 테스트가 있다.
- generated OCR artifact는 `.gitignore`로 제외했고, `backend/scripts/check_ocr_artifact_privacy.py`로 forbidden key/local path를 검사한다.
- PR/export base는 `backend/scripts/check_pr_export_base.py`로 skeleton base와 generated OCR artifact tracked base를 거부한다.
- backend dev-env doctor는 `.env` 내용을 열지 않고 tracked 여부만 확인한다.
- Rate limit subject key는 검증되지 않은 `Authorization` header를 신뢰하지 않고 client host digest를 사용한다.
- Production에서는 process-local limiter만으로 부팅하지 않도록
  `RATE_LIMIT_EXTERNAL_ENFORCEMENT=true`와 함께 외부 계층 종류
  (`RATE_LIMIT_EXTERNAL_PROVIDER`) 및 non-secret 운영 증거
  (`RATE_LIMIT_EXTERNAL_POLICY_REF`)가 필요하다.

## 다음 검증 gate

| Gate | 목적 | 권장 명령/근거 |
| --- | --- | --- |
| Backend doctor | 새 작업자 환경 재현성 확인 | `PYTHONPATH=backend/Nutrition-backend:backend .venv/bin/python backend/scripts/check_backend_dev_env.py --repo-root .` |
| OCR privacy scan | generated artifact 유출 방지 | `backend/scripts/check_ocr_artifact_privacy.py --check-tracked-generated --project-root .` |
| PR base gate | team PR base 정합성 확인 | `backend/scripts/check_pr_export_base.py --base-ref <base>` |
| Product API smoke | raw response field 유출 방지 | `backend/scripts/smoke_supplement_analyze_api.py` |
| Field-level OCR KPI | parser/layout 개선 효과 확인 | 16 fixture evaluation, `field_match_ratio >= 0.95` 목표 |
| Mobile release gate | token/HTTP/cert pin 회귀 방지 | `flutter test` + flavor build + release artifact scan |

## 남은 위험

- `team/develop`은 현재 OCR backend tree가 없는 skeleton base라 작은 OCR patch PR의 base로 부적합하다.
- `team/feat/ocr-p1-5-followup`은 code-bearing branch지만 generated OCR eval artifacts가 tracked되어 새 PR base로 부적합하다.
- 현재 OCR 성능은 provider만 교체해서 해결된 상태가 아니다. `field_extractor`, layout parser, `supplement_parser`, local LLM structured parse를 분리해서 봐야 한다.
- Learning/vector와 YOLO ROI는 코드가 있어도 production sign-off와 raw payload non-storage 검증 전에는 feature-gated로 유지한다.
