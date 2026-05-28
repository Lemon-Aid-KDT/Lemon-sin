# Food Recognition Training Plan (dev-guide 16 Track)

> **작성일**: 2026-05-11 (v5) | **트랙**: dev-guide 16 본체 R&D | **대상 브랜치**: `work-space/jongpil`  
> **참조 문서**: [`docs/dev-guides/16-meal-recognition.md`](../../dev-guides/16-meal-recognition.md)
>
> **v5 변경점**: Phase A를 한 번에 머지하지 않고 **A1 / A2 / A3** 3개 PR로 분할. 각 PR이 독립적으로 black/ruff/mypy/pytest 통과해야 머지 가능. 커밋 단위 작게 유지.  
> **v4 변경점**: Phase A를 dev-guide 06/08과 독립적으로 진행하도록 조정. `RdaMatcher`는 Phase A에서 100g 기준 `FoodNutritionProfile` 출력까지만 검증, `NutrientIntake` 변환은 사용자가 g/인분을 직접 입력한 경우의 06 완료 후 follow-up PR로 분리. AI Hub 다운로드는 Phase B부터. 모델 파일 보관 정책은 Beta 학습 이후 결정.

## 유지해야 할 기준 (Locked Roadmap)

```
MVP:    mock YOLO + mock GCV hint + RDA matcher
Beta:   YOLOv8 detection fine-tuning + GCV OCR/label 보조
Future: 필요하면 모바일 온디바이스 분류/탐지 모델 검토
```

이 계획서는 위 로드맵을 따라 **YOLOv8 detection 중심**으로 구성된다. MobileNet/EfficientNet 분류기 트랙은 본 계획의 범위가 **아니며**, "Future" 부록에서만 가능성으로 짧게 언급한다.

## 목표 (Goal)

dev-guide 16의 GCV + YOLOv8 식단 인식 시스템을 **MVP는 mock-first**, **Beta는 실제 YOLOv8 fine-tuning + 실 GCV 호출**로 구축한다. mock 단계에서 모든 데이터 계약과 파이프라인을 먼저 고정해서, Beta 학습 결과가 들어오자마자 mock 자리만 실 어댑터로 swap하면 끝나는 구조를 만든다.

## 산출물 (Deliverables) — 전체 트랙 요약

### MVP 산출물 (Phase A)
- `backend/src/meal/`: `base.py`, `exceptions.py`, `google_vision.py`, `yolo_v8.py`, `fusion.py`, `portion_estimator.py`, `text_parser.py`, `pipeline.py`
- `backend/src/nutrition/rda_matcher.py`
- `data/meal_vision/`: `mock_predictions.json` (10~20장), `classes.yaml`, `dataset.yaml`, `README.md`
- `data/rda/`: `korean_foods.csv` (최소 100종), `food_aliases.json` (최소 100종)
- `tests/fixtures/meal_images/` 샘플 10~20장
- Unit 25+ / Integration 3+ 테스트 통과
- dev-guide 16 Definition of Done 모두 충족

### Beta 산출물 (Phase B + C + D)
- `ml/` 트랙 폴더 (YOLOv8 학습 파이프라인)
- AI Hub 우선순위 50종 학습 데이터셋 (YOLO format)
- `models/meal/yolov8-food.pt` (학습 모델, gitignored)
- 학습 메트릭 리포트: mAP@50, Top-3 정확도, F1, confusion matrix
- 실 `GoogleVisionMealHintAdapter`, `YoloV8MealDetector` (mock과 동일 인터페이스)
- Beta 목표 지표 달성:
  - mAP@50 ≥ 0.75
  - Top-3 음식 후보 정확도 ≥ 0.85
  - F1 ≥ 0.70
  - 중량 추정 평균 오차 ≤ 30%

### Future 산출물 (Phase F — 검토만, 본 트랙 비-목표)
- 모바일 온디바이스 가능성에 대한 짧은 기술 메모 (별도 트랙)

## 비-목표 (Non-Goals)

- ❌ MobileNet/EfficientNet 분류기 학습 (이전 v2 계획 폐기)
- ❌ TFLite/CoreML 변환 (Future, 본 트랙 범위 외)
- ❌ Claude Vision 기반 인식 (이전 dev-guide 16 버전 — 이미 GCV+YOLO로 교체됨)
- ❌ MVP에서 전체 800클래스 YOLO 학습 (dev-guide 16 §"이 작업에서 하지 말 것")
- ❌ GCV label만으로 음식명 확정 (보조 역할로만)
- ❌ FastAPI 라우터 통합 (별도 작업)
- ❌ 모바일 식단 입력 UI (dev-guide 20 범위)
- ❌ **Phase A 시작 전 dev-guide 06/08 완료 대기** — Phase A는 독립적으로 진행
- ❌ **Phase A에서 AI Hub 데이터 다운로드** — Phase B부터 진행

---

## dev-guide 16 Contract 정리

### Adapter 계층 (dev-guide 16 §역할 분리)

