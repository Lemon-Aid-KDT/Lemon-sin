# 2026-06-12 OCR/YOLO/Gemma4 로드맵 가이드라인

> 목표: Lemon-Aid 영양제 라벨 인식 파이프라인에서 `field_match >= 0.85`, `ingredient_recall >= 0.85`를 달성하기 위한 팀 실행 설계와 의사결정 gate를 고정한다.
>
> 결론: Gemma4 비전 모델을 MLX로 바로 fine-tuning하는 방향은 주력 경로가 아니다. 먼저 YOLO ROI/section detector로 영역을 안정화하고, PaddleOCR 설정 튜닝과 recognition fine-tuning으로 텍스트 recall을 올린다. Gemma4는 OCR empty/low-confidence/field 누락 상황에서만 보조 검증기 또는 후보 생성기로 붙인다.

## 1. Executive Summary

### 왜 OCR 학습 우선인가

현재 backend는 local OCR provider가 PaddleOCR 중심으로 이미 배선되어 있다.

| 근거 | 현재 repo 상태 |
| --- | --- |
| 의존성 | `backend/pyproject.toml`의 `ocr-local` extra가 `paddlepaddle==3.2.0`, `paddleocr>=3.6,<3.7`로 고정되어 있다. |
| runtime 설정 | `backend/Nutrition-backend/src/config.py`가 `ocr_primary_provider=paddleocr`, `enable_local_ocr`, `local_ocr_model_profile`, `local_ocr_text_recognition_model_dir`를 노출한다. |
| Paddle provider | `backend/Nutrition-backend/src/ocr/providers/paddle.py`가 PP-OCRv5 detector/recognizer와 custom recognition model dir를 사용한다. |
| 평가/gate | `paddleocr_clova_eval.py`, `evaluate_detector_roi_full_fallback_structured_extraction.py`, `gate_paddleocr_finetune_against_baseline.py`가 PaddleOCR 기준으로 이미 존재한다. |

따라서 목표 metric을 올리기 위해서는 새 VLM stack을 먼저 도입하기보다, 기존 PaddleOCR pipeline에서 누락되는 작은 텍스트 line, 성분명/함량 token, 섹션별 crop 품질을 개선하는 편이 blast radius가 작고 검증 가능하다.

### Gemma4/MLX fine-tune을 주력으로 두지 않는 이유

| 항목 | 판단 |
| --- | --- |
| 공식 지원 경로 | Google 공식 Gemma 문서에서 Gemma4는 image input을 지원하지만, vision fine-tuning 공식 가이드는 Hugging Face Transformers + QLoRA 경로다. MLX 문서는 Apple Silicon에서 `mlx_lm.generate`, `mlx_vlm.generate`, `mlx_vlm.server`로 실행하는 통합을 설명한다. MLX 기반 Gemma4 vision fine-tuning을 이 프로젝트의 주력 학습 경로로 추천하는 공식 문서는 현재 확인하지 못했다. |
| metric 적합성 | `field_match`, `ingredient_recall`, `norm_edit_dis`는 deterministic OCR/extraction 평가와 더 직접적으로 맞다. VLM fine-tuning은 hallucination 및 schema drift 방어가 별도 과제가 된다. |
| 운영 리스크 | Gemma4가 보이지 않는 텍스트를 추측하면 supplement label 데이터가 오염된다. 특히 원문 OCR 결과와 사용자 확인 전 structured answer를 직접 저장하면 회귀 분석이 어려워진다. |
| 기존 배선 | `OllamaVisionAssistAdapter`는 이미 fallback/verification 성격으로 설계되어 있으며, primary OCR provider가 아니다. |

### Gemma4를 어디에 보조로 붙일지

Gemma4/Ollama는 다음 조건을 만족할 때만 호출한다.

| 호출 조건 | 입력 | 출력 | 저장 정책 |
| --- | --- | --- | --- |
| OCR empty | ROI image, OCR text 없음, expected JSON schema | `visible_text_fragments`, `confidence`, `warnings` | final answer로 직접 저장 금지 |
| low confidence | ROI image, PaddleOCR text, PaddleOCR confidence 요약 | 보이는 텍스트 기반 보정 후보 | user confirmation 또는 deterministic validator 통과 후 반영 |
| ingredient gap | 성분표 ROI image, 현재 추출 성분 list, 누락 후보 schema | 누락 가능 fragment 후보 | metric log에는 후보 여부만 redacted 저장 |
| field missing | 브랜드/제품명/주의사항 ROI image, OCR text | 보이는 field 후보 | structured extraction의 review 후보로만 사용 |

## 2. 목표 Metric 정의

### Primary gates

| Metric | Gate | 계산 위치 | 설명 |
| --- | ---: | --- | --- |
| `field_match` | `>= 0.85` | `evaluate_detector_roi_full_fallback_structured_extraction.py` | 영양성분 field unit match. production 승격 gate에서는 `field_match_ratio_macro`와 `field_match_ratio_micro`가 모두 0.85 이상이어야 한다. |
| `ingredient_recall` | `>= 0.85` | `evaluate_detector_roi_full_fallback_structured_extraction.py` | 기대 성분명 중 추출 결과에서 발견된 비율. ingredient list recall을 낮추는 false negative가 핵심 병목이다. |
| `norm_edit_dis` | `>= 0.90` | PaddleOCR recognition eval / `gate_paddleocr_finetune_against_baseline.py` | line-level normalized edit distance. recognition model 승격 후보의 최소 하한이다. |

