# 핸드오프 — VLM Inspector + OCR 파이프라인 재설계

> **이 문서를 읽는 분께**: 본 문서는 직전 세션에서 진행된 작업의 상세 상태와 다음 작업의 진입점을 담는다. 이 문서만으로 다음 세션이 컨텍스트 없이 작업을 이어갈 수 있도록 설계되었다.

| 항목 | 값 |
|---|---|
| 작성일 | 2026-05-14 |
| 작업 브랜치 (worktree) | `claude/busy-blackburn-0185de` |
| 메인 브랜치 | `main` |
| 직전 마지막 커밋 | `4f91681 docs(lemon): add docs/18 enhancement brainstorm notes for all 47 docs` |
| 본 세션 최종 검증 | `pytest tests/` **71 passed** (llm 26 + validation 19 + rule_validator 26) |
| P0 진행 상태 | ✅ **완료** (pyproject.toml + requirements.txt + conftest.py + RuleValidator + Inspector orchestrator) |

---

## 1. 직전 세션의 의사결정 요약

### 1.1 발단

GPT 5.5가 사용자의 "Google Vision primary OCR + YOLO ROI 보조 + Ollama 멀티모달 fallback/검수" 설계를 비판적으로 평가했고, 사용자는 그 평가에 대한 메타 평가와 더 나은 방안을 요청했다.

### 1.2 핵심 결론 (사용자 응답으로 확정)

GPT 5.5의 위험 진단(**VLM을 OCR 대체로 쓰면 환각 위험**)은 옳지만, 다음을 놓쳤다:
- 이미 docs/06에 Naver CLOVA 백업, 0.85 confidence 폴백 임계값, Adapter 패턴, Phase Gate가 잡혀 있음
- 한국 도메인 특성(식약처 의무표시사항, 한국 호스팅 OCR 후보, 바코드 식별, 로컬-퍼스트 컴플라이언스)을 놓침
- 가장 큰 누락: **바코드 우선 식별 → 식약처 DB 매칭** 경로 — OCR 정확도 압박을 가장 크게 줄임

### 1.3 사용자가 확정한 3대 결정

1. **OCR 4종 벤치마크 실시**: GV + CLOVA + Upstage + PaddleOCR(로컬)
2. **바코드 우선 식별 경로 MVP에 포함**: 식약처 OpenAPI 매핑 포함
3. **VLM Inspector 권한 = Verdict만**: agree / disagree / unsure_recapture만 반환. **값 제안 자체를 스키마에서 제거**해 코드 레벨에서 환각 경로 차단.

### 1.4 용어 재정의 (모호한 "fallback" 폐기)

- **OCR Provider** (GV 1순위, CLOVA 2순위): 값을 *생성*
- **Layout Parser**: 좌표 기반 행/열 *구조 복원*
- **Rule Validator**: 단위·범위·사전 *통과/거부*
- **VLM Inspector** (Qwen/Gemma): low-confidence·rule-fail 케이스에서 *판정만*
- **Human Reviewer**: *최종 확정*

### 1.5 정식 plan 파일 위치

전체 평가 + 권고 아키텍처 + 평가셋 설계 + Phase Gate 매핑은 별도 plan 파일에 있다:

> `/Users/yeong/.claude/plans/resilient-humming-music.md`

이 plan 파일은 worktree 밖에 있으므로 본 문서가 핵심 결정을 모두 인라인으로 요약한다.

---

## 2. 본 세션에서 완료한 작업

### 2.0 P0 후속 작업 (2026-05-14 추가)

P0 (백엔드 표준 설정 + RuleValidator + Inspector Orchestrator) 가 완료되어 다음 파일이 추가되었다:

