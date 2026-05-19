# Lemon Healthcare 팀 공유 보고서 - 2026-05-19 작업 내용 정리 (taedong-design)

## 한 줄 요약

오늘은 회원가입 10-step 플로우(약관 모달 → 프로필 → 이메일 → 목적·관심사 → 신체 → HealthKit → Review → 가입완료 → 약관)를 **토스/필라이즈 톤**으로 전면 재설계하고, **하단 5탭 셸 + 메인 대시보드 상단 헤더(레몬·에이드 워드마크 + 캘린더 + 본문 라운드)** 를 Pillyze 시안 기반으로 우리 LADS(Flat 2.0 + Soft UI) 톤으로 변환했습니다. `.env` 시스템(flutter_dotenv)으로 OAuth 키 주입을 간소화했고, ML 팀원이 mac에서 iOS 빌드할 수 있도록 `IOS_SETUP.md` (Info.plist URL Scheme · Google iOS Client ID 박힘) 작성해 인계 패키지(`HANDOFF_ML_v2`) 구성을 마쳤습니다.

## 기준 정보

- 작업 기준일: 2026-05-19
- 로컬 경로: `C:\Claude_Projects\lemon_healthcare\Lemon_Aid`
- 현재 브랜치: `taedong-design`
- 디자인 시스템: LADS v2 (`mobile/lib/utils/design_tokens_v2.dart`)
- 의존성 핀: `flutter_riverpod 2.5.1`, `google_sign_in 6.2.2`, `intl ^0.20.0` 유지 (메이저 업그레이드 금지)

## 오늘 작업 목적

- 회원가입 흐름을 **시니어 친화 + 토스/필라이즈 톤** 으로 다듬어 사용자 진입 마찰 최소화
- 모든 화면에서 **공통 디자인 토큰(LADS)** 사용 → 일관성 §17 강제
- ML 팀원이 OCR 통합 테스트할 수 있도록 **iOS 셋업 + 환경변수 시스템** 완성
- 메인 대시보드 P0 (캘린더 헤더 + 본문 골격) 까지 진척

## 구현 범위 요약

### 1. 회원가입 플로우 (signup_flow_screen.dart) — 전면 재설계

- **약관 동의 모달** 신규: 로그인 화면 "회원가입" 버튼 → 모달 → 동의 시에만 진입
- **10-step PageView**: Welcome → Profile → Email → Purpose → Concerns → Body → Healthkit → Review → 가입완료 → Terms
- **OAuth 신규 사용자**: `?oauth=1` 쿼리로 진입 → Email 단계 자동 스킵 + 이름·이메일 프리필
- **사전 동의**: `?consented=1` 쿼리 → Terms 단계 자동 스킵
- **MealTimes (식사 시간) 단계 완전 제거** → 총 9~10단계로 축소
- **`_StepHeader`** 컴포넌트: 타이틀(700ms easeOutQuart, slide 32px) + 서브(600ms, slide 24px, 520ms 지연) — 앱이 말 거는 듯한 시그니처 등장
- **`_StaggeredColumn`** 컴포넌트: 헤더 종료 후(900ms 지연) 콘텐츠 80~130ms 간격 stagger fade+slide — 모든 step 일괄 적용
- **`_FloatingField`** 신규: Material InputDecoration 한계 회피, 직접 구현. 빈 상태 라벨이 입력 위치에 placeholder처럼 있다가 포커스 시 위로 슬라이드 + 작아짐 + brand 색 (220ms easeOutCubic)
- **`_BrandToggle`** 신규: Material Switch 파란색 대체, brand 노랑 + 흰 thumb, soft shadow
- **이름 입력 동적 안내**: 입력 시 "권장 칼로리, 영양 성분 섭취량은 성별과 만 나이에 따라 달라질 수 있어요." fade+size transition
- **생년월일**: Cupertino 휠 datepicker(한국어 로케일) + selectionOverlay 회색선 가리기 overlay
- **가입 완료 (Step Dashboard)**: 캐릭터 통통 튀는 무한 모션(1400ms 사이클) + 타이틀 `Curves.elasticOut` scale 0.6→1.0 톡톡 튀는 등장 + 서브 늦게 fade
- **마지막 CTA "메인으로"** → `markSignupComplete()` + `/login` 으로 이동 (수동 로그인 흐름)