### Secondary metrics

| Metric | 사용 목적 |
| --- | --- |
| `acc` | PaddleOCR recognition exact match. `norm_edit_dis`와 함께 fine-tuned recognizer 품질을 본다. |
| `field_match_ratio_macro` | 이미지별 field match 평균. 일부 이미지에서 성능이 무너지는지 확인한다. |
| `field_match_ratio_micro` | 전체 field unit 기준 평균. production gate의 aggregate 품질을 본다. |
| `roi_merge_stats` | detector crop과 full-image fallback이 어떤 비율로 쓰였는지 확인한다. |
| detector `mAP50` / section recall | YOLO section detector가 OCR 대상 영역을 놓치지 않는지 확인한다. |

### full-image OCR vs ROI-scoped OCR 평가 차이

| 평가 방식 | 장점 | 한계 | gate 사용 |
| --- | --- | --- | --- |
| full-image OCR | detector 실패 시 baseline/fallback 품질을 볼 수 있다. | 라벨 외 텍스트가 섞여 structured extraction precision이 흔들릴 수 있다. | fallback coverage 확인 |
| ROI-scoped OCR | 성분표/주의사항/브랜드 등 section별 text-space를 줄인다. | YOLO box가 타이트하거나 섹션을 놓치면 OCR recall이 떨어진다. | primary promotion 기준 |
| detector ROI + full fallback | 실제 production flow와 가장 가깝다. | detector/OCR/extraction 병목을 함께 보기 때문에 원인 분석은 추가 breakdown이 필요하다. | 최종 structured gate |

### holdout/test split leakage 방지 규칙

- 같은 제품 SKU, 같은 라벨 이미지의 crop 변형, 같은 원본에서 파생된 synthetic/augmented line crop은 train/val/holdout을 넘나들 수 없다.
- teacher OCR로 생성한 pseudo label은 원본 이미지 단위 group id를 유지하고, 같은 group id는 하나의 split에만 배정한다.
- hyperparameter 선택에 사용한 validation split은 최종 holdout으로 재사용하지 않는다.
- holdout 결과는 threshold 통과 여부만 gate에 사용하고, 학습 재시도 방향 결정에는 실패 유형 요약만 사용한다.
- TODO: 현재 benchmark manifest에 product/SKU/group id가 없는 샘플이 있다면, split script에서 원본 파일 hash 또는 sanitized sample id 기반 group key를 추가한다.

## 3. 전체 Pipeline 설계

```text
input image
  -> YOLO section detection
  -> ROI crop + padding
  -> full-image OCR fallback branch
  -> PaddleOCR text extraction
  -> deterministic post-processing
  -> structured extraction
  -> Gemma4 verification/assist only when gated
  -> user confirmation for uncertain fields
  -> redacted metric logging
```

| 단계 | 입력 | 처리 | 출력 | 실패/fallback |
| --- | --- | --- | --- | --- |
| 1. 입력 이미지 | user image | EXIF orientation, format validation | normalized image handle | invalid image reject |
| 2. YOLO section detection | image | 영양제, 성분표, 주의사항, 알레르기, 브랜드/제품 영역 detection | section boxes + class + confidence | full-image OCR fallback |
| 3. ROI crop + padding | section boxes | 타이트 crop 방지를 위해 padding 적용 | ROI images | crop too small이면 full image 사용 |
| 4. full-image OCR fallback | image | PaddleOCR full image pass | fallback OCR text | OCR empty면 Gemma assist 후보 |
| 5. PaddleOCR text extraction | ROI images | `server_detection` + Korean recognizer 또는 custom rec model | section-scoped OCR lines | low confidence이면 assist 후보 |
| 6. deterministic post-processing | OCR lines | Unicode NFC, 공백, 단위, 괄호, mg/ug/IU 정규화 | normalized text | 원문 OCR payload 저장 금지 |
| 7. structured extraction | normalized text | field/ingredient parser | structured supplement fields | missing field는 review 후보 |
| 8. Gemma4 verification/assist | ROI image + OCR text + schema | 보이는 텍스트만 후보화/검증 | candidate fragments | 직접 final answer 저장 금지 |
| 9. user confirmation | uncertain fields | UI 또는 operator review | confirmed values | 미확정 값은 confidence 낮게 유지 |
| 10. metric logging | predictions + labels | numeric aggregate만 저장 | redacted JSON/Markdown | raw payload 저장 금지 |

## 4. 단계 A: 학습 전 Quick Wins

단계 A는 모델 학습 없이 detector/OCR runtime 설정, 전처리, ROI crop 정책, post-processing만 바꿔 같은 holdout에서 before/after를 비교한다.

### A1. PaddleOCR model profile