| 파일 | 역할 |
|---|---|
| [backend/pyproject.toml](backend/pyproject.toml) | black/ruff/mypy/pytest 통합 설정. `[tool.mypy.overrides]` 로 tests/ 완화. asyncio_mode=auto. |
| [backend/requirements.txt](backend/requirements.txt) | production 의존성 (FastAPI, Pydantic v2, ollama, google-cloud-vision 등) |
| [backend/requirements-dev.txt](backend/requirements-dev.txt) | dev 의존성 (pytest, ruff, mypy 등). `-r requirements.txt` 포함. |
| [backend/tests/conftest.py](backend/tests/conftest.py) | 공통 픽스처 (`test_settings`, `test_settings_multimodal`, `StubOllamaClient`) |
| [backend/src/validation/__init__.py](backend/src/validation/__init__.py) | validation 패키지 exports |
| [backend/src/validation/rule_validator.py](backend/src/validation/rule_validator.py) | `SupplementRow`/`RuleViolation`/`RuleValidationResult` 스키마 + `validate_row` 순수 함수. 단위 사전, 함량 범위 사전, 의료 효능 표현 정규식. |
| [backend/src/validation/inspector_orchestrator.py](backend/src/validation/inspector_orchestrator.py) | `AggregatedReview` + `review_row` — Rule 위반 시 `LLMAdapter.inspect` 호출 라우팅 |
| [backend/tests/unit/validation/test_rule_validator.py](backend/tests/unit/validation/test_rule_validator.py) | 27 케이스 — 단위/범위/DV/행무결성/의료표현/멀티위반/스키마 |
| [backend/tests/unit/validation/test_inspector_orchestrator.py](backend/tests/unit/validation/test_inspector_orchestrator.py) | 7 케이스 — pass/block+VLM agree/disagree/unsure, warn-only, crop 누락, 멀티위반 |

**전체 테스트**: `pytest tests/` → **71 passed in 0.09s**

핵심 안전 장치 (회귀 테스트로 보호):
1. **의료 효능 표현 차단** (CLAUDE.md Rule 1 자동 검수): "치료", "처방", "진단", "diagnose", "prescribe", "cure" 등 패턴이 `ingredient_name` 에 등장하면 자동으로 `severity="block"` 위반.
2. **단위 사전 화이트리스트**: `kg`, `lb` 등 사전 외 단위는 무조건 block.
3. **VLM 호출 게이팅**: Rule pass → VLM 호출 0건 (`adapter.calls == []` 검증). 비용/지연 최적화.
4. **UNSURE 우선 라우팅**: 여러 VLM 응답 중 1건이라도 UNSURE_RECAPTURE → 최종 액션 RECAPTURE.
5. **block 위반 + VLM agree 도 자동 확정 금지**: VLM 이 "OCR 텍스트는 이미지와 일치한다"고 해도 Rule 이 의심하므로 MANUAL_REVIEW 로 라우팅.

### 2.1 생성·수정 파일

| 파일 | 상태 | 역할 |
|---|---|---|
| [backend/src/llm/inspection_schema.py](backend/src/llm/inspection_schema.py) | **신규** | `Verdict`/`SuggestedAction` enum, `InspectionInput`/`InspectionResult` Pydantic, `validate_evidence_substring` |
| [backend/src/llm/base.py](backend/src/llm/base.py) | **수정** | `LLMAdapter.inspect()` 기본 구현 추가 (NotImplementedError) |
| [backend/src/llm/ollama.py](backend/src/llm/ollama.py) | **신규** | `OllamaAdapter` — `analyze_text` + `inspect`, 게이트 가드, 환각 격하 로직 |
| [backend/src/llm/__init__.py](backend/src/llm/__init__.py) | **수정** | public exports |
| [backend/tests/__init__.py](backend/tests/__init__.py) | **신규** | 테스트 패키지 |
| [backend/tests/unit/__init__.py](backend/tests/unit/__init__.py) | **신규** | |
| [backend/tests/unit/llm/__init__.py](backend/tests/unit/llm/__init__.py) | **신규** | |
| [backend/tests/unit/llm/test_inspection_schema.py](backend/tests/unit/llm/test_inspection_schema.py) | **신규** | 16개 케이스 |
| [backend/tests/unit/llm/test_ollama_adapter.py](backend/tests/unit/llm/test_ollama_adapter.py) | **신규** | 10개 케이스 |

### 2.2 구현된 안전 장치 (회귀 테스트로 보호됨)