| 컴포넌트 | 책임 | MVP 구현 | Beta 구현 |
|---------|------|----------|-----------|
| `GoogleVisionMealHintAdapter` | OCR 텍스트, label hint, object hint 추출 | mock response | 실 Cloud Vision 호출 |
| `YoloV8MealDetector` | 음식 bbox/class/confidence 탐지 | `MockYoloV8MealDetector` | `ultralytics.YOLO` |
| `MealFusionEngine` | YOLO 결과 + GCV hint 병합 | deterministic merge | 동일 (변경 없음) |
| `PortionEstimator` | 시각적 양 추정 보조값 | A2 mock pipeline 보조값, 기본 영양 계산에는 사용하지 않음 | 사용자 입력 보조/미래 추정 개선 |
| `RdaMatcher` | 음식명/class → 농진청 food_code 매칭 + 100g nutrition profile | 100종 시드 | 전체 데이터 |

핵심 원칙: **MVP의 mock과 Beta의 실 구현은 동일한 Protocol/ABC를 따른다**. 데이터 계약(`MealDetection`, `RecognizedMealItem`, `RecognizedMeal`)도 변경 없음.

### Pydantic DTOs (dev-guide 16 §1. base.py)

```python
class BoundingBox:
    x_min: float; y_min: float; x_max: float; y_max: float

class MealDetection:  # YOLO/GCV의 원시 후보
    class_name_ko: str
    confidence: float
    bbox: BoundingBox | None
    source: str  # "yolo_v8" | "google_vision"

class RecognizedMealItem:  # 최종 음식 항목
    name_ko: str
    food_code: str | None
    estimated_grams: float
    estimated_amount: str
    confidence: float
    portion_confidence: float
    needs_user_review: bool
    sources: list[str]  # ["yolo_v8", "google_vision"]
    alternatives: list[MealDetection]

class RecognizedMeal:
    meal_type: str
    items: list[RecognizedMealItem]
    engine: str
    raw_input: str
```

### Fusion 규칙 (dev-guide 16 §4. fusion.py)

- YOLO class가 `food_aliases.json`에 있으면 primary candidate
- GCV OCR에 음식명이 있으면 alias confidence 보강
- YOLO와 GCV가 충돌하면 YOLO 우선, `needs_user_review=True`
- 동일 음식 다중 bbox → confidence 최고 항목이 대표, 나머지는 `alternatives`

### 신뢰도 정책 (dev-guide 16 §결과 신뢰도 정책)

| YOLO confidence | 처리 |
|---|---|
| `≥ 0.70` | 자동 후보 표시 |
| `0.40 ~ 0.69` | `needs_user_review=True` |
| `< 0.40` | 자동 확정 X, GCV hint와 함께 후보 보관만 |

GCV는 음식 확정의 **주 엔진이 아니다** — OCR/label hint로 alias 보강만 한다.

---

## 폴더 구조

```
Lemon-sin/
├── backend/                                # dev-guide 16 본체
│   └── src/
│       ├── meal/
│       │   ├── __init__.py
│       │   ├── base.py                     # DTOs
│       │   ├── exceptions.py
│       │   ├── google_vision.py            # Real + Mock GCV Adapter
│       │   ├── yolo_v8.py                  # Real + Mock YOLOv8 Detector
│       │   ├── fusion.py                   # MealFusionEngine
│       │   ├── portion_estimator.py
│       │   ├── text_parser.py
│       │   └── pipeline.py                 # 이미지/텍스트 식단 파이프라인
│       └── nutrition/
│           └── rda_matcher.py
│
├── data/
│   ├── meal_vision/                        # MVP mock 데이터
│   │   ├── mock_predictions.json
│   │   ├── classes.yaml                    # YOLO 클래스 정의 (MVP 15~20종, Beta 50종+)
│   │   ├── dataset.yaml                    # YOLO fine-tuning 데이터셋 설정
│   │   └── README.md
│   └── rda/
│       ├── korean_foods.csv                # 농진청 식품성분표 시드 (MVP 100종)
│       └── food_aliases.json               # YOLO class → RDA food_code 매핑
│
├── ml/                                     # ★ Beta YOLOv8 학습 트랙
│   ├── README.md                           # dev-guide 16 Beta 단계 가이드
│   ├── requirements-ml.txt                 # ultralytics, torch, albumentations, pyyaml
│   ├── configs/
│   │   ├── yolov8n_v1_50class.yaml         # Beta v1: 50종, 작은 모델
│   │   └── yolov8s_v2_150class.yaml        # Beta v2 (옵션): 150종, 중형
│   ├── data/                               # ★ gitignored
│   │   ├── raw/                            # AI Hub 원본
│   │   ├── processed/                      # YOLO format 변환
│   │   │   ├── images/{train,val,test}/
│   │   │   └── labels/{train,val,test}/    # YOLO txt
│   │   └── meta/
│   │       ├── class_priority.json         # 50/100/150/800 우선순위 단계
│   │       └── annotation_stats.json
│   ├── notebooks/
│   │   ├── 00_aihub_eda.ipynb              # AI Hub 데이터 탐색
│   │   ├── 01_annotation_conversion.ipynb  # JSON → YOLO txt 변환 검증
│   │   └── 02_yolo_eval.ipynb              # 학습 결과 분석
│   ├── src/
│   │   ├── __init__.py
│   │   ├── data/
│   │   │   ├── aihub_loader.py             # AI Hub 데이터 로더
│   │   │   ├── annotation_converter.py     # AI Hub JSON → YOLO txt
│   │   │   ├── splits.py                   # train/val/test 분할
│   │   │   └── augmentations.py            # Albumentations
│   │   ├── train/
│   │   │   └── yolov8_trainer.py           # ultralytics wrapper
│   │   └── eval/
│   │       ├── coco_metrics.py             # mAP@50, mAP@50:95
│   │       ├── topk_accuracy.py            # Top-3 정확도
│   │       └── confusion_classes.py        # 클래스 혼동 분석
│   ├── scripts/
│   │   ├── prepare_dataset.py              # AI Hub → YOLO 변환 CLI
│   │   ├── train_yolov8.py                 # 학습 CLI
│   │   └── eval_yolov8.py                  # 평가 CLI
│   └── outputs/                            # ★ gitignored
│       ├── checkpoints/
│       └── runs/                           # Ultralytics 기본 출력
│
└── models/                                 # ★ gitignored 또는 LFS
    └── meal/
        └── yolov8-food.pt                  # 학습 결과 모델 (런타임 로드)
```

