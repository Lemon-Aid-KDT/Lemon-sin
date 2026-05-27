# Food-backend

음식 사진 분석 기능의 독립 백엔드 작업 공간입니다.

이 폴더는 `docs/data-yolo-food-detection` 브랜치에서 가져온 식단 이미지 인식
코드와 테스트를 `Nutrition-backend`와 분리해 보관한다. 현재 Lemon-Aid main
API의 OCR/영양제/건강 데이터 endpoint는 `Nutrition-backend`에 남기고, 음식
YOLO/GCV/RDA 실험 코드는 이곳에서 별도로 검증한다.

## 책임 범위

- 음식 이미지 분류 입력 계약
- YOLO food detection 후보 산출
- Google Vision hint 결합
- portion estimation
- 음식명 alias 기반 RDA profile 매칭
- 식단 이미지 분석 unit/integration test

## 구조

```text
Food-backend/
├── src/
│   ├── meal/
│   └── nutrition/
└── tests/
    ├── integration/
    └── unit/
```

## 검증

repo root에서 실행한다.

```bash
python -m pytest \
  backend/Food-backend/tests/unit/meal \
  backend/Food-backend/tests/unit/nutrition/test_rda_matcher.py \
  backend/Food-backend/tests/integration/meal \
  -q --no-cov
```

`Food-backend`와 `Nutrition-backend`는 둘 다 `src` package name을 사용한다.
따라서 두 backend의 tests를 한 pytest 세션에 섞지 않고, 각 backend의
`pyproject.toml` 기준으로 분리 실행한다.

## 데이터 위치

학습/fixture 데이터는 source branch 구조와 호환되도록 repo root의 `data/` 아래에
둔다. 대용량 AIHub 원본/학습 산출물은 커밋하지 않고, 작은 manifest와 mock
fixture만 추적한다.