| 설정 | 권장 | 근거 |
| --- | --- | --- |
| `LOCAL_OCR_MODEL_PROFILE` | `server_detection` | repo provider에서 `server_detection`은 `PP-OCRv5_server_det` + `korean_PP-OCRv5_mobile_rec` 조합이다. |
| 금지 기본값 | `server` | repo provider에서 `server`는 recognition까지 `PP-OCRv5_server_rec`로 바꾼다. 공식 PaddleOCR 문서의 PP-OCRv5 server recognizer 설명은 중국어/번체/영어/일본어 중심이며, repo에는 한국어 mobile recognizer가 따로 있다. |

### A2. Detection input size and limit type

| 설정 | 후보값 | 공식/실험 구분 |
| --- | --- | --- |
| `LOCAL_OCR_TEXT_DET_LIMIT_TYPE` | `max` | PaddleOCR OCR result schema의 `text_det_params.limit_type`로 확인된다. |
| `LOCAL_OCR_TEXT_DET_LIMIT_SIDE_LEN` | `1280`, `1536` | 공식 문서의 단일 추천값이 아니라 프로젝트 실험 후보값이다. 반드시 grid 평가 후 채택한다. |

### A3. Detection threshold sweep

| 파라미터 | 현재 repo 상태 | 문서화 기준 |
| --- | --- | --- |
| `text_det_thresh` | `paddleocr_clova_eval.py`에는 CLI/sweep 배선이 있으나 runtime `paddle.py:_predict_kwargs`에는 아직 없다. | PaddleOCR OCR result schema에 `text_det_params.thresh`가 존재한다. runtime default 전환 전 `config.py` + `_predict_kwargs` wiring 필요. |
| `text_det_box_thresh` | eval script에는 존재, runtime provider에는 미배선 | PaddleOCR OCR result schema에 `box_thresh`가 존재한다. |
| `text_det_unclip_ratio` | eval script에는 존재, runtime provider에는 미배선 | PaddleOCR OCR result schema에 `unclip_ratio`가 존재한다. |
| `use_dilation` | 기존 계획 문서에는 후보로 있으나, 현재 확인한 PaddleOCR OCR usage 공식 문서에서 해당 parameter name을 찾지 못했다. | 공식 문서에서 확인 불가, 실험값으로만 채택 가능. source/API 재확인 전 production 기본값 금지. |

### A4. `label_enhance` preprocessing

| 항목 | 정책 |
| --- | --- |
| 목적 | 저대비, 작은 글자, 기울어진 라벨에서 detector/recognizer 입력 품질을 개선한다. |
| 후보 처리 | CLAHE, denoise, deskew, 조건부 upscale. |
| 금지 | 무조건 이진화, 원본 이미지 overwrite, raw OCR text debug dump. |
| 채택 조건 | 같은 holdout에서 ROI/full fallback structured metric과 line-level OCR metric을 모두 비교한다. |

TODO: `label_enhance`가 이미 runtime에 완전히 구현되어 있는지, 아니면 `local_ocr_preprocess_mode` enum만 존재하고 구현이 필요한지 별도 코드 확인 후 구현 티켓으로 분리한다.

### A5. ROI crop padding

| 정책 | 설명 |
| --- | --- |
| 기본 원칙 | YOLO box를 그대로 OCR에 넣지 말고 section별 padding을 둔다. |
| 후보값 | `max(12px, 0.12 * box_h)`는 기존 repo 계획의 실험 후보값이다. 공식 문서 추천값이 아니므로 holdout sweep으로만 채택한다. |
| 평가 | padding별 OCR empty rate, ingredient recall, field match를 함께 본다. |

### A6. 단위 정규화 post-pass

| 정규화 대상 | 예시 |
| --- | --- |
| Unicode | NFC normalization |
| 공백 | 중복 whitespace collapse |
| 단위 | `mg`, `MG`, `㎎`, `마이크로그램`, `ug`, `µg` normalized token |
| 숫자 | comma/period/전각 숫자 normalization |
| 괄호 | ingredient alias 또는 함량 단위 주변 괄호 normalization |

정규화는 OCR 원문을 바꾸는 학습 label 생성과 production structured extraction을 분리해야 한다. 학습 label은 별도 normalized label column을 둘 수 있지만, raw teacher payload를 운영 로그에 저장하면 안 된다.

### A7. before/after 평가 방법

```bash
# 1) PaddleOCR standalone quick-win sweep
.venv-paddle/bin/python backend/scripts/paddleocr_clova_eval.py \
  --manifest <redacted_eval_manifest.jsonl> \
  --output-dir outputs/generated/ocr-eval/<run-id> \
  --profile server \
  --max-side 1280 \
  --preprocess-mode label_enhance

# 2) Detector ROI + full fallback structured extraction
python backend/scripts/evaluate_detector_roi_full_fallback_structured_extraction.py \
  --eval-split holdout \
  --model <section-detector.pt> \
  --predicted-boxes-jsonl <redacted_predicted_boxes.jsonl> \
  --output-dir outputs/generated/ocr-eval/<run-id>
```

주의: `paddleocr_clova_eval.py`의 `--profile server`는 standalone script 내부에서 server detector + Korean mobile recognizer 조합을 뜻한다. runtime env에서는 `LOCAL_OCR_MODEL_PROFILE=server_detection`을 사용한다.

Requires human decision: 단계 A에서 절대 target을 바로 넘지 못했지만 metric이 개선될 경우, default 채택에 필요한 최소 개선폭을 별도 팀 gate로 정한다. 공식 문서 추천값이 아니므로 임의 개선폭을 문서에서 성능 보장처럼 쓰지 않는다.

