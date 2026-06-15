# PaddleOCR 성능 개선 계획 (Lemon-Aid 영양제 라벨 OCR)

> 작성일: 2026-06-09
> 목표: PaddleOCR을 CLOVA를 대체할 수 있는 **1순위(primary) OCR**로 끌어올린다.
> 근거: 코드 매핑 + 웹 리서치(PP-OCRv5 공식 문서, HF 모델 카드, 2024–2025 논문/이슈) + 적대적 검증.
> 동반 문서: 구현 평가는 [`2026-06-09-pipeline-implementation-evaluation-v2.md`](./2026-06-09-pipeline-implementation-evaluation-v2.md).

---

## 0. 한눈에 보는 결론 (Executive Summary)

PaddleOCR이 "매우 안 좋게" 보이는 진짜 원인은 **recognizer 모델의 한계가 아니다.** 리서치·측정·코드 근거가 모두 같은 곳을 가리킨다:

1. **지표가 깨져 있다.** 현재 0.95 char-LCS 게이트는 *전체 이미지 OCR을 섹션 한정 GT로 채점*하기 때문에 precision이 구조적으로 ~0.30에 갇혀, recognizer를 아무리 키워도 F1 상한이 ≈0.68–0.71이다. → **먼저 지표를 고쳐야 한다.**
2. **공짜/저비용 레버를 안 썼다.** 검출 프로파일 교체, 입력 해상도 상향, 전처리(CLAHE+조건부 업스케일), ROI 텍스트-공간 스코핑은 **학습 없이** 며칠 안에 적용 가능하고 효과가 크다.
3. **학습은 마지막 수단인데 먼저 했고, 그마저 레시피가 어긋났다.** 합성 2-epoch CPU 파인튜닝이 catastrophic forgetting(0.518→0.037)을 냈다 — 일반 데이터 미혼합 + 과한 LR + 사전(dict) 변경이라는 교과서적 실패.

> 핵심 한 줄: **"학습으로 모델을 키우기" 전에, "지표를 고치고(메트릭) → 켜고(설정) → 잘라서 넣고(ROI/전처리) → 그 다음에 도메인 파인튜닝"** 순서로 간다.

또한 강조: PaddleOCR은 한국어 오픈 엔진 중 최선이다(2025 벤치마크에서 EasyOCR·Tesseract 대비 우위). 한국어 모델이 *없어서* 약한 게 아니다 — 이미 최강인 `korean_PP-OCRv5_mobile_rec`(88.0% line-acc)를 쓰고 있다.

---

## 1. 현황 진단 (Root-Cause)

### 1.1 현재 PaddleOCR 구성 (코드 확인)
- 엔진: PaddleOCR 3.x / PP-OCRv5 `predict()` API (`paddle.py`), `paddlepaddle==3.2.0`, `paddleocr>=3.6,<3.7`.
- 모델: det=`PP-OCRv5_mobile_det`, rec=`korean_PP-OCRv5_mobile_rec`, `lang='korean'`, profile=`mobile`.
- 전처리: `autocontrast`(EXIF + RGB + autocontrast + `thumbnail(2048)` + PNG 재인코딩). **이진화·기울기보정·업스케일 없음.**
- predict 노브: `text_det_limit_side_len / limit_type / rec_score_thresh` 3개만, 전부 기본 None → 상류 기본값 사용.
- 방향: `use_textline_orientation=False`; `use_doc_orientation_classify/unwarping`은 **하드코딩 False**.
- 런타임: `.env`가 `OCR_PRIMARY_PROVIDER="clova"`로 PaddleOCR을 **요청 경로에서 제외**.

### 1.2 저성능 root-cause 가설 (우선순위 순)

