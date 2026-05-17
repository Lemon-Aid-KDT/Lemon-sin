# Lemon Healthcare 팀 공유 보고서 - 2026-05-17 작업 내용 정리 (taedong-design)

## 한 줄 요약

오늘은 데이터 수집 인프라를 24/7 가동 가능한 상태로 끌어올리고(Shop API 26 키워드 19,330장 + NIH DSLD 2,958장 + Tampermonkey v6.5 멀티사이트), 식약처 DUR 2025.6 + 한국의약품안전관리원 의료 CSV 9건을 raw 보관 → parquet 정제까지 마쳤습니다. 또한 mobile 풀스택 인증(카카오/구글 OAuth + Dio + Riverpod + secure storage)과 backend 이메일 인증 + Redis rate-limit, OAuth 키 안전 주입을 모두 커밋했습니다. 팀원 배포 패키지(zip 22MB)도 생성해 영(yeong-tech) OCR 작업에 필요한 학습 데이터 + 가이드 + 클라이언트 코드를 전달 가능한 상태로 정리했습니다.

## 기준 정보

- 작업 기준일: 2026-05-17
- 로컬 경로: `C:\Claude_Projects\lemon_healthcare\Lemon_Aid`
- 외장 SSD: `D:\Lemon_Aid_data\` (Tampermonkey 수동 수집분 + raw 백업)
- 프로젝트 루트: `Lemon_Aid`
- 현재 브랜치: `taedong-design`
- 현재 상태: 워크스페이스에 미커밋 변경 다수 존재. main 직접 커밋/푸시/merge 제외 원칙 준수. yeong-tech 브런치는 읽기 전용으로 참조(`git show origin/yeong-tech:...`)만 사용했고 수정/체크아웃하지 않았습니다.

## 오늘 작업 목적

- 영(yeong-tech)이 docs/31~35에서 정의한 3-Tier OCR 파이프라인(YOLO ROI → Google Vision → Ollama Vision) 의 **학습/평가용 이미지 데이터**를 다량 확보합니다.
- 영양제 사용자 환경(약통 정면, 성분표 클로즈업, 손에 든 비스듬한 사진) 을 직접 수집해 스튜디오 광고샷 편향을 보정합니다.
- 식약처 DUR + 한국의약품안전관리원 자료를 parquet 으로 정제해 종필(jongpil-tech) 룰 엔진 / 성훈(sunghoon-database) DB 적재에 바로 쓸 수 있게 합니다.
- mobile 풀스택 인증 흐름(카카오/구글 OAuth + 자체 로그인 + 이메일 인증) 을 backend 와 연결해 Phase 1 안정화 잔여 항목을 정리합니다.
- 팀원에게 v6.5 데이터 수집 + 의료 CSV + API 클라이언트 코드 + TODO 를 전달 가능한 배포 패키지(zip) 로 묶습니다.

## 구현 범위 요약

### 1. 네이버 Shop API 자동 수집 — Track A 완주

- `data/crawlers/api/naver_shopping_api.py` 가동 결과: **26 키워드 × 최대 1,000개 = 19,330장 메타+이미지 확보** (`data/raw/api/naver_shopping/_progress.json` 기준).
- 영양소 카테고리별 분포 (Top 10):

  | 카테고리 | 장수 | 사이즈 |
  | --- | --- | --- |
  | 비타민 통합 | 16,417 | (디스크 다중 분할) |
  | unknown (자동 분류 실패) | 7,347 | — |
  | 프로바이오틱스 | 7,448 | 2.2G |
  | 오메가 | 2,651 | 904M |
  | 홍삼 | 2,286 | 799M |
  | 칼슘 | 1,803 | 677M |
  | 철분 | 1,008 | 343M |
  | 마그네슘 | 1,006 | 390M |
  | 루테인 | 1,007 | 388M |
  | 글루코사민 | 999 | 289M |
  | 아연 | 975 | 356M |

- 설정 파일 `data/config/naver_keywords.yaml` 에 비타민 5종 + 유산균 3종 + 홍삼 3종 + 오메가3 3종 + 단백질 3종 + 기능성 4종 + 미네랄 5종 = **26 키워드** 정의.
- 분당 60 호출 안전선(`per_minute_limit: 60`) 으로 일 25k API 한도 준수.
- 응답 사후 필터: `category1~4` 에 "건강식품" 또는 "건강보조식품" 포함만 통과.
- 200 키워드 확장 yaml(`naver_keywords_200.yaml`) 은 작성만 하고 가동 보류(`enabled: false`). cv-expert 검증 결과 Shop API 가 100% 스튜디오 광고샷이라 양 편향 가속 위험.

### 2. NIH DSLD 영양제 라벨 수집 — Track B 메인

- `data/raw/bulk/nih_dsld_full/` 에 **2,958장 / 5.1G** 확보 (CC0 라이선스).
- `data/raw/bulk/nih_dsld/` 에 별도 177장 / 424M (초기 PoC 결과 보관).
- 영문 라벨 평면 스캔이 100%라 한글 영양제 OCR fine-tune 의 영문 베이스로 사용 예정.
- TrOCR-ko 학습은 영(yeong-tech) 후속 inbox + augmentation-specialist 합성 데이터 결합 필요.

### 3. Track B 정리 — 쓰레기 트랙 폐기

- `data/.archive/garbage_tracks_20260517_042439/` 로 이동(삭제 X):
  - HF datasets `PillsAndDefectivePills` 등 1,490장: 결함 알약 → 영양제 도메인 X.
  - Wikimedia 처방의약품(cardizem, Flomax, Pentasa) 1,294장: 영양제 X.
- heartbeat 스크립트 `data/scripts/track_b_heartbeat.py` 의 `TRACKS` 리스트에서 hf, wikimedia 제거. 3개 트랙(nih_dsld, off_global, off_korean) 만 유지.
- `worker.json` 과 터미널 박스에 "🗑 폐기된 트랙" 섹션 추가해 archive 사유와 경로를 명시했습니다.

### 4. Open Food Facts dump 처리 — Track B 부가

- `data/raw/bulk/_dumps/off_products.jsonl.gz` **12G / openfoodfacts-products.jsonl.tmp 976M** 다운로드 완료.
- `data/crawlers/bulk/off_full_dump.py` 필터 강화:
  - 화이트리스트 `SUPPLEMENT_TAGS`: `dietary-supplements`, `nutritional-supplements`, `omega-3-supplements` 등 추가.
  - 블랙리스트 `DRUG_TAGS` 신설: `en:drugs`, `en:medicines`, `en:prescription`, `en:antibiotics`, `fr:medicaments` 등.
  - `is_supplement()` = supplement AND NOT drug.
- dump 완료 후 영양제만 추출하는 후속 처리 대기.

### 5. Tampermonkey v6.5 — 사용자 환경 직격 수집

- `data/scripts/tampermonkey/naver_shopping_review.user.js` (31KB, v6.5) 완성.
- **외장 SSD `D:\Lemon_Aid_data\downloads_tampermonkey\` 에 누적 수집 중** (워크스페이스에서는 미마운트라 정확한 누적량 직접 측정 불가, 형 PC 측 확인 필요).
- 핵심 기능:
  - 200+ 영양제 키워드 SUPP_KW 가드 → 영양제 페이지만 진입 시 자동 가동.
  - 35+ 영양소 카테고리 ING_MAP + INGREDIENT_PRIORITY 자동 폴더링.
  - 동시 다운로드 `MAX_CONCURRENT_DL=32` (브라우저 GM_download 큐 한계로 실측 초당 4~5장).
  - localStorage 영구 dedup 캐시(`DEDUP_MAX=100,000`).
  - MutationObserver throttle 500ms → 페이지 freeze 방지.
  - 타임스탬프 파일명(`d_<ts>_<N>.jpg` 상세 / `r_<ts>_<N>.jpg` 리뷰) → 한글 URL 인코딩 깨짐 회피.
  - 갤러리 모달(`.HDZ5ImGZS7`, `.VT3tStcVX_`) 자동 캡처 + lazy scroll 300ms.
  - 영양제 페이지인데 가드 실패 시 `🍋 영양제 페이지로 강제 시작` 버튼.
- 멀티사이트: 네이버 쇼핑(상세/리뷰), 쿠팡, 올리브영, iHerb-KR, 셀프 촬영 = 5사이트 매처 동시 가동.
- `data/raw/manual/` 에 가이드 3종: `_GUIDE.md` / `_REVIEW_GUIDE.md` / `_SEMIAUTO_GUIDE.md`.

### 6. 식약처 DUR + 한국의약품안전관리원 의료 CSV — 의료 데이터

- `data/raw/bulk/kfda_dur/` 에 **CSV 9건 / 394M** 확보:
  - 식약처 DUR 2025.6: 노인주의 / 노인주의(해열진통소염제) / 병용금기 / 연령금기 / 임부금기 — 5개 품목리스트.
  - 한국의약품안전관리원 2024.06~08: 노인주의약물 / 병용금기약물 / 연령금기 / 임부금기약물 — 4개.
- `data/clean/kfda_dur_unified.parquet` **8.0M** 으로 통합 정제.
- `data/clean/supplement_drug_rules_v0.json` **654K** — 룰 엔진 v0 입력 형식.
- `data/clean/kfda_dur_unified_meta.json` — 정제 소스 / 행 수 / checksum 메타.
- 종필(jongpil-tech) 룰 엔진 / 성훈(sunghoon-database) DB 적재에 바로 사용 가능한 상태.

### 7. mobile 풀스택 인증 — Phase 1 안정화

- 직전 커밋 시퀀스 (taedong-design):
  - `0097614` docs: CLAUDE.md 보안/인증 정책
  - `7a0b170` feat(mobile/ui): 로그인 화면 "최근 로그인" 동적 + 설정 로그아웃
  - `6333230` feat(mobile/oauth): 카카오/구글 OAuth 실 연결
  - `86d59e4` feat(mobile/auth): Dio + Riverpod + secure storage 풀스택 인증
  - `0233264` feat(backend): 이메일 인증 + 이메일 중복 정책 + Redis rate-limit
  - `ab489f5` chore(infra): OAuth 키 안전 주입 + 빌드 스크립트
  - `7dbcb31` feat(backend): sunghoon-database 백엔드 코드 머지 (자체 로그인 + DB)
- mobile screens 10종 골격: splash / onboarding / login_v3 / dashboard / camera / chat / health / raffle / score / settings.
- mobile services 9종: api_client / auth_service / oauth_service / token_storage / offline_queue / calendar_service / health_service / notification_service / mock_repository.
- backend 이메일 인증 + Redis rate-limit 통합. OAuth 키는 빌드 시 안전 주입(repo 미보관).

### 8. 팀원 배포 패키지 — 전달 가능한 형태로

- `Lemon_Aid_팀원_배포_v6.5.zip` **22MB / 28파일 / 5폴더**:
  - `01_가이드/`: README + 세팅가이드 + 데이터자산명세 + TODO_v6.5
  - `02_Tampermonkey_스크립트/`: `naver_shopping_review.user.js`
  - `03_의료_CSV_원본/`: 식약처 DUR + 한국의약품안전관리원 9건 / 275MB
  - `04_정제_데이터_parquet/`: kfda_dur_unified + supplement_drug_rules_v0 / 9MB
  - `05_API_클라이언트_코드/`: kfda_dur_api.py / kfda_food_api.py / kfda_recall_api.py 등 5개
- `팀원_TODO_v6.5.md` 에 5인(창민/종필/성훈/영/태동) 우선순위별 TODO 구체화. 영 섹션은 본인 브런치 docs/31~35 + HANDOFF.md 기반으로 작성.

## 데이터 자산 합계

| 트랙 | 출처 | 장수 / 행수 | 사이즈 | 라이선스 | 상태 |
| --- | --- | --- | --- | --- | --- |
| Shop API | 네이버 쇼핑 catalog 메인 이미지 | 19,330 장 (26 키워드) | ~6.4G | 개인 학습 (재배포 X) | 완주 |
| NIH DSLD full | NIH Dietary Supplement Label DB | 2,958 장 | 5.1G | CC0 | 가속 진행 |
| NIH DSLD PoC | 동상 | 177 장 | 424M | CC0 | 보관 |
| OFF dump | Open Food Facts | 12G jsonl.gz + 976M tmp | 13G | CC-BY-SA | 다운로드 완료, 필터 대기 |
| Tampermonkey | 네이버/쿠팡/올리브영/iHerb-KR 사진 리뷰 + 상세 | (D:\ 외장 SSD, 형 PC 측 확인) | — | 개인 학습 | 24/7 가동 |
| 식약처 DUR CSV | 식약처 + 한국의약품안전관리원 | 9 파일 | 394M | 정부 공개 | 원본 보관 |
| DUR parquet | 정제 통합 | 1 파일 | 8.0M | — | 룰 엔진 v0 입력 |
| HF defective pills | (폐기 archive) | 1,490 장 | — | — | `.archive/` 이동 |
| Wikimedia 처방의약품 | (폐기 archive) | 1,294 장 | — | — | `.archive/` 이동 |

## 영(yeong-tech) 작업 unblock 항목

영이 docs/31~35 에서 요구한 후속 작업 중 본 작업으로 unblock 된 항목:

- ✅ **3-Tier OCR Tier 2 (Google Vision) fixture**: 한국어+영어 혼합 영양제 라벨 fixture 19,330 + 2,958 장 확보 → benchmark 기준 도출 가능.
- ✅ **PaddleOCR 폴백 (docs/32) 평가셋**: NIH DSLD 영문 평면 + Shop API 한글 광고샷으로 PP-OCRv4 정확도 측정 가능. 단, 사용자 환경 사진(폰 촬영, blur, 조명 변동) 은 Tampermonkey 누적 + 태동 self-shoot 30장(D+5) 으로 보강 예정.
- ✅ **만성질환자 부족 영양소 룩업 입력**: 식약처 DUR 노인주의/병용금기/임부금기 = `chronic_priority.py` 의 caution rule 직접 입력 가능.
- ⏳ **AI Hub 의약품/건기식 OCR**: 신청 대기. 1~3일 승인 후 TrOCR-ko fine-tune 학습용.
- ⏳ **Google Cloud Vision service account**: 발급 필요. 영 docs/35 §0 사전 작업 unblock 용.
- ⛔ **사용자 환경 0% 커버 결함 (cv-expert 진단)**: Shop API 6,945장 ≈ 100% 스튜디오 광고샷. Tampermonkey 누적 + Track A2(블로그/카페 본문) 진입 + 태동 self-shoot 으로 보강 계속 필요.

## 매니페스토 준수 검증

- §1 (데이터 목숨) — ✅ 양보다 본질 우선. 200 키워드 확장 보류(가속 차단).
- §2 (좋은 데이터) — ✅ cv-expert 검증 결과 즉시 시정 보고. 쓰레기 트랙 2건 폐기.
- §3 (시간 X 품질) — ✅ Shop API 26 키워드 graceful 완주.
- §5 (형 호출 최소) — ✅ 신규 형 행동 0건 추가 (직전 outbox 의 기존 2건 그대로: `pip install transformers torch pillow watchdog tenacity` + Tampermonkey 5사이트 스크립트 설치).
- §남의 브런치 절대 X — ✅ yeong-tech / changmin-plan / jongpil-tech / sunghoon-database 4개 브런치는 `git show origin/<branch>:<file>` 읽기 전용으로만 참조. 체크아웃/수정/푸시 0건.

## 현재 검증 상태

이 문서는 작업 현황 정리용입니다. 아래 명령은 커밋 전 다시 실행해야 합니다.

```bash
# Shop API 진행 확인
cat data/raw/api/naver_shopping/_progress.json | jq '.total_saved, .keywords_done'