## 5. 단계 B: PaddleOCR Recognition Fine-tuning

### B1. line crop dataset 설계

| Dataset field | 설명 |
| --- | --- |
| `image` | text line crop. 원본 이미지 전체가 아니라 OCR recognition 학습에 필요한 line crop만 사용한다. |
| `label` | human-confirmed 또는 teacher consensus text. PaddleOCR recognition format은 `image_path<TAB>text` 형태를 따른다. |
| `source_group_id` | 같은 제품/원본/augmentation이 split을 넘지 않도록 묶는 key. |
| `label_source` | `human`, `clova_google_consensus`, `synthetic`, `domain_corpus` 등. |
| `privacy_class` | 저장 가능 범위와 retention policy를 판단하는 내부 flag. |

PaddleOCR recognition training 문서는 `SimpleDataSet`, `rec_gt_train.txt`, `rec_gt_test.txt`, dictionary file을 사용한다. dictionary는 인식하려는 모든 문자를 포함하고 UTF-8로 저장해야 한다.

### B2. train/val/holdout split 기준

| Split | 사용 |
| --- | --- |
| train | model weight update |
| validation | LR/epoch/augmentation/model selection |
| holdout | 최종 gate. 학습, hyperparameter 선택, prompt 수정, post-processing rule tuning에 사용 금지 |

Leakage 방지 checklist:

- [ ] 같은 원본 이미지에서 생성된 crop/augmentation은 같은 split에만 있다.
- [ ] 같은 제품 SKU 또는 동일 라벨 디자인은 가능한 한 같은 split에만 있다.
- [ ] teacher consensus 실패 sample은 holdout label로 자동 승격하지 않는다.
- [ ] holdout 실패 sample을 보고 rule을 수정하면, 그 다음 gate에는 새 holdout 또는 freeze된 nested holdout을 사용한다.

### B3. 일반 한국어 corpus + 도메인 corpus 혼합

| Corpus | 목적 | 주의 |
| --- | --- | --- |
| 일반 한국어 OCR corpus | catastrophic forgetting 방지 | repo dictionary와 문자 범위가 맞는지 확인 |
| 도메인 line crop | 영양성분표, 브랜드, 주의사항, 알레르기 표기 recall 개선 | 제품명/성분명 편향과 leakage 방지 |
| synthetic corpus | 작은 글자/저대비/회전/압축 artifact 보강 | real holdout 성능으로만 채택 판단 |

공식 문서에서 혼합 비율, LR, epoch, batch에 대한 이 프로젝트 전용 추천값은 확인할 수 없다. 기존 repo 계획과 A100 실험값은 실험 후보일 뿐이며, gate 통과 전에는 성능 보장으로 쓰지 않는다.

### B4. dictionary 유지/확장 기준

| 기준 | 정책 |
| --- | --- |
| 기존 Korean dict | 기본 유지 |
| 영양제 특수 문자 | `µ`, `㎍`, `㎎`, `%`, `/`, `(`, `)`, `-`, `+`, `.` 등 실제 label에 반복 등장하는 문자만 추가 후보 |
| rare typo | OCR 오류를 dictionary에 추가하지 않는다. human-confirmed label 기준으로만 추가한다. |
| encoding | UTF-8 고정 |

### B5. training parameters 기록 정책

| 파라미터 | 문서화 방식 |
| --- | --- |
| LR | 공식 추천값으로 단정하지 않는다. repo 실험 config 값과 결과를 run metadata로 기록한다. |
| epoch | early-stop 기준과 함께 기록한다. |
| batch | GPU memory, throughput, convergence 결과와 함께 기록한다. |
| eval interval | metric curve 해상도와 early-stop 감도에 영향을 주므로 run metadata에 고정 기록한다. |
| augmentation | 어떤 augmentation을 켰는지, 왜 켰는지 기록한다. RecConAug 제거/유지는 holdout metric으로만 판단한다. |

### B6. export 후 runtime 연결

```bash
# fine-tuned recognition inference model을 runtime에 연결하는 target env
export OCR_PRIMARY_PROVIDER=paddleocr
export ENABLE_LOCAL_OCR=true
export LOCAL_OCR_MODEL_PROFILE=server_detection
export LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR=outputs/generated/supplement-learning/<run>/models/<inference-dir>
export LOCAL_OCR_TEXT_DET_LIMIT_TYPE=max
export LOCAL_OCR_TEXT_DET_LIMIT_SIDE_LEN=1280
```

주의: `LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR`는 inference export 산출물을 가리켜야 한다. checkpoint directory를 runtime에 직접 연결하지 않는다.

### B7. fine-tuned model promotion gate

```bash
python backend/scripts/gate_paddleocr_finetune_against_baseline.py \
  --task recognition \
  --baseline-summary <baseline_metrics.json> \
  --finetuned-summary <finetuned_metrics.json> \
  --min-metric acc=<team_threshold> \
  --min-metric norm_edit_dis=0.90 \
  --output outputs/generated/ocr-eval/<run-id>/recognition-gate.json
```

Promotion 조건:

