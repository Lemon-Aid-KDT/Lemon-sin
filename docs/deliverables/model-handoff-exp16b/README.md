# exp16b 모델 인수인계 — 앱 적용 가이드 (지원 40클래스)

> 대상: 앱에 음식 탐지 모델을 통합하는 팀원. 2026-06-12.

## 핵심 한 줄

**best.pt(50클래스)는 그대로 쓰고, 추론 호출에 지원 40클래스 필터 한 줄만 넣으면 됩니다.**
재학습·모델 변환 불필요 — 필터 방식은 실사용 사진 739장에서 검증됨(지원 클래스 결과 변화 0).

## 파일 구성

| 파일 | 설명 |
|---|---|
| `best.pt` | **직접 복사 필요** (git에 없음 — 2MB+ 커밋 금지 규칙): `C:\Lemon-sin\runs\food_yolo\exp16b_taxo50_aihubreal_pc1_s42_b16_w8_cache_disk_det_true\weights\best.pt` (19.5MB) |
| `exp16b_deploy_config.json` | 클래스 50개 전체 이름(인덱스 순서), 지원 40클래스 인덱스/이름, 미지원 10클래스, 권장 conf(0.10) — **모델에서 직접 추출한 값** |
| `food_predictor.py` | 통합 예시 래퍼 (`predict_top1` / `predict_all`) |

## 통합 방법 (셋 중 하나)

### ① ultralytics 직접 사용 — 가장 간단 (권장)

```python
import json
from ultralytics import YOLO

cfg = json.load(open("exp16b_deploy_config.json", encoding="utf-8"))
model = YOLO("best.pt")

results = model.predict(image, conf=0.10, classes=cfg["supported_class_indices"])
# classes 인자가 미지원 10클래스를 추론 단계에서 제외 → 결과에 절대 안 나옴
```

### ② 래퍼 사용

```python
from food_predictor import FoodPredictor

fp = FoodPredictor("best.pt")
top1 = fp.predict_top1("photo.jpg")    # None이면 "인식하지 못했어요" 안내
foods = fp.predict_all("photo.jpg")    # 다중 음식
```

### ③ ONNX/TFLite 등으로 export하는 경우

- export는 50클래스 **그대로** 진행 (출력 텐서의 클래스 차원 = 50).
- 앱 후처리에서 `excluded_class_names`에 해당하는 **인덱스의 박스를 버리면** 됨.
- ⚠️ 라벨 파일에서 10개를 "삭제"하면 안 됨 — **인덱스 순서가 어긋나면 전부 오답**이 됩니다.
  라벨 파일은 50개 전체(`names` 순서대로)를 유지하고, 허용 목록으로 필터링하세요.

## 앱 UX 규칙 (발표 내용과 일치시키기)

1. **음식 미인식** (박스 없음 또는 conf < 0.10): "음식을 인식하지 못했어요. 다시 찍어주세요." + 직접 선택 유도.
2. **미지원 10종**은 필터 덕분에 결과에 절대 나타나지 않음. 단, 사용자가 미지원 음식을 찍으면 ①"인식 불가"로 빠지거나 ②**비슷한 지원 음식으로 표시될 수 있음** → 그래서 3·4번의 사용자 확인·보정 UX(결과 확인 후 직접 수정/선택)가 안전망이며 반드시 유지해야 함.
3. **영양 매핑**: 클래스명 기준 조인 — `data/food_images/manifests/class_nutrition_taxo59.csv` (100g 정규화, 1인분 250g 환산은 앱 단).
4. AI 결과는 사용자가 직접 확인·보정 가능해야 하며, 건강 참고용(진단·처방 아님) 문구 유지.

## 왜 이 방식인가 (Q&A 대비)

- 모델 헤드는 50클래스로 학습됐지만, 미지원 10클래스 출력을 막아도 **나머지 40클래스의 예측은 1장도 바뀌지 않음**을 실사용 사진 739장 전수 시뮬레이션으로 확인했습니다 (이 10클래스가 다른 음식의 정답을 가리는 경우가 0건).
- 따라서 "40클래스 재학습 모델"과 "50클래스 + 필터"는 지원 범위 내에서 동일하게 동작하며, 후자가 재학습 리스크·비용 없이 즉시 적용 가능합니다.
- 미지원 10종은 실데이터 보강(이미 313장 수집) 후 재학습 시 재포함 예정 — 그때는 새 best.pt + 갱신된 config만 교체하면 됩니다.

## 성능 참고 (실사용 기준)

- top-1 인식률 (wild 실폰사진, 지원 40클래스, n=545): **0.598** [95% CI 0.558~0.637]
- 음식 위치 탐지율 (conf≥0.10): **96.3%** (712/739)
- 검증셋 mAP50 (studio, 별개 지표): 0.922
