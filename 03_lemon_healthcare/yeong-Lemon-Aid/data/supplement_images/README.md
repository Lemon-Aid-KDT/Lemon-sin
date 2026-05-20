# Supplement Image Dataset

영양제 이미지 데이터셋 작업 공간입니다.

## 분류 흐름

1. 수집원을 `public_sources`, `web_crawl`, `friend_contributed`로 구분한다.
2. 웹 크롤링 데이터는 `supplement_label`, `supplement_bottle`, `blister_pack`, `nutrition_facts_panel`, `non_supplement`, `unknown` 같은 영어 클래스명으로 평탄 저장한다.
3. 영양제 여부, OCR 가능 여부, 언어(`ko`, `en`, `mixed`, `unknown`), 성분/함량/섭취방법 추출 가능 여부는 `manifests/`의 taxonomy와 full manifest에서 관리한다.
4. OCR/ROI 후보 산출물은 `interim/`, 확정 학습 입력은 `processed/`에 둔다.
5. 중복, 저품질, 애매한 라벨은 `quarantine/` 아래로 격리한다.

```text
supplement_images/
├── raw/
│   ├── public_sources/
│   ├── web_crawl/{class_name_en}/
│   │   ├── images/{hash}.jpg
│   │   └── metadata.jsonl
│   └── friend_contributed/
│       ├── inbox/
│       └── ingested/
│           ├── images/{hash}.jpg
│           └── metadata.jsonl
├── interim/
│   ├── ocr_candidates/
│   └── roi_candidates/
├── processed/
│   ├── ocr_text/
│   ├── normalized_labels/
│   └── cropped_regions/
├── splits/
│   ├── train.csv
│   ├── val.csv
│   └── test.csv
├── manifests/
│   ├── taxonomy.json
│   ├── classes.json
│   ├── fixtures/
│   └── stats/
├── quarantine/
│   ├── duplicates/
│   ├── low_quality/
│   └── ambiguous/
└── scripts/
```

---

## Stage 0 — OCR Baseline 측정 워크플로 (한/영 영양제 라벨)

목적: 완전 로컬(PaddleOCR + Ollama Vision) 정책으로 한국어/영어 영양제 라벨 OCR의 현 인식률 baseline을 산출한다. Stage 0이 통과하지 못하면 Stage 1~4 개선 작업의 효과를 측정할 기준이 없다.

게이트 통과 조건:

- fixture ≥ 30장
- raw 이미지 / raw OCR text / raw provider payload **미저장** (redaction 정책 통과)
- segment별(`ko_only`, `en_only`, `ko_en`, `dense_table`, `low_quality`) 정확도 baseline JSON + Markdown 산출

진행 순서: 사용자 작업(①~④) → 자동 진행(⑤~⑦) → 결과 해석(⑧).

---

## ① 사진 수집 (사용자 작업)

`raw/friend_contributed/inbox/`에 영양제 라벨 사진 30~50장을 복사한다. 파일명은 임의(`{hash}.jpg`로 자동 정규화됨), JPEG/PNG/WebP만 허용.

- **한/영 segment 분포 목표**: 한국어 only ≥ 10장, 영어 only ≥ 10장, 한/영 혼용 ≥ 10장
- **라벨 종류 다양성**: dense table(영양·기능정보), simple text, blister pack, supplement bottle
- **최소 해상도**: 320×240 (`prepare_supplement_ocr_live_manifest.py` 기본값 기준)
- **최대 크기**: 20MB
- **EXIF 정보**: prepare 스크립트가 자동 제거. 원본 그대로 복사

분류가 끝난 사진은 `raw/friend_contributed/ingested/images/`로 옮기고 `metadata.jsonl`에 hash와 동의 메모 인덱스를 기록한다.

---

## ② 동의 메모 (사용자 작업)

`raw/friend_contributed/inbox/CONSENT.md` 한 파일에 모든 기여자의 동의 사실을 누적 기록한다(템플릿 동일 위치에 포함). 누적 항목:

