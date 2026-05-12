# dev-guides/16 — 식단 인식 (Google Cloud Vision + YOLOv8)

> **Phase**: 3 | **선행 작업**: [`06-deficient-nutrient-diagnosis.md`](./06-deficient-nutrient-diagnosis.md), [`08-llm-supplement-parsing.md`](./08-llm-supplement-parsing.md) | **예상 소요**: MVP 1일, YOLO fine-tuning 3~5일

---

## 🎯 작업 목표

사용자가 식사 사진 또는 텍스트("점심: 김치찌개, 공기밥, 계란말이")를 입력하면 음식 후보와 100g 기준 영양 프로필을 구조화한다. 사용자가 g 또는 인분을 직접 입력한 경우에만 해당 양 기준 영양소 계산으로 확장한다.

이미지 입력은 **Google Cloud Vision + YOLOv8** 조합으로 처리한다. MVP에서는 실제 YOLO 학습 없이 수동 mock 예측으로 파이프라인과 데이터 계약을 먼저 고정하고, Beta 단계에서 AI Hub 음식 이미지 데이터셋으로 YOLOv8을 fine-tuning한다.

---

## 📋 산출물

```
backend/
├── src/
│   ├── meal/
│   │   ├── __init__.py
│   │   ├── base.py                  # 공통 DTO + Adapter Protocol
│   │   ├── exceptions.py
│   │   ├── google_vision.py         # OCR/label hint Adapter
│   │   ├── yolo_v8.py               # YOLOv8 Adapter + Mock Adapter
│   │   ├── fusion.py                # YOLO + GCV 결과 병합
│   │   ├── portion_estimator.py     # g 단위 추정
│   │   ├── text_parser.py           # 텍스트 입력 정규화
│   │   └── pipeline.py              # 이미지/텍스트 식단 파이프라인
│   └── nutrition/
│       └── rda_matcher.py           # 농진청 식품성분표 매칭
├── data/
│   ├── meal_vision/
│   │   ├── mock_predictions.json    # MVP용 수동 mock
│   │   ├── classes.yaml             # YOLO 클래스 정의
│   │   ├── dataset.yaml             # fine-tuning 데이터셋 설정
│   │   └── README.md                # 데이터 획득·전처리 가이드
│   └── rda/
│       ├── korean_foods.csv         # 농진청 식품성분표 최소 시드
│       └── food_aliases.json        # 음식명 alias / 클래스 매핑
└── tests/
    ├── unit/meal/
    │   ├── test_google_vision.py
    │   ├── test_yolo_v8.py
    │   ├── test_fusion.py
    │   ├── test_portion_estimator.py
    │   ├── test_text_parser.py
    │   └── test_pipeline.py
    ├── unit/nutrition/
    │   └── test_rda_matcher.py
    └── integration/meal/
        └── test_meal_image_pipeline.py
```

---

## 📐 설계 명세

### 입력 방식

```
[방식 A: 이미지 입력 - MVP]
  사진 → image_hash → mock_predictions.json
  → YOLODetection[] mock → Fusion
  → 농진청 DB 매칭 → 100g 기준 영양 프로필
  → 사용자가 g/인분을 입력한 경우에만 해당 양 기준 영양소 재계산

[방식 A: 이미지 입력 - Beta]
  사진 → Google Cloud Vision(label/text/object hints)
      → YOLOv8(food bbox/class/confidence)
      → Fusion(YOLO primary, GCV auxiliary)
      → 농진청 DB 매칭 → 100g 기준 영양 프로필
      → 사용자가 g/인분을 입력한 경우에만 해당 양 기준 영양소 재계산

[방식 B: 텍스트 입력]
  "점심: 김치찌개, 공기밥, 계란말이 1개"
  → TextParser(정규화)
  → Phase 2 LLM Adapter 또는 규칙 기반 parser
  → 농진청 DB 매칭 → 100g 기준 영양 프로필
  → 사용자가 g/인분을 입력한 경우에만 해당 양 기준 영양소 재계산
```

