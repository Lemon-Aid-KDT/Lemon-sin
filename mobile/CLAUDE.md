# Lemon Aid Mobile — Claude 작업 컨텍스트

> 이 문서는 Claude (CLI / Cowork / 모든 AI 보조 도구) 가 Lemon Aid Flutter 앱 작업 시
> **매번 가장 먼저 읽어야 하는** 컨텍스트 카드.
> 새 화면 / 위젯 / 디자인 작업할 때 — 이 문서의 약속을 어기지 않는 것이 1순위.

---

## 0. 우선순위 (절대 어기지 말 것)

1. **UX / UI 가 최우선.** 코드 추상화 · 아키텍처는 그 다음.
2. **사용자와 같이 만든다.** 혼자 화면 / 위젯 다 짜지 않는다. 결정마다 옵션 2 ~ 3 개 + 추천 1 개로 짧게 묻는다.
3. **전면 수정은 흔하다.** 디자인 / 5 탭 구조 / 카드 모양 — 한 번 결정했어도 바뀔 수 있다. 옛 결정에 묶이지 말고 새 지시 들어오면 즉시 따른다.
4. **최고의 작업물.** "동작하면 됨" 으로 끝내지 않는다. 디자인 토큰 / 약속 다 따른다.
5. **기획서 (`PROJECT_GUIDE.md`) 는 기준**. 단, UX 결정으로 바뀐 부분은 이 문서의 §3 "결정 누적" 과 **사용자의 가장 최근 지시** 를 따른다 — 새 지시 > 이 문서 > 기획서 순서.
6. **보안 — 키는 절대 소스에 박지 않는다.**
   - API 키 / OAuth Native App Key / Client Secret / DB 비번 — 어떤 키도 `.dart` 파일에 평문으로 박지 않는다.
   - 주입 방법: `--dart-define=KEY=value`. `lib/utils/oauth_config.dart` 처럼 `String.fromEnvironment()` 한 군데에서만 읽는다.
   - `.env` 는 깃에 안 올라가지만 `.env.example` 은 올라간다 — example 에 실 키 적지 말 것.
   - 키 노출 발견 시 즉시 (1) 해당 키 회전 (재발급), (2) 사용자 / 팀에 알림, (3) 가능하면 history rewrite. 노출된 키는 회전 전까지 작동 가능한 상태로 둔다고 가정.

7. **남용 방지 (rate-limit / 일일 한도) — 비용 / 발송 / 외부 API 호출은 무조건 가드.**
   - 이메일·SMS·푸시 등 **외부에 돈 / 평판이 나가는 모든 작업**에 rate-limit 필수.
   - 기본 정책 (개별 정책은 §11 참고):
     - **이메일 인증 코드 발송**: 동일 이메일 기준 **1 분에 1 회**, **하루 5 회**까지.
     - **비번 찾기 / 재인증 코드**: 위와 동일 (퍼퍼스 별 카운터 분리).
     - **로그인 시도 실패**: 동일 이메일 기준 **10 분에 5 회** (계정 잠금 또는 추가 인증 요구).
   - 제한 초과 시 응답: **429 Too Many Requests** + 사용자에게 "잠시 후 다시 시도해주세요. 약 N 초 후 가능" 안내.
   - 백엔드가 유일한 진실 — 모바일도 같이 가드하되 (UX 차원), 백엔드 가드 없는 호출은 절대 만들지 않는다.