## .gitignore 추가 항목 (Phase A에서 즉시 적용)

```gitignore
# Meal vision / YOLO 학습 부산물
models/
ml/outputs/
ml/data/raw/
ml/data/processed/
ml/notebooks/.ipynb_checkpoints/
*.pt
runs/
wandb/
```

> ★ **모델 파일 보관 정책(LFS vs Releases vs 외부 스토리지)은 Beta 학습 이후 결정**한다. 지금은 위 패턴으로 gitignore에 묶어두면 충분.

---

## Phase A — MVP (Mock-first, 예상 1일)

> dev-guide 16의 MVP는 **모델 학습 없이** mock으로 파이프라인과 계약 고정.

### Phase A 독립성 원칙 (★ 중요)

- **dev-guide 06/08 완료를 blocker로 두지 않는다.** Phase A는 mock-first 독립 파이프라인으로 시작.
- **AI Hub 데이터 다운로드를 Phase A에서 진행하지 않는다.** Phase B에서 처음 시작.
- **`RdaMatcher`는 100g 기준 `FoodNutritionProfile`까지만 검증한다.** 사용자가 g/인분을 직접 입력한 경우의 `NutrientIntake` 변환 계층은 06 완료 후 별도 작업으로 추가.
- **모델 파일 보관 정책은 Beta 학습 이후 결정.** Phase A에서는 .gitignore 패턴 추가만.

### Phase A 산출물 (A1 + A2 + A3 합산)
- `backend/src/meal/` 8개 모듈 + `backend/src/nutrition/rda_matcher.py`
- `data/meal_vision/mock_predictions.json` (샘플 10~20장 분량)
- `data/meal_vision/{classes.yaml, dataset.yaml, README.md}`
- `data/rda/korean_foods.csv` (100종 시드)
- `data/rda/food_aliases.json` (100종)
- `tests/fixtures/meal_images/` 샘플 이미지
- `.gitignore` 갱신 (Phase A 시점에 모델 부산물 패턴 추가)
- Unit 테스트 25+, Integration 테스트 3+ 통과

### Phase A PR 분할 (A1 / A2 / A3)

Phase A는 한 번에 머지하지 않는다. 3개 PR로 쪼개서 각각이 독립적으로 black/ruff/mypy/pytest 통과해야 머지 가능. 커밋 단위는 작게 유지(아래 권장 참고).

---

#### A1 — DTO + 예외 + 시드 데이터 + Mock fixture (Foundation)

> ★ 다른 두 PR(A2, A3)이 의존하는 기반.

**스코프:**
- DTO: `BoundingBox`, `MealDetection`, `RecognizedMealItem`, `RecognizedMeal` (Pydantic v2, `frozen=True`)
- 예외 계층: `MealRecognitionError`, `MealApiError`, `MealParseError`
- 시드: `korean_foods.csv` 100종, `food_aliases.json` 100종
- Mock fixture: `mock_predictions.json` 10~20장 분량
- YAML 설정: `classes.yaml`, `dataset.yaml`, README
- `.gitignore`에 모델 부산물 패턴 추가

**파일:**
- `backend/src/meal/__init__.py`
- `backend/src/meal/base.py`
- `backend/src/meal/exceptions.py`
- `data/meal_vision/mock_predictions.json`
- `data/meal_vision/classes.yaml`
- `data/meal_vision/dataset.yaml`
- `data/meal_vision/README.md`
- `data/rda/korean_foods.csv`
- `data/rda/food_aliases.json`
- `tests/unit/meal/__init__.py`
- `tests/unit/meal/test_base.py`
- `tests/unit/meal/test_seed_integrity.py`
- `.gitignore` (수정)