- 촬영자 ID (가명, 예: `contributor-001`)
- 촬영일자 (YYYY-MM-DD)
- 사용 범위 명시: "Lemon Healthcare OCR fixture 평가 및 비공개 학습 목적, 외부 전송 없음, raw 이미지 저장소 retention 0일 정책 적용"
- 제출 사진 파일 hash 또는 인덱스 범위

> 외부 전송 또는 학습용 vector 적재는 별도 `image_learning_dataset` consent 게이트를 통과한 뒤에만 진행한다. 기본 정책은 raw 이미지 비저장 + 가명 처리다.

---

## ③ PaddleOCR 설치 (사용자 작업, GPU 환경 결정 후)

정식 venv(`backend/.venv`)가 재생성된 상태에서:

```bash
cd /Users/yeong/99_me/00_github/03_lemon_healthcare/yeong-Lemon-Aid/backend

# GPU 환경 (권장)
.venv/bin/pip install "paddleocr>=3.0" "paddlepaddle-gpu>=3.0"

# CPU만 사용 시
.venv/bin/pip install "paddleocr>=3.0" "paddlepaddle>=3.0"

# 설치 확인
.venv/bin/python scripts/probe_paddleocr_runtime.py
```

기대 출력은 `{"ok": true, "stage": "import", ...}`. 첫 실행 시 PaddleOCR이 한국어/영어 모델을 자동 다운로드(~수백 MB). `local_ocr_text_recognition_model_dir`, `local_ocr_text_detection_model_dir` 환경변수로 모델 경로를 고정할 수 있다.

---

## ④ Ground-Truth 라벨링 (사용자 작업)

각 case마다 두 개의 expected snapshot 파일을 작성한다.

- `backend/Nutrition-backend/tests/fixtures/supplement_labels/expected/<case_id>.snapshot_v2.json`
- `backend/Nutrition-backend/tests/fixtures/supplement_labels/expected/<case_id>.snapshot_v3.json`

**case_id 명명 규칙**: `{lang}_{layout}_{seq}` (예: `ko_dense_table_010`, `en_simple_001`, `ko_en_blister_005`).

**V2 schema 필수 필드** (라벨링 가이드):

- `schema_version`: `"supplement-parsed-snapshot-v2"`
- `requires_user_confirmation`: `true`
- `source`: `ocr_provider`, `ocr_confidence`는 fixture 작성 시점에는 임의값 가능. **`raw_image_stored`, `raw_ocr_text_stored`, `raw_provider_payload_stored` 세 개는 반드시 `false`**
- `product`: `product_name`, `manufacturer`, `barcode_text`/`barcode_format`(없으면 `null`)
- `serving`: `serving_size_text`, `serving_amount`, `serving_unit`, `daily_servings`, `evidence_refs`
- `ingredient_candidates[]`: `display_name`, `normalized_name`(lowercase + trim), `nutrient_code_candidates[]`, `amount`, `unit`, `daily_amount`, `confidence`(사람 라벨 신뢰도 1.0 기본), `source: "human_label"`, `evidence_refs`
- `intake_method`, `precautions`, `functional_claims`, `low_confidence_fields`, `warnings`

**V3 schema**: V2와 동일 구조에 `evidence_spans[]`가 추가됨 (각 인식 텍스트의 (page, block, paragraph, word) bounding box 인용).

**라벨링 템플릿**: `backend/Nutrition-backend/tests/fixtures/supplement_labels/expected/ko_dense_table_001.snapshot_v2.json`을 복사한 뒤 수정한다.

**라벨링 표준 어휘**:

- `unit`: `mg`, `mcg`, `μg`, `ug`, `IU`, `CFU`, `mL`, `ml`, `g`, `%`, `정`, `캡슐`
- `nutrient_code`: `data/nutrition_reference/nutrient/nutrient_codes.json` 표준 코드 사용 (예: `VITC`, `VITD`, `CA`, `FE`, `MG`, `ZN`)
- 의료 표현 금지(`diagnose`, `treat`, `cure`, `진단`, `처방`, `치료`) — `CLAUDE.md` Rule 1

