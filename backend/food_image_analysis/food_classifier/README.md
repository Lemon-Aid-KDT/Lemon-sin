# 음식 분류기 (단일요리) — exp16b 게이트 + DINOv3 분류 + 영양

사진 한 장(음식 하나)을 받아 **음식 종류 40종 분류 + 영양 정보**를 반환하는 모듈.
실사용(폰사진) 인식률 **0.842** (우리가 학습한 YOLO exp16b 단독 0.598 대비 +0.244).

> 제품 가이드: 사용자에게 **"음식 하나만 나오게 촬영"** 안내. (한상/다중요리는 차기 과제)

---

## 파이프라인

```
사진 → ① exp16b: 음식 있나? (없으면 "다시 찍어주세요")
     → ② DINOv3-vitb16 + 선형프로브: 사진 전체를 40종 분류 (크롭 X)
     → ③ 영양 매핑: class → 영양표(100g)
```

- **왜 전체 이미지 분류(크롭 X)?** 단일요리는 음식이 화면을 채워, 박스로 자르면 맥락(접시·상차림)이 사라져 정확도 하락(크롭 0.72 vs 전체 0.84). 검증됨.
- **왜 exp16b가 필요?** DINO는 "음식 없음"을 못 함(무조건 40종 중 하나). exp16b가 음식 유무 게이트.

## 파일

| 파일 | 역할 | git |
|---|---|---|
| `food_classifier.py` | 핵심 모듈 `FoodClassifier` | ✅ |
| `app.py` | Streamlit 데모 | ✅ |
| `train_probe.py` | 프로브 재학습 스크립트(실데이터 바뀌면) | ✅ |
| `probe_head.pt` (123KB) | 학습된 DINOv3 선형 프로브 | ✅ |
| `probe_classes.json` | 40종 클래스 목록 | ✅ |
| `nutrition/food_nutrition_40class.csv` | 40종 영양표(100g 기준, 웹검증 보정) | ✅ |
| `nutrition/food_nutrition_40class_upsert.sql` | DB(food_nutrition) 삽입용 | ✅ |

## 사전 준비 (git에 없는 것 — 팀원이 직접)

1. **exp16b 모델** (19.5MB, 2MB+ 커밋 금지 규칙 → 파일공유로 받기):
   `runs/food_yolo/exp16b_taxo50_aihubreal_pc1_s42_b16_w8_cache_disk_det_true/weights/best.pt`
   (다른 위치면 `FoodClassifier(exp16b_path=...)`로 지정)
2. **DINOv3 가중치** (HuggingFace 자동 다운로드, ~350MB):
   - ⚠️ **게이트 모델**: huggingface.co에서 `facebook/dinov3-vitb16-pretrain-lvd1689m` 라이선스 동의 + 토큰(`hf auth login` 또는 `HF_TOKEN` 환경변수).
   - ⚠️ **상용 라이선스 별도**: 현재는 성과발표/연구용. **상용 배포 전 DINOv3 라이선스 검토 필요** — 제약 시 DINOv2-large(Apache-2.0, wild 0.826)나 DINOv2-giant(Apache, 0.842, 4.4GB)로 교체 가능(둘 다 `train_probe.py`의 DINO_ID만 바꿔 재학습).
3. **의존성**: `transformers<5` (4.x 필수 — 5.x는 DINOv3 처리 비호환) + `ultralytics`, `torch`, `streamlit`, `pillow`, `pyyaml`.

## 실행 (데모)

```powershell
$env:HF_TOKEN = "hf_..."   # DINOv3 게이트 토큰
python -m streamlit run backend/food_image_analysis/food_classifier/app.py --server.port 8510
```

## 코드에서 사용

```python
from food_classifier import FoodClassifier
from PIL import Image

fc = FoodClassifier()                     # 모델·프로브·영양표 로드 (1회)
r = fc.analyze(Image.open("food.jpg"))
if r is None:
    print("음식이 없어요. 다시 찍어주세요.")
else:
    print(r["name_ko"], f"{r['conf']*100:.0f}%")   # 예: 김치찌개 62%
    if r["nutrition"]:
        print("100g당", r["nutrition"]["kcal_100g"], "kcal")
```

## develop 병합 방법

```bash
# 팀원(리뷰어)
git fetch origin
git checkout develop
git merge --no-ff origin/feat/ai-food-classifier-dino   # 또는 PR로 Squash and Merge
```
- 머지 후 위 "사전 준비"의 exp16b best.pt를 해당 경로에 두고, DINOv3 토큰 설정하면 동작.
- 영양 DB: `nutrition/food_nutrition_40class_upsert.sql`을 food_nutrition 테이블에 실행(팀원 0027 마이그레이션의 taxo59 시드 중 서비스 40종 보정본).

## 성능 (검증)

- 실사용 wild 545장(단일요리, 모델 미학습 제3자 폰사진): top-1 인식률 **0.842**.
- exp16b 단독(우리 YOLO) 0.598 → DINOv3 프로브 0.842 (+0.244).
- ※ "top-1 인식률"은 mAP50과 다른 지표(서비스 시나리오: 사진 1장→음식 1종).