**테스트:**
- Pydantic validation — `RecognizedMealItem(estimated_grams=0)` → `ValidationError`
- `BoundingBox` 좌표 검증 — `x_min < x_max`, `y_min < y_max`
- 시드 정합성:
  - `food_aliases.json`의 모든 `food_code` ∈ `korean_foods.csv`
  - `classes.yaml`의 모든 클래스명이 `food_aliases.json`에 매핑 존재
  - `mock_predictions.json`의 모든 `class_name_ko`가 `classes.yaml`에 정의

**커밋 단위 권장 (작게 유지):**
1. `feat(meal): DTO + 예외 골격 (base.py, exceptions.py)`
2. `feat(data): 농진청 100종 시드 CSV + aliases JSON`
3. `feat(data): MVP mock predictions 10~20장 + YAML 설정`
4. `test(meal): DTO 검증 + 시드 정합성 테스트`
5. `chore(gitignore): 모델 부산물 패턴 추가 (models/, ml/outputs/, *.pt 등)`

**A1 Definition of Done:**
- `mypy backend/src/meal --strict` 통과 (예외/DTO 한정)
- 시드 정합성 테스트 100% 통과
- `black backend/src/meal tests/unit/meal --check` 통과
- `ruff check backend/src/meal tests/unit/meal` 통과
- `pytest tests/unit/meal -v` 통과

---

#### A2 — Mock 어댑터 + Fusion + Portion + Pipeline (Core)

> A1의 DTO·시드 위에서 추론 파이프라인의 뼈대를 만든다. RDA matching은 A3에서 연결되므로 A2에서는 stub.

**스코프:**
- `MockYoloV8MealDetector` — image hash로 `mock_predictions.json` 룩업
- `MockGoogleVisionMealHintAdapter` — image hash로 mock GCV response
- `MealFusionEngine` — primary + alias 보강 + 충돌 처리 + 다중 bbox 대표
- `PortionEstimator` — `default_serving_g` × bbox 면적 비중 보정 (×0.7 / ×1.0 / ×1.2)
- `MealPipeline` — image_hash → mock → fusion → portion → **RDA stub** → `RecognizedMeal`
- (실 `YoloV8MealDetector`, 실 `GoogleVisionMealHintAdapter`는 Beta Phase B/D에서)

**파일:**
- `backend/src/meal/yolo_v8.py` (Mock + ABC, 실 구현은 Beta)
- `backend/src/meal/google_vision.py` (Mock + ABC, 실 구현은 Beta)
- `backend/src/meal/fusion.py`
- `backend/src/meal/portion_estimator.py`
- `backend/src/meal/pipeline.py` (A2 1차 — RDA stub 포함, A3에서 교체)
- `tests/unit/meal/test_yolo_v8.py`
- `tests/unit/meal/test_google_vision.py`
- `tests/unit/meal/test_fusion.py`
- `tests/unit/meal/test_portion_estimator.py`
- `tests/unit/meal/test_pipeline.py`

**테스트:**
- Mock YOLO: 등록된 image hash → detection 리스트, 미등록 → 빈 리스트
- Mock GCV: hint(label/ocr/object) 추출 일관성
- Fusion 4종 규칙:
  - YOLO primary
  - GCV alias 보강
  - 충돌 → YOLO 우선 + `needs_user_review=True`
  - 동일 음식 다중 bbox → 최고 confidence 대표 + 나머지 `alternatives`
- Portion: 기본 1인분, 작은 bbox → ×0.7, 큰 bbox → ×1.2
- Pipeline: 신뢰도 정책 3구간 (`≥0.70` / `0.40~0.69` / `<0.40`) 적용

**커밋 단위 권장:**
1. `feat(meal): MockYoloV8MealDetector + ABC + 단위 테스트`
2. `feat(meal): MockGoogleVisionMealHintAdapter + ABC + 단위 테스트`
3. `feat(meal): MealFusionEngine + Fusion 규칙 4종 테스트`
4. `feat(meal): PortionEstimator + bbox 비중 보정 테스트`
5. `feat(meal): MealPipeline 1차 (RDA stub) + 통합 테스트`

**A2 Definition of Done:**
- 모든 단위 테스트 통과
- 신뢰도 정책 3구간 분류 정확
- Pipeline이 mock JSON의 모든 케이스에 대해 `RecognizedMeal` 반환
- `mypy backend/src/meal --strict` 통과
- `black`, `ruff`, `pytest tests/unit/meal` 통과

---

#### A3 — RDA matcher + 100g Nutrition Profile + Text parser + Compliance polish (Integration & Polish)

> Phase A 마무리. A3의 제품 방향은 "이미지로 양을 단정하지 않고, 음식 식별 후 100g 기준 영양 프로필을 제공"하는 것이다. 사용자가 g 또는 인분을 직접 입력한 경우에만 해당 양 기준 영양소를 재계산한다. RDA matching, 텍스트 입력, edge case 보강, 의료 표현 자동 검사로 dev-guide 16 §Definition of Done(06 의존 제외)을 모두 충족한다.