### 2. 하단 5탭 셸 (main_shell.dart) — Pillyze 톤 변환

- **5탭 구조**: 홈 / 챗 / [중앙 카메라 FAB] / 점수 / 설정
- **중앙 카메라 FAB**: 64px 원, **위→아래 그라데이션** (`#FFD43A → #FFC700`), + 기호(`Icons.add_rounded` w700), 탭바 위로 20dp 떠있음, 2단 그림자 (brand alpha + 검정 미세)
- **활성 탭**: brand 비비드 노랑 아이콘 (filled 통일 — 무게감), 라벨 검정 w700, 26px 사이즈 강조 (AnimatedSize 180ms)
- **비활성 탭**: `#C5CBD6` 옅은 그레이지 (filled 그대로), 라벨 inkTertiary w500
- 상단 매우 옅은 1px 구분선 (`#F1F3F6`) + 위로 soft shadow
- 아이콘 셋: 홈(하트) / 챗(말풍선) / 점수(메달) / 설정(톱니바퀴)

### 3. 메인 대시보드 (dashboard_screen.dart) — P0 골격

- **상단 brand 노랑 헤더**:
  - **"레몬·에이드" 한국어 워드마크** (가운데 흰색 원 점 — 로그인 화면 시그니처와 동일 톤)
  - 우측 아이콘 3개: 캘린더 · 알림 · 프로필
  - 요일 strip (월화수목금토일) + 날짜 strip (이번 주 7일, 오늘은 흰 원 + w800 강조)
- **본문 라운드**: 헤더와 만나는 지점에서 본문(흰)이 위쪽 좌·우 28px 둥글게 위로 솟아오름 (Pillyze 시그니처)
- **메인 박스**: 흰 배경, AppRadius.lg(20) 라운드, LADS 표준 soft shadow (140,155,175 / 0.20 / blur 16 / offset 0,5)
- 본문 카드 콘텐츠는 다음 단계 (캐릭터 + 식단 + 5종 분석 + 최근 분석 + 면책 등)

### 4. `.env` 시스템 (flutter_dotenv) — 개발 편의 + 보안 균형

- `mobile/pubspec.yaml`: `flutter_dotenv ^5.1.0` 의존성 + `assets: - .env` 등록
- `mobile/lib/main.dart`: `await dotenv.load(fileName: '.env')` 부트
- `mobile/lib/utils/oauth_config.dart`: dart-define 우선, 없으면 .env 폴백 (`dotenv.maybeGet`)
- `mobile/.env.example` 갱신, `mobile/.env` 는 .gitignore 의 `*.env` 룰로 차단
- 환경변수 등록 없이 `flutter run` 한 번이면 OAuth 작동 (개발 편의)

### 5. iOS 셋업 (mac 팀원용)

- `mobile/ios/IOS_SETUP.md` 신규:
  - `flutter create --platforms=ios .` + `pod install`
  - **Info.plist URL Scheme** 박음:
    - 카카오: `kakaoe77b0826818850493f5ffeb1014a0833`
    - 구글 iOS Client ID: `402778318501-r0voee5fga2cso9sf1musmp6mj8t4r4a.apps.googleusercontent.com`
    - Reversed: `com.googleusercontent.apps.402778318501-r0voee5fga2cso9sf1musmp6mj8t4r4a`
  - 카메라/사진/마이크 권한 description
  - 다크모드 강제 OFF (`UIUserInterfaceStyle: Light`)
