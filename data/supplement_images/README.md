# Supplement Image Dataset

영양제 이미지 데이터셋 작업 공간입니다.

## 분류 흐름

1. 수집원을 `public_sources`, `web_crawl`, `friend_contributed`로 구분한다.
2. 웹 크롤링 데이터는 `supplement_label`, `supplement_bottle`, `blister_pack`, `nutrition_facts_panel`, `non_supplement`, `unknown` 같은 영어 클래스명으로 평탄 저장한다.
3. 영양제 여부, OCR 가능 여부, 언어(`ko`, `en`, `mixed`, `unknown`), 성분/함량/섭취방법 추출 가능 여부는 `manifests/`의 taxonomy와 full manifest에서 관리한다.
4. OCR/ROI 후보 산출물은 `interim/`, 확정 학습 입력은 `processed/`에 둔다.
5. 중복, 저품질, 애매한 라벨은 `quarantine/` 아래로 격리한다.

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
│   └── cropped_regions/
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