**스코프:**
- `RdaMatcher` + `FoodNutritionProfile` DTO (food_code, 100g 기준 영양소, 정보성 특징/주의 문구)
  ```python
  class FoodNutritionProfile(BaseModel):
      food_code: str | None
      name_ko_canonical: str
      category: str | None
      base_amount_g: float = 100.0
      default_serving_g: float
      nutrients_per_100g: dict[str, float]
      highlights: list[str]
      cautions: list[str]
      needs_user_review: bool
  ```
- `AmountNutritionEstimate` DTO (사용자가 직접 g 또는 인분을 입력한 경우에만 계산)
  ```python
  class AmountNutritionEstimate(BaseModel):
      food_code: str | None
      name_ko_canonical: str
      amount_g: float
      serving_count: float | None
      nutrients_for_amount: dict[str, float]
  ```
- `text_parser.py` — 정규화·alias 처리만 (LLM 호출 X)
- `pipeline.py` 기본 인식 결과는 `RecognizedMeal` 유지. 이미지 기반 `estimated_grams`를 기본 영양 계산에 사용하지 않는다.
- A3에서는 pipeline 출력의 `RecognizedMealItem.name_ko`를 `RdaMatcher`에 전달해 100g 기준 nutrition profile을 얻는 연결 경로를 검증한다.
- Edge case 테스트 5+ 추가
- Compliance 자동 검사 (의료 표현 단어 사용 없는지)

**파일:**
- `backend/src/nutrition/rda_matcher.py`
- `backend/src/meal/text_parser.py`
- `backend/src/meal/pipeline.py` (수정 — A2의 stub 교체)
- `tests/unit/nutrition/__init__.py`
- `tests/unit/nutrition/test_rda_matcher.py`
- `tests/unit/meal/test_text_parser.py`
- `tests/unit/meal/test_pipeline_edge_cases.py`
- `tests/unit/meal/test_compliance.py`
- `tests/integration/meal/__init__.py`
- `tests/integration/meal/test_meal_image_pipeline.py`

**테스트:**
- RDA matching:
  - 매칭 성공: alias → food_code → `FoodNutritionProfile` 정확
  - 100g 정규화: `nutrient_per_100g = nutrient_per_unit / unit_size_g * 100` 공식 검증
  - 사용자 입력 g scaling: `nutrient_for_amount = nutrient_per_100g * amount_g / 100` 공식 검증
  - 사용자 입력 인분 scaling: `amount_g = unit_size_g * serving_count` 후 영양소 계산 검증
  - CSV에 없는 영양소(예: `sugar_g`)는 highlights/cautions로 생성하지 않음
  - 매칭 실패: `needs_user_review=True`로 반환
  - 한 음식에 여러 alias가 있을 때 우선순위 일관성
- Text parser:
  - 정규화: 공백·특수문자 처리
  - alias → canonical name 매핑 정확성
- Edge cases (5+):
  - 빈 mock detection → 빈 `RecognizedMeal`
  - 모든 detection이 `confidence < 0.40` → 자동 확정 X, 후보 보관만
  - YOLO/GCV 충돌 케이스 → YOLO 우선 + `needs_user_review=True`
  - 동일 음식 다중 bbox → 대표 1개 + `alternatives`
  - 매칭 실패 음식 → pipeline 결과 항목 보존 + nutrition profile은 `needs_user_review=True`
  - 1글자 음식명 / 특수문자 포함 이름
- Compliance:
  - DTO 필드명·함수명·docstring·로그 메시지에서 `진단`, `처방`, `치료`, `보장` 단어 사용 없음 검사
  - 사용자 노출 문구는 "단백질이 풍부한 편", "나트륨이 상대적으로 있는 편" 같은 정보 제공형 표현만 허용
  - "주의해야 한다"처럼 단정적/의학적 판단으로 읽힐 수 있는 표현은 피하고, 필요한 경우 "섭취량은 개인 목표에 맞게 조절해 주세요" 수준으로 완화
  - 시스템 프롬프트가 있다면 동일 검사

**커밋 단위 권장:**
1. `feat(nutrition): RdaMatcher + 100g nutrition profile DTO + 단위 테스트`
2. `feat(meal): text_parser 정규화·alias 처리 + 단위 테스트`
3. `feat(nutrition): 사용자 입력량 기반 영양소 scaling 추가`
4. `test(meal): edge case 5+ 케이스 추가`
5. `test(meal): 의료 표현 자동 검사 + compliance polish`
6. `test(meal): 통합 테스트 (image → RecognizedMeal → 100g nutrition profile)`

**A3 Definition of Done:**
- dev-guide 16 §Definition of Done 중 06 의존 제외 항목 100% 충족
- Unit 25+, Integration 3+ 달성
- Edge case 5+ 케이스 커버
- 기본 영양 표시가 100g 기준으로 생성됨
- 사용자가 직접 입력한 g/인분 기준 scaling 함수가 검증됨
- 이미지 기반 `estimated_grams`가 기본 영양 계산에 사용되지 않음
- 의료 표현 자동 검사 통과
- `mypy backend/src/meal backend/src/nutrition --strict` 통과
- `black`, `ruff`, `pytest tests/` 전체 통과
- 06 후 follow-up PR(`to_nutrient_intakes` 추가)을 위한 hook은 100g profile/사용자 입력량 기반으로 명시됨