- 카카오 디벨로퍼스 콘솔에 iOS 번들 ID `com.lemonaid.lemon_aid` 등록 완료

### 6. 인계 패키지 (`HANDOFF_ML_v2/`)

- `00_README.txt` 폴더 안내
- `01_HANDOFF_TO_ML.md` 메인 셋업 가이드
- `02_FRONTEND_GUIDE.md` 모바일 코드 구조 (디자인 시스템, 위젯, 라우트)
- `03_IOS_SETUP.md` iOS 시뮬 셋업 (mac)
- `04_ALL_KEYS.txt` 모든 키 + 어디 넣는지
- `backend.env` 실키 박힌 백엔드 .env
- `mobile.env` 실키 박힌 모바일 .env (`KAKAO_NATIVE_APP_KEY` + `GOOGLE_SERVER_CLIENT_ID`)
- `mobile.env.example` 빈 템플릿

### 7. 기타

- **Welcome 캐릭터** "안녕!" 마스코트로 교체 (시안에서 누끼 따서 `mobile/assets/mascot/hello-mascot.png`, 246×210)
- **약관 모달 디자인** 정립: 체크박스 (원형 회색→brand 노랑 + 흰 체크), [필수] 인라인 텍스트, "보기" 우측 정렬, 의료 면책 박스
- **로그인 화면**: OAuth 새 사용자 → `_routeAfterOAuth` 가 약관 모달 호출 → 동의 시 `/signup?oauth=1&consented=1&name=...&email=...`
- **iOS Bundle ID**: 카카오 디벨로퍼스에 등록 완료

## 변경된 파일 (이번 커밋 범위)

```
mobile/lib/screens/dashboard_screen.dart   (대시보드 P0 골격)
mobile/lib/widgets/common/main_shell.dart  (하단 5탭 Pillyze 톤)
mobile/lib/main.dart                       (.env 로드)
mobile/lib/utils/oauth_config.dart         (.env 폴백)
mobile/lib/screens/auth/signup_flow_screen.dart  (회원가입 10-step)
mobile/lib/screens/auth/consent_modal.dart       (약관 모달 신규)
mobile/lib/screens/auth/login_screen_v3.dart     (OAuth + 약관 모달 연결)
mobile/pubspec.yaml                        (flutter_dotenv 추가)
mobile/.env.example                        (템플릿 갱신)
mobile/ios/IOS_SETUP.md                    (iOS 셋업 가이드 신규)
mobile/scripts/run-dev.sh                  (mac용 빌드 스크립트)
mobile/assets/mascot/hello-mascot.png      (안녕! 누끼)
HANDOFF_TO_ML.md                           (ML 팀원 인계 메인)
HOTKEYS.md                                 (단축키 정리)
```

## 다음 단계 (TODO)

- [ ] 메인 대시보드 본문 카드 (캐릭터 + 식단 + 5종 분석 결과 + 최근 분석 + 면책)
- [ ] 카메라 화면 (촬영 → 분석 API 호출 → 결과 화면)
- [ ] 분석 결과 5종 출력 화면 (부족 영양소 / 과다 / 주의 / 점수 / 목적별)
- [ ] OCR API 연동 (영양제 팀원 작업 받아서 모바일 연결)
- [ ] iOS 빌드 검증 (mac 팀원)
- [ ] 챗 / 점수 / 설정 탭 화면 골격
- [ ] 만성질환·복약 정보 입력 화면

## 가드 (의료법 §27, 약사법 §65)

- 모든 사용자 보이는 카피에서 **"진단"·"처방"·"치료"·"효능"·"효과"** 금지 — 점검 완료
- 약관 모달에 의료 면책 박스 노출 (`레몬에이드는 건강 관리를 도와드리는 서비스로 의사·약사·영양사의 진단을 대신하진 않아요.`)
- 추후 분석 결과 화면에도 동일 면책 의무 노출 예정
