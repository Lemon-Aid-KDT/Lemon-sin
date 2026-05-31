# 음식 분류 카스케이드 — 1단계: is_food 게이트

`output/stage1/{food,not_food}` 의 라벨로 **"음식이냐 아니냐"** 를 판별하는
경량 분류기를 학습한다. 앱에서 사용자가 사진을 올리면 이 게이트를 먼저 통과시키고,
음식이 아니라고 판단되면 **"다시 촬영"** 을 요청한다.

## 설계: 공유 백본 + 경량 헤드

```
사진
 └─ CLIP ViT-L/14 (frozen, 무거움 — 딱 1번 실행) ──▶ 768차원 임베딩
                                                      ├─▶ [is_food 헤드]  ← 지금 단계
                                                      ├─▶ [cuisine 헤드]  ← 다음 단계
                                                      ├─▶ [meal 헤드]
                                                      └─▶ ...
```

- 무거운 백본은 **한 번만** 돌고, 각 단계는 그 벡터를 받는 **수십 KB짜리 로지스틱 회귀**.
- "여러 경량 모델을 겹친다"는 구조 그대로 — 헤드를 독립적으로 추가/교체 가능.
- GPU 없이 CPU만으로 학습/추론 가능 (CNN fine-tune 대비 학습이 수 초로 끝남).

## 파일

| 파일 | 역할 |
|------|------|
| `clip_features.py` | 공유 CLIP 백본. 이미지 → 768차원 임베딩 (모든 단계가 재사용) |
| `01_extract_embeddings.py` | food/not_food 이미지를 임베딩으로 변환해 캐시 (느린 1회성, 재시작 가능) |
| `02_train_is_food.py` | 임베딩으로 로지스틱 회귀 헤드 학습·평가·저장 |
| `predict.py` | 추론 모듈. 이미지 → **음식일 확률**만 반환 (`FoodClassifier`) |
| `app.py` | **Streamlit 제어판**. 임계값 조절 + 통과/재촬영 판정 (제어·UX 담당) |
| `embeddings/is_food.npz` | 임베딩 캐시 (자동 생성) |
| `models/is_food_head.joblib` | 학습된 헤드 (자동 생성) |
| `models/is_food_head.json` | 메타데이터(정확도, 추천 임계값 등) |

> **역할 분리**: 파이썬(`predict.py`)은 **모델 추론(확률 계산)만** 한다.
> "임계값을 넘었나 / 재촬영을 요청할까" 같은 **제어·UX는 Streamlit(`app.py`)** 이 담당한다.

## 실행 순서

```powershell
conda activate dl_env   # torch / transformers / sklearn / streamlit 설치된 환경

# ① 임베딩 추출 (CPU에서 ~2장/초, 6000장/클래스면 약 100분. 재시작 가능)
python classifier/01_extract_embeddings.py

# ② 학습 + 평가 (수 초)
python classifier/02_train_is_food.py

# ③ Streamlit 앱에서 성능 조절하며 음식 여부 확인
streamlit run classifier/app.py
```

### 추출 장수 조절
`01_extract_embeddings.py` 의 `LIMIT_PER_CLASS`(기본 6000) 또는
환경변수로 조절:
```powershell
$env:IS_FOOD_LIMIT = "3000"   # 더 빠르게
$env:IS_FOOD_CACHE = "...별도경로.npz"   # 캐시 위치 변경
```

## 게이트 임계값

`02_train` 이 임계값별 동작표를 출력한다.

- **임계값↑** → not_food 오통과는 줄지만, 진짜 음식인데 재촬영 요청이 늘어남.
- 헬스케어 앱은 "비음식 통과"가 더 위험하므로 **0.6~0.7** 권장 (메타에 0.6 저장).
- 운영하면서 재촬영 요청율이 너무 높으면 낮추면 됨.

## 라벨 노이즈 검수

현재 라벨은 CLIP 제로샷 결과라 100% 정답은 아니다.
`02_train` 이 **"라벨 오류 의심"** 목록(모델이 강하게 반대한 예시)을 출력하므로,
그 이미지들만 눈으로 확인해 폴더를 바로잡으면 정확도 상한이 올라간다.

## 연동 — Streamlit / 백엔드

모델은 확률만 주고, 통과/재촬영 판정은 호출하는 쪽이 한다.

```python
from predict import FoodClassifier

clf = FoodClassifier()              # CLIP 백본 1회 로드
prob = clf.predict_image(pil_img)   # 0.0 ~ 1.0

if prob >= threshold:               # threshold 는 UI 슬라이더 값
    ...  # 다음 단계(메뉴/칼로리)로
else:
    ...  # 사용자에게 '다시 촬영' 안내
```

Streamlit 앱(`app.py`)이 위 로직을 슬라이더로 조절하며 보여준다.
나중에 FastAPI 백엔드도 같은 `FoodClassifier` 를 임포트해 쓰면 된다.

`Lemon-sin` 의 taxonomy(한/양/중/일/기타 × main/soup/side/dessert)에 맞춰
다음 단계는 같은 `clip_features` 임베딩 위에 **cuisine 헤드 / meal 헤드** 를
똑같은 방식(`0x_train_*.py`)으로 추가하면 된다.