### 역할 분리

| 컴포넌트 | 책임 | MVP 구현 | Beta 구현 |
|---------|------|----------|-----------|
| `GoogleVisionMealHintAdapter` | OCR 텍스트, label hint, object hint 추출 | mock response | 실제 Cloud Vision 호출 |
| `YoloV8MealDetector` | 음식 bbox/class/confidence 탐지 | `MockYoloV8MealDetector` | `ultralytics.YOLO` |
| `MealFusionEngine` | YOLO 결과와 GCV hint 병합 | deterministic merge | 동일 |
| `PortionEstimator` | 시각적 양 추정 보조값 산출 | MVP 기본 영양 계산에는 사용하지 않음 | 사용자가 원할 때 보조 추정 또는 UI 참고값 |
| `RdaMatcher` | 음식명/class → 농진청 food_code 매칭 + 100g 기준 영양 프로필 생성 | 최소 CSV 100종 | 전체 RDA/농진청 데이터 |

### 결과 신뢰도 정책

- YOLO confidence `>= 0.70`: 자동 후보로 표시.
- YOLO confidence `0.40 ~ 0.69`: `needs_user_review=True`.
- YOLO confidence `< 0.40`: 자동 확정하지 않고 GCV label/OCR hint와 함께 후보로만 보관.
- GCV는 음식 확정의 주 엔진이 아니다. OCR/label hint로 alias 보강만 한다.
- 사진 기반 양 추정은 보조 정보로만 취급하며, 기본 영양 표시는 100g 기준으로 제공한다.

---

## 📊 데이터 요구사항

### 사용할 후보 데이터셋

사용 예정 데이터셋 구성:

| 구분 | 클래스 수 | 이미지 수 | 형식 |
|------|----------:|----------:|------|
| 특수외식메뉴 | 200 | 81,140 | jpg / json |
| 일반외식·배달메뉴 | 300 | 80,590 | jpg / json |
| 끼니대체메뉴 (빵, 떡, 죽 및 스프류 포함) | 200 | 61,300 | jpg / json |
| 음료 및 차류 | 100 | 9,057 | jpg / json |
| **합계** | **800** | **232,087** | jpg / json |

### MVP 데이터

MVP는 모델 학습을 하지 않고 mock 기반으로 진행한다.

필요 데이터:

- `tests/fixtures/meal_images/` 샘플 이미지 10~20장.
- `data/meal_vision/mock_predictions.json` 10~20장 분량.
- `data/rda/korean_foods.csv` 최소 100개 음식.
- `data/rda/food_aliases.json` 최소 100개 음식의 alias.

MVP mock 예측 예시:

```json
{
  "sample_kimchi_stew_rice.jpg": {
    "detections": [
      {
        "class_id": 12,
        "class_name_ko": "김치찌개",
        "confidence": 0.86,
        "bbox_xyxy": [120, 180, 520, 620]
      },
      {
        "class_id": 3,
        "class_name_ko": "공기밥",
        "confidence": 0.91,
        "bbox_xyxy": [560, 210, 780, 460]
      }
    ],
    "gcv_hints": {
      "labels": ["food", "rice", "stew"],
      "ocr_text": ""
    }
  }
}
```

### Beta fine-tuning 데이터

Beta 목표:

- 우선순위 50개 음식 클래스.
- 클래스당 최소 300장 이상.
- 총 15,000~25,000장.
- train/val/test = 70/15/15.
- bbox annotation을 YOLO format으로 변환.

전체 800클래스/232,087장은 최종 확장용으로 둔다. 처음부터 800클래스를 학습하면 클래스 불균형, annotation 품질, 혼동 클래스 관리 때문에 일정 리스크가 크다.

### 클래스 우선순위

1. MVP mock: 15~20개 대표 음식.
2. Beta v1: 50개 음식.
3. Beta v2: 100~150개 음식.
4. 장기: 전체 800개 클래스.

우선 포함 음식 예시:

- 밥류: 공기밥, 잡곡밥, 볶음밥, 비빔밥, 김밥
- 국/찌개: 김치찌개, 된장찌개, 미역국, 순두부찌개
- 면류: 라면, 칼국수, 냉면, 짜장면
- 단백질/반찬: 계란말이, 불고기, 제육볶음, 닭가슴살, 두부
- 분식/간편식: 떡볶이, 만두, 샌드위치
- 음료: 아메리카노, 라떼, 주스

---

## 🔧 구현 명세

### 1. `src/meal/base.py`

핵심 DTO:

- `BoundingBox`: `x_min`, `y_min`, `x_max`, `y_max`.
- `MealDetection`: YOLO/GCV의 원시 후보.
- `RecognizedMealItem`: 최종 음식 항목.
- `RecognizedMeal`: 식사 전체.

필수 필드:

- 음식명: `name_ko`
- 매칭 코드: `food_code | None`
- 보조 추정량: `estimated_grams`, `estimated_amount` (기본 영양 계산에는 사용하지 않음)
- 신뢰도: `confidence`, `portion_confidence`
- 검토 필요 여부: `needs_user_review`
- 출처: `sources` (`["yolo_v8", "google_vision"]` 등)

### 2. `src/meal/google_vision.py`

Google Cloud Vision은 다음만 담당한다.

- `label_detection`: 음식/접시/그릇 등 label hint.
- `text_detection`: 메뉴판, 영수증, 포장 라벨 등 OCR 텍스트.
- `localized_object_detection`: 일반 객체 hint.

주의:

- GCV label을 최종 음식명으로 직접 확정하지 않는다.
- Service Account JSON은 커밋 금지.
- 실 API 테스트는 `GOOGLE_APPLICATION_CREDENTIALS` 없으면 skip.

### 3. `src/meal/yolo_v8.py`

MVP:

- `MockYoloV8MealDetector`가 `mock_predictions.json`을 읽어 detection 반환.
- 실제 `ultralytics` 의존성은 MVP 필수 아님.

Beta:

- `YoloV8MealDetector`가 `ultralytics.YOLO(model_path)`를 래핑.
- 모델 파일은 `models/meal/yolov8-food.pt` 같은 경로를 사용하되 Git에는 커밋하지 않는다.

### 4. `src/meal/fusion.py`

병합 규칙:

- YOLO class가 `food_aliases.json`에 있으면 primary candidate.
- GCV OCR에 음식명이 있으면 alias confidence를 보강.
- YOLO와 GCV가 충돌하면 YOLO를 우선하되 `needs_user_review=True`.
- 같은 음식이 여러 bbox로 탐지되면 confidence가 높은 항목을 대표로 두고 나머지는 `alternatives`에 보관.

### 5. `src/meal/portion_estimator.py`

MVP 원칙:

- 이미지에서 음식의 실제 섭취량(g)을 정확히 판별한다고 단정하지 않는다.
- 기본 영양 정보는 `PortionEstimator` 결과가 아니라 `RdaMatcher`의 100g 기준 영양 프로필을 사용한다.
- `PortionEstimator`는 UI 참고용/미래 확장용 보조값으로 유지한다.

선택/미래 추정:

- 접시/그릇 bbox가 탐지되면 상대 면적으로 보정.
- 사용자가 직접 g 또는 인분을 입력하면 그 입력값을 기준으로 영양소를 재계산한다.
- 사용자 수정값 저장과 개인화는 Phase 4 이후로 미룬다.

### 6. `src/nutrition/rda_matcher.py`

농진청 식품성분표와 매칭하고 100g 기준 영양 프로필을 만든다.