- [ ] `norm_edit_dis >= 0.90`.
- [ ] `acc`는 baseline 이상이며, 팀이 정한 절대 하한을 통과한다.
- [ ] structured ROI/full fallback gate에서 `field_match >= 0.85`, `ingredient_recall >= 0.85`가 함께 통과한다.
- [ ] gate output에 raw OCR text, provider payload, local model absolute path가 저장되지 않는다.
- [ ] inference export hash와 config가 기록되어 reproducible하다.

## 6. 단계 C: 데이터/Teacher Distillation

### C1. CLOVA + Google Vision 합의 라벨링

| 단계 | 정책 |
| --- | --- |
| teacher 호출 | CLOVA OCR, Google Cloud Vision OCR을 동일 line crop 또는 ROI에 적용 |
| 합의 조건 | normalized text 기준 edit distance 또는 exact normalized match. epsilon은 실험값이므로 팀 결정 필요 |
| 채택 | 두 teacher가 합의하고 human spot-check를 통과한 line crop만 pseudo label로 채택 |
| 폐기 | teacher 간 불일치, low confidence, 개인정보 의심, 원본 보존 정책 위반 sample |

Google Cloud Vision 공식 문서는 `TEXT_DETECTION`과 dense document용 `DOCUMENT_TEXT_DETECTION`을 OCR feature로 제공한다. 이 문서는 teacher 후보로만 사용한다는 의미이며, Cloud Vision 결과가 정답이라는 뜻은 아니다.

Requires human decision: teacher 원문 보존 정책 예외가 필요한지 결정해야 한다. 현재 원칙은 provider payload/raw OCR text를 운영 산출물에 저장하지 않는 것이다. 학습 전용 접근통제 저장소에 제한 보존할 경우 retention 기간, 접근자, redaction 규칙을 별도 승인해야 한다.

### C2. StyleText/SynthTIGER/KoTDG 사용 가능성

| 도구/데이터 | 상태 |
| --- | --- |
| PaddleOCR data synthesis tools | 공식 문서에서 Text_renderer, SynthText, TextRecognitionDataGenerator, SynthText3D, UnrealText, SynthTIGER가 data synthesis 후보로 나열된다. |
| KoTDG | 한국어 OCR synthetic data 후보로 검토 가능하지만, 현재 이 문서에서 공식 추천값이나 성능 개선을 단정하지 않는다. |
| StyleText | PaddleOCR 계열 synthetic style transfer 후보로 검토 가능하나, 현재 확인한 최신 synthesis page에는 명시 목록으로 보이지 않는다. 사용 전 공식 repo/docs를 별도 확인한다. |

### C3. privacy/storage 제한

- [ ] raw OCR/provider payload를 `outputs/generated/...` gate output에 저장하지 않는다.
- [ ] 원본 이미지 absolute path를 metric output에 저장하지 않는다.
- [ ] teacher payload는 기본적으로 저장 금지다.
- [ ] 학습 label로 필요한 text만 최소화해서 저장하고, source/provider 원문 response는 폐기한다.
- [ ] human review 화면에는 필요한 crop과 label 후보만 노출하고, secret/API response를 노출하지 않는다.

## 7. Gemma4 Vision Assist 설계

### 호출 조건

Gemma4 assist는 다음 중 하나 이상이 true일 때만 실행한다.

- `ocr_text == ""` 또는 section OCR line count가 0.
- PaddleOCR confidence가 team threshold 아래.
- expected ingredient가 structured extraction에서 빠졌고, 성분표 ROI가 존재한다.
- 브랜드/제품명/주의사항/알레르기 field가 missing이고 해당 ROI가 존재한다.
- detector ROI와 full-image OCR이 서로 충돌해 verification이 필요하다.

### 입력 payload

```json
{
  "source_region": "yolo_roi",
  "roi_type": "supplement_facts",
  "ocr_text": "<redacted-or-in-memory-only>",
  "expected_schema": {
    "visible_text_fragments": ["string"],
    "possible_field": "string|null",
    "confidence": "0..1",
    "warnings": ["string"]
  },
  "instruction": "Only report text that is visible in the image. Do not infer hidden text."
}
```

저장 정책: payload는 in-memory request로만 사용한다. metric output에는 호출 여부, reason code, confidence bucket, accepted/rejected count만 redacted aggregate로 남긴다.

### 출력 제한

| 제한 | 이유 |
| --- | --- |
| 보이는 텍스트만 허용 | supplement label hallucination 방지 |
| confidence 필수 | user confirmation priority 산정 |
| JSON schema 강제 | downstream parser drift 방지 |
| final answer 직접 저장 금지 | OCR/structured extraction ground truth 오염 방지 |
| missing field 추측 금지 | 법/건강 관련 정보 오기입 방지 |

### MLX fine-tuning이 후순위인 이유

- Google 공식 MLX 문서는 Gemma4를 Apple Silicon에서 실행하고 `mlx_vlm.server`로 서빙하는 경로를 설명한다.
- Gemma4 vision fine-tuning 공식 가이드는 Hugging Face Transformers + QLoRA이며, L4/A100급 BF16 GPU와 16GB 초과 memory를 요구한다.
- 따라서 “Gemma4 vision을 MLX로 바로 fine-tuning”하는 것은 공식적으로 확인된 주력 경로가 아니며, 현재 목표 metric에는 PaddleOCR recognition/ROI 개선이 더 직접적이다.