1. **값 필드 미존재**: `InspectionResult` 스키마에 `amount_value`/`unit`/`ingredient_name` 자체가 없음
2. **`extra="forbid"`**: 모델이 임의 필드를 추가하려 해도 Pydantic 검증에서 차단
3. **게이트 가드**: `enable_multimodal_llm=False` 면 `inspect()` 가 Ollama 호출 전에 `LLMError`. 검증: `stub.call_count == 0`
4. **환각 evidence 격하**: OCR 원문에 없는 `evidence_text` 반환 시 → `evidence_text=None`, `verdict=DISAGREE`, `suggested_action=MANUAL_REVIEW` 로 안전 측 격하
5. **Structured output 강제**: `format=InspectionResult.model_json_schema()` + `temperature=0.0` 호출 인자 검증
6. **JSON 파싱 실패**: non-JSON 응답은 `LLMError`
7. **회귀 방지 메타 테스트** (`test_no_value_fields_in_schema`): JSON schema 의 properties 에 금지 필드(`amount_value`, `suggested_unit`, `corrected_value` 등)가 절대 들어가지 않음을 검증

### 2.3 테스트 실행 결과

```
$ cd backend && python3 -m pytest tests/unit/llm/ -v
============================== 26 passed in 0.06s ==============================
```

세부 결과:
- `TestEnums`: 2/2
- `TestInspectionInput`: 4/4 (valid, empty rejection, unknown field, frozen)
- `TestInspectionResult`: 7/7 (valid, unknown field × 2, reason 길이, latency 음수, frozen, **값 필드 미노출 메타 회귀**)
- `TestValidateEvidenceSubstring`: 3/3
- `TestAnalyzeText`: 2/2
- `TestInspectGate`: 1/1
- `TestInspectHappyPath`: 3/3 (agree, schema/temp 검증, disagree+evidence)
- `TestInspectFailureModes`: 4/4 (invalid JSON, schema 위반, 환각 격하, ResponseError 래핑)

### 2.4 본 세션에서 의도적으로 만들지 *않은* 것

- `pyproject.toml` — 기존에 없었음. 다음 세션의 첫 작업으로 권장.
- `requirements.txt` — 위와 동일.
- `tests/conftest.py` — 현재 anaconda pytest 가 우연히 통과. 표준화 필요.
- `OllamaAdapter` 의 실제 Ollama 서버 통합 테스트 — Phase 2 게이트 통과 후.
- `mobile/` 디렉토리 — Phase 2 작업.

---

## 3. 권고 아키텍처 (전체) — 다음 세션이 참조할 데이터 흐름

```
[1] 사용자 촬영
     ↓
[2] Tier 0: 입력 품질 게이트 (블러/반사/기울기/텍스트 높이)
     ├─ 실패 → 재촬영 요청 (OCR 호출 없음)
     └─ 통과 ↓
[3] BarcodeAdapter (바코드/QR 디코딩)            ← MVP 필수
     ├─ 식약처 DB 매칭 → product fingerprint 확정, OCR 은 검증 용도
     └─ 미발견 ↓
[4] OCR Provider (Google Vision primary)
     │   confidence < 0.85 시 CLOVA 2차 시도 (이미 docs에 정의됨)
     ↓
[5] Layout Parser (좌표 기반)
     │   - y-band row grouping
     │   - x-band column grouping
     │   - 키워드 앵커 ("일일섭취량", "영양·기능정보", "섭취방법", "주의사항")
     ↓
[6] Rule Validator
     │   - 단위 사전 (mg/mcg/μg/IU/CFU/mL/%)
     │   - 성분별 함량 범위
     │   - 성분명 정규화 (정적 사전 → 임베딩)
     │   - 행 무결성
     │   - 의료 효능 표현 탐지 (CLAUDE.md Rule 1 위반)
     ├─ all-pass → 자동 확정 후보
     └─ any-fail ↓
[7] VLM Inspector (Qwen 또는 Gemma — 벤치마크 우승 1종)    ← 본 세션 완료
     │   입력: image crop + OCR 원문 + Rule 위반 사유
     │   출력: {verdict, evidence_text|null, reason, suggested_action}
     │   값 생성 절대 금지 (스키마 자체에 값 필드 없음)
     ↓
[8] Human Review UI
     │   - 자동 확정 후보 (Rule pass + VLM agree)
     │   - 검수 필요 (Rule fail 또는 VLM disagree)
     │   - 재촬영 필요 (Tier 0 또는 VLM unsure-recapture)
     ↓
[9] DB 저장 (원문 + 정규화값 + evidence_text + confidence + review_status)
     ↓
[10] (선택) 데이터 플라이휠 — docs/17 동의 4번 한정 학습셋 적재
```