| # | 가설 | 근거 | 성격 |
|---|---|---|---|
| R1 | **채점 지표가 구조적으로 막혀 있음** — 섹션-only GT vs 전체-이미지 OCR → precision ≤ ~0.30, F1 상한 ≈0.68–0.71 | `2026-06-08-text-f1-improvement-design.md`; 203장 중 57%가 precision<0.30 | 지표/평가 |
| R2 | **모바일 det + 저해상도 입력** — `limit_type='min', side_len=64`라 작은 크롭이 확대조차 안 됨 | PP-OCRv5 det 기본값, `paddle.py` predict 노브 미설정 | 검출 |
| R3 | **전처리 부재** — glossy/저대비/기울기/곡면 라벨을 보정 못 함; 작은 글자 업스케일 불가 | `preprocessing.py` autocontrast+축소만 | 전처리 |
| R4 | **rec 입력 높이 48px 고정** — 텍스트 높이 <24px면 사실상 빈 크롭을 인식 | PP-OCRv5 `rec_image_shape=[3,48,320]` (Issue #14109) | 인식 |
| R5 | **ROI 미적용** — 전체 이미지를 통째로 OCR → 잡음/과독(over-read) | ROI 크롭 게이트 비활성 | 스코핑 |
| R6 | **도메인 토큰 미세 실패** — `μg/㎍/IU/%/·` 등 단위가 dict 누락 시 line 실패 | `korean_dict.txt` 특수기호 미보장 | 인식(도메인) |
| R7 | **실사진 품질** — 각도/곡면/반사가 CER 38%의 주원인(모델 한계 아님) | `v3/final_summary.md` | 입력 |

> R1·R5가 "전략", R2·R3·R4가 "값싼 즉효", R6·R7이 "도메인 학습/품질"이다. 비싼 recognizer 재학습은 R6를 위한 것이지 R1~R5를 못 고친다.

---

## 1.5 실행 환경 제약 (env-split) — 벤치마크·학습을 어디서 돌리나 ⚙️

> 이 절은 모든 단계(A/B/C)의 "어디서 실행하는가"를 규정한다. **메인 백엔드 venv에서는 PaddleOCR을 돌릴 수 없다** — 검증 완료된 하드 제약이다.

### 1.5.1 현실 (2026-06-10 직접 검증)

| 환경 | Python | PaddleOCR | 비고 |
|---|---|---|---|
| **`.venv`** (메인 백엔드) | 3.13.7 | ❌ **설치 불가** | `import paddleocr` → `ModuleNotFoundError`. macOS arm64 + py3.13용 paddlepaddle 휠 부재 |
| **`.venv-paddle`** (전용) | 3.12.13 | ✅ paddleocr 3.6.0 / paddlepaddle 3.3.1 | CPU 전용 (`is_compiled_with_cuda()=False`) |
| **Docker 프로덕션** | 3.13-slim (linux) | ✅ `INSTALL_LOCAL_OCR=true` 시 in-image 설치 | linux x86_64 py3.13 휠 존재 → 인프로세스 동작 가능 |
| **A100 원격(Windows)** | py3.12 `.venv-paddle-rec-v2-clean` | ✅ paddlepaddle-GPU 3.2.2 | 학습 전용 (CUDA) |

근거: `docs/handoff/2026-06-06-clova-gt-paddleocr-prompt.md:45` ("env-split 절대 위반 금지: paddle은 `.venv-paddle`(py3.12)에만, backend `.venv`(py3.13)에는 설치 불가"), `backend/Dockerfile:1,35-36`, `backend/.venv-paddle/` import 테스트.

### 1.5.2 운영 규칙

- **로컬 PaddleOCR 실행/벤치마크는 `.venv-paddle`(py3.12) 또는 A100에서만.** 메인 백엔드(`.venv` py3.13)에서 paddle을 import하면 `paddle.py:158-163`이 `OCRError("PaddleOCR is not installed. Install backend .[ocr-local].")`로 실패한다(앱 전체는 안 죽고 해당 provider만 실패 → 이것이 Mac에서 `OCR_PRIMARY_PROVIDER=clova`인 의존성 차원의 이유).
- **단계 A 벤치(server_detection / det 노브 / `label_enhance` 전처리)**: `paddleocr_clova_eval.py`, `build_supplement_benchmark_v2_candidate_pool.py` 등 standalone 스크립트를 `.venv-paddle`로 실행 → JSONL 관측치 → `merge_paddleocr_text_observations_into_benchmark`(py3.13 backend)로 병합. 즉 **paddle 실행(3.12)과 평가 집계(3.13)는 프로세스가 분리**되어 있다.
- **단계 B/C 학습**: A100(`run_a100_paddleocr_windows_training.ps1`, py3.12 + CUDA)에서. CPU에서의 server det은 ~4.3s/img로 느리므로 대량 벤치/학습은 CPU에서 돌리지 말 것.
- **프로덕션 승격(`OCR_PRIMARY_PROVIDER=paddleocr`) 전 체크**: ① Docker 이미지가 `INSTALL_LOCAL_OCR=true`로 빌드됐는지, ② `preload_paddleocr.py`로 모델 캐시가 프리워밍됐는지(`PRELOAD_PADDLEOCR=true`), ③ 파인튜닝 모델 dir(`LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR`)이 이미지/볼륨에 포함됐는지.

### 1.5.3 버전 드리프트 (통일 권장)

| 위치 | paddlepaddle | paddleocr |
|---|---|---|
| `pyproject.toml` `ocr-local` 핀 | **3.2.0** | >=3.6,<3.7 |
| 로컬 `.venv-paddle` | **3.3.1** | 3.6.0 |
| A100 원격 | **3.2.2** (GPU) | 3.6.0 |
| Dockerfile 설치 | **3.2.0** | >=3.6,<3.7 |

→ 4곳의 paddlepaddle 버전이 제각각이다. 인식 결과·전처리 동작이 버전에 따라 미세하게 달라질 수 있으므로, **평가→학습→프로덕션 전 구간의 paddlepaddle/paddleocr 버전을 한 쌍으로 고정**(예: 학습에 쓴 버전을 Dockerfile·pyproject 핀에 그대로 반영)한 뒤 게이트를 측정해야 재현성이 보장된다.

---

## 2. 개선 로드맵 (3단계)

### 단계 A — Quick Wins: 학습 無, 설정·전처리만 (목표 1주)

> 코드 변경 최소, 환경변수/소량 패치로 측정 가능한 정확도 상승. **모든 항목은 기존 평가 하니스로 before/after를 잰 뒤 채택.**

| ID | 작업 | 방법 | 예상 효과 | 난이도 |
|---|---|---|---|---|
| A1 | **지표 재정의 (최우선)** | 0.95 char-LCS precision 게이트 폐기 → ROI/recall 기반 + 실사진 line-level CER로 전환 (3절·7절) | 도달 가능 목표 확보, 의사결정 정상화 | 낮음 |
| A2 | **검출 프로파일 server_detection** | `LOCAL_OCR_MODEL_PROFILE=server_detection` (server det + **한국어 mobile rec 유지**) | 인쇄 텍스트 검출 HMean 0.770→0.92+ | 낮음 |
| A3 | **검출 입력 해상도 상향** | `LOCAL_OCR_TEXT_DET_LIMIT_TYPE=max`, `LOCAL_OCR_TEXT_DET_LIMIT_SIDE_LEN=1280`(필요시 1536) | 작은 행 누락 감소 | 낮음 |
| A4 | **det 임계값 노브 배선 + 튜닝** | `_predict_kwargs`에 `text_det_thresh/box_thresh/unclip_ratio/use_dilation` 추가, sweep | 조밀·흐린 행 recall↑ | 중간 |
| A5 | **전처리 모드 `label_enhance` 추가** | CLAHE + 조건부 업스케일(텍스트 높이<32px) + deskew, 이진화 금지, `max_side_px` 2048→3000 | 저대비/작은 글자/기울기 보정 | 중간 |
| A6 | **ROI 크롭 패딩** | YOLO/레이아웃 박스에 8–15% 패딩 후 크롭(가장자리 글자 잘림 방지, Issue #15603 회피) | 숫자/단위 끝자리 보존 | 낮음 |
| A7 | **단위 정규화 post-processor** | `ug→μg, mcg→μg, lU/Iu→IU, 숫자 내 O→0` 결정론적 후처리 | 다운스트림 파싱 정확도↑ | 낮음 |

**왜 server_detection이고 server가 아닌가 (검증된 함정):**
한국어 **server recognizer는 존재하지 않는다.** `server` 프로파일은 rec을 비한국어 `PP-OCRv5_server_rec`로 바꿔 **한국어 정확도를 떨어뜨린다.** 반드시 `server_detection`(server det + `korean_PP-OCRv5_mobile_rec` 유지)을 쓴다. (코드상 `_text_detection_model_name`은 `server_detection`/`server`에서 server det을 주지만 `_text_recognition_model_name`은 `server`일 때만 rec을 교체함 → `server_detection`이 정확히 원하는 조합.)

> ⚠️ Apple Silicon에는 CUDA/MPS가 없어(`v3/gpu_acceleration_assessment.md`) server det이 CPU에서 느리다(~4.3s/img). A1~A7 벤치는 A100/CUDA 박스나 배치 평가로 돌리고, 운영 지연이 문제면 `limit_side_len`을 1280으로 캡한다.

---

### 단계 B — 도메인 파인튜닝: recognizer(+det) (목표 2–4주, A100)

> A 단계로도 CLOVA에 못 미치면, **올바른 레시피로** 한국어 rec을 도메인 파인튜닝한다. 기존 catastrophic-forgetting을 막는 것이 핵심.

| ID | 작업 | 핵심 포인트 |
|---|---|---|
| B1 | LR 정상화 | 기존 5e-4 → 파인튜닝 권장 **piecewise [1e-4, 2e-5]** (bs=128). 사전학습 표현 파괴 방지 |
| B2 | 일반:도메인 1:1 혼합 | `label_file_list=[domain, general]`, `ratio_list=[1.0, 0.1]`(general이 ~10배일 때) → forgetting 방지 |
| B3 | dict 유지 우선 | 가능하면 `korean_dict.txt` 그대로(변경 시 초기 acc=0). 단위 기호가 정말 필요하면 최소 확장(5절 참조) |
| B4 | 증강 조정 | 깨끗한 크롭이면 `RecConAug` 제거, `RecAug` 유지(GTC/SAR 과적합 방지) |
| B5 | 충분한 epoch + best by acc | eval every 500 iters, acc 기준 best 저장. 초반 backbone 일부 freeze 고려 |
| B6 | inference export + 런타임 연결 | `export_model.py` → `LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR` 지정 → `ENABLE_LOCAL_OCR=true` |
| B7 | (선택) det 파인튜닝 | 라벨 행 분리가 나쁘면 det도 (>=500장, lr~1e-4, bs=8). 단 `paddle.py`에 `text_detection_model_dir` kwarg 추가 필요 |

**기존 인프라 재사용:** `run_a100_paddleocr_windows_training.ps1`(korean rec yml 해석 + 사전학습 다운로드 + train + export), `run_paddleocr_finetune_plan.py`, `materialize_paddleocr_dataset.py`, `register/promote_*`가 이미 갖춰져 있다. **새로 만들 게 아니라 LR/혼합/증강만 바로잡아 재실행.**

---

### 단계 C — 데이터·증류 파이프라인 (전략, 4주+)

> 파라미터·일반 파인튜닝이 정체되면 데이터 품질로 천장을 올린다.

| ID | 작업 | 핵심 포인트 |
|---|---|---|
| C1 | **Teacher 증류 라벨링** | CLOVA + Google Vision로 실사진 line-crop을 자동 전사 → **두 teacher가 합의(정규화 edit-distance ≤ ε)한 것만** 채택 → rec 학습셋. 기존 `TEACHER_PROVIDERS={clova, google_vision}` 재사용. ⚠️ 현재 redaction이 teacher 원문을 지워 candidate 0건 → **학습 전용·접근통제 저장소에서 teacher 원문 보존**(사용자에 미노출, 모델 아티팩트)하는 정책 예외 필요 |
| C2 | **StyleText 스타일 합성** | 실제 라벨 크롭의 폰트/배경/질감을 학습해 우리 코퍼스를 그 스타일로 재렌더 → sim-to-real 간극 해소(현재 PIL 폰트-온-화이트의 약점) |
| C3 | **SynthTIGER / KoTDG** | NAVER SynthTIGER(한국어 6M 학습 검증)로 배경/블러/노이즈/롱테일 균형 합성. 희귀 단위 토큰 오버샘플 |
| C4 | **도메인 코퍼스/렉시콘** | DB 카탈로그에서 성분 표기명·함량+단위 패턴·섭취 문구를 line corpus로 추출 → 합성/스타일 입력 + dict 커버리지 점검 |
| C5 | (선택) **CML 지식 증류** | 평문 파인튜닝이 baseline을 넘은 뒤, CML(frozen teacher + 상호학습 student 2)로 +3–5% |
| C6 | (선택) **VLM OCR 파일럿** | 정체 시 `PaddleOCR-VL-0.9B`(한국어 edit-distance 0.052, OmniDocBench 1위) 또는 surya를 factory에 GPU 한정 provider로 추가, 동일 게이트로 비교 |

---

## 3. 지표·게이팅 재정의 (가장 중요 — 먼저 한다)

**문제:** 현재 게이트는 *전체-이미지 OCR을 섹션-only GT로 char-LCS 채점* → precision ≤ ~0.30, **F1 0.90/0.95는 수학적으로 불가능**. (검증: 203장 중 57% precision<0.30; recognizer-only 상한 ≈0.68–0.71)

**해결 — 3가지 지표로 분리:**
1. **Recall 중심 char-LCS** (전체-이미지일 때): precision 게이트 폐기, recall + field_match_ratio로 판정.
2. **ROI 스코핑 후 precision 회복**: 텍스트-공간 스코핑(`src/parsing/layout_parser.py:218 parse_label_layout`) 또는 이미지-공간 ROI로 *섹션에 해당하는 텍스트만* 채점 대상으로 한정. 설계 문서가 **무학습으로 F1 0.33→0.50–0.63** 예측 — 그런데 아직 미실행. **이걸 단계 A에서 먼저 측정한다.**
3. **실사진 line-level CER/acc**: teacher line-crop으로 `tools/eval.py`의 `acc`(완전일치) + `norm_edit_dis`(=1−CER) 측정. 채점 전 Unicode NFC·공백·단위 케이싱 정규화.

**승격 게이트(기존 `gate_paddleocr_*` 재사용):**
> 파인튜닝 모델이 **holdout 52(실사진, 학습/HP선택에 절대 미사용)**에서 baseline을 *모든* 필수 지표에서 이기고 **절대 하한**(예: field_match_ratio ≥ 0.85 AND norm_edit_dis ≥ 0.90)을 통과할 때만 `OCR_PRIMARY_PROVIDER=paddleocr`로 전환. **LCS precision 게이트로는 판정하지 않는다.**

---

## 4. 엔진·모델 선택 (구체 인자)

| 항목 | 권장 | 비고 |
|---|---|---|
| 엔진 버전 | PP-OCRv5 / PaddleOCR 3.x | 이미 적용됨(유지). v4/v3는 파인튜닝 base로만 |
| 검출 모델 | `PP-OCRv5_server_det` | 인쇄 텍스트 HMean 0.945(ch)/0.917(en). `server_detection` 프로파일로 |
| 인식 모델 | `korean_PP-OCRv5_mobile_rec` **유지** | 한국어 88.0%. **server rec로 바꾸지 말 것**(한국어 비특화) |
| profile | `server_detection` | server det + korean mobile rec 조합 |
| lang | `korean` | 유지 |
| 방향/언랩 | textline_orientation OFF 유지; doc_unwarp는 **곡면 크롭 한정** 선택적 ON | 현재 하드코딩 False → 설정 플래그로 승격 필요(B/C) |
| StructureV3 | **불채택** | 크롭-섹션 OCR엔 과함. 일반 OCR 파이프라인 유지 |

```python
# 목표 런타임 구성 (server_detection + 한국어 mobile rec)
PaddleOCR(
    lang="korean",
    text_detection_model_name="PP-OCRv5_server_det",
    text_recognition_model_name="korean_PP-OCRv5_mobile_rec",
    text_recognition_model_dir=<파인튜닝 후 export dir 또는 None>,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,      # 곡면 크롭만 선택적 True
    use_textline_orientation=False,
)
# predict 시: text_det_limit_type="max", text_det_limit_side_len=1280,
#            text_det_box_thresh=0.45, text_det_unclip_ratio=2.0,
#            text_det_thresh=0.2, use_dilation=True, text_rec_score_thresh=0.0
```

---

## 5. 전처리 파이프라인 설계 (구체 값)

**권장 순서 (`label_enhance` 신규 모드):**
1. EXIF transpose → 2. grayscale → 3. **CLAHE**(`clipLimit≈2.5, tileGridSize=(8,8)`) → 4. light denoise(`fastNlMeansDenoising h≈7`) → 5. **deskew**(텍스트 마스크 `minAreaRect`, |각도|>0.5°면 회전) → 6. (필요시) perspective 보정 → 7. **조건부 업스케일**(중앙값 텍스트 높이<32px면 `INTER_CUBIC` 2x 또는 ESPCN x2) → 8. **이진화 금지**(DB 검출기는 CLAHE grayscale에서 더 잘 됨; 얇은 한글 획 파괴 방지).

**파라미터 기준값**
- `max_side_px`: 2048 → **3000** (디테일 보존, 다운샘플 방지)
- det: `limit_type=max`, `limit_side_len=1280~1536`, `thresh 0.3→0.2`, `box_thresh 0.6→0.45`, `unclip_ratio 1.5→2.0`, `use_dilation=True`
- rec: 입력 높이 48px 고정 → 작은 텍스트는 업스케일로 글자 높이 ≥ 24–48px 확보
- ROI: 박스마다 `max(12px, 0.12*box_h)` 패딩 후 크롭, **섹션별 독립 OCR**(각 크롭에 업스케일·CLAHE 개별 적용)
- 곡면 병: polygon 검출 출력 + `unclip_ratio≈2.0` + 해당 크롭만 `use_doc_unwarping=True`; 매우 저해상도 크롭만 Real-ESRGAN

> 배선 위치: `src/ocr/preprocessing.py`에 `LocalOCRPreprocessMode='label_enhance'` 추가(OpenCV), `LOCAL_OCR_PREPROCESS_MODE`로 노출. det 노브는 `src/config.py` + `paddle.py:_predict_kwargs` 확장. **그리드 sweep으로 최적값 확정 후 기본값 채택.**

---

## 6. 파인튜닝 레시피 (실행 명령)

**데이터 포맷**
- rec: `이미지경로\t정답텍스트` (UTF-8, 한 줄 1샘플). 공식 최소 5,000 라인(dict 불변 시). repo는 이미 ~70,778 train / 6,828 val 보유.
- det: `이미지경로\t[{"transcription":..., "points":[[x1,y1]...[x4,y4]]}]`
- dict: `character_dict_path` 한 줄 1문자, 라벨의 모든 문자(한글+숫자+단위 `mg/㎍/%`+구두점) 커버. 단위 기호 확장 시 초기 acc=0은 정상.

**학습 (A100, 기존 PowerShell 래퍼)**
```powershell
# smoke (파이프라인 검증)
.\run_a100_paddleocr_windows_training.ps1 -Mode smoke -BatchSize 128 -LearningRate 0.0001
# full
.\run_a100_paddleocr_windows_training.ps1 -Mode full -Epochs 100 -BatchSize 128 -LearningRate 0.0001
```
내부 호출(요지):
```bash
python tools/train.py -c configs/rec/PP-OCRv5/multi_language/korean_PP-OCRv5_mobile_rec.yml \
  -o Global.pretrained_model=pretrain/korean_PP-OCRv5_mobile_rec_pretrained \
     Global.character_dict_path=<dict.txt> Global.use_space_char=True \
     Global.epoch_num=100 Optimizer.lr.learning_rate=0.0001 \
     Train.dataset.label_file_list=['rec_gt_train.txt','rec_gt_general.txt'] \
     Train.dataset.ratio_list=[1.0,0.1] \
     Eval.dataset.label_file_list=['rec_gt_val.txt'] \
     Train.loader.batch_size_per_card=128
```
**config.yml 핵심 항목:** `Global`(epoch_num, pretrained_model, character_dict_path, use_space_char, save_inference_dir) · `Architecture`(rec/SVTR_LCNet, GTC-NRTR head) · `Optimizer`(Adam, Cosine/Piecewise lr + warmup, L2~3e-5) · `Train.dataset`(SimpleDataSet, label_file_list, **ratio_list**, transforms에서 RecConAug 제거/RecAug 유지) · `Eval`(acc, norm_edit_dis).

**inference export + 런타임 연결**
```powershell
.\run_a100_paddleocr_windows_training.ps1 -Mode export
# tools/export_model.py → inference dir 생성 → 앱 호스트로 복사
```
```bash
# 앱 .env
LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR=/path/to/exported/inference
ENABLE_LOCAL_OCR=true
# 게이트 통과 후에만:
OCR_PRIMARY_PROVIDER=paddleocr
```
> `paddle.py`는 PaddleOCR 3.x이므로 레거시 `rec_model_dir`가 아니라 **`text_recognition_model_dir`**로 연결된다(이미 `local_ocr_text_recognition_model_dir`로 배선됨).

**(선택) CML 증류:** 평문 파인튜닝이 baseline을 넘은 뒤 `*_rec_distillation.yml`(DistillationModel, Teacher freeze + student) + `DistillationDMLLoss + DistillationCTCLoss(+SARLoss)`로 +3–5%.

---

## 7. 합성·약지도 데이터 (sim-to-real 해소)

| 도구 | 용도 | 명령(요지) |
|---|---|---|
| **SynthTIGER** (NAVER) | 한국어 rec 합성(배경/블러/노이즈/롱테일) | `pip install synthtiger`(libraqm) → `synthtiger -o synth_ko -w 4 -c 20000 -v template.py SynthTiger config.yaml` |
| **StyleText** (PaddleOCR) | 실사진 스타일 전이 합성 | `python3 tools/synth_image.py --style_image <실크롭> --text_corpus <코퍼스> --language ko` |
| **TRDG / KoTDG** | 경량 빠른 시작(한국어 dict/font/bg) | `./run.py -c <n> -l ko --dict words.txt -o out` |
| **Teacher 증류** | 실사진 line-crop 자동 라벨 | CLOVA+Google Vision 합의 필터 → `crop\t합의전사` |

**catastrophic forgetting 방지 = 데이터 규칙:** 합성-only 금지. **항상 일반 한국어 코퍼스 ~1:1 혼합**(`ratio_list`). 기존 0.518→0.037 실패가 바로 "합성 600라인 + 일반 미혼합 + 2 epoch"였다.

**코퍼스(C4):** DB 카탈로그에서 성분 표기명·함량+단위(`억 CFU, μg, IU`)·섭취 문구 추출 → 합성/StyleText 입력 + dict 커버리지 검증. 희귀 단위는 오버샘플 + SynthTIGER 롱테일 균형.

---

## 8. 마일스톤 & 성공 기준

| 단계 | 작업 | 기간 | 성공 기준(게이트) |
|---|---|---|---|
| **0. 지표 수정** | A1: precision 게이트 폐기, recall/CER/ROI 지표 도입 | 2–3일 | 게이트 JSON이 도달 가능 목표를 산출 |
| **1. Quick Wins** | A2–A7 + ROI 텍스트-공간 스코핑 측정 | 1주 | holdout 52에서 field_match/recall **+0.05↑**, 무학습 F1 0.33→0.50+ 확인 |
| **2. 파인튜닝** | B1–B6 올바른 레시피 재실행 | 2–4주 | holdout에서 baseline 전 지표 초과 + 절대 하한(field_match ≥0.85, norm_edit_dis ≥0.90) |
| **3. 데이터/증류** | C1–C5 (정체 시) | 4주+ | CLOVA 대비 동등/우위, 외부 API 비용 제거 |
| **4. 승격** | `OCR_PRIMARY_PROVIDER=paddleocr` 전환 | 게이트 통과 시 | CLOVA를 fallback으로 강등, 회귀 모니터 |

**최종 목표 지표(제안):** 실사진 holdout 기준 **field_match_ratio ≥ 0.85**, **norm_edit_dis(=1−CER) ≥ 0.90**, ROI 스코핑 후 **char-F1 ≥ 0.85**. (현재 char-LCS F1 0.324 → 지표 재정의 + ROI + 파인튜닝의 합으로 달성)

---

## 9. 재사용할 기존 리포 자산

- **학습/평가:** `run_a100_paddleocr_windows_training.ps1`, `run_paddleocr_finetune_plan.py`, `build_paddleocr_finetune_run_plan.py`, `materialize_paddleocr_dataset.py`, `run_paddleocr_baseline_eval.py`, `evaluate_ocr_three_tier.py`, `paddleocr_clova_eval.py`
- **게이팅/승격:** `gate_paddleocr_finetune_against_baseline.py`, `gate_paddleocr_text_extraction_target.py`, `register_paddleocr_finetune_run_from_plan.py`, `promote_*`
- **데이터:** `build_synthetic_paddleocr_rec_dataset.py`(→ TRDG/SynthTIGER로 대체/보강), `build_clova_realphoto_rec_dataset.py`, `build_crawling_realphoto_rec_dataset.py`, `build_paddleocr_improvement_candidates.py`(teacher 합의 필터)
- **설계 문서:** `2026-06-08-text-f1-improvement-design.md`(지표 천장 증명 + 텍스트-공간 스코핑 레버), `2026-06-06-paddleocr-95pct-findings-and-finetune-recipe.md`, `2026-06-06-a100-remote-paddleocr-finetune-guide.md`, `2026-06-07-cpu-finetune-results.md`
- **런타임 배선점:** `src/ocr/providers/paddle.py`(`_predict_kwargs`, `_text_*_model_name`), `src/ocr/preprocessing.py`(`label_enhance`), `src/config.py`(det 노브), `src/parsing/layout_parser.py:218`(텍스트-공간 스코핑)

---

## 10. 참고 링크

**PP-OCRv5 / 모델**
- PP-OCRv5 소개(server vs mobile, 인쇄 HMean): https://www.paddleocr.ai/main/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5.html
- 다국어(한국어) 인식: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md
- `korean_PP-OCRv5_mobile_rec` 카드: https://huggingface.co/PaddlePaddle/korean_PP-OCRv5_mobile_rec
- `PP-OCRv5_server_det` 카드: https://huggingface.co/PaddlePaddle/PP-OCRv5_server_det
- PaddleOCR 3.0 기술 리포트: https://arxiv.org/html/2507.05595v1

**검출/전처리 튜닝**
- Text Detection 모듈(limit_side_len/box_thresh/unclip_ratio): https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/module_usage/text_detection.html
- 작은 텍스트 검출 누락(#13164): https://github.com/PaddlePaddle/PaddleOCR/discussions/13164
- 타이트 크롭 검출 0건 회귀(#15603): https://github.com/PaddlePaddle/PaddleOCR/issues/15603
- rec 입력 shape 48px(#14109): https://github.com/PaddlePaddle/PaddleOCR/issues/14109
- OCR 전처리(CLAHE/deskew 순서): https://www.nitorinfotech.com/blog/improve-ocr-accuracy-using-advanced-preprocessing-techniques/

**파인튜닝/증류/평가**
- 파인튜닝 가이드(샘플 수/LR/ratio_list): http://www.paddleocr.ai/v2.9/en/ppocr/model_train/finetune.html
- 인식 학습/평가(acc, norm_edit_dis): https://www.paddleocr.ai/latest/en/version2.x/ppocr/model_train/recognition.html
- config.yml 레퍼런스: http://www.paddleocr.ai/main/en/version2.x/ppocr/blog/config.html
- 지식 증류(CML/DML): http://www.paddleocr.ai/v2.9/en/ppocr/model_compress/knowledge_distillation.html
- PP-OCRv5 파인튜닝 사례: https://arxiv.org/pdf/2510.04003
- CER/WER 평가: https://towardsdatascience.com/evaluating-ocr-output-quality-with-character-error-rate-cer-and-word-error-rate-wer-853175297510/

**합성 데이터 / 대안 엔진**
- SynthTIGER(NAVER): https://github.com/clovaai/synthtiger · 논문: https://arxiv.org/pdf/2107.09313
- StyleText: https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.5/StyleText/README.md
- TRDG: https://github.com/Belval/TextRecognitionDataGenerator · KoTDG: https://github.com/Diuven/KoTDG
- PaddleOCR-VL(한국어 edit-dist 0.052): https://arxiv.org/abs/2510.14528 · surya: https://github.com/datalab-to/surya · ko-trocr: https://huggingface.co/ddobokki/ko-trocr
- PaddleOCR vs EasyOCR(2025): https://www.codesota.com/ocr/paddleocr-vs-easyocr · 한국어 8엔진 비교: https://devocean.sk.com/blog/techBoardDetail.do?ID=165524&boardType=techBlog

---

### 한 줄 요약
> **지표를 고치고(3절) → server_detection·해상도·CLAHE·ROI를 켜고(단계 A) → 1:1 혼합·저LR로 올바르게 파인튜닝하고(단계 B) → teacher 증류·StyleText로 데이터 천장을 올린(단계 C) 다음, holdout 게이트를 통과하면 `OCR_PRIMARY_PROVIDER`를 paddleocr로 전환한다.**
