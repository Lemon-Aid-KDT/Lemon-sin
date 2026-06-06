# realworld_collected_v1 — 실환경 수집 학습셋 (2026-06-06)

> 팀 수집(team_collected) + 웹 크롤(web_crawl) 실환경 사진을 **LLM 비전으로 검수**(단일요리+taxo59 매칭)하고 **박싱·group-split**한 첫 실데이터 학습셋. selectstar로 못 채우던 한식 클래스에 진짜 실데이터를 채우는 시작점.

## 구성
- **train 1,379 / val 413 = 1,792장 / 59클래스** (`data/food_images/processed/realworld_collected_v1/`, YOLO det 형식)
- 출처: **team_collected** KEEP 1,449 (3,949장에서 단일요리+클래스매칭만, 37%) + **web_crawl** KEEP 343 (395장, 87%)
- 박스: **exp11 best.pt 모델박스 1,657(92%)** + 단일요리 center fallback 135(8%). 클래스 = VLM 판정.
- **group-split**(누수 방지): team=세션id(`orig_..._<10digit>_p_`)/파일명, web=folder/file. 같은 group은 train/val 안 갈림. 클래스별 ~15% val(이미지<7이면 전부 train).

## 검수 핵심 (왜 VLM 검수가 필수였나)
- team_collected: 63% 드롭 — 닭가슴살 다이어트식·제육볶음·오므라이스·한상차림(59밖/멀티).
- web_crawl 노이즈: **cold-ramen 폴더는 42%만 실제 냉라멘**, 나머지 26장은 뜨거운 일본라멘 → japanese-ramen으로 정확히 재분류(폴더 라벨 그대로 썼으면 오염).

## ⚠️ gitignore / 재생성
- **데이터셋 이미지·라벨은 `data/food_images/` 라 git 미추적**(대용량). 이 저장소엔 **재생성 스크립트 + 검수 매니페스트**만 커밋.
- 재생성: `python docs/superpowers/plans/exp06_review/_build_realworld_collected.py` (team_keep_list.txt·web_crawl_keep_list.txt + exp11 모델 필요).
- 매니페스트(이 폴더에 사본 커밋): `team_collected_classification.csv`·`web_crawl_classification.csv`·`*_keep_list.txt`.

## 한계 / TODO
- **박스 = 모델생성**(SAM2 도입 시 더 tight). fallback 135장은 center box.
- **group 적은 클래스는 split 불균형**(예: seaweed-rice-roll 37/44 — 김밥 세션이 통째 val로, 누수방지 결과). 정상이나 학습 비율은 비균형.
- **thin 클래스**(seafood-clear-tang 3, 순대·된장찌개·샌드위치·햄버거·양식수프 4~5) → 계속 수집.
- 라벨은 **VLM 파생**(고품질, spot-check 권장).
- ⚠️ **friend_contributed 783(wild 평가셋)과 섞지 말 것**(평가 누수). 이 데이터셋의 val은 자체 group-split분.

## 다음
- 더 수집(thin 클래스 우선) → v2. AIHub+selectstar와 혼합 학습(균형 주의). SAM2 박싱. group-split을 출처 더 정교하게.