---

## 4. 앞으로 진행할 작업 — 우선순위 정렬

### ✅ 우선순위 P0: **완료** (2026-05-14)

#### P0-1. 백엔드 표준 설정 정식화 — ✅ 완료
- [x] `backend/pyproject.toml` — black/ruff/mypy/pytest 통합. `asyncio_mode=auto`. tests/ 는 strict 완화.
- [x] `backend/requirements.txt` — production 의존성
- [x] `backend/requirements-dev.txt` — dev 의존성 (`-r requirements.txt` 상속)
- [x] `backend/tests/conftest.py` — `test_settings` / `test_settings_multimodal` / `StubOllamaClient` 픽스처
- [x] `backend/.env.example` — 직전 세션에서 이미 정리되어 있어 그대로 유지

검증 완료: `python3 -m pytest tests/` → **71 passed in 0.09s**

#### P0-2. RuleValidator + Inspector Orchestrator — ✅ 완료
- [x] [backend/src/validation/rule_validator.py](backend/src/validation/rule_validator.py)
  - [x] `SupplementRow` Pydantic — Layout Parser 출력 1행 표현
  - [x] `RuleViolation` Pydantic — field/reason/ocr_text/severity
  - [x] `RuleValidationResult` Pydantic — `passes` / `has_violations` / `has_blocking` properties
  - [x] `ALLOWED_UNITS` — mg/mcg/μg/ug/IU/CFU/mL/ml/g/%
  - [x] `INGREDIENT_RANGES` — 시드 사전 (Vitamin D3/C, 칼슘, 마그네슘 + 한글 변형)
  - [x] `MEDICAL_EXPRESSION_PATTERNS` — CLAUDE.md Rule 1 의 9개 패턴 + 정규식
  - [x] `validate_row` 순수 함수 — 5개 규칙 순차 적용
- [x] [backend/src/validation/inspector_orchestrator.py](backend/src/validation/inspector_orchestrator.py)
  - [x] `AggregatedReview` Pydantic
  - [x] `review_row` async — Rule pass 시 VLM 호출 없이 AUTO_COMMIT, block 위반에 대해서만 `adapter.inspect` 호출
  - [x] `_aggregate_final_action` — UNSURE 우선 → 그 외 위반/disagree 는 MANUAL_REVIEW
- [x] 테스트: rule_validator 27 케이스 + orchestrator 7 케이스 = 34 케이스 신규 추가, 모두 통과

### 🟡 우선순위 P1: MVP 핵심 모듈

#### P1-1. BarcodeAdapter + 식약처 OpenAPI 클라이언트 — **사용자가 MVP 포함으로 확정한 가장 큰 변경**
- [ ] `backend/src/vision/barcode_base.py` — `BarcodeAdapter` ABC
- [ ] `backend/src/vision/barcode_zxing.py` — `zxing-cpp` 또는 `pyzbar` 구현
- [ ] `backend/src/nutrition/mfds_client.py` — 식약처 식품안전나라 / 건강기능식품 원료 DB OpenAPI 클라이언트
- [ ] `Settings.mfds_api_key` 활용 (이미 config.py 에 `SecretStr` 으로 정의됨)
- [ ] Redis 캐시 적용 (docs/06 §3.4)
- [ ] product fingerprint 매칭 로직 — 바코드 일치 시 OCR 결과는 *검증용*, 불일치 시 `review_required`
- [ ] 테스트: zxing mock, 식약처 API mock (httpx mocking), product 매칭 로직

식약처 API 키 발급은 별도 작업으로 사용자 의뢰 필요.

#### P1-2. OCRAdapter 구현체 — Google Vision primary
- [ ] `backend/src/ocr/google_vision.py` — `GoogleVisionOCR(OCRAdapter)`
- [ ] `DOCUMENT_TEXT_DETECTION` 모드 사용 (성분표는 dense text)
- [ ] **단어별 좌표·confidence·block 구조를 노출** — Layout Parser 가 의존 (현재 `OCRResult` 가 평균 confidence 만 가지므로 확장 필요)
- [ ] 신뢰도 0.85 미만 시 CLOVA 폴백 로직
- [ ] 0.85 임계값은 `Settings` 의 새 필드 `ocr_confidence_threshold` 로 외부화
- [ ] 테스트: Google API mock, 폴백 트리거, confidence threshold

