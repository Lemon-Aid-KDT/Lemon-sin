# LEMON-AID 디텍터 최종 인계 (v3 + CLIP)

> ⚠️ 이전에 보낸 패키지는 폐기하세요. **이것이 최종본입니다.**
> 음식 영역 검출(1-class food region). 종류 판별은 분류기(별도). 디텍터는 박스만.

---

## 1. 최종 구성 = v3 + CLIP
| 부품 | 파일 | 역할 |
|---|---|---|
| **디텍터** | `detector_best.pt` (v3) | 음식 영역 박스 검출 |
| **CLIP 필터** | `food_filter.py` | 박스 중 비음식 제거 |

> CLIP 가중치(openai/clip-vit-base-patch16, ~600MB)는 첫 실행 시 HuggingFace에서 자동 다운로드. 인터넷 필요.

## 2. 최종 설정 (이 값 그대로 사용 — 여러 실사진 직접 비교로 확정)
```
Detector conf   = 0.30
NMS IoU         = 0.15      # 다중박스 억제 (겹친 박스 합침)
agnostic_nms    = True      # 1-class라 효과 큼, 다중박스 잡는 핵심
max_det         = 50
imgsz           = 512
CLIP 필터       = ON
  CLIP food 임계값 = 0.25
  CLIP crop padding = 1.00
```

## 3. 추론 흐름
```
사진 → v3 디텍터(conf 0.30, NMS IoU 0.15, agnostic) → 박스들
     → CLIP 필터(임계 0.25, padding 1.0)로 비음식 박스 제거
     → 남은 박스 = 음식 영역 → (분류기로 전달)
```

## 4. 추론 코드 예시
```python
from ultralytics import YOLO
from food_filter import CLIPFoodFilter
from PIL import Image

det  = YOLO("detector_best.pt")
clip = CLIPFoodFilter()

img = Image.open("음식사진.jpg").convert("RGB")
res = det.predict(img, conf=0.30, iou=0.15, agnostic_nms=True, max_det=50, imgsz=512)[0]

boxes = [tuple(map(float, b)) for b in res.boxes.xyxy.tolist()]
W, H = img.size
crops = []
for x1, y1, x2, y2 in boxes:                       # padding 1.0 = 박스 그대로
    crops.append(img.crop((x1, y1, x2, y2)))
mask, scores = clip.filter(crops, threshold=0.25)  # CLIP food 임계 0.25
final_boxes = [b for b, m in zip(boxes, mask) if m]
# final_boxes = 최종 음식 영역 → 분류기로
```

## 5. 데모로 설정 재현/조정
```
python -m streamlit run compare_demo.py --server.port 8504
```
- v3 선택, conf 0.30 / NMS IoU 0.15 / agnostic ON / CLIP ON 0.25 → 위 최종 설정과 동일
- 사진 드래그하면 박스 결과 바로 확인

## 6. 알려진 약점
- 초밥/스시·핑거푸드(판 위 낱개) 약함 — 학습 데이터에 거의 없어서. 일식 커버하려면 데이터 보강 필요.
- 한식 한상은 강함 (실전 한상 8장 기준 mAP50 0.833).

## 7. 동봉 파일
- `detector_best.pt` — v3 디텍터 (최종 모델)
- `food_filter.py` — CLIP 필터
- `compare_demo.py` — 설정 재현/테스트 데모
- `README_디텍터_최종.md` — 이 문서
- `ANNOTATION_GUIDE.md` — 박스 라벨 기준 (평가셋 확장 시)