### 06 후 후속 통합 (Phase A 범위 밖, 별도 작업)

dev-guide 06에서 공식 `NutrientIntake` 스키마가 정의되면 다음을 추가:

1. `backend/src/nutrition/rda_matcher.py`에 변환 함수 추가:
   ```python
   def to_nutrient_intakes(
       profiles: list[FoodNutritionProfile],
       amount_g_by_food_code: dict[str, float],
   ) -> list[NutrientIntake]: ...
   ```
2. 사용자가 직접 입력한 g/인분이 있는 항목만 `NutrientIntake[]`로 변환한다. 입력량이 없으면 100g 기준 profile만 제공한다.
3. 통합 테스트 추가 (사진 → 인식 → 100g profile → 사용자 입력량 → 영양소 list → 06 모듈 연동)

이 통합은 **dev-guide 06 완료 직후의 작은 follow-up PR**로 처리. Phase A 완성도와는 무관.

### Phase A Aggregate Definition of Done (A1 + A2 + A3 머지 후)

- A1, A2, A3 각 PR의 개별 Definition of Done 모두 충족
- `pytest tests/unit/meal tests/unit/nutrition tests/integration/meal -v` 전체 통과
- dev-guide 16 §Definition of Done 중 **06 의존 항목 제외** 모두 충족 (`NutrientIntake` 변환은 06 후 follow-up PR)
- `mock_predictions.json` 모든 케이스에 대해 pipeline 테스트 통과
- 음식 후보/`needs_user_review` 플래그가 일관된 스키마로 반환
- `RdaMatcher`가 `FoodNutritionProfile`을 정확히 반환 (100g 기준 영양소 값 검증)
- 사용자 입력 g/인분이 있을 때만 amount 기준 영양소 scaling이 수행됨
- `black src tests --check`, `ruff check src tests`, `mypy src --strict`, `pytest` 통과
- 사용자 노출 문구에 진단/처방/치료/보장 표현 없음
- `.gitignore`에 `models/`, `ml/outputs/`, `*.pt` 등 패턴 추가됨
- 06 후 follow-up hook 준비됨 (100g profile + 사용자 입력량 기반 변환 함수 시그니처 합의)

---

## Phase B — Beta 데이터 준비 (예상 1~2일, AI Hub 다운로드 별도)

### 산출물
- `ml/` 트랙 폴더 + `requirements-ml.txt`
- AI Hub 우선 50종 학습 데이터셋 (gitignored, YOLO format)
- `ml/data/meta/class_priority.json` (50/100/150/800 단계)
- `data/meal_vision/classes.yaml` 확장 (Beta v1: 50종)
- `data/meal_vision/dataset.yaml` (YOLO 학습 설정)
- `ml/scripts/prepare_dataset.py`
- `notebooks/00_aihub_eda.ipynb`, `01_annotation_conversion.ipynb`

### 작업
1. **AI Hub 계정 + 데이터 다운로드** (사용자 직접) — 50종 우선, 전체 232,087장 받지 않음
2. **AI Hub 라벨 → YOLO format 변환**
   - 입력: AI Hub JSON (이미지별 bbox + class)
   - 출력: YOLOv8 txt (`class_id cx cy w h` 정규화 좌표)
   - `annotation_converter.py`에 변환 로직 + 단위 테스트
3. **클래스 우선순위 정의** (dev-guide 16 §클래스 우선순위)
   - Beta v1: 50종 (밥류·국찌개·면류·반찬·단백질·간편식·음료에서 우선 음식)
   - Beta v2: 100~150종
   - 장기: 800종
4. **클래스 매핑 정합 검사** — `classes.yaml`의 클래스명 ↔ `korean_foods.csv`의 `name_ko` ↔ `food_aliases.json`의 키. 자동화 스크립트로 검증
5. **train/val/test 70/15/15 stratified split**
6. **품질 통계** — `annotation_stats.json`: 클래스당 매수, bbox 크기 분포, 클래스 불균형 비율
7. **EDA 노트북**으로 시각화

### Definition of Done
- 50종 학습 데이터가 YOLO format으로 변환되어 `ml/data/processed/` 아래 준비
- `classes.yaml`의 50종 모두 `food_aliases.json`에 매핑되어 있고 `food_code`가 `korean_foods.csv`에 존재 (정합성 검사 통과)
- 클래스당 최소 매수 ≥ 300장 (dev-guide 16 §Beta fine-tuning 데이터)
- 클래스 매수 불균형 < 5배 (가장 많은 클래스 ÷ 가장 적은 클래스 < 5)

---

## Phase C — YOLOv8 Fine-tuning (예상 3~5일, 학습 시간 포함)

> dev-guide 16의 Beta 단계. 본 트랙의 핵심.

