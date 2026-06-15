# YOLO Section 205 BBox Review Runbook (2026-06-14)

> 목적: `blocked_by_annotation_review` 상태인 supplement section detector 학습 게이트를 해소하기 위해 205개 사적 이미지에 섹션 bbox를 수동 주석하고, 학습 export 직전 preflight/promotion까지 진행한다.

## 현재 상태

- 대상 bundle: `outputs/generated/supplement-learning/2026-06-05/operator-review/yolo-section-annotation-bundle/`
- 현재 preflight: `pending_human_bbox_review=205`, `blank_box_row_count=205`, `valid_accepted_row_count=0`
- 다음 operator action: `complete_supplement_section_bbox_review`
- A100 학습은 아직 실행 금지. 205행 전부 review/pass 후에만 진행한다.

## 라벨

| Label | 의미 |
|---|---|
| `product_identity` | 제품명, 브랜드, 전면 라벨, title block |
| `supplement_facts` | Supplement Facts 또는 Nutrition Facts 전체 패널 |
| `ingredient_amounts` | 성분명, 함량, 단위, daily value 표 셀 |
| `precautions` | 주의사항, 알레르기, contraindication, consult-doctor 문구 |
| `intake_method` | 섭취 방법, 용법, serving instruction |
| `other_ingredients` | 기타 원료, inactive ingredients, capsule shell, additives |
| `functional_claims` | 기능성/마케팅 claim, certification, benefit text |

## Label Studio 방식 권장

Label Studio 공식 문서 기준 `Image` tag는 image annotation 결과를 원본 이미지 기준 0-100 percentage 좌표로 저장하고, `RectangleLabels`는 image bbox용 labeled rectangle을 생성한다.

- Image tag: https://labelstud.io/tags/image.html
- RectangleLabels tag: https://labelstud.io/tags/rectanglelabels.html

1. Label Studio 프로젝트 생성
2. Labeling config에 아래 파일 내용 붙여넣기
   - `outputs/generated/supplement-learning/2026-06-05/operator-review/yolo-section-annotation-bundle/label-studio-config.xml`
3. task import
   - `outputs/generated/supplement-learning/2026-06-05/operator-review/yolo-section-annotation-bundle/label-studio-tasks.json`
4. 205개 task에 필요한 섹션 bbox를 모두 그림
5. Label Studio에서 JSON export

주의:
- 이미지가 표시되지 않으면 bundle 루트에서 static server를 띄우고, task의 `data.image`를 `http://127.0.0.1:<port>/images/...` 형태로 변환한 copy를 import한다.
- 최종 pipeline은 image URL이 아니라 `fixture_id`와 export된 rectangle 결과만 사용한다.

## 변환

Label Studio export를 annotation JSONL로 변환한다. 이 단계는 bbox가 있는 row만 `accepted_for_training`으로 바꾸고, 빈 row는 pending으로 남긴다.

```bash
cd /Volumes/Corsair\ EX400U\ Media/yeong_offload/99_me/00_github/03_lemon_healthcare/Lemon-Aid

backend/.venv/bin/python backend/scripts/convert_label_studio_yolo_annotations.py \
  --label-studio-export outputs/generated/supplement-learning/2026-06-05/operator-review/yolo-section-annotation-bundle/label-studio-export.json \
  --template outputs/generated/supplement-learning/2026-06-05/operator-review/yolo-section-annotation-bundle/annotation.todo.jsonl \
  --output outputs/generated/supplement-learning/2026-06-05/operator-review/yolo-section-annotation-bundle/annotation.reviewed.jsonl \
  --apply
```

## Preflight

전부 review 되었는지 strict preflight로 확인한다.

```bash
cd /Volumes/Corsair\ EX400U\ Media/yeong_offload/99_me/00_github/03_lemon_healthcare/Lemon-Aid/backend

PYTHONPATH=Nutrition-backend .venv/bin/python scripts/preflight_supplement_yolo_annotation_decisions.py \
  --template ../outputs/generated/supplement-learning/2026-06-05/operator-review/yolo-section-annotation-bundle/annotation.reviewed.jsonl \
  --output ../outputs/generated/supplement-learning/2026-06-05/operator-review/yolo-section-annotation-bundle/annotation-preflight.reviewed.strict.json \
  --require-all-reviewed
```

PASS 기대값:
- `template_row_count=205`
- `valid_accepted_row_count=205`
- `pending_review_row_count=0`
- `blank_box_row_count=0`
- `ready_for_requested_promotion=true`

## Promotion

Strict preflight 통과 후에만 YOLO detect export와 source map을 만든다.

```bash
cd /Volumes/Corsair\ EX400U\ Media/yeong_offload/99_me/00_github/03_lemon_healthcare/Lemon-Aid/backend

PYTHONPATH=Nutrition-backend .venv/bin/python scripts/promote_supplement_yolo_annotation_template.py \
  --template ../outputs/generated/supplement-learning/2026-06-05/operator-review/yolo-section-annotation-bundle/annotation.reviewed.jsonl \
  --output ../outputs/generated/supplement-learning/2026-06-05/operator-review/yolo-section-annotation-bundle/supplement-section-yolo-detect-export.json \
  --source-map ../outputs/generated/supplement-learning/2026-06-05/operator-review/yolo-section-annotation-bundle/supplement-section-yolo-detect-export.source-map.json \
  --summary ../outputs/generated/supplement-learning/2026-06-05/operator-review/yolo-section-annotation-bundle/supplement-section-yolo-detect-export.summary.json \
  --source-run-id 2026-06-05-crawling-image-refresh
```

## 다음 단계

Promotion 이후에만 아래 순서로 진행한다.

1. `materialize_supplement_section_yolo_dataset.py`
2. `validate_supplement_section_yolo_dataset.py --require-files`
3. `gate_supplement_yolo_section_dataset.py`
4. 사용자 승인 후 A100 `yolov8s.pt` 우선 재학습

## 금지

- raw OCR text, provider payload, absolute private path, product folder literal 저장 금지
- 빈 bbox row를 accepted 처리 금지
- 2026-06-09 `yolo26s` 임시 배선 금지
- 300 epoch no-early-stop 재학습 금지