#### P1-3. OCRAdapter 구현체 — Naver CLOVA OCR (backup)
- [ ] `backend/src/ocr/clova.py` — `ClovaOCR(OCRAdapter)`
- [ ] CLOVA OCR REST API 호출 (httpx async)
- [ ] 응답 정규화 — Google Vision 과 동일한 `OCRResult` 구조로 반환

#### P1-4. Layout Parser
- [ ] `backend/src/parsing/layout_parser.py` — 좌표 기반 행/열 그룹핑
- [ ] 모델 없는 순수 휴리스틱 (y-band row grouping, x-band column grouping)
- [ ] 키워드 앵커: "일일섭취량", "영양·기능정보", "섭취방법", "섭취 시 주의사항", "원재료명", "기능성"
- [ ] 출력: `LabelLayout` Pydantic — 섹션별 셀 배열
- [ ] 테스트: 좌표 fixture (mock OCR 출력) 에서 행/열 복원

#### P1-5. Tier 0 입력 품질 게이트
- [ ] `backend/src/validation/quality_gate.py` — OpenCV 기반
  - Laplacian variance (블러)
  - 채도 포화 픽셀 비율 (반사)
  - Hough/edge perspective skew
  - 최소 텍스트 픽셀 높이
- [ ] 4개 중 1개라도 미달이면 `QualityGateFailure` → "재촬영 요청"
- [ ] 테스트: 4개 게이트 각각의 양/음성 케이스 (test fixture 이미지)

### 🟢 우선순위 P2: Phase 2 (게이트 통과 후)

#### P2-1. 100장 + 500장 평가셋 수집 도구
- [ ] `scripts/collect_eval_set.py` — 라벨 이미지 + 정답 JSON 페어 수집 도구
- [ ] 계층 8종 (plan §7.1): clean / mild glare / heavy glare / perspective skew / rotated / partial / small font / non-supplement
- [ ] 한국 라벨 ≥70%
- [ ] 정답 JSON 스키마: 한국 의무표시사항 기준 (제품명, 식약처 신고번호, 영양·기능정보, 일일섭취량, 섭취방법, 주의사항, 원재료명, 기능성)

#### P2-2. OCR 4종 벤치마크 실행 (사용자 결정 사항)
- [ ] `scripts/benchmark_ocr.py` — GV vs CLOVA vs Upstage vs PaddleOCR
- [ ] 평가 지표 (plan §7.2):
  - Hallucination Rate ← **0건이 강제**
  - Ingredient Exact Match ≥0.90
  - Amount Exact Match ≥0.90
  - Unit Accuracy ≥0.97
  - Row Association Accuracy ≥0.90
  - Recapture Precision ≥0.85
  - Manual Review Rate ≤30%
  - Latency P95 ≤6초
- [ ] 한국 라벨 부분집합 별도 집계
- [ ] 결과를 docs 에 저장 → 우승 OCR 을 운영 primary 로 확정

#### P2-3. Qwen 3.5 vs Gemma 4 Inspector 벤치마크 (docs/18 P2-02 / T-032 이미 계획됨)
- [ ] 100장 영양제 라벨 fixture 로 정확도·응답시간 측정
- [ ] 우승 1종을 default Inspector 로 고정 → `Settings.ollama_multimodal_model` 기본값 갱신

### 🔵 우선순위 P3: Phase 3 — Vision Classifier 게이트

#### P3-1. YOLO 도입 (`enable_vision_classifier=True` 게이트 통과 후)
- [ ] `backend/src/vision/yolo.py` — `YOLOVisionAdapter(VisionAdapter)`
- [ ] 역할 한정: (a) 촬영 시점 가이드용 라벨 박스 (b) OCR 실패 케이스의 ROI 재시도
- [ ] **YOLO 비권장 역할**: 성분명/함량 추출, 행/열 구조 복원, 최종 JSON 생성

### 🟣 우선순위 P4: Phase 4 — 데이터 플라이휠