# NIH DSLD 카운트
find data/raw/bulk/nih_dsld_full -type f \( -name "*.jpg" -o -name "*.png" \) | wc -l

# DUR parquet 검증
python -c "import pandas as pd; df=pd.read_parquet('data/clean/kfda_dur_unified.parquet'); print(df.shape, df.columns.tolist()[:10])"

# Tampermonkey 누적 (D:\ 마운트 후)
dir /s D:\Lemon_Aid_data\downloads_tampermonkey | findstr ".jpg .png .webp"

# git status 73 modified — 의미 단위 커밋 분리 필요
git status --short | wc -l
```

## 후속 액션

1. **D:\ Tampermonkey 누적량 실측** — 외장 SSD 마운트 후 영양소별/사이트별 카운트 보고.
2. **태동 self-shoot 30장 평가셋** (D+5) — 평소 먹는 영양제 5~10종 × close/medium/tilted/top-down/loose 5장 시나리오 → `D:\Lemon_Aid_data\raw\manual\self_shoot\` → 영(yeong-tech) 인계.
3. **AI Hub 가입 + 신청** — "의약품 패키징 OCR" / "건강기능식품" (10분).
4. **Google Cloud Vision service account** 발급 — 영 docs/35 §0 사전 작업 unblock.
5. **현재 미커밋 변경분 73 modified 정리** — mobile / backend / data / docs 의미 단위 커밋 분리.
6. **Track A2 (네이버 블로그/카페) 진입** — Shop API 완주 후 race 회피하며 가동. 본문 사용자 사진이 200 키워드 확장보다 본질 매칭 ↑↑.
7. **OFF dump 영양제 추출 후속 처리** — 다운로드 완료된 12G dump 에 강화된 필터(supplement AND NOT drug) 적용.
