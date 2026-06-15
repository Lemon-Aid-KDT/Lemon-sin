# PR — 단일요리 음식 분류기 (exp16b 게이트 + DINOv3 + 영양)

> 브랜치 `feat/ai-food-classifier-dino` → `develop`. PR 본문은 이 문서를 사용.

## 무엇을 했나요
사진 한 장(음식 하나)으로 **음식 40종 분류 + 영양 정보**를 내는 단일요리 음식 분류기 추가.
- `backend/food_image_analysis/food_classifier/` 신설 — 모듈·데모·학습된 프로브·40종 영양표
- 동작: exp16b 음식 유무 게이트 → DINOv3-vitb16 전체 분류(40종) → 영양 매핑(100g)
- 실사용 폰사진 인식률 0.842 (기존 우리 YOLO exp16b 단독 0.598 대비 +24%p)

## 왜 했나요
- 우리가 학습한 YOLO(exp16b)는 실사용 사진에서 0.598에 그침(스튜디오↔실사용 도메인갭).
- 웹 사전학습 DINOv3 특징 + 실데이터 선형학습이 0.842로 +24%p 개선.
- 단일요리는 전체 이미지 분류가 크롭보다 정확(0.84 vs 0.72) → 사용자 "한 음식만 촬영" 가이드 전제.

## 어떻게 검증했나요
- [ ] 단위 테스트 (미추가 — smoke test / Streamlit AppTest로 대체)
- [x] 로컬에서 동작 확인 (스모크: 회 0.50 + 영양 114kcal/100g, AppTest 통과)
- [ ] CI 통과 (PR 후 확인)

## 영향 범위
- [ ] mobile
- [x] backend (`food_image_analysis/food_classifier/`)
- [x] ai (DINOv3 분류기 + 학습 프로브)
- [x] data (40종 영양표 CSV + DB upsert SQL)
- [x] docs (모듈 README·PR_NOTES — PROJECT_GUIDE §14는 보류, 아래 참조)

## 📋 변경 파급 효과 점검 (§17.10 표 참조)
- [ ] **PROJECT_GUIDE.md §14 — ⏸ 보류**: guide.html 동기화 도구(`scripts/sync_guide.py`)가 현재 guide.html의 md-source 블록을 못 찾아 동작 안 함(사전 인프라 이슈). 도구 수정 후 문서 담당자가 §14에 `food_image_analysis/food_classifier` 추가 권장. 모듈은 본 폴더 README·PR_NOTES로 문서화됨.
- [ ] §11 데이터 모델 — food_nutrition은 팀원 0027 테이블, 본 PR은 보정 데이터 upsert SQL 동봉
- [ ] §9 호출 흐름 — 해당 없음(독립 모듈)
- [ ] §15.1 / §16.5 CODEOWNERS — 해당 없음
- [x] requirements — 모듈 전용 `food_classifier/requirements.txt` 추가(메인 requirements.txt는 미존재)
- [ ] .env / 시크릿 — DINOv3 게이트용 `HF_TOKEN` 필요(개인 토큰, 레포 시크릿 아님)
- [ ] guide.html — 미수정(PROJECT_GUIDE 미변경 + 동기화 도구 이슈)
- [ ] 해당 없음

## 리뷰어가 봐야 할 곳
- `food_classifier.py` → `analyze()`: 탐지 게이트 → **전체 이미지** 분류(크롭 X) → 영양
- `README.md`: 모델 준비물(exp16b 파일공유·DINOv3 토큰)·**상용 라이선스 주의**·병합법

## 스크린샷 / 로그
- 스모크: `회 0.50 | 100g 114.61 kcal`

## 병합 전 준비물 (git에 없음)
1. **exp16b best.pt** (19.5MB, 파일공유) → `runs/food_yolo/exp16b_taxo50_aihubreal_.../weights/best.pt`
2. **DINOv3** — HF 게이트 모델: 라이선스 동의 + `HF_TOKEN`. 첫 실행 시 ~350MB 자동 다운로드.
3. `pip install -r backend/food_image_analysis/food_classifier/requirements.txt` (transformers<5 포함)
4. 영양 DB: `nutrition/food_nutrition_40class_upsert.sql`을 `food_nutrition` 테이블에 실행.

## ⚠️ 주의
- **DINOv3 상용 라이선스 별도** — 현재 발표/연구용. 상용 배포 전 검토 필요(제약 시 DINOv2-large/giant = Apache-2.0, 0.826/0.842로 교체 가능: `train_probe.py`의 `DINO_ID`만 바꿔 재학습).
- 0.842는 "top-1 인식률"(사진 1장→음식 1종)로 mAP50과 다른 지표.
- 다중요리(한상)는 차기 과제(현재 단일요리 전용).

**PR 크기**: ~10 파일 / 코드 ~250줄 (+영양 SQL 31KB·바이너리 프로브 123KB). **머지: Squash and merge.**