라벨링 schema 검증:

```bash
cd /Users/yeong/99_me/00_github/03_lemon_healthcare/yeong-Lemon-Aid/backend
.venv/bin/python -c "
import json
import sys
from pathlib import Path
sys.path.insert(0, 'Nutrition-backend')
from src.models.schemas.supplement_snapshot import SupplementParsedSnapshotV2, SupplementParsedSnapshotV3
target = Path('Nutrition-backend/tests/fixtures/supplement_labels/expected/<case_id>.snapshot_v2.json')
SupplementParsedSnapshotV2.model_validate(json.loads(target.read_text()))
print('schema valid')
"
```

---

## ⑤ Manifest 자동 생성 (자동, ①~④ 완료 후)

```bash
cd /Users/yeong/99_me/00_github/03_lemon_healthcare/yeong-Lemon-Aid/backend
.venv/bin/python scripts/prepare_supplement_ocr_live_manifest.py \
  --source-root ../data/supplement_images/raw/friend_contributed/inbox \
  --work-dir ../data/supplement_images/private_workspace/stage0 \
  --sample-size 50 \
  --min-width 320 --min-height 240 \
  --max-bytes 20000000 \
  --min-label-score 2 \
  --manifest-name manifest.jsonl
```

결과는 `private_workspace/stage0/manifest.jsonl`과 선택된 이미지 복사본(gitignored). 원본은 `inbox/`에 그대로 유지하고, 분류가 끝나면 사용자가 `ingested/`로 옮긴다.

---

## ⑥ Observation 수집 (자동, 완전 로컬)

Ollama 서버 실행 + 모델 로드 확인:

```bash
curl -sS http://127.0.0.1:11434/api/tags | grep -E "qwen3.5|gemma4"
```

PaddleOCR + Ollama Vision (완전 로컬, secret 불필요):

```bash
RUN_PADDLEOCR_PROBE=1 \
.venv/bin/python scripts/collect_supplement_ocr_observations.py \
  --manifest ../data/supplement_images/private_workspace/stage0/manifest.jsonl \
  --output-dir ../outputs/generated/ocr-eval/observations-stage0 \
  --providers paddleocr_local
```

주의:

- 환경변수는 `RUN_PADDLEOCR_PROBE`(스크립트 정확한 이름). `RUN_PADDLEOCR_SMOKE` 아님
- `--providers`에 `clova_ocr`, `google_vision_document`는 포함하지 않는다(완전 로컬 정책)
- Ollama Vision의 service-level 효과는 `evaluate_ocr_three_tier.py` 출력에서 확인한다

---

## ⑦ Baseline + Three-Tier 평가 (자동)

```bash
.venv/bin/python scripts/evaluate_supplement_ocr_baseline.py \
  --manifest ../data/supplement_images/private_workspace/stage0/manifest.jsonl \
  --output-dir ../outputs/generated/ocr-eval/baseline-stage0

.venv/bin/python scripts/evaluate_ocr_three_tier.py \
  --manifest ../outputs/generated/ocr-eval/observations-stage0/manifest-with-observations.jsonl \
  --output-dir ../outputs/generated/ocr-eval/three-tier-stage0

# Redaction 회귀 검증
grep -rn '"raw_artifacts_stored": *true\|"raw_ocr_text_stored": *true\|"raw_provider_payload_stored": *true' \
  ../outputs/generated/ocr-eval/ && exit 1 || echo "redaction OK"
```

---

## ⑧ 결과 해석 가이드

| Metric | 의미 |
| --- | --- |
| `field_exact_match_rate` | ground-truth vs actual snapshot 비교. Stage 0에서는 actual 미수집이므로 `None` |
| `expected_snapshot_valid_count` | 라벨링 schema 통과 수. 라벨링 완료 fixture 수와 일치해야 한다 |
| `confirmation_required_rate` | 사용자 확인 요구 비율. 정상이면 `1.0` (모든 결과 review 필수) |
| `raw_image_stored`, `raw_ocr_text_stored`, `raw_provider_payload_stored` | 모두 `false`여야 한다. `true`면 정책 위배로 PR 차단 |
| `providers.paddleocr_local.ingredient_name_exact_rate` | Stage 0 baseline의 핵심 수치. Stage 1 quick wins 이후 비교 |
| `providers.paddleocr_local.parser_success_rate` | OCR 결과가 structured parser를 통과한 비율 |
| `providers.paddleocr_local.average_latency_ms` | PaddleOCR primary 호출 평균 latency |