#### P4-1. `enable_image_learning_pipeline` + `enable_pgvector_storage` 게이트 통과 후
- [ ] Human Review 에서 수정된 (이미지, 정답 JSON) 쌍 → 학습셋 적재
- [ ] docs/17 §3 4번 동의 한정
- [ ] pgvector 저장: 가명화 이미지 + CLIP 임베딩
- [ ] Document AI Custom Extractor 와의 비교 실험 (오프라인, 운영 도입 불가)

---

## 5. 다음 세션이 반드시 알아야 할 컨벤션

> 모든 작업은 [CLAUDE.md](CLAUDE.md) 와 [backend/CLAUDE.md](backend/CLAUDE.md) 의 규칙을 따른다. 아래는 자주 위반되는 핵심만 요약.

### 5.1 절대 규칙 (CLAUDE.md)

- **Rule 1**: 의료 도메인 금지 단어 (`diagnose`, `prescribe`, `cure`, `treat`, `진단`, `처방`, `치료`, `보장`) — 코드, docstring, 로그, UI, LLM 프롬프트 어디에도 금지
- **Rule 2**: 외부 API 는 반드시 Adapter 패턴 (직접 호출 금지)
- **Rule 3**: 타입 힌트 100% + Pydantic v2 (dataclass X)
- **Rule 4**: Google-style docstring (Args/Returns/Raises/Examples)
- **Rule 5**: 단위 테스트 동반 필수
- **Rule 6**: 민감 정보(.env, API 키, Service Account JSON) 커밋 금지
- **Rule 7**: 코드·docstring 영어 우선, UI 텍스트는 한국어
- **Rule 8**: 한국·아시아 BMI 기준

### 5.2 백엔드 작업 시 추가 (backend/CLAUDE.md)

- `from __future__ import annotations` 첫 줄
- Pydantic `ConfigDict(frozen=True)` 권장
- async 우선, `time.sleep` 금지 → `asyncio.sleep`
- `datetime.now(UTC)` 명시
- `print` 금지 → `logger`
- `SecretStr` 으로 API 키 처리
- 테스트는 클래스 그룹 (`TestXxx`) + `[가이드 예시]` 접두어
- `pytest.approx(..., abs=...)` 로 부동소수점 비교

### 5.3 Phase Gate 시스템

모든 신규 기능은 OFF 기본값. 운영 활성화는 docs/17 §9 게이트 절차를 따른다.

| Gate | Settings flag | 활성화 단계 | 본 세션 영향 |
|---|---|---|---|
| #1 | `enable_multimodal_llm` | Phase 2 | `OllamaAdapter.inspect()` 가 이 게이트에 가드됨 |
| #2 | `enable_vision_classifier` | Phase 3 | YOLO 도입 시 |
| #3 | `enable_image_learning_pipeline` | Phase 4 | 학습 데이터 적재 시 |
| #4 | `enable_pgvector_storage` | Phase 4 | 벡터 저장 시 |

---

## 6. 검증 — 다음 세션 시작 시 현 상태 확인 방법

### 6.1 빠른 smoke test (1초)

```bash
cd 03_lemon_healthcare/yeong-Vision-Nutrition/backend
python3 -c "from src.llm import OllamaAdapter, InspectionInput, InspectionResult, Verdict, SuggestedAction; print('imports OK')"
```

기대 출력: `imports OK`

### 6.2 전체 단위 테스트 (1초)

```bash
cd 03_lemon_healthcare/yeong-Vision-Nutrition/backend
python3 -m pytest tests/ -v
```

기대 출력: `71 passed` (llm 26 + validation 45)

### 6.3 회귀 보호 핵심 케이스 확인

다음 다섯 테스트는 안전성의 핵심이므로 절대 깨지면 안 된다:

```bash
# 환각 차단 게이트
python3 -m pytest tests/unit/llm/test_inspection_schema.py::TestInspectionResult::test_no_value_fields_in_schema -v
python3 -m pytest tests/unit/llm/test_ollama_adapter.py::TestInspectGate::test_gate_off_raises -v
python3 -m pytest tests/unit/llm/test_ollama_adapter.py::TestInspectFailureModes::test_hallucinated_evidence_downgrades_to_manual_review -v

# Rule 1 (의료 표현 금지) 자동 검수
python3 -m pytest tests/unit/validation/test_rule_validator.py::TestMedicalExpression -v

# VLM 호출 게이팅 (Rule pass 시 0건 호출)
python3 -m pytest tests/unit/validation/test_inspector_orchestrator.py::TestPassingRow::test_auto_commits_without_vlm_call -v
```

