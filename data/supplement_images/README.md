# Supplement Image Dataset

영양제 이미지 데이터셋 작업 공간입니다.

## 분류 흐름

1. 수집원을 `public_sources`, `web_crawl`, `friend_contributed`로 구분한다.
2. 웹 크롤링 데이터는 `supplement_label`, `supplement_bottle`, `blister_pack`, `nutrition_facts_panel`, `non_supplement`, `unknown` 같은 영어 클래스명으로 평탄 저장한다.
3. 영양제 여부, OCR 가능 여부, 언어(`ko`, `en`, `mixed`, `unknown`), 성분/함량/섭취방법 추출 가능 여부는 `manifests/`의 taxonomy와 full manifest에서 관리한다.
4. OCR/ROI 후보 산출물은 `interim/`, 확정 학습 입력은 `processed/`에 둔다.
5. 중복, 저품질, 애매한 라벨은 `quarantine/` 아래로 격리한다.

## 영양제 섹션 YOLO26 detector 계약

영양제 OCR 보조용 YOLO는 음식 탐지 모델이 아니라 라벨 내부 OCR 영역을 찾는
section detector다. Ultralytics detect dataset YAML은 `section_yolo/dataset.yaml`에
고정하고, 실제 이미지/라벨은 `processed/section_yolo/` 아래에 둔다.

필수 class는 다음 4개다.

- `supplement_facts`: 성분표/함량 표
- `precautions`: 주의사항, 경고, 알레르기/알러젠 문구
- `intake_method`: 섭취 방법, suggested use, directions, dosage
- `ingredients`: 기타 원료/성분 선언

학습 전 검증:

```bash
cd backend
.venv/bin/python scripts/validate_supplement_section_yolo_dataset.py ../data/supplement_images/section_yolo/dataset.yaml
.venv/bin/python scripts/validate_supplement_section_yolo_dataset.py ../data/supplement_images/section_yolo/dataset.yaml --require-files
```

첫 번째 명령은 class 계약만 검증한다. 두 번째 명령은 실제 이미지/라벨 파일까지
검증하므로 annotation이 준비된 뒤에 통과해야 한다.

```text
supplement_images/
├── raw/
│   ├── public_sources/
│   ├── web_crawl/{class_name_en}/
│   │   ├── images/{hash}.jpg
│   │   └── metadata.jsonl
│   └── friend_contributed/
│       ├── inbox/
│       └── ingested/
│           ├── images/{hash}.jpg
│           └── metadata.jsonl
├── interim/
│   ├── ocr_candidates/
│   └── roi_candidates/
├── processed/
│   ├── ocr_text/
│   ├── normalized_labels/
│   ├── section_yolo/
│   │   ├── images/{train,val,test}/
│   │   └── labels/{train,val,test}/
│   └── cropped_regions/
├── section_yolo/
│   └── dataset.yaml
├── splits/
│   ├── train.csv
│   ├── val.csv
│   └── test.csv
├── manifests/
│   ├── taxonomy.json
│   ├── classes.json
│   ├── fixtures/
│   └── stats/
├── quarantine/
│   ├── duplicates/
│   ├── low_quality/
│   └── ambiguous/
└── scripts/
```