8. **`docs/UX_DIARY.md` = Lemon Aid UX/UI 디자인 바이블 (단일 진실 원천).**
   - 모든 UX 결정 / UI 변경 / 화면 명세 / 디자인 시스템 변동은 **반드시 UX_DIARY 의 해당 챕터 안에 반영**한다.
   - **카테고리 추가가 아니라 카테고리 안 내용 갱신**이 원칙. 새 §X.X 만들지 않는다 — 기존 챕터 안에 누적.
   - 작업 끝났을 때 누가 와서 봐도 "이 앱의 모든 UX/UI 결정이 여기 다 있다" 가 돼야 한다 — 보고서 / 가이드 / 바이블 통합본.
   - 매 작업 후 점검 — "내가 바꾼 것이 UX_DIARY 에 반영됐는가?" 안 됐으면 즉시 갱신.

   **갱신 위치 매핑 (어떤 변경 → 어느 챕터)**:
   - **프로덕트 정의 / 페르소나** → §1
   - **UX 원칙 / 12 핵심 / 의료법 룰** → §2
   - **디자인 토큰 (색 / 폰트 / 간격 / 라운드 / 그림자 / 모션)** → §3.x
   - **공통 컴포넌트 (AppCard / Button / TextField / OutputCard / ConfidenceBadge / EmptyState / 모달 / NutrientBar / MainShell)** → §4
   - **화면 결정 / 변경 (S-01 Splash ~ S-13 Settings, 14개 화면)** → §5.x
   - **인증 / 보안 / Rate Limit / iOS 합류** → §6.x
   - **라우팅 / 5탭 셸** → §7.x
   - **데이터 / 상태 (Riverpod / secure storage / API / 모델)** → §8.x
   - **Figma 작업 룰 (페이지 구조 / 네이밍 / 해상도 / Auto Layout / AI 프롬프트)** → §9.x
   - **도구 분담 (Stitch / Claude Design / Figma / VS Code) / 워크플로** → §10
   - **운영 / 검증 (접근성 / 시니어 모드 / 다크 모드 / 의료법 면책 / 응급 신호 / 핸드오프 / 사용성 테스트 / A/B 실험)** → §11.x
   - **일자별 한 줄 변경 요약 (날짜 · 챕터 · 한 줄)** → §12

   - 코드만 바꾸고 UX_DIARY 안 갱신하면 **작업 미완료**로 간주. UX_DIARY §12 한 줄 색인 추가도 필수.

9. **`data/` = 데이터 수집·CV 모델 학습의 단일 진실 원천.**
   - 데이터 수집 / 정제 / 학습 결정 → `data/README.md` (학습 가이드 + 진행 상태) + `data/SOURCES.md` (8 트랙 합법성)
   - CV 모델 (분류기 / inference / 모바일 통합) → `data/models/` + `backend/src/api/analyze.py` (예정)
   - **합법 8 트랙만** — 비공식 크롤링 / 탐지 회피 코드 0건. 코드 작성 전 SOURCES.md 합법성 검토.
   - 학습 데이터 수집 결정 (새 트랙 추가 / 라이선스 변경 / robots.txt 결과) 변경 시 `data/SOURCES.md` 갱신.
   - 학습 모델 결정 (아키텍처 / 하이퍼파라미터 / 평가 지표 / SOTA 비교) 변경 시 `data/README.md` "CV/ML 학습 포인트" 섹션 갱신.

10. **결정의 근거 항상 명시 — "왜 이렇게 했는가 / 다른 방법보다 왜 이게 나은가".**
    - 사용자(태동)는 ML/DL/CV/UX 전 영역 마스터 목표 — 단순 코드 받아쓰기 X, **이해하면서 가는** 게 핵심.
    - 라이브러리 / 아키텍처 / 하이퍼파라미터 / API / 디자인 / 인프라 결정마다 **"왜 A 보다 B 가 나은가"** 트레이드오프 명시.
    - 추천 대안 1~2개도 같이 — 사용자가 다른 길을 알고 선택할 수 있게.
    - 형식 (간결): `결정 → 근거 (한 줄) → 대안 (한 줄, 왜 안 채택했는지)`.
    - 예) "ResNet-50 채택 — pretrained 안정 + timm zoo 즉시. EfficientNet-B0 도 후보였으나 학습 속도 느림 / mobile 추론 차이 미미."
    - 짧게 — 매 결정마다 박사 논문 쓰지 말 것. 한두 줄로 충분. 사용자가 "왜?" 한 번 물으면 깊게 파고들 준비.
    - 코드 주석에도 (특히 ML 코드) "왜 이 값" 한 줄. 학습 노트북엔 markdown 셀에 학습 포인트 명시.
    - **단, 사용자가 "그냥 빨리 가자" 라고 명시하면 근거 생략 — 사용자 결정 우선.**