### 산출물
- `ml/configs/yolov8n_v1_50class.yaml` (또는 v8s)
- `ml/src/train/yolov8_trainer.py`
- `ml/scripts/train_yolov8.py`
- `models/meal/yolov8-food.pt` (학습 모델, gitignored)
- `ml/outputs/runs/v1/` — Ultralytics 기본 출력 (curves, predictions, conf matrix)
- 학습 메트릭 리포트 (`notebooks/02_yolo_eval.ipynb`)
- 클래스 혼동 분석 (`ml/src/eval/confusion_classes.py`)

### 작업
1. **베이스 모델 선택**:
   - YOLOv8n (3.2M params, 빠른 학습) → MVP/검증용
   - YOLOv8s (11.2M params, 정확도↑) → 본 학습용
2. **하이퍼파라미터 설정** (config YAML):
   - epochs 100, batch 16 (GPU VRAM 따라 조정)
   - imgsz 640, lr 1e-3, cos schedule
   - Augmentation: HSV, flip, mosaic, mixup
3. **학습 실행** — `yolo train` 또는 Python API 래퍼
4. **평가**:
   - mAP@50, mAP@50:95
   - Top-3 음식 후보 정확도 (커스텀 메트릭)
   - 클래스별 AP + F1
   - confusion matrix → 혼동 쌍 (김치찌개 vs 된장찌개 등) 식별
5. **중량 추정 평가** — bbox 면적 → 추정 g 변환 후 ground truth와 평균 절대 오차 측정
6. **체크포인트 검증** — `best.pt`를 `models/meal/yolov8-food.pt`로 배치, `YoloV8MealDetector`가 정상 로드되는지 확인

### Definition of Done
- mAP@50 ≥ **0.75** (dev-guide 16 Beta 목표)
- Top-3 음식 후보 정확도 ≥ **0.85**
- F1 ≥ **0.70**
- 중량 추정 평균 오차 ≤ **30%**
- `best.pt` 파일이 `YoloV8MealDetector(model_path="models/meal/yolov8-food.pt")`로 로드 가능
- 가장 헷갈리는 5쌍 클래스 식별 + 합칠지/보강할지 결정 문서

---

## Phase D — 실제 GCV 통합 (예상 1일)

> mock GCV를 실 Cloud Vision API 호출로 교체. 인터페이스 변경 없음.

### 산출물
- `backend/src/meal/google_vision.py`에 `GoogleVisionMealHintAdapter` (실 구현) 추가
- `GOOGLE_APPLICATION_CREDENTIALS` 환경변수 처리
- 실 API 통합 테스트 (credential 없으면 skip)

### 작업
1. **Cloud Vision SDK 호출** — `label_detection`, `text_detection`, `localized_object_detection`
2. **응답 → `MealDetection[]` 변환** — alias 매핑은 `food_aliases.json` 재사용
3. **에러·재시도 처리** — quota exceeded, 네트워크 timeout 등
4. **비용 추적 로깅** — INFO 레벨로 API 호출 카운트 (민감 정보 X)
5. **integration 테스트** — credential 있을 때만 실행, 없으면 skip

### Definition of Done
- mock 어댑터와 실 어댑터가 **동일 `Protocol`** 충족 (interchangeable)
- 실 API 호출 1회 통합 테스트 (credential 환경에서)
- `service-account.json` 등 비밀 파일 커밋 금지 검증
- Beta 파이프라인이 mock 없이 동작

---

## Phase E — Beta v2 확장 (옵션, 예상 2~3일)

> 50종 → 100~150종으로 확장. Phase C 결과가 안정적일 때만 진행.

### 작업
1. AI Hub에서 추가 100종 라벨링 검증
2. `food_aliases.json` + `korean_foods.csv` 확장
3. 클래스 불균형 완화 (oversampling 또는 class weight)
4. 재학습 후 메트릭 비교 (v1 vs v2)
5. 혼동 클래스 합치기 결정 (예: 된장국 vs 미역국 합칠지)

---

## Phase F — Future: 모바일 온디바이스 (검토만, 비-목표)

> ★ 본 트랙의 범위가 **아님**. dev-guide 16의 Future 항목으로 가능성만 메모.

### 후일 검토 사항 (구현 X)
- YOLOv8 모델을 TFLite 또는 CoreML로 변환 시 정확도/크기 trade-off
- 모바일 추론 속도 (Pixel/iPhone에서 한 장당 200~500ms 예상)
- 오프라인 사용 사례 정당화 — 인터넷 없는 환경에서 식단 인식 필요한가?
- 모바일 모델 + 클라우드 fallback 라우팅 (현재 GCV+YOLO 백엔드 아키텍처와의 정합)
- 별도 트랙으로 분리할 결정 시점 — Beta v2 안정화 이후

본 계획서는 모바일 온디바이스 구현을 **하지 않는다**. 필요해질 때 별도 plan 문서로 분리.

---

## 위험 요소 (Risks)