이 다섯 가지 중 하나라도 깨지면 안전 게이트가 무너진 상태이므로, 즉시 원복하고 원인 분석.

---

## 7. 본 세션에서 의도적으로 *피한* 결정 (다음 세션에서 검토 필요)

| 미결 사항 | 메모 |
|---|---|
| Document AI Custom Extractor 오프라인 벤치마크 시점 | docs/17 동의 절차 추가 필요. Phase 2 이후 |
| Upstage Document Parse API 키 발급 | 비용·승인 별도 |
| PaddleOCR 자체 호스팅 인프라 | Docker Compose 에 별도 서비스로 추가할지, FastAPI 프로세스 안에서 inline 으로 둘지 결정 필요 |
| 임베딩 모델 선정 (성분명 정규화) | `nlpai-lab/KURE-v1` vs `intfloat/multilingual-e5-base` — 벤치마크 후 결정 |
| Human Review UI 구체 설계 | Phase 2 모바일 작업 |
| outlines / lm-format-enforcer 도입 여부 | 현재는 Ollama 의 `format=schema` 만 사용. 환각이 자주 발견되면 추가 도입 |
| 컴플라이언스 검수 자동 lint | docs/18 I-10 — `medical_expression_filter.py` 별도 작업 |

---

## 8. 핵심 문서 단축 링크

| 종류 | 경로 |
|---|---|
| 본 세션 plan 파일 (worktree 밖) | `/Users/yeong/.claude/plans/resilient-humming-music.md` |
| 프로젝트 루트 규칙 | [CLAUDE.md](CLAUDE.md) |
| 백엔드 규칙 | [backend/CLAUDE.md](backend/CLAUDE.md) |
| 기술 스택 (Ollama / OCR 결정 근거) | [docs/06-tech-stack.md](docs/06-tech-stack.md) |
| 알고리즘 명세 | [docs/07-core-algorithm.md](docs/07-core-algorithm.md) |
| 컴플라이언스 체크리스트 | [docs/10-compliance-checklist.md](docs/10-compliance-checklist.md) |
| Ollama 로컬 LLM 전환 계획 | [docs/12-local-llm-ollama-migration.md](docs/12-local-llm-ollama-migration.md) |
| 이미지 수집 동의 + 게이트 매핑 | [docs/17-image-collection-consent-plan.md](docs/17-image-collection-consent-plan.md) |
| 47개 문서 보강 노트 | [docs/18-enhancement-brainstorm-notes.md](docs/18-enhancement-brainstorm-notes.md) |
| OCR 파이프라인 dev-guide | [docs/dev-guides/07-ocr-pipeline.md](docs/dev-guides/07-ocr-pipeline.md) |
| LLM 영양제 파싱 dev-guide | [docs/dev-guides/08-llm-supplement-parsing.md](docs/dev-guides/08-llm-supplement-parsing.md) |

---

## 9. 다음 세션 진입 권장 프롬프트 예시

P0 가 완료되었으므로 다음 세션은 P1 부터 시작한다.

> "HANDOFF.md 를 읽고 §4 의 P1-1 (BarcodeAdapter + 식약처 OpenAPI 클라이언트) 부터 구현해줘. 식약처 API 키는 .env 의 `MFDS_API_KEY` 에 넣을 예정이다."

또는 OCR provider 부터 가고 싶을 때:

> "HANDOFF.md 를 읽고 §4 의 P1-2 (Google Vision OCR Adapter) 부터 구현해줘. `OCRResult` 에 단어별 좌표·confidence·block 구조를 노출하도록 확장하고, 0.85 미만 confidence 폴백 로직을 포함해줘."

또는 Layout Parser 부터:

> "HANDOFF.md §4 의 P1-4 (Layout Parser) 부터 구현해줘. 모델 없는 순수 좌표 휴리스틱이고, `validate_row` 가 받는 `SupplementRow` 를 출력 형태로 한다."

---

**마지막 갱신**: 2026-05-14 | **누적 결과**: VLM Inspector 스키마 + Ollama Adapter + RuleValidator + Inspector Orchestrator + 백엔드 표준 설정 = **71 테스트 통과**