11. **설명은 항상 쉽게 — 누구나 이해할 만큼.**
    - 전문 용어 쓸 때 **반드시 한 줄 풀이 동봉** (예: "CLIP — 사진과 글자를 같은 공간에 배치하는 AI 모델 (OpenAI 2021)").
    - 약어 처음 등장 시 풀어쓰기 (예: "CV (컴퓨터 비전 — 사진/영상 이해 분야)").
    - 비유 / 예시 적극 — 추상 개념은 일상 사물로 (예: "Transfer Learning = 영어 잘하는 사람이 일본어 빨리 배우는 것").
    - 수식 / 논문 인용은 보조 — 본문은 한국어 일반인 톤.
    - "당연히 알겠지" 라는 가정 금지 — 모든 결정은 **처음 듣는 사람도 이해 가능** 하게.
    - **"비전공자" 같은 표현 사용 금지** — 사용자 영역을 한정하지 말 것. "이해하기 쉬운 설명" 으로만 표현.
    - 복잡한 결정은 단계별 — 한 번에 다 던지지 말고 "1단계는 X / 2단계는 Y" 분리.

---

## 1. 프로젝트 한 줄

만성질환자용 AI 영양 · 복약 관리 Agent.
사진 한 장으로 음식 · 영양제를 기록하고, 부족한 영양 · 활동을 안내받는 모바일 앱.
주력층 30 ~ 50 대 + 60 대 이상 동시 충족. 식탁 앞에서 30 초 ~ 2 분 사용.

---

## 2. 디자인 시스템 (단일 출처)

### 2.1 사용 파일

**정식 — 항상 이걸 쓴다:**
- `lib/utils/design_tokens_v2.dart` — `AppColor` / `AppText` / `AppShadow` / `AppRadius` / `AppSpace` / `AppCard` / `AppPrimaryButton` / `AppSecondaryButton` / `AppTextField`
- `lib/widgets/common/app_modals.dart` — `showAppDialog` / `showAppBottomSheet` / `showAppCelebrateDialog`

**legacy — 새 코드에서 쓰지 말 것:**
- `lib/utils/tokens.dart` — 옛 `LemonColors` / `LemonText` / `LemonSpace` / `LemonFont`. 기존 화면 (Splash 등) 에 남아 있지만 점진 교체 대상.

### 2.2 디자인 시스템 v2.1 — Hybrid (UX_DIARY §14.10)

- **Flat 2.0 80 ~ 90 %** + **뉴모피즘 액센트 10 ~ 20 %**
- 카드 기반. Elev 1 그림자 (`AppShadow.elev1`) 가 기본.
- 뉴모피즘 (`AppShadow.neuPop`) 은 메인 CTA · OAuth · 감성 카드에만.

### 2.3 컬러 (UX_DIARY §14.12)

- 브랜드 블루 — `AppColor.brand` `#4C7EF7`
- 레몬 옐로 (액센트) — `AppColor.yellow` `#FFC700`
- Success — `AppColor.success` `#22B07D`
- Danger — `AppColor.danger` `#EF4452`
- Warning — `AppColor.warning` `#FF9500`
- 잉크 — `ink` `#191F28` / `inkSecondary` `#4E5968` / `inkTertiary` `#8B95A1`

### 2.4 폰트

- `Pretendard` 단일. weight 500 · 600 · 700 · 800 사용.
- 본문 = `AppText.body` (15px) / 큰 본문 = `AppText.bodyLg` (17px)
- 캡션 = `AppText.caption` (13px) / 마이크로 = `AppText.micro` (11px)

### 2.5 간격 / 라디우스

- `AppSpace.xs/sm/md/lg/xl/xxl/xxxl` = 4 / 8 / 12 / 16 / 24 / 32 / 48
- `AppRadius.xs/sm/md/lg/xl/full` = 8 / 12 / 16 / 20 / 24 / 999

---

## 3. 결정 누적 (대화로 확정된 것)

### 3.1 사용자 (1주차)

- 주 사용자 — 30 ~ 50 대 만성질환 관심층 + 60 대 이상 동시 고려
- 사용 시간 — 1 회 30 초 ~ 2 분 · 하루 3 ~ 5 회
- 사용 맥락 — 식탁 앞 · 약통 옆 · 운동 직후 (손 자유롭지 않음)
- 기본 원칙 — 큰 글씨 · 큰 버튼 (≥ 48 px) · 대비 ≥ 4.5:1 · 카메라 1 탭