| 리스크 | 영향 | 완화 방안 |
|---|---|---|
| AI Hub 다운로드 시간·용량 (232,087장) | Phase B 시작 지연 | 50종 우선 다운로드, 클래스별 디렉토리 단위로 분할 받기 |
| AI Hub annotation 형식 ↔ YOLO format 차이 | 변환 버그 → 학습 실패 | `annotation_converter.py`에 unit test, 변환 결과 시각화 노트북 |
| 클래스명 불일치 (`classes.yaml` ↔ `korean_foods.csv` ↔ `food_aliases.json`) | Fusion/Matching 0건 → 파이프라인 실패 | Phase B에 정합성 자동 검증 스크립트 |
| 클래스 불균형 (특수외식 200 vs 음료 100) | 적은 클래스 학습 부족 | class weight, oversampling, Beta v1은 50종으로 시작 |
| 시각적 유사 음식 (찌개·국 계열) | mAP 정체 | confusion 분석 → 합치기 또는 데이터 보강 |
| GCV API 비용 | 운영 시 부담 | 환경변수로 mock/real 전환, 캐시 적용 |
| YOLO 학습 시간 (로컬 GPU 사양) | Phase C 지연 | YOLOv8n으로 빠른 검증 → YOLOv8s로 본 학습 |
| 중량 추정 본질적 한계 (사진만으로 ±30% 어려움) | UX 실망 | UI에서 "사진 기반 추정값" 명시 + 사용자 수정 허용 |
| MVP→Beta 전환 시 mock의 hard-coded 값이 실제와 다름 | 회귀 테스트 실패 | mock과 real을 동일 Protocol로 강제, dependency injection으로 swap |

## Critical Path

```
[Phase A — MVP]
  backend/src/meal/* (mock 위주) + RDA seed
        │
        ├─→ dev-guide 16 Definition of Done 충족 ✓
        │
[Phase B — Beta 데이터]
  AI Hub 50종 + YOLO format 변환 + 정합성 검증
        │
[Phase C — YOLOv8 학습]
  YOLOv8 fine-tuning + 평가
  mAP@50 ≥ 0.75, Top-3 ≥ 0.85, F1 ≥ 0.70
        │
[Phase D — 실 GCV 통합]
  mock GCV → real GCV swap
        │
[Phase E — Beta v2 확장] (옵션)
  100~150종 확장
        ⋮
[Phase F — Future] (검토만)
  모바일 온디바이스 가능성 메모
```

총 예상 소요:
- **MVP**: 1일
- **Beta (v1 50종)**: 4~7일 (AI Hub 다운로드 + 변환 + 학습 + GCV 통합)
- **Beta v2**: +2~3일 (옵션)

## 의존성·전제

- **Phase A는 dev-guide 06/08과 독립적** — mock-first로 시작, `RdaMatcher`는 100g 기준 `FoodNutritionProfile`까지만 검증
- **dev-guide 16 본체는 Phase A에서 (06 의존 부분 제외) 완성** — base.py, exceptions.py, mock adapter, fusion, portion 보조값, RDA 100g profile, pipeline 모두 MVP 산출물
- **06 후 후속 PR로 `NutrientIntake` 변환 통합** — 사용자 입력 g/인분이 있는 경우에만 amount 기준으로 변환하며, Phase A 완성도와 무관한 별도 작업
- **Phase B는 AI Hub 다운로드가 선행** — 사용자가 외부에서 직접 진행 (Phase A에서는 다운로드 X)
- **Phase D는 GCP 계정 + Cloud Vision API 활성화 + 서비스 어카운트** 필요
- **Phase E는 Phase C 메트릭이 dev-guide 16 목표를 충족할 때만 진행**

## 추가 결정 필요 (Open Decisions)

Phase A는 즉시 시작 가능. 다음 결정들은 Phase B 시작 전에만 확정하면 됨:

**Phase B 시작 전 (AI Hub 다운로드 시 결정):**
1. **YOLOv8 모델 크기** — n (빠른 학습, 정확도↓) vs s (느린 학습, 정확도↑) vs m (학습 매우 오래, 정확도↑↑)
2. **Beta v1 클래스 정확히 어떤 50개** — dev-guide 16 §우선 포함 음식 예시를 기준으로 사용자/팀이 확정

**Beta 학습 이후 결정 (Phase C/D 완료 시점):**
3. **모델 파일 보관 정책** — Git LFS vs GitHub Releases vs 외부 스토리지. 학습 결과 파일 크기 확인 후 판단

## Immediate Next Steps

- [x] ~~Phase A 시작 전 결정 — 선행 dev-guide 확인~~ — 불필요 (Phase A 독립 진행으로 결정됨)
- [ ] **A1 시작** — DTO + 예외 + 시드 + Mock fixture (작은 커밋 5개, 첫 PR)
- [ ] A1 머지 후 **A2 시작** — Mock 어댑터 + Fusion + Portion + Pipeline (커밋 5개, 두 번째 PR)
- [ ] A2 머지 후 **A3 시작** — RDA matcher + 100g nutrition profile + Text parser + Edge cases + Compliance (커밋 6개, 세 번째 PR)
- [ ] Phase A (A1+A2+A3) 완료 후 Open Decisions #1, #2 확정 → Phase B 진입
- [ ] Phase B 시점에 AI Hub 계정 등록 + 50종 다운로드 시작
- [ ] dev-guide 06 완료 시 follow-up PR로 100g profile + 사용자 입력량 기반 `to_nutrient_intakes(...)` 변환 통합