### 향후 파일럿 조건

Gemma4 vision QLoRA 파일럿은 아래 조건을 모두 만족할 때만 시작한다.

- [ ] 단계 A/B 후에도 `field_match` 또는 `ingredient_recall`이 target에 도달하지 못한다.
- [ ] OCR failure taxonomy에서 VLM assist가 실제로 복구 가능한 case 비율이 충분하다.
- [ ] VLM output을 final answer가 아니라 후보/검증으로만 쓰는 adapter contract가 구현되어 있다.
- [ ] 같은 holdout gate에서 PaddleOCR-only, PaddleOCR+Gemma assist를 분리 비교한다.
- [ ] hallucination audit set을 통과한다.

## 8. PaddleOCR-VL / 대체 VLM 파일럿

### 언제 검토할지

| 조건 | 조치 |
| --- | --- |
| YOLO ROI + PaddleOCR fine-tune 후에도 작은 글자/복잡 레이아웃 누락이 반복 | PaddleOCR-VL provider 파일럿 검토 |
| ingredient table 구조가 OCR line sequence만으로 복원되지 않음 | layout-aware VLM pilot 검토 |
| Gemma4 assist가 자주 hallucination하거나 schema를 깨뜨림 | PaddleOCR-VL 또는 다른 document parsing model을 동일 gate에서 비교 |

### 비교 gate

| Provider | 비교 기준 |
| --- | --- |
| PaddleOCR baseline | 현재 production 후보 |
| PaddleOCR + fine-tuned rec | 단계 B 후보 |
| PaddleOCR + Gemma4 assist | gated assist 후보 |
| PaddleOCR-VL pilot | 동일 holdout, 동일 structured extraction schema, 동일 privacy rules |

모든 provider는 같은 `field_match`, `ingredient_recall`, `norm_edit_dis` 또는 provider별 대응 metric, latency, GPU memory, hallucination audit로 비교한다.

### GPU/Apple Silicon/serving 제약

PaddleOCR-VL 공식 문서는 full pipeline 사용을 강조하며, VLM component만 직접 호출하는 것은 공식 pipeline과 다르다고 설명한다. NVIDIA GPU inference는 CUDA/compute capability 제약이 있고, A100은 문서상 vLLM/FastDeploy류 요구 조건에 포함되는 CC >= 8 계열이다. Apple Silicon은 MLX-VLM 조합 지원 matrix가 별도로 표시된다.

### hallucination 방지 조건

- [ ] full PaddleOCR-VL pipeline과 VLM component 단독 호출을 혼동하지 않는다.
- [ ] VLM output은 OCR 대체 정답이 아니라 candidate provider output으로만 저장한다.
- [ ] 보이지 않는 성분/함량을 생성한 sample은 hard fail로 기록한다.
- [ ] raw image/provider payload 저장 금지 정책을 유지한다.

## 9. 실행 Runbook

### 9.1 순서

| 순서 | 담당 | 명령/산출물 | 통과 기준 |
| ---: | --- | --- | --- |
| 1 | YOLO 담당 | section detector train/eval | detector gate 통과 |
| 2 | QA/eval 담당 | ROI/full fallback structured eval | baseline metric freeze |
| 3 | OCR 담당 | PaddleOCR quick-win sweep | no regression + target 접근 |
| 4 | OCR 담당 | recognition fine-tuning/export | `norm_edit_dis >= 0.90` gate |
| 5 | backend 담당 | `LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR` 연결 | runtime smoke + redacted output |
| 6 | VLM 담당 | Gemma4 assist gated eval | hallucination audit 통과 |
| 7 | 팀 리드 | production default 전환 심사 | primary gates 통과 |

### 9.2 detector gate

```bash
python backend/scripts/gate_supplement_section_detector_metrics.py \
  --summary <detector_eval_summary.json> \
  --output outputs/generated/ocr-eval/<run-id>/detector-gate.json
```

현재 script default:

| Gate | Default |
| --- | ---: |
| `min_map50` | `0.70` |
| `min_ingredient_recall` | `0.85` |
| `min_supplement_facts_recall` | `0.85` |
| `min_key_class_recall` | `0.65` |

### 9.3 ROI/full fallback structured eval

```bash
python backend/scripts/evaluate_detector_roi_full_fallback_structured_extraction.py \
  --eval-split holdout \
  --model <section-detector.pt> \
  --predicted-boxes-jsonl <redacted_predicted_boxes.jsonl> \
  --output-dir outputs/generated/ocr-eval/<run-id>
```

산출물 요구:

- [ ] `evaluation_mode == detector_roi_full_fallback`.
- [ ] `field_match_ratio_macro`, `field_match_ratio_micro`, `ingredient_recall` 포함.
- [ ] `roi_merge_stats` 포함.
- [ ] `raw_ocr_text_stored == false` 또는 동등한 privacy flag.
- [ ] `provider_payloads_stored == false` 또는 동등한 privacy flag.
- [ ] `absolute_paths_stored == false`.

### 9.4 PaddleOCR recognition export and gate

