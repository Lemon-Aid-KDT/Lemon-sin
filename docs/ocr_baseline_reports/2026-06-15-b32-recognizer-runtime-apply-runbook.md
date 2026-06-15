# b32 fine-tuned recognizer — backend OCR runtime 임시 적용 runbook (2026-06-15)

> **목적**: 지금 바로 비교/테스트에 쓸 수 있는 *best-available* PaddleOCR fine-tuned recognition 모델(b32)을 backend local OCR runtime에 연결한다.
> **⚠️ production gate 미통과**: 현재 production을 통과한 모델은 없다. 이 적용은 "best available runtime candidate"이며, 최종 production 전환은 holdout/test structured gate에서 **field_match ≥ 0.85 & ingredient_recall ≥ 0.85**를 통과해야 한다.

## 1. 대상 모델
- 모델: `supplement_rec_crawling_v2_png_sanitized_mixed_lr5e5_b32_20260611_best_accuracy_inference`
- 로컬 경로(host): `outputs/generated/supplement-learning/2026-06-05/operator-review/models/supplement_rec_crawling_v2_png_sanitized_mixed_lr5e5_b32_20260611_best_accuracy_inference` (PaddleOCR 3.x inference: `inference.json` / `inference.pdiparams` / `inference.yml`)
- 컨테이너 마운트 경로: `/app/models/paddle_rec_b32` (docker-compose `volumes`에 `:ro`로 배선됨)
- validation 최고 모델 `v2_clean_p90_fresh_lr2e4_b96`은 inference export/structured gate가 아직 없어 **적용 대상 아님**.

## 2. 확인된 코드 배선 (코드 수정 불필요)
`LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR` → `Settings.local_ocr_text_recognition_model_dir`(config.py) → `PaddleOCRAdapter.extract_text`가 `_get_paddle_predictor(text_recognition_model_dir=...)`로 전달 → PaddleOCR `text_recognition_model_dir` kwarg로 주입(paddle.py:178-179). 선택된 detector/profile은 유지하고 recognizer 가중치만 교체.
det 튜닝 노브는 `_predict_kwargs(settings)`가 `predict()` kwargs로 변환(paddle.py:254-264): `text_det_limit_side_len`/`text_det_limit_type`/`text_det_box_thresh`.

**config dump 검증(실측, Paddle 미로드)**:
```
model_profile           : mobile
detection model name    : PP-OCRv5_mobile_det
recognition model name  : korean_PP-OCRv5_mobile_rec   # custom dir가 가중치 override
text_recognition_model_dir (predictor kwarg): /app/models/paddle_rec_b32
predict() kwargs        : {'text_det_limit_side_len': 2048, 'text_det_limit_type': 'max', 'text_det_box_thresh': 0.4}
```

## 3. 적용 구성 (box040 det-sweep 재현)
| env | 값 | 근거(box040.json) |
|---|---|---|
| `ENABLE_LOCAL_OCR` | `true` | Paddle 사용 전제 |
| `LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR` | `/app/models/paddle_rec_b32` | b32 recognizer 마운트 경로 |
| `LOCAL_OCR_TEXT_DET_BOX_THRESH` | `0.4` | `det_box_thresh = 0.4` |
| `LOCAL_OCR_TEXT_DET_LIMIT_SIDE_LEN` | `2048` | `max_side = 2048` |
| `LOCAL_OCR_TEXT_DET_LIMIT_TYPE` | `max` | 긴 변 2048 상한 |
| `LOCAL_OCR_MODEL_PROFILE` | `mobile`(기본 유지) | box040 `detection_model = PP-OCRv5_mobile_det` → **server_detection 아님**. JSON에서 확인 안 됨 → 적용 안 함 |

> **step 4 결론**: `LOCAL_OCR_MODEL_PROFILE=server_detection`은 box040 eval에서 사용되지 않았다(detection = mobile_det). 사용자 지침대로 **확인된 경우에만 적용** → 미적용(기본 `mobile`).

## 4. 적용 명령 (compose 배선 완료, recreate만 필요)
docker-compose.yml에 ① 3개 env 배선(`LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR`/`..._DET_LIMIT_SIDE_LEN`/`..._DET_LIMIT_TYPE`) ② `/app/models/paddle_rec_b32` :ro 마운트를 추가함(WIP, 미커밋). `.env` 미수정 — shell-env override로 적용(비침습):

```bash
cd "/Volumes/Corsair EX400U Media/yeong_offload/99_me/00_github/03_lemon_healthcare/Lemon-Aid"
ENABLE_LOCAL_OCR=true \
LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR=/app/models/paddle_rec_b32 \
LOCAL_OCR_TEXT_DET_BOX_THRESH=0.4 \
LOCAL_OCR_TEXT_DET_LIMIT_SIDE_LEN=2048 \
LOCAL_OCR_TEXT_DET_LIMIT_TYPE=max \
docker compose up -d backend
```

> **⚠️ Docker Desktop 마운트 주의**: 백엔드 컨테이너 recreate 시 외장드라이브 경로(`/Volumes/Corsair EX400U Media`, 공백 포함)의 bind 마운트가 VirtioFS VM에서 스턱될 수 있다(`mkdir … file exists`). 발생 시 `docker` CLI로는 못 풀고 **Docker Desktop 재시작**(`docker desktop restart`)만이 해결(스택 전체 ~수초 재시작). 새로 추가한 모델 마운트도 같은 외장 경로라 동일 리스크.

적용 후 컨테이너 확인:
```bash
docker exec lemon-aid-backend-1 /opt/venv/bin/python -c \
  "from src.config import get_settings as g; s=g(); print(s.local_ocr_text_recognition_model_dir, s.local_ocr_text_det_box_thresh, s.local_ocr_text_det_limit_side_len, s.local_ocr_text_det_limit_type)"
docker exec lemon-aid-backend-1 sh -c 'ls /app/models/paddle_rec_b32'   # inference.json/.pdiparams/.yml
```

## 5. 검증 (이미 통과)
```bash
cd backend && .venv/bin/python -m pytest Nutrition-backend/tests/unit/ocr/test_paddle_provider.py --no-cov -q   # 21 passed
```
+ §2 config dump(설정→실제 predictor/predict kwargs)로 배선 확인 완료.
실 이미지 live OCR run은 **사적 라벨 이미지 + 수십 초 CPU 추론 + (Clova 켜진 경우) 외부 provider** 호출이라 이 runbook에서는 실행하지 않음. 필요 시 적용 후 컨테이너에서 운영자 비공개 이미지로 별도 측정(수치는 raw OCR/이미지 미출력).

## 6. 롤백
shell-env 없이 `docker compose up -d backend` 재실행(또는 `LOCAL_OCR_TEXT_RECOGNITION_MODEL_DIR=` 빈 값) → 업스트림 mobile recognizer로 복귀. compose의 마운트/배선은 빈 기본값이라 미사용 시 무영향.