### 3.2 사용자가 멈추는 4 지점 (UX 1주차 핵심)

1. **처음 켤 때** — 안내 3 단계 안 · 카메라 1 탭
2. **결과 의심** — 확신 · 출처 · 고치기 경로 함께
3. **고치고 싶을 때** — 같은 카드 안에서 인라인 수정 (다른 화면 X)
4. **하루 마무리** — 점수 + 다음 할 일 한 줄

### 3.3 화면 결정 6 기준

1. 한눈에 중요한 것 1 개만 강조
2. 손가락 거리 — 주요 작업 3 탭, 카메라 1 탭
3. 신뢰 표시 — AI 결과에 출처 · 확신 · 시간 중 최소 2 개
4. 가독성 — 14 pt 이상 · 48 px 이상 · 대비 4.5:1
5. 같은 의미 = 같은 모양 — design_tokens_v2 단일 출처
6. 빠져나갈 길 — 오류 · 없음 · 로딩에 "다음 행동 한 줄"

### 3.4 결과 카드 4 요소 (모든 결과 카드 공통 약속)

1. **결과 큰 글씨** — 사용자가 먼저 봐야 할 핵심
2. **확신 정도** — % 또는 색상 배지 (≥ 80 초록 / 60 ~ 80 주황 / < 60 검토 권장)
3. **출처 / 시간** — 공식 DB · 마지막 업데이트 시각 등 작은 라벨
4. **다음 행동** — "저장 / 고치기 / 더 보기" 한 줄

### 3.5 빈 화면 약속 (없음 = 3 가지 이유)

- **신규** — "기록을 시작해요"
- **동기화 실패** — "다시 시도"
- **권한 없음** — "설정 열기"

### 3.6 안내 문구 톤

- 일상어 — "포만감 / 가벼움 / 권장량보다 낮음"
- 진단 · 처방 표현 금지
- 모든 결과 화면 하단 푸터 — "건강 참고용이며 진단 · 처방이 아닙니다" (한 줄 고정)

---

## 4. 화면 구조 (라우터)

### 4.1 7 개 화면 (1주차 뼈대)

| 코드 | 화면 | 파일 |
|---|---|---|
| S-01 | Splash | `lib/screens/splash_screen.dart` |
| S-02 | Login | `lib/screens/auth/login_screen_v3.dart` |
| S-03 | Signup | `lib/screens/auth/signup_screen.dart` |
| S-04 | Verify | `lib/screens/auth/verify_email_screen.dart` |
| S-05 | Consent | `lib/screens/auth/consent_screen.dart` |
| S-06 | Onboarding | `lib/screens/onboarding_screen.dart` |
| S-07 | Dashboard (Home) | `lib/screens/dashboard_screen.dart` |

### 4.2 메인 5 탭 (2주차 — 진행 중, 잦은 변경 예상)

**현재 가안 — 사용자와 같이 만들면서 바뀐다:**
- 홈 / 카메라 / 챗 / 점수 / 설정 (이름 · 순서 · 개수 모두 미확정)
- 카메라가 중앙 탭인지 중앙 FAB 인지 — 미확정
- 점수 / 응모 / 헬스 등 보조 탭 위치 — 미확정

**기본 골격 (구현 시):**
- BottomNavigationBar 셸 + IndexedStack 으로 유지 (탭 전환 시 상태 보존)
- 활성 = `AppColor.brand`, 비활성 = `AppColor.inkTertiary`
- 아이콘은 Material rounded

**중요:** 5 탭 구조는 **사용자와 같이 결정**한다. Claude 단독 결정 금지.

### 4.3 라우터 규칙

- `lib/utils/router.dart` — go_router 단일.
- 인증 가드 미적용 — D2 에 auth_provider 와 연결 예정.
- `initialLocation = /` (Splash). 라우팅 결정은 Splash 내부 `_initRoute`.

---

## 5. Splash 시퀀스 (확정)

### 5.1 시스템 splash (Android 12+)

- 흰 배경만 (`values-v31/styles.xml` · `values-night-v31/styles.xml`)
- 아이콘 제거 — 원형 마스크 강제 회피 (사용자 결정)

### 5.2 Flutter Splash