- `food_aliases.json`: YOLO class name → RDA food_code 후보.
- `korean_foods.csv`: food_code별 1회 제공량과 영양소.
- `nutrient_per_100g = nutrient_per_unit / unit_size_g * 100` 방식으로 정규화.
- 기본 표시값은 100g 기준 영양 프로필이다.
- 사용자가 g를 직접 입력하면 `nutrient_for_amount = nutrient_per_100g * amount_g / 100`으로 계산한다.
- 사용자가 인분 수를 입력하면 `amount_g = unit_size_g * serving_count`로 환산한 뒤 계산한다.
- 매칭 실패 시 항목을 버리지 않고 `needs_user_review=True`로 반환한다.
- `sugar_g`처럼 CSV에 없는 영양소는 특징 문구로 생성하지 않는다.

---

## 🧪 테스트 전략

### Unit

- `test_yolo_v8.py`: mock JSON 로딩, bbox 파싱, confidence 필터.
- `test_google_vision.py`: GCV response mock 파싱, OCR/label hint 추출.
- `test_fusion.py`: YOLO/GCV 병합, 충돌 시 review flag.
- `test_portion_estimator.py`: 기본 1인분, bbox 기반 보정.
- `test_rda_matcher.py`: alias → food_code, 100g 기준 영양소 정규화, 사용자 입력 g/인분 기준 scaling.
- `test_pipeline.py`: 이미지 hash → mock → fusion → 100g nutrition profile 연결 가능성.

### Integration

- `test_meal_image_pipeline.py`: 샘플 이미지 1장과 mock prediction으로 `RecognizedMeal` 생성.
- 실 GCV 테스트는 credential 없으면 skip.
- 실 YOLO 테스트는 model path 없으면 skip.

### 목표 지표

MVP:

- mock 기반 pipeline 테스트 100% 통과.
- 음식 후보/100g 기준 영양 프로필/검토 필요 플래그가 일관된 스키마로 반환.

Beta:

- YOLO `mAP@50 >= 0.75`.
- Top-3 음식 후보 정확도 `>= 0.85`.
- 음식 항목 F1 `>= 0.70`.
- 중량 추정 평균 오차 `<= 30%`.

---

## ✅ Definition of Done

- [ ] `docs/dev-guides/16`가 GCV + YOLOv8 구조로 갱신됨.
- [ ] MVP는 수동 mock 기반으로 동작.
- [ ] `data/meal_vision/mock_predictions.json` 작성.
- [ ] `data/meal_vision/classes.yaml`, `dataset.yaml`, `README.md` 작성.
- [ ] `data/rda/korean_foods.csv` 최소 100종 작성.
- [ ] `data/rda/food_aliases.json` 최소 100종 작성.
- [ ] `src/meal/base.py`, `exceptions.py`, `google_vision.py`, `yolo_v8.py`, `fusion.py`, `portion_estimator.py`, `text_parser.py`, `pipeline.py` 작성.
- [ ] `src/nutrition/rda_matcher.py` 작성.
- [ ] 단위 테스트 25개 이상.
- [ ] 통합 테스트 3개 이상.
- [ ] `black`, `ruff`, `mypy`, `pytest` 통과.
- [ ] 사용자 노출 문구에 진단/처방/치료/보장 표현 없음.

---

## 🚫 이 작업에서 하지 말 것

- ❌ MVP에서 전체 800클래스 YOLO 학습부터 시작.
- ❌ GCV label만으로 음식명을 확정.
- ❌ 사진 기반 추정량을 확정값처럼 표현.
- ❌ "당뇨에 나쁜 음식", "치료 식단" 같은 의료 판단.
- ❌ 모바일 식단 입력 화면 구현. 이는 [`20-mobile-meal-input-screen.md`](./20-mobile-meal-input-screen.md) 범위.
- ❌ FastAPI 라우터 통합. 별도 API 작업에서 처리.

---

## 🔗 관련 문서

- [`06-deficient-nutrient-diagnosis.md`](./06-deficient-nutrient-diagnosis.md) — NutrientIntake, 영양 상태 평가
- [`08-llm-supplement-parsing.md`](./08-llm-supplement-parsing.md) — LLM Adapter 패턴
- [`20-mobile-meal-input-screen.md`](./20-mobile-meal-input-screen.md) — 모바일 식단 입력 UI