```bash
# export 완료 후 inference dir만 runtime 후보로 사용
python backend/scripts/gate_paddleocr_finetune_against_baseline.py \
  --task recognition \
  --baseline-summary <baseline_rec_metrics.json> \
  --finetuned-summary <finetuned_rec_metrics.json> \
  --min-metric acc=<team_threshold> \
  --min-metric norm_edit_dis=0.90 \
  --output outputs/generated/ocr-eval/<run-id>/paddle-rec-gate.json
```

### 9.5 Gemma4 assist gated eval

```bash
ENABLE_MULTIMODAL_LLM=true \
ENABLE_MULTIMODAL_VERIFICATION=true \
MULTIMODAL_OCR_ASSIST_POLICY=low_confidence \
OLLAMA_VISION_MODEL=gemma4:e4b \
python backend/scripts/evaluate_detector_roi_full_fallback_structured_extraction.py \
  --eval-split holdout \
  --model <section-detector.pt> \
  --predicted-boxes-jsonl <redacted_predicted_boxes.jsonl> \
  --output-dir outputs/generated/ocr-eval/<run-id>-gemma-assist
```

TODO: 현재 structured eval script가 Gemma4 assist를 직접 비교하는 옵션을 제공하는지 확인한다. 미지원이면 별도 pilot provider/eval harness를 추가하되, output privacy contract는 동일하게 유지한다.

### 9.6 실패 시 rollback/fallback

| 실패 | rollback/fallback |
| --- | --- |
| detector gate fail | previous detector 유지, full-image OCR fallback 유지 |
| quick-win setting regression | env default를 이전 값으로 되돌리고 sweep 결과만 보관 |
| fine-tuned rec gate fail | `LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR` unset, baseline recognizer 유지 |
| Gemma assist hallucination fail | `MULTIMODAL_OCR_ASSIST_POLICY=disabled`, verification only 또는 완전 비활성화 |
| production metric regression | `OCR_PRIMARY_PROVIDER` 이전 provider로 rollback, PaddleOCR는 shadow eval로 강등 |

## 10. 팀 작업 분장

| 역할 | 책임 | 산출물 |
| --- | --- | --- |
| YOLO 담당 | section class 정의, train/eval, detector threshold, ROI padding 후보 제공 | detector weights, redacted detector summary, predicted boxes JSONL |
| OCR 튜닝 담당 | PaddleOCR profile/sweep, recognition fine-tuning, export, gate | OCR sweep summary, inference model dir, recognition gate JSON |
| 데이터/라벨링 담당 | line crop dataset, teacher consensus, human review, split leakage 방지 | sanitized manifest, split report, label QA report |
| backend integration 담당 | env/config wiring, provider fallback, Gemma assist adapter contract | runtime config PR, smoke test output, rollback plan |
| QA/eval 담당 | holdout freeze, metric scripts 실행, privacy 검증, release gate | structured eval report, gate decision log |

## 11. 의사결정 Gate

### Gate A: Quick Wins 채택

| 조건 | 결정 |
| --- | --- |
| `field_match`/`ingredient_recall` no regression | 후보 유지 |
| OCR empty rate 감소 | 후보 유지 |
| latency/memory가 production budget 초과 | reject 또는 shadow only |
| 공식 문서 확인 불가 parameter 사용 | experiment only, default 금지 |

Requires human decision: target 미달 상태에서 quick-win default를 채택할 최소 개선폭을 정한다.

### Gate B: fine-tuned model promotion

| 조건 | 결정 |
| --- | --- |
| `norm_edit_dis >= 0.90` | recognition 후보 가능 |
| baseline 대비 `acc`, `norm_edit_dis` 모두 개선 | 후보 가능 |
| structured eval에서 `field_match >= 0.85`, `ingredient_recall >= 0.85` 미달 | production default 금지 |
| checkpoint만 있고 inference export 없음 | runtime 연결 금지 |

### Gate C: Gemma4 assist enable

| 조건 | 결정 |
| --- | --- |
| OCR empty/low-confidence/field missing case에서만 호출 | enable 후보 |
| hallucination audit fail | disabled |
| output이 schema를 벗어남 | reject |
| final answer 직접 저장 경로 존재 | release blocker |

### Gate D: production default 전환

모두 만족해야 한다.

- [ ] detector gate 통과.
- [ ] `field_match_ratio_macro >= 0.85` and `field_match_ratio_micro >= 0.85`.
- [ ] `ingredient_recall >= 0.85`.
- [ ] recognition fine-tune 사용 시 `norm_edit_dis >= 0.90`.
- [ ] privacy flags pass: raw OCR/provider payload/absolute private image path 저장 없음.
- [ ] rollback env가 문서화되어 있다.
- [ ] shadow run 또는 canary에서 regression 없음.

## Appendix: Current A100 Candidate

이 후보는 현재 가져온 b32 early-stop best recognition model이다. production pass가 아니라 recognition 후보 evidence로만 기록한다.

| 항목 | 값 |
| --- | --- |
| run suffix | `v2_png_sanitized_mixed_lr5e5_b32_fixedscale48_noshm_stage3dict_eval100_nometric_noguard_20260611` |
| early-stop action | `stopped` |
| checked at | `2026-06-12T17:34:23.5226334+09:00` |
| latest eval epoch | `17` |
| latest eval acc | `0.83069248704417187` |
| latest eval norm_edit_dis | `0.89068241831183492` |
| best epoch | `7` |
| best acc | `0.843163144302871` |
| best norm_edit_dis | `0.90131779592271266` |
| stale/patience | `10 / 10` |