- 로티 — `assets/animations/lemonaid_gold.json` · 280×280 · 1.5x 속도 (원본 6 초 → 4 초 사이클) · 무한 반복
- 워드마크 제거 — 로티 + 태그라인만
- 태그라인 — `상큼하게 찍고, 톡 쏘게 채우는 스마트 헬스케어`
- 태그라인 글자 한 자씩 타이핑 (현재 120 ms / 글자, 150 ms 지연 후 시작)
- "상" / "톡" 위 노란 점 — 0 → 10 pt → 4 → 7 → 6 스프링 + 위에서 떨어짐 + 글로우 링 확산 + 글자 색 노란 깜빡
- 글자 톡톡 — 회전 ±8° → 0 + y -12 → 0 → -2 → 0 + 스케일 0.6 → 1.08 → 0.97 → 1.0
- 폰트 17 px (`AppText.bodyLg`)

### 5.3 라우팅 분기

- **개발 빌드** (debug / profile) — 타이핑 끝 + 안착 + 머무름 보장 (`_minSplashDuration` 동적 계산)
- **배포 빌드** (release) — 인증 응답 도착 즉시 라우팅. 로티는 그동안 무한 반복. 최대 15 초 timeout.

---

## 6. 공용 위젯 (필수 — 새 화면 만들 때 이걸 먼저 본다)

### 6.1 이미 만들어진 것 (`design_tokens_v2.dart`)

- `AppCard` — 흰 배경 + Elev 1 + 라디우스 16
- `AppPrimaryButton` — 브랜드 블루 + 뉴모피즘 액센트
- `AppSecondaryButton` — 흰 배경 + 보더 + 2 단 그림자
- `AppTextField` — 모서리 보더 깨짐 회피 CustomPaint (`_OutlinedBorderDecoration`)

### 6.2 모달 (`widgets/common/app_modals.dart`)

- `showAppDialog` — 표준 다이얼로그 (Soft Hybrid Dialog, Claude Design 02)
- `showAppBottomSheet` — 표준 바텀시트 (Claude Design 04)
- `showAppCelebrateDialog` — 축하 / 완료 모달 (Claude Design 06)

### 6.3 만들 것 (2주차 작업 시 우선 생성)

- `OutputCard` — 5 종 출력 카드 공통 셸 (라벨 + 확신 % + 헤드라인 + 디테일 + 출처 + chevron)
- `EmptyState` — 빈 화면 3 종 (신규 / 동기화 실패 / 권한 없음)
- `ConfidenceBadge` — 확신 % 표시 (≥80 초록 · 60 ~ 80 주황 · <60 빨강)
- `MainShell` — BottomNav 셸 (5 탭)

---

## 7. 작업 원칙 (Claude 가 코드 짤 때)

1. **읽기 먼저 · 쓰기 나중.** 새 화면 만들기 전 `design_tokens_v2.dart` 와 기존 비슷한 화면 1 ~ 2 개 읽는다.
2. **하드코딩 금지.** 색 / 폰트 / 간격 / 라디우스 — 항상 토큰으로.
3. **새 위젯은 `widgets/common/` 또는 `widgets/<feature>/`** 에. `screens/` 안에 두지 않는다.
4. **모달 / 다이얼로그 — 직접 만들지 않는다.** 항상 `showAppDialog` / `showAppBottomSheet` 사용. 시안 다르면 그때만 새로.
5. **빌드 검증** — Flutter 환경 있으면 `flutter analyze`, 없으면 사용자가 빌드.
6. **시스템 reminder · CLAUDE.md 변경** 후에는 사용자가 `flutter clean && flutter run` 해야 시스템 splash · 어댑티브 아이콘 등 OS 캐시 반영됨.

