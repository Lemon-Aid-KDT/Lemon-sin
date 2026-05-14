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

---

## 8. UX_DIARY 핵심 섹션 색인

`docs/UX_DIARY.md` 안의 자주 보는 섹션 :

- **§14.10** — Hybrid 디자인 시스템 v2.1
- **§14.11** — 인풋 · 라벨 정의
- **§14.12** — 컬러 시스템 (#4C7EF7 + #FFC700 확정 근거)
- **§14.13** — 모달 디자인 (Claude Design 핸드오프 분석)
- **§14.14** — UI px 가이드

새 화면 작업 시 — UX_DIARY 의 해당 섹션을 먼저 확인 → 약속 어기지 않는다.

---

## 9. 그 외 합의 (시간 / 일정)

- 발표 / 브리핑 PDF — `Lemon_Aid_Week1_Integrated_Briefing.pdf` 가 1주차 최종본.
- 2주차 의제 — 메인 5 탭 셸 + 본 화면 (홈 / 카메라 결과 카드 / 챗) + 빈 화면 3 종 통일.
- 발주처 / AI 팀 합의 대기 항목 — AI 응답 메타 4 키 (`confidence` · `source` · `editable_fields[]` · `fallback_text`).

---

## 10. 인증 / 보안 정책 (2026-05-13 확정)

### 10.1 계정 매칭 / 중복

- **OAuth ID 매칭 우선** — 같은 `google_id` / `kakao_id` 면 같은 사람으로 간주 (자동 로그인).
- **이메일 중복 차단** — 다른 방식이라도 같은 이메일이면 신규 가입 거부 (409 Conflict).
  - 예: 이메일로 자체 가입한 `a@b.com` 이 있으면, 같은 이메일의 카카오 / 구글 신규 가입 차단.
  - 안내문에 어떤 방식으로 가입돼 있는지 분기 노출 ("구글로 가입돼 있어요").
- **다른 이메일이면 OK** — 같은 사람이라도 서로 다른 이메일이면 별개 계정 허용.
- **이메일 동의 미수락 OAuth** (카카오에서 `kakao_account.email` 미동의) — `email=None` 으로 들어옴. 이 케이스는 이메일 중복 검사 스킵 (`kakao_id` 매칭만).

### 10.2 이메일 인증

- **시점**: 자체 회원가입 직후 강제. 미인증 유저는 보호 라우트 진입 시 verify-email 로 redirect.
- **UX**: 6 자리 숫자 코드. 매직 링크 안 씀 (시니어 친화).
- **유효 시간**: 10 분. 만료 시 재발송 요구.
- **발송 채널**: Resend (개발 / MVP). 운영 가면 도메인 인증 후 자체 도메인 발신자로.
- **재사용**: 비밀번호 찾기 등 다른 흐름에서도 같은 코드 발송 인프라 재사용 (`purpose` 컬럼으로 구분).

### 10.3 Rate Limit (남용 방지) — **필수**

이메일 / SMS / 푸시 / 외부 API 호출 모두 백엔드에서 가드. **모바일 가드는 보조 (UX 차원)**.

| 작업 | 동일 식별자 기준 | 단기 제한 | 일일 제한 |
|---|---|---|---|
| 이메일 인증 코드 발송 | email | **1 분에 1 회** | **하루 5 회** |
| 비밀번호 찾기 코드 발송 | email | 1 분에 1 회 | 하루 5 회 |
| 로그인 시도 실패 | email + IP | 10 분에 5 회 | (계정 잠금 또는 captcha) |
| OAuth 토큰 검증 | IP | 1 분에 10 회 | — |

- 초과 시 응답 **429 Too Many Requests** + `Retry-After` 헤더.
- 모바일 메시지: "잠시 후 다시 시도해주세요 (N 초 후 가능)".
- 카운터 저장소: Redis (이미 docker-compose 에 들어있음). 키: `rl:{purpose}:{email}` , TTL 으로 자동 만료.
- **개발 환경 우회**: `kDebugMode` + 특정 테스트 이메일 (예: `dev+*@lemonaid.test`) 만 rate-limit 면제. 운영에선 절대 우회 없음.

### 10.4 비밀번호 정책

- 최소 8 자, 영문 + 숫자 혼합 (특수문자 권장 — 강제 아님).
- 평문 저장 금지 (bcrypt — 백엔드 `passlib`).
- 사용자 표시 입력 마스킹 기본, 토글로 보이기 허용.

### 10.5 세션 / 토큰

- JWT access 30 분 / refresh 7 일.
- access 만료 시 refresh 로 자동 갱신 (api_client 인터셉터).
- refresh 도 만료 → 강제 로그아웃, `/login` 으로.
- 로그아웃 시 백엔드 refresh 토큰 revoke + 로컬 secure storage 삭제.

### 10.6 iOS 합류 시 작업 목록 (2026-05-13 합의 — Android 끝나고 진행)

**책임**: 팀 Mac 보유자 + Apple Developer 계정 (팀이 발급, 형 부담 X).

**GCP 추가 작업**:
- iOS OAuth Client ID 발급 — Bundle ID `com.lemonaid.lemon_aid`
- 새 환경변수: `GOOGLE_IOS_CLIENT_ID` (Android 와 별도)
- Web Client ID 는 그대로 공용 (백엔드 검증용)

**카카오 추가 작업**:
- 디벨로퍼스 → 플랫폼 → iOS 등록, Bundle ID 입력
- Native App Key 는 Android 와 동일한 값 사용 (플랫폼 공용)

**iOS 측 코드**:
- `mobile/ios/Runner/Info.plist`:
  - URL Scheme: `kakao{KAKAO_NATIVE_APP_KEY}`
  - URL Scheme: 구글 `REVERSED_CLIENT_ID`
  - LSApplicationQueriesSchemes: `kakaokompassauth`, `kakaolink`
- 다트 코드는 변경 거의 없음 (`kakao_flutter_sdk_user`, `google_sign_in` 둘 다 iOS/Android 공용)

**Apple Sign-In (App Store 가이드라인 4.8 — 소셜 로그인 있으면 필수)**:
- `sign_in_with_apple` 패키지 추가
- 백엔드 `POST /api/v1/auth/apple` 엔드포인트 (apple_id 컬럼 추가 필요)
- Apple Developer 콘솔에서 "Sign in with Apple" capability 활성화
- 로그인 화면 "Apple 로 계속하기" 버튼 onPressed 연결

**현재 코드 준비 상태**:
- `OAuthConfig` 가 키 한 군데로 모음 — iOS 추가돼도 그대로 확장
- `OAuthService.signInWithKakao()`, `signInWithGoogle()` 플랫폼 무관 동작
- 백엔드 `/auth/kakao`, `/auth/google` 도 토큰만 받아 검증 — 클라이언트 OS 무관
- Android 코드 (manifest / build.gradle) 외엔 iOS 합류로 인한 모바일 코드 변경 거의 없음