| Artifact | Repo-relative path | SHA-256 |
| --- | --- | --- |
| inference model | `outputs/generated/supplement-learning/2026-06-05/operator-review/models/supplement_rec_crawling_v2_png_sanitized_mixed_lr5e5_b32_20260611_best_accuracy_inference/inference.pdiparams` | `0c21084793f2e2dd9b1099de66d9401bbc5b93635e6f35c22bfd100a04db9b3f` |
| checkpoint | `outputs/generated/supplement-learning/2026-06-05/operator-review/models/supplement_rec_crawling_v2_png_sanitized_mixed_lr5e5_b32_20260611_best_accuracy_checkpoint/best_accuracy.pdparams` | `6fc03d0bff1901600cc637ab8cf55974fa10085058efa42dbf02f7d0c28fad3d` |

Promotion 상태:

- [x] inference export 존재.
- [x] `norm_edit_dis >= 0.90` recognition 후보 조건은 best checkpoint 기준 충족.
- [ ] `field_match >= 0.85` structured gate 미실행/미확정.
- [ ] `ingredient_recall >= 0.85` structured gate 미실행/미확정.
- [ ] production default 전환 미승인.

## References

공식 문서 또는 논문에서 확인한 내용만 기술 근거로 사용한다. 공식 문서에서 확인할 수 없는 값은 실험 후보로만 표시한다.

| 주제 | URL | 사용 근거 |
| --- | --- | --- |
| PaddleOCR General OCR Pipeline | https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html | OCR pipeline module, PP-OCRv5/v6 detector/recognizer model list, `text_det_params.limit_side_len`, `limit_type`, `thresh`, `box_thresh`, `unclip_ratio`, `text_rec_score_thresh` 확인 |
| PaddleOCR Recognition Training | https://www.paddleocr.ai/latest/en/version2.x/ppocr/model_train/recognition.html | `SimpleDataSet`, `rec_gt_train.txt`, `rec_gt_test.txt`, dictionary UTF-8/character coverage 규칙 |
| Ultralytics YOLO Train | https://docs.ultralytics.com/modes/train/ | YOLO train settings, checkpoint, early stopping, `imgsz`, `batch` 등 training 설정 |
| Ultralytics YOLO Predict | https://docs.ultralytics.com/modes/predict/ | prediction result, `save_crop`, image input handling |
| Gemma overview | https://ai.google.dev/gemma/docs | Gemma4 text/audio/image input, tuning guide 목록 |
| Gemma4 model card | https://ai.google.dev/gemma/docs/core/model_card_4 | Gemma4 multimodal input, model sizes, context window, deployment profile |
| Gemma with MLX | https://ai.google.dev/gemma/docs/integrations/mlx | MLX/MLX-VLM run/server integration 확인. MLX vision fine-tuning 추천 문서는 확인하지 못함 |
| Gemma vision QLoRA | https://ai.google.dev/gemma/docs/core/huggingface_vision_finetune_qlora | Gemma vision task fine-tuning 공식 경로, HF Transformers + QLoRA, L4/A100/BF16 GPU 조건 |
| Gemma with Ollama | https://ai.google.dev/gemma/docs/integrations/ollama | `gemma4:e2b`, `gemma4:e4b`, image input, API image payload, tuned model GGUF conversion 경로 |
| Ollama Gemma4 model page | https://ollama.com/library/gemma4 | Ollama model tag 확인 보조 |
| PaddleOCR-VL usage | https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/PaddleOCR-VL.html | PaddleOCR-VL full pipeline, hardware support matrix, A100/CUDA 조건, hallucination 방지 주의 |
| PaddleOCR-VL paper | https://arxiv.org/abs/2510.14528 | PaddleOCR-VL 논문 식별 및 academic reference |
| Google Cloud Vision OCR | https://cloud.google.com/vision/docs/ocr | `TEXT_DETECTION`, `DOCUMENT_TEXT_DETECTION` OCR feature 확인 |
| PaddleOCR data synthesis tools | https://www.paddleocr.ai/latest/en/data_anno_synth/data_synthesis.html | Text_renderer, SynthText, TextRecognitionDataGenerator, SynthText3D, UnrealText, SynthTIGER 후보 확인 |

## Implementation TODOs

- TODO: `text_det_thresh`, `text_det_box_thresh`, `text_det_unclip_ratio`를 runtime env/config와 `paddle.py:_predict_kwargs`에 노출하는 별도 구현 티켓을 만든다.
- TODO: `use_dilation`은 공식 문서/API/source에서 parameter name을 재검증하기 전까지 default 후보에서 제외한다.
- TODO: Gemma4 assist를 structured eval에서 PaddleOCR-only와 나란히 비교하는 harness가 있는지 확인한다.
- TODO: teacher raw text 저장 예외가 필요한 경우 보안/개인정보 승인 문서를 먼저 만든다.
- Requires human decision: quick-win default 채택 최소 개선폭.
- Requires human decision: teacher consensus epsilon.
- Requires human decision: recognition `acc` 절대 하한.