7. **모든 기기 호환 (Responsive — 절대 어기지 말 것).**
   - 타깃: 안드로이드 / iOS, 5인치 소형 폰 ~ 7인치 대형 폰 ~ 폴더블 ~ 태블릿까지 같은 코드로 동작.
   - **고정 px 하드코딩 금지**. 화면 크기에 의존하는 값(전체 너비/높이, 카드 너비 등)은 항상 **비율 또는 MediaQuery 기반** 으로 계산.
     - ❌ `width: 380, height: 600`
     - ✅ `width: MediaQuery.of(context).size.width * 0.9`
     - ✅ `Expanded`, `Flexible`, `FractionallySizedBox`, `AspectRatio` 사용
   - **컴포넌트 내부 작은 값(아이콘 24, 패딩 16 등)** 은 토큰 그대로 OK — 이건 시각적 일관성 위해 유지. 단 **레이아웃 그릇** 은 비율로.
   - **카메라 / 이미지 / 미리보기** — 항상 `AspectRatio` + `LayoutBuilder` 로 박스 크기 받아서 계산. 절대 px 박지 말 것.
   - **폰트 크기** — 토큰(`AppText.title` 등) 그대로 사용. `MediaQuery.textScaleFactor` 가 시스템 폰트 크기 자동 반영. 시니어 모드 호환.
   - **SafeArea** 필수 — 노치 / 하단 제스처 바 / 폴더블 힌지 회피.
   - **세로/가로 회전** — 기본은 세로 고정이지만, `LayoutBuilder` 로 짜면 자동 대응. `MediaQuery.orientation` 분기 가능.
   - **테스트** — 새 화면 만들 때 최소 3 사이즈 (소형 폰 360x640, 표준 390x844, 태블릿 768x1024) 시뮬에서 시각 점검. 잘림 / 겹침 / 빈 공간 큼 등 모두 잡는다.
   - **체크리스트**:
     - [ ] 화면 너비를 직접 박은 곳 없는가? (`width: 380` 같은 거)
     - [ ] `MediaQuery.size.width *` 또는 `Expanded` / `Flexible` 사용했는가?
     - [ ] 카메라/이미지 미리보기에 `AspectRatio` + `LayoutBuilder` 썼는가?
     - [ ] `SafeArea` 감쌌는가?
     - [ ] 시뮬레이터 3 사이즈에서 시각 점검했는가?

8. **모션 / 애니메이션 — 현업 기준 (절대 어기지 말 것).**
   - 모든 화면·상호작용은 **사용자 입장에서 부드럽게 움직이는 현업 수준** 으로 만든다.
     기준점: **토스 · 애플 (iOS) · Pillyze** 같은 톤.
   - **상태 변화는 즉각 전환 금지 — 항상 애니메이션.**
     - 화면 전환, 탭 전환, 토글, 카드 등장/사라짐, 리스트 갱신, 로딩→완료
     - "딱" 바뀌면 안 됨. 자연스럽게 흐르듯.
   - **모든 화면 전환(라우팅) 도 애니메이션 필수.**
     - go_router `pageBuilder` 에서 `CustomTransitionPage` 사용 — 기본 전환은
       페이드+슬라이드 (iOS 톤). push = 우→좌 슬라이드 + 페이드, 모달성 화면 =
       아래→위 슬라이드. 전환 없는 즉각 교체 금지.
     - 전환 시간 300~400ms, `Curves.easeOutQuart`.
   - **표준 커브 / 시간** (디자인 토큰화 권장 — `AppMotion`):
     - 마이크로 인터랙션 (토글·버튼 눌림): 150~200ms, `Curves.easeOutCubic`
     - 컨텐츠 전환 (카드 등장·페이드): 250~350ms, `Curves.easeOutQuart`
     - 화면 단위 전환: 300~400ms
     - 톡톡 튀는 강조 (성공·완료): `Curves.easeOutBack` 또는 `elasticOut` (절제해서)
   - **권장 위젯**: `AnimatedContainer`, `AnimatedSwitcher`, `AnimatedOpacity`,
     `AnimatedAlign`, `AnimatedPositioned`, `TweenAnimationBuilder`, `Hero`,
     암묵적 애니메이션 우선. 복잡하면 `AnimationController`.
   - **누르는 모든 것에 피드백** — `HapticFeedback` (selectionClick / lightImpact)
     + 시각 반응 (scale down 0.96 같은 press 효과).
   - **stagger** — 여러 요소 동시 등장 시 80~130ms 간격 순차 등장 (한꺼번에 X).
   - **과하면 안 됨** — 화려함이 목적이 아니라 "자연스러움". 시니어 사용자 고려.
     움직임이 정보 전달을 방해하면 뺀다.
   - 새 화면·위젯 만들 때 — "이게 토스였으면 어떻게 움직였을까?" 를 항상 자문한다.