segment별 분석은 `manifest.jsonl`의 `labels` 필드를 기준으로 별도 집계한다(`labels: ["ko"]`, `["en"]`, `["ko","en"]`, `["dense_table"]` 등).

---

## 자주 발생하는 문제

- **`ModuleNotFoundError: No module named 'paddleocr'`** → ③ 설치 누락
- **probe 출력이 `{"ok": false, "stage": "import", ...}`** → langchain 또는 paddle 의존성 누락. `pip show paddleocr paddlepaddle`로 확인
- **Ollama 응답 timeout** → `ollama list`로 모델 확인. `qwen3.5:9b` 미설치 시 `ollama pull qwen3.5:9b`, vision 모델은 `ollama pull gemma4:e4b`
- **Manifest sample_size 부족** → inbox 파일 수가 `--sample-size`보다 적거나, `--min-label-score 2`를 통과하지 못함(LABEL_KEYWORDS와 무관한 사진). 더 많은 라벨 사진을 추가하거나 `--min-label-score 1`로 완화
- **expected snapshot 라벨링 오류** → ④의 schema 검증 명령으로 확인. `validation error`를 그대로 수정
- **PaddleOCR 모델 다운로드 느림** → `PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True` 환경변수로 source check를 끄거나 model dir를 미리 받아 환경변수로 지정

---

## 검증 명령 요약 (한 번에 모두)

```bash
cd /Users/yeong/99_me/00_github/03_lemon_healthcare/yeong-Lemon-Aid/backend

# 1) 코드 quality
.venv/bin/python -m black --check Nutrition-backend/src Nutrition-backend/tests alembic
.venv/bin/python -m ruff check Nutrition-backend/src Nutrition-backend/tests alembic scripts
.venv/bin/python -m mypy Nutrition-backend/src Nutrition-backend/tests --strict
.venv/bin/python -m pytest Nutrition-backend/tests -q --no-cov

# 2) 핵심 안전 회귀 5종
.venv/bin/python -m pytest \
  Nutrition-backend/tests/unit/llm/test_inspection_schema.py::TestInspectionResult::test_no_value_fields_in_schema \
  Nutrition-backend/tests/unit/llm/test_ollama_adapter.py::TestInspectGate::test_gate_off_raises \
  Nutrition-backend/tests/unit/llm/test_ollama_adapter.py::TestInspectFailureModes::test_hallucinated_evidence_downgrades_to_manual_review \
  Nutrition-backend/tests/unit/validation/test_rule_validator.py::TestMedicalExpression \
  Nutrition-backend/tests/unit/validation/test_inspector_orchestrator.py::TestPassingRow::test_auto_commits_without_vlm_call \
  -v
```

---

## 다음 단계 안내

Stage 0이 통과한 뒤에는 `plan` 파일(`/Users/yeong/.claude/plans/stateless-sniffing-swan.md`) §I "Final Roadmap"의 Stage 1~4를 차례로 진행한다.

- **Stage 1**: 영문 anchor 추가, PaddleOCR 전처리 옵션 활성화, parser_domain_correction + nutrient_code_matcher 정식 endpoint 통합
- **Stage 2**: PaddleOCR 한/영 다언어 인스턴스, multi-ROI 좌표 병합
- **Stage 3**: PaddleOCR recognition fine-tuning, PaddleOCR + Ollama Vision cross-verification
- **Stage 4**: Ollama Vision 시스템 프롬프트 한/영 명시 강화

각 Stage마다 동일한 evaluation 명령(⑤~⑦)을 재실행해서 segment별 정확도 변화를 추적한다.