9. **레몬 마스코트 — 15 포즈 (2026-05-22 도입).**
   - 에셋: `mobile/assets/mascot/poses/<pose>.png` (2x: `poses/2x/`)
   - 코드: `utils/mascot_poses.dart` — `MascotPose` enum + `MascotFor` 추천 매핑.
     캐릭터 쓸 땐 **항상 이 파일 통해서** — 직접 경로 박지 말 것.
   - **15 포즈와 의미** (`MascotPose.<이름>`):
     - `find` 돋보기 — 검색·탐색·분석 중 / `hello` 인사 — 환영·온보딩
     - `help` 도움 — 안내·가이드 / `happy` 행복 — 좋은 결과·칭찬
     - `solve` 해결 — 완료 / `wow` 놀람 — 발견·강조
     - `curious` 호기심 — 질문·챗봇 / `thinking` 생각 — 로딩·분석 중
     - `fresh` 상큼 — 건강·활력 / `thanks` 감사 — 감사 인사
     - `working` 작업 — 처리 중 / `resting` 휴식 — 빈 상태·여유
     - `celebrate` 축하 — 성취·가입완료 / `fighting` 파이팅 — 응원
     - `cool` 멋짐 — 자신감·프로필
   - **화면별 추천** (`MascotFor.<용도>`): `greeting(hour)` 시간대별 인사,
     `onboarding` / `signupDone` / `analyzing` / `analysisGood` / `chat` /
     `emptyState` / `profile` / `scoreGood` / `camera`.
   - **운영 규칙**:
     - 같은 화면·맥락엔 항상 같은 포즈 (일관성). 추천 매핑을 우선 따른다.
     - 빈 상태(분석 0건 등)엔 마스코트 + 안내 문구 = 친근하게.
     - 캐릭터 등장도 모션 룸(§8) 적용 — 톡 튀거나 부드럽게 fade-in.
     - 사용자가 "여기 캐릭터 쓰자" 하면 — 맥락 보고 `MascotFor` 또는
       `MascotPose` 중 맞는 포즈를 **먼저 제안**한다.

---

## 8. UX_DIARY 챕터 색인

`docs/UX_DIARY.md` (2026-05 재구조, 12 챕터) — 자주 보는 챕터:

- **§2** — UX 원칙 (사용자 친화 7원칙 / Nielsen 5 / 12 핵심 / 의료법 룰)
- **§3** — 디자인 시스템 (컬러 #4C7EF7 + #FFC700 / 타입 / 간격 / 라운드 / 그림자 / 모션)
- **§4** — 공통 컴포넌트 (AppCard / Button / TextField / OutputCard / 모달 3종)
- **§5** — 화면 명세 14개 (Splash / Login v3 / Signup / Verify / Consent / Onboarding / Dashboard / Camera / Score / Health / Chat / Raffle / Settings)
- **§6** — 인증 / 보안 정책 (계정 매칭 / 이메일 인증 / Rate Limit / 비밀번호 / 세션 / iOS 합류)
- **§11** — 운영 / 검증 (접근성 / 시니어 모드 / 의료법 면책 / 응급 신호 / 핸드오프)

새 화면 작업 시 — UX_DIARY 의 해당 챕터를 먼저 확인 → 약속 어기지 않는다. 변경 시 같은 챕터 안에 누적 + §12 한 줄 색인 추가.

---

## 9. 그 외 합의 (시간 / 일정)

- 발표 / 브리핑 PDF — `Lemon_Aid_Week1_Integrated_Briefing.pdf` 가 1주차 최종본.
- 2주차 의제 — 메인 5 탭 셸 + 본 화면 (홈 / 카메라 결과 카드 / 챗) + 빈 화면 3 종 통일.
- 발주처 / AI 팀 합의 대기 항목 — AI 응답 메타 4 키 (`confidence` · `source` · `editable_fields[]` · `fallback_text`).

---

## 10. 인증 / 보안 정책

→ **`docs/UX_DIARY.md` §6 참조** (계정 매칭 / 이메일 인증 / Rate Limit / 비밀번호 / 세션 토큰 / iOS 합류 시 작업 / 키 관리 — 모두 §6.1~§6.7).
