# Lemon Aid 모바일 UX/UI 디자인 바이블

> **한 줄 요약** — Lemon Aid 앱의 모든 UX/UI 결정 / 디자인 시스템 / 화면 명세 / 컴포넌트 가이드의 **단일 진실 원천**.
> 코드 ↔ Figma ↔ 문서 3방향 일치 유지. 이 문서가 어긋나면 코드를 고치는 게 아니라 이 문서를 먼저 갱신한다.

문서 갱신 원칙
- **카테고리 안 내용 갱신**이 원칙 — 새 챕터를 만들지 않는다.
- 화면 변경 → §5.x / 디자인 토큰 → §3.x / 공통 컴포넌트 → §4 / 인증·보안 → §6 / 라우팅 → §7 / 데이터 → §8 / Figma·도구 → §9·§10 / 운영·검증 → §11 / 일자별 한 줄 → §12.
- 코드만 바꾸고 이 문서를 안 갱신하면 **작업 미완료**로 간주.

관련 문서
- `mobile/CLAUDE.md` — Claude(CLI/AI 보조 도구) 매번 먼저 읽는 컨텍스트 카드 (이 바이블의 짧은 인덱스 역할)
- `PROJECT_GUIDE.md` — 발주처·팀 공식 합의 (이 바이블과 충돌 시 최근 결정이 우선)

---

## §1. 프로덕트 한 줄 + 타겟 사용자

### 1.1 프로덕트 한 줄

만성질환자용 AI 영양·복약 관리 Agent. 사진 한 장으로 음식·영양제를 기록하고, 부족한 영양·활동을 안내받는 모바일 앱.

핵심 동사: **찍는다 → 분석한다 → 기록한다 → 본다.**
사용 빈도: 하루 3~5회 짧은 진입 + 주 1회 점수 회고.
사용 시간: 1회당 30초~2분 (사진 한 장이면 끝).
사용 맥락: 식탁 위 · 약통 옆 · 외출 중 · 운동 직후 — 한 손 · 짧은 시간 · 정보 즉각 확인.

### 1.2 페르소나

#### 김건강 (52세 · 남 · 1차 핵심)

| 항목 | 내용 |
|------|------|
| 한 줄 | 고혈압 진단 2년차, 당뇨 전단계, 영양제 4종 |
| 디지털 친화도 | 중상 (카톡·유튜브·삼성헬스 능숙, 새 앱 5분 학습 한계) |
| 사용 맥락 | 아침 식사 후 거실 소파, 안경 없이 폰, 노안 시작 |
| JTBD | 약·영양제 충돌 확인 / 가족 안심 / 합병증 예방 |
| 페인포인트 | 영양제 라벨 영문, 약사 설명 잊어버림, 앱 글씨 작음 |
| 핵심 감정 | 불안 (재진단) · 무게감 (가족 책임) |
| 자주 묻는 질문 | "같이 먹어도 돼?" "지난번 검사 어땠더라?" |

**디자인 함의**: 본문 17px+ (안경 없이도 읽힘) · 첫 화면 "지난번 비타민 D 부족했어요" (기억해주는 느낌) · 응급/단정 표현 X · 챗봇 입구 명확.

#### 박직장 (38세 · 남 · 2차 확장)

| 항목 | 내용 |
|------|------|
| 한 줄 | 콜레스테롤·공복혈당 경계, 영양제 2종, 시간 부족 |
| 디지털 친화도 | 매우 높음 |
| 사용 맥락 | 출퇴근 지하철, 점심 후 5분, 한 손 조작 |
| JTBD | 최소 시간 예방 / 3개월 후 미리 보기 |
| 페인포인트 | 정보 과잉 · 잔소리 · 광고 |
| 핵심 감정 | 효율 추구 · 자기 통제 |

**디자인 함의**: 한 손 조작 (핵심 액션 하단 1/3) · 정보 밀도 ↑ + Progressive Disclosure · 다크 모드 v2 · 응모권 자연스러움 OK.

### 1.3 두 페르소나 충돌 지점 + 우선순위

| 지점 | 김건강 | 박직장 | 결정 |
|---|---|---|---|
| 글씨 크기 | 17px+ | 14px 익숙 | **16px 기본 + 시니어 모드 토글** (김건강 우선) |
| 다크 모드 | 야간 부담 | 선호 | v2 (운영 직전) |
| 정보 밀도 | 낮게 | 높게 | 카드 단위 접힘 |
| 알림 톤 | 격려 | 무덤덤 | Settings 사용자 토글 |
| 게이미피케이션 | 부담 | 자연스러움 | 응모권만 — 점수 경쟁 X |

**충돌 시 김건강(50대 시니어 친화)가 우선.** 박직장이 못 쓰는 화면은 거의 없음 — 그 반대가 더 자주 일어남.

관련 코드: `lib/screens/auth/login_screen_v3.dart`, `lib/screens/dashboard_screen.dart`

---

## §2. UX 원칙 (모든 결정의 상위 룰)

### 2.1 사용자 친화 7대 원칙 (UX 1순위)

**전제**: 사용자가 못 쓰면 UI도, 비즈니스도, AI도 의미 없다. 친화가 모든 결정의 상위 룰.

**1. 한 화면 한 일 (Hick의 법칙)**
- 각 화면은 사용자가 할 일이 한 가지. 둘 이상이면 메인 1 + 보조 1 + 부가 0~1까지.
- 좋음: Dashboard "오늘 상태 확인" 핵심 / 나쁨: 입력 폼 + 차트 + 챗봇 + 광고 동시.

**2. 큰 글씨 큰 터치 (Fitts의 법칙)**
- 본문 최소 16dp / 핵심 17~20dp / 시니어 모드 19~22dp.
- 터치 최소 48×48dp / 시니어 56×56dp. 두 버튼 사이 8dp 이상.
- 비밀번호 보기 기본 ON (시니어 모드) — ●●● 안 보이면 입력 어려움.

**3. 솔직한 면책 (의료법 + 신뢰)**
- 분석 결과 / 챗봇 답변엔 항상 "참고용" 명시.
- "진단" "처방" "치료" 단어 X. 응급 키워드 (가슴 통증 · 호흡곤란) → 즉시 119 안내.
- 다크패턴 X — 일괄 동의 버튼 / 작게 숨긴 약관 등.

**4. 다음 액션 명확 (Doherty 0.4초)**
- 모든 화면 primary 1개 — 사용자가 "다음 뭐 해야 하지?" 묻지 않게.
- 로딩 1.5초↑ → progress bar + 진행 단계 텍스트.
- 빈 상태 (Empty)는 절대 빈 화면 X — 다음 액션 CTA. 에러는 친절한 한 줄 + 재시도.

**5. 폴백 항상 (네트워크 X / 권한 X / 데이터 X)**
- OCR 실패 → 수동 입력 / 카메라 권한 거부 → 갤러리 모드 / 건강 권한 거부 → 수동 숫자 입력.
- API 실패 → 캐시된 결과 + "마지막 동기화 N분 전". AI 응답 실패 → "다시 시도" + Mock 답변.
- 모든 화면은 인터넷 없어도 최소 1개 기능 동작.

**6. 빠른 학습 (시니어 인지 부담 ↓)**
- 첫 진입 항상 안내 — 코치마크 X (길면 닫고 잊어버림), 첫 빈 상태 CTA로 대체.
- 같은 아이콘 같은 의미. 메뉴 명사는 사용자 언어 ("응모권" O / "리워드" X).
- 동일 액션은 동일 위치 (Primary 항상 하단, 닫기 항상 좌상).
- 학습 곡선: 첫 3분 안에 핵심 가치 1회 경험 (사진 → 5출력).

**7. 회복 가능 (실수 → 되돌리기)**
- 모든 위험 액션 (삭제 · 로그아웃 · 응모) → 확인 다이얼로그.
- Snackbar 액션 후 "되돌리기" 5초 제공.
- 입력 중 백버튼 → "버릴까요?" 다이얼로그 (입력값 보호).
- 30일 데이터 저장 (실수로 지운 분석 복구). 자동 저장 — 입력 중 앱 죽어도 60% 복구.

**친화도 체크표** — 각 화면 명세 ⑫에 결과 박음:

| 항목 | OK 조건 |
|---|---|
| 한 화면 한 일 | primary action 1개로 답할 수 있는가 |
| 큰 글씨 큰 터치 | 모든 텍스트 16+ / 터치 48+ 확인 |
| 면책 | 분석 · 권고에 caption 또는 배너 |
| 다음 액션 | primary 1개 시각적으로 가장 강함 |
| 폴백 | 인터넷 · 권한 · 데이터 없을 때 화면이 비지 않음 |
| 빠른 학습 | 첫 진입 사용자가 안내 없이 30초 내 핵심 발견 |
| 회복 가능 | 실수한 action에 되돌리기 또는 확인 |

### 2.2 Nielsen 10 Heuristics — 우리에게 핵심 5개

| # | 원칙 | Lemon Aid 적용 |
|---|------|---------------|
| 1 | 시스템 상태 가시성 | OCR · LLM 진행률 · 스피너 · 상태 라벨 |
| 3 | 사용자 제어 · 자유 | AI 결과 미리보기 → 승인 (자동 저장 X) |
| 5 | 오류 방지 | 상한 초과 영양제는 입력 단계에서 경고 |
| 7 | 유연성 · 효율 | 카메라 / 갤러리 / 수동 입력 3옵션 |
| 9 | 오류 회복 | "다시 시도" + 수동 입력 폴백 |

(나머지 5개 — 현실 매칭 · 일관성 · 인지 우선 · 미니멀 · 도움말 — 도 적용하지만, 위 5개가 헬스케어 도메인에서 특히 중요)

### 2.3 Lemon Aid UX 12 핵심 체크리스트

화면 끝낼 때마다 자가 검수.

| # | 항목 | 통과 조건 |
|---|---|---|
| 1 | 시니어 50대+ 친화 | 본문 16+, 터치 48+, 영문 약어 풀어쓰기, 자동 사라지는 토스트 X |
| 2 | AI 미리보기 → 승인 | 분석 결과 편집 가능 카드, [저장]/[수정]/[다시 분석] 3액션, 자동 저장 X |
| 3 | 의료법 안전 표현 | "진단·처방·치료·보장" 0개, 권유형 카피, 질병명 단정 X |
| 4 | 오프라인 대응 | 사진 촬영 항상 가능, 동기화 상태 표시, 재시도 명확 |
| 5 | "기억해주는 Agent" | 두 번째 방문 시 "지난번 비타민 D 부족했어요" |
| 6 | 점수 부담 없이 | 자연어 피드백 강조, 낮은 점수에도 긍정 카피 |
| 7 | 사용자 결정 주도 | 권유형, 선택지 제시 (예/아니오/나중에) |
| 8 | 한 손 조작 | 핵심 버튼 하단 1/3, FAB 우하단, 스와이프만 의존 X |
| 9 | 데이터 입력 부담 ↓ | 만성질환 다중선택 칩, 약 이름 자동완성, 건너뛰기 가능 |
| 10 | 면책 고지 노출 | 첫 진입 1회 풀 모달, 권고 화면 작은 배너, 주 1회 풀버전 재노출 |
| 11 | 응급 신호 감지 | 다이어트 권고 사라짐 (BMI <17), 1577-0199 / 한국섭식장애협회 버튼 |
| 12 | 사진 촬영 학습 | 카메라 진입 시 샘플 사진, 흐림 자동 감지 → "다시 촬영" |

### 2.4 의료·건강 분야 특화 룰

- **Calm Technology (Mark Weiser)** — 알림 최소화, 주의 빼앗지 않기.
- **Inclusive Design Toolkit (MS)** — 일시·상황 장애 고려 (햇빛·진동하는 버스 안).
- **응급 키워드 자동 감지** — "가슴 아파요" / "숨이 안 쉬어져요" → 풀스크린 119 안내 + 진동·소리 + 닫기 friction.
- **다이어트 권고 자동 차단** — BMI <17 등 섭식장애 신호 감지 시 권고 사라짐 + 한국섭식장애협회 안내.
- **약 이름·의약품 처방 표현 절대 금지** — 챗봇 답변은 성분명·식품명만. 의약품 식별 시 백엔드 단호한 거부.
- **응급 외 빨간색 풀스크린 X** — 시각 충격 톤다운.
- **의료기관 로고·실제 의사 사진·약품 패키지 직접 노출 X** (약사법).

관련 코드: `lib/utils/oauth_config.dart`, 백엔드 `src/api/v1/auth/` (의료 진단 키워드 감지)

---

## §3. 디자인 시스템 (단일 출처)

> **정식 출처**: `mobile/lib/utils/design_tokens_v2.dart` — `AppColor` · `AppText` · `AppShadow` · `AppRadius` · `AppSpace` · `AppCard` · `AppPrimaryButton` · `AppSecondaryButton` · `AppTextField`.
> **legacy**: `lib/utils/tokens.dart` (`LemonColors` / `LemonText` 등) — 새 코드 사용 금지. Splash 등 기존 화면에 점진 교체.
>
> 디자인 시스템 v2.1 — **Hybrid: Flat 2.0 80~90% + 뉴모피즘 액센트 10~20%** (2026-05-12 채택).
> 카드 기반. Elev 1 그림자 기본. 뉴모피즘 (`AppShadow.neuPop`)은 메인 CTA · OAuth · 감성 카드에만.

### 3.1 컬러 팔레트

#### 3.1.1 메인 2색 (2026-05-12 확정)

| 색 | HEX | 토큰 | 역할 | 사용 케이스 | 금지 케이스 |
|---|---|---|---|---|---|
| **브랜드 블루** | `#4C7EF7` | `AppColor.brand` | 모든 액션 · CTA · 링크 · focus | Primary 버튼 / 텍스트 링크 / focus 인풋 보더 | 본문 텍스트 (가독성 ↓) |
| **레몬 옐로** | `#FFC700` | `AppColor.yellow` | 캐릭터 · 하이라이트 · 축하 · 로고 점 | 캐릭터 후광 / 성취 카드 / 강조 chip | **본문 텍스트 (대비 1.7) · 메인 액션 (블루가 메인)** |

근거: 헬스 · 금융 카테고리의 학습된 패턴 = 푸른계열 = 신뢰. 채도 높은 라이트 블루로 차가움 톤다운. 흰 배경 위 대비비 4.52 (AA 본문 통과). 옐로는 블루(이성)와 보완색 — 양극 강조로 시선 + 따뜻함.

#### 3.1.2 보조 톤

| 토큰 | HEX | 용도 |
|---|---|---|
| `brandPressed` | `#2F66E2` | 버튼 눌림 / hover |
| `brandSoft` | `#EDF3FF` | chip 배경, 옅은 강조 영역 |
| `yellowSoft` | `#FFF6CC` | 노란 chip / 캐릭터 후광 / 성취 카드 배경 |

#### 3.1.3 시맨틱 컬러 (의미 전달용)

| 토큰 | HEX | 의미 | 사용 |
|---|---|---|---|
| `success` | `#00C471` | 성공 · 통과 · 긍정 영양 | OK 보더 / 점수 양호 / 체크 |
| `warning` | `#FF9500` | 경고 · 중간 영양 | 점수 보통 / 주의 chip |
| `danger` | `#E53E3E` | 위험 · 에러 | error 보더 / 점수 위험 / 삭제 |

> 시맨틱 컬러는 **반드시 텍스트·아이콘과 함께** 사용 (색맹 대응). 색만으로 의미 전달 금지.

#### 3.1.4 그레이 스케일 (잉크 + 표면)

| 토큰 | HEX | 용도 |
|---|---|---|
| `ink` | `#191F28` | 본문 / 타이틀 |
| `inkSecondary` | `#4E5968` | 부제 / 라벨 |
| `inkTertiary` | `#8B95A1` | 캡션 / placeholder / 비활성 백 버튼 |
| `inkDisabled` | `#C5C8CE` | 비활성 텍스트 |
| `border` | `#EEF1F6` | 카드 보더 |
| `borderStrong` | `#DEE2E8` | 인풋 강조 보더 |
| `sunken` | `#F7F8FA` | 인풋 평소 베이스 (현재 흰색 통일 추세) |
| `section` | `#F2F4F6` | 섹션 구분 배경 / 모달 컨테이너 bg |
| `surface` | `#FFFFFF` | 카드 · 인풋 평소 |
| `bg` | `#FFFFFF` | 화면 전체 배경 |

#### 3.1.5 외부 가이드 컬러 (브랜드 가이드 준수)

| 토큰 | HEX | 가이드 |
|---|---|---|
| `kakao` | `#FEE500` | 카카오 공식 (텍스트 `#191919`) |
| `appleBlack` | `#1A1F2E` | Apple 공식 (텍스트 `#FFFFFF`) |
| Google | `#FFFFFF` + border `#DADCE0` | Google 공식 |

#### 3.1.6 사용 매핑 (어디에 어떤 색)

| UI 요소 | 컬러 |
|---|---|
| 화면 배경 | `bg` 흰색 |
| 카드 · 인풋 평소 | `surface` 흰색 |
| 본문 텍스트 | `ink` |
| 라벨 · 부제 | `inkSecondary` |
| placeholder | `inkTertiary` |
| 메인 CTA Primary 버튼 | `brand` |
| 버튼 누름 | `brandPressed` |
| 텍스트 링크 / focus 라벨 | `brand` |
| Focus 인풋 보더 | `brand` 1.5px |
| 캐릭터 · 로고 점 · 강조 chip | `yellow` |
| 영양 점수 양호 / OK 보더 / 체크 | `success` |
| 점수 보통 / 경고 chip | `warning` |
| Error 보더 / 위험 / 삭제 | `danger` |
| Error 인풋 배경 | `#FFF5F5` (danger의 옅은 변형) |

#### 3.1.7 접근성 (WCAG AA 대비비)

흰 배경 기준:

| 색 | 대비비 | AA 본문 | AA 큰 글자 |
|---|---|---|---|
| `ink` `#191F28` | 16.6:1 | ✓ | ✓ |
| `inkSecondary` `#4E5968` | 8.8:1 | ✓ | ✓ |
| `inkTertiary` `#8B95A1` | 3.7:1 | ✗ | ✓ |
| `brand` `#4C7EF7` | 4.52:1 | ✓ | ✓ |
| `yellow` `#FFC700` | 1.7:1 | ✗ | ✗ — **본문 사용 금지** |
| `success` `#00C471` | 2.7:1 | ✗ | ✓ |
| `danger` `#E53E3E` | 4.1:1 | ✗ (4.5 직전) | ✓ |

#### 3.1.8 시니어 모드 (대비 강화)

시니어 모드 활성화 시 토큰 자동 swap:

| 일반 → 시니어 |
|---|
| `inkSecondary` → `ink` (라벨도 본문 검정) |
| `inkTertiary` → `inkSecondary` (캡션도 짙게) |
| `border` → `borderStrong` (보더 진하게) |
| `brand` (본문 링크) → `brandPressed` (더 진한 블루) |

#### 3.1.9 다크 모드 (운영 직전 별도 결정)

원칙:
- 배경 `#0F1419` (순흑 아닌 따뜻한 검정), 카드 `#1A1F28`, 잉크 반전.
- 브랜드 블루 더 밝게 `#7BA4FA`. 노란 그대로.
- 시맨틱은 채도 ↓ 명도 ↑ 톤 보정.
- 그림자 alpha 0.04 → 0.30 자동 증가 (안 보이면 보더로 대체).

#### 3.1.10 legacy 마케팅 톤 (보존)

옛 레몬 단독 톤 (`#CA8A04` / `#FACC15` / 크림 `#FEFAE0`)은 다음 용도로만 보존:
- 마케팅 페이지 · 랜딩 페이지
- 응모권 당첨 축하 모달 (전체 노랑 그라데이션)
- 보조 디자인 자료 (앱 본체 화면 사용 금지)

### 3.2 타이포그래피

#### 3.2.1 폰트 패밀리 (2026-05-11 확정)

| 폰트 | 용도 | 라이선스 | 사용 weight |
|---|---|---|---|
| **Pretendard** | 본문 · 라벨 · 카드 타이틀 · 캡션 · 면책 (전체 70~80%) | SIL OFL 1.1 | 400 / 500 / 600 / 700 / 800 |
| **Gmarket Sans Bold** | 디스플레이 — 워드마크 "Lemon Aid" / 큰 헤드라인 / 응모권 큰 숫자 | G마켓 (무료 상업) | Light / Medium / Bold |
| **Plus Jakarta Sans** | 영문 라벨 · 외래어 (vitamin, OCR) | SIL OFL 1.1 | 400 / 600 / 700 / 800 |

백업 폰트:
- iOS — Apple SD Gothic Neo → SF Pro
- Android — Noto Sans KR → Roboto
- 영문 — Inter → -apple-system

라이선스 의무: `assets/fonts/` 에 LICENSE 파일 동봉 + Settings → "오픈소스 라이선스" 페이지 표시.
자동 설치: `pwsh scripts/install_fonts.ps1` (Pretendard / Gmarket Sans / Plus Jakarta Sans 자동 다운로드).

#### 3.2.2 타입 토큰 (design_tokens_v2)

| 토큰 | size / weight / line-height | 폰트 | 용도 |
|---|---|---|---|
| `AppText.display` | 32 / 800 / 1.2 | GmarketSans Bold | 큰 환영 · 응모권 누적 |
| `AppText.title` | 24 / 800 / 1.3 | GmarketSans Bold | 화면 타이틀 |
| `AppText.heading` | 20 / 700 / 1.4 | Pretendard 700 | 섹션 헤딩 |
| `AppText.subheading` | 17 / 600 / 1.5 | Pretendard 600 | 카드 제목 |
| `AppText.bodyLg` | 17 / 500 / 1.5 | Pretendard | 큰 본문 / 안내 |
| `AppText.body` | 15 / 500 / 1.6 | Pretendard | 본문 (기본) |
| `AppText.bodyEmphasis` | 17 / 700 / 1.5 | Pretendard 700 | 핵심 수치 (tabular nums) |
| `AppText.caption` | 13 / 500 / 1.5 | Pretendard | 도움말 / helper |
| `AppText.micro` | 11 / 600 | Pretendard | 마이크로 라벨 |
| `AppText.disclaimer` | 13 / 400 / 1.6 | Pretendard | 면책 고지 |

> 본문 최소 16dp는 사용자 친화 7원칙에서 도출된 시니어 기준 — 일반 토큰은 15(body) / 17(bodyLg) 두 단계로 운영하고, 시니어 모드에서 각각 +3 ~ +4 swap.

#### 3.2.3 시니어 모드 타입 (자동 분기)

| 토큰 | 일반 | 시니어 |
|---|---|---|
| body | 15 / 1.6 | 19 / 1.7 |
| bodyEmphasis / subheading | 17 / 1.5 | 20 / 1.6 |
| caption | 13 / 1.5 | 15 / 1.6 |
| touchTarget | 48 | 56 |

구현: `final isElder = ref.watch(elderModeProvider);` → `isElder ? AppText.elderly* : AppText.*`.

#### 3.2.4 워드마크 정책

- 워드마크 "Lemon Aid" / "레몬•Aid" → **Gmarket Sans Bold** (한·영 통일된 로고 인상).
- 한글화 (2026-05-12): "Lemon" → "레몬", "Aid" 유지 → **"레몬•Aid"** (사이에 노란 점).
- 워드마크 영문 부분에 작은 레몬 점 박기 (건강의신 마이크로 디테일 모방).
- 숫자 표시: Display·title 영역 = Gmarket Sans / 본문 영역 = Pretendard 700 tabular nums.

### 3.3 간격 (AppSpace)

| 토큰 | dp | 용도 |
|---|---|---|
| `xs` | 4 | 아이콘 간격 |
| `sm` | 8 | 인라인 요소 |
| `md` | 12 | 카드 padding 보조 |
| `lg` | 16 | 카드 padding (표준) / 카드 간 간격 |
| `xl` | 24 | 섹션 간격 / 화면 좌우 마진 |
| `xxl` | 32 | 큰 분리 |
| `xxxl` | 48 | 화면 마진 보조 / 큰 호흡 |
| `touchTarget` | 48 | 모든 클릭 영역 최소 |

원칙: 4dp 그리드 — 모든 간격 4의 배수. 8 그리드 베이스로 다양한 dpi에서 정렬 깨지지 않음.

### 3.4 라운드 (AppRadius)

| 토큰 | dp | 용도 |
|---|---|---|
| `xs` | 8 | Chip · Badge · 작은 태그 |
| `sm` | 12 | Button · TextField · 작은 버튼 |
| `md` | 16 | Card · Sheet · 메인 버튼 |
| `lg` | 20 | 큰 카드 |
| `xl` | 24 | 모달 · BottomSheet 상단 |
| `full` | 999 | Pill · Avatar |

위계: 카드 28 ↔ 버튼 16 — 모달 안 버튼은 카드보다 작은 라운드.

### 3.5 그림자 (AppShadow)

| 토큰 | 값 | 용도 |
|---|---|---|
| `none` | — | 평면 |
| `elev1` | `rgba(0,0,0,0.04)` blur 12 offset (0,4) | Card 기본 |
| `elev2` | `rgba(0,0,0,0.06)` blur 20 offset (0,8) | 떠 있는 카드 · BottomSheet 상단 |
| `elev3` | `rgba(0,0,0,0.12)` blur 40 offset (0,16) | 모달 |
| `neuPop` | 좌상 흰 `#FFFFFF` blur 10 (-4,-4) + 우하 `rgba(177,183,194,0.55)` blur 12 (4,6) | 뉴모피즘 액센트 — 메인 CTA / OAuth / 감성 카드 |
| `neuInset` | inner 좌상 흰 0.85 + inner 우하 `rgba(177,183,194,0.45)` | 뉴모 눌림 (pressed) |

원칙: 모든 카드 동일 elev1. 그림자 단계가 많으면 시각 위계를 추측해야 해서 인지 부하 ↑. 시니어 모드는 그림자 alpha 자동 강화 (또는 보더로 대체).

### 3.6 모션 (AppMotion)

| 토큰 | Duration / Easing | 용도 |
|---|---|---|
| `fast` | 80ms / `curvePress` easeOut | Press feedback |
| `base` | 200ms / `curveDefault` easeInOut | 표준 전환 / 카드 entry |
| `slow` | 320ms / `curveDefault` | 화면 전환 |
| `entry` | 400ms / `curveEntry` cubic(0.2,0,0,1) | 카드 등장 (Score 5장 stagger 200ms) |
| `exit` | 160ms / `curveExit` easeIn | 사라짐 |
| `modalEnter` | 220ms / easeOutCubic | Dialog 등장 (scale 0.96 → 1.0) |
| `celebrateEnter` | 280ms / **easeOutBack** | Celebrate (살짝 튀는 느낌) |

**Reduce Motion 대응**: `MediaQuery.disableAnimations` true → 모션 0ms (또는 fade만). 시니어가 빠른 모션에 어지러움 호소 가능.

햅틱 (iOS):
- 버튼 탭 Light · 토글 Medium · 분석 완료 Success notification · 오류 Warning · 응급 모달 Heavy.

로딩·대기:
- <0.4s 즉시 표시 / 0.4~1s Spinner / 1~4s Skeleton + 진행률 / 4~10s Skeleton + Streaming + 취소 / >10s 백그라운드 옵션.
- LLM (2.5~6초) → **Skeleton + Streaming + 취소**.

관련 코드: `lib/utils/design_tokens_v2.dart`

---

## §4. 공통 컴포넌트

### 4.1 기본 atoms (design_tokens_v2.dart에서 export)

#### AppCard
- 흰 배경 `#FFFFFF` + Elev 1 그림자 (보더 X 또는 1px `#EEF1F6`).
- 라디우스 16, 패딩 16~20.
- Tap state: scale 0.98 + bg 살짝 변경.
- 한 카드 = 한 가지 주제. Gestalt 근접성 — 카드는 시각적 경계로 "한 묶음" 즉시 인지.

#### AppPrimaryButton
- 브랜드 블루 `#4C7EF7` 솔리드 + 흰 텍스트 + 뉴모피즘 액센트.
- 라디우스 12, 높이 54 (시니어 60).
- pressed: opacity 0.85 또는 색 `#2F66E2` + scale 0.97 (80ms).
- Disabled: bg `border #EEF1F6`, text `inkTertiary`. Loading: bg 유지 + spinner 좌측 + "처리 중...".
- elderMode prop 자동 분기: height / fontSize / spinnerSize.

#### AppSecondaryButton
- 흰 배경 + 1.5px brand 보더 + brand 텍스트 (또는 1px `#DEE2E8` + ink 텍스트).
- 그림자 없음 또는 2단 약한 그림자.
- 라디우스 12, 높이 52.

#### AppTextField (§4.1.1 인풋 5대 우선순위 참조)
- **모서리 보더 깨짐 회피 CustomPaint** `_OutlinedBorderDecoration` — Flutter BoxDecoration border 모서리 렌더링 버그 회피.
- 높이 56 (시니어 64), 라디우스 12, 좌우 padding 18.
- 보더 평소 1.2px (옅음) / focus·error·ok 1.5px.
- 라벨 항상 노출 (floating X), 입력 후에도 라벨 보임 — 시니어 인지 부담 ↓.
- 4 상태: default / focus(brand) / ok(success ✓) / error(`#FFF5F5` bg + danger 보더).
- 상태 전환 AnimatedDefaultTextStyle + AnimatedContainer 120ms.

##### 4.1.1 인풋 5대 우선순위 (Lemon Aid는 본질적으로 데이터 입력 앱)

평균 사용자 1주 20~40회 인풋 진입. 12개 화면 × 평균 2.5 필드 = 30+ 인풋 인스턴스.

| # | 원칙 | UX 근거 |
|---|---|---|
| 1 | **즉시 인지 (Affordance)** | 0.3초 안에 "여기 적는다" 시각 단서 — 회색 베이스 + 보더 + 라벨 항상 노출 |
| 2 | **명확한 피드백 (Feedback)** | 입력 도중 OK / Error 즉시 — 사용자가 "잘 하고 있나?" 의문 없게 |
| 3 | **실패해도 회복 가능 (Recovery)** | 에러 메시지 "왜 틀렸는지" + "어떻게 고치는지" (예: "8자 이상, 영문+숫자") |
| 4 | **모든 사람 다 쓸 수 있음 (Accessibility)** | 시니어 · 저시력 · 키보드 사용자 도달 가능 — 라벨 크기 · 보더 대비 · 자동 포커스 |
| 5 | **반복해도 피로 없음 (Endurance)** | 매일 진입해도 시각 노이즈 X — 평소 차분, 액션 시점에만 색 강조 |

##### 4.1.2 인풋 변형

| 변형 | 용도 | 차이 |
|---|---|---|
| `AppTextField` | 단일 라인 | 기본 |
| `AppTextField(obscure)` | 비밀번호 | 마스킹 + 👁 토글 (3초 자동 복귀, 시니어 ON 기본) |
| `AppMultilineField` (TODO) | 챗봇 입력 / 메모 | minLines 1, maxLines 5, 자동 높이 |
| `AppNumberField` (TODO) | 체중 · 키 | 숫자 키패드 + 단위 suffix |
| `AppDateField` (TODO) | 생년월일 | 시스템 DatePicker |
| `AppOTPField` | 6자리 인증 | §5.4 Verify Email 별도 명세 |
| `AppSearchBar` (TODO) | 음식 검색 | 돋보기 + X clear + 자동완성 |

### 4.2 OutputCard — 5종 출력 카드 공통 셸

Score 화면 5장 + Dashboard 5장 모두 동일 위젯 사용. 약속된 필드:

```
{ label / icon / iconBg / iconFg / headline / detail / source / confidence / onTap }
```

- 라벨 (상단) `subheading` — 카드 컬러 액센트 (좌측 4dp 바)
- 아이콘 (좌상) — iconBg soft + iconFg
- headline (중) — `bodyEmphasis` 17/700 핵심 수치
- detail — `body` 본문 한 줄
- source — `caption` `inkMute` ("식약처 · 2분 전")
- confidence — ConfidenceBadge
- chevron — 우측 → 상세 페이지

### 4.3 ConfidenceBadge

AI 결과 확신도 표시. **결과 카드 4요소** 약속 동기화:

| 확신 | 색 | 라벨 |
|---|---|---|
| ≥ 0.8 | `success` | "확신 84%" |
| 0.6 ~ 0.8 | `warning` | "확신 70%" |
| < 0.6 | `danger` | "검토 권장" |

색만으로 의미 전달 X — 반드시 텍스트 라벨 병기.

### 4.4 EmptyState — 빈 화면 3종

빈 화면 = 3가지 이유:

| 상태 | 메시지 | 다음 액션 |
|---|---|---|
| 신규 | "기록을 시작해요" | "사진 한 번이면 5가지 결과" + 카메라 CTA |
| 동기화 실패 | "잠시 동기화가 안 됐어요" | "다시 시도" |
| 권한 없음 | "권한이 필요해요" | "설정 열기" + "수동 입력으로 계속" |

원칙: 빈 화면 절대 빈 채로 두지 않는다 (§2.1 원칙 4).

### 4.5 모달 시스템 (app_modals.dart) — 3종 위젯

`widgets/common/app_modals.dart` — 모달은 본 화면과 시각 무게 달라야 함 (Flat 2.0 + 뉴모피즘 30~40%).

| 위젯 | 용도 | 등장 모션 |
|---|---|---|
| `showAppDialog` (Soft Hybrid) | Confirm / Alert — 결정 묻기 | fade + scale 0.96 → 1.0, 220ms easeOutCubic |
| `showAppBottomSheet` | 옵션 리스트 / 폴백 안내 / 멀티 액션 | slide-up + scrim 0.5 |
| `showAppCelebrateDialog` | 성취 · 축하 (가입 완료 · 목표 달성 · 7일 연속) | scale 0.85 → 1.0, 280ms easeOutBack + confetti 6점 |

토큰:
- Scrim — Default `rgba(20,26,44,0.45)` / Soft 0.35 + blur 2px / Celebrate 0.50 + blur 6px.
- Dialog bg `section #F2F4F6` + 흰 inset border. Sheet bg `section`. Celebrate bg `surface #FFFFFF`.
- Radius — Dialog 28 / Sheet top 28 / Celebrate 28.
- Shadow — Modal drop `0 30px 60px -10px rgba(20,26,44,0.35)` / Sheet up `0 -20px 40px -10px rgba(20,26,44,0.25)` / Celebrate `0 24px 60px -12px rgba(20,26,44,0.28)`.
- Primary 글로우 — brand solid + blur 14 spread -4 alpha 0.55.
- Danger Secondary — text-only red (빨강 솔리드 매번 쓰면 둔감화).

사용 매핑:

| 상황 | 모달 |
|---|---|
| 작성 중 데이터 날아감 경고 | AppDialog Soft + Primary "계속 작성" / Secondary danger "나가기" |
| 단순 확인 (Yes/No) | AppDialog + Primary "확인" / Secondary "취소" |
| 단일 안내 (OK) | AppDialog + Primary "확인" 만 |
| 다중 옵션 (3+) | AppBottomSheet |
| 위험 결정 (계정 삭제) | AppDialog Hero (03 시안, 추후 추가) |
| 성취 · 축하 | AppCelebrateDialog + confetti |

폐기된 시안: 00 Material 기본 / 01 Flat Pure / 05 iOS Action Sheet.

Backdrop 탭 — Dialog/Sheet `barrierDismissible: true`. **Celebrate는 닫힘 X** (꼭 액션 눌러야 — 성취 충분히 보이게).

### 4.6 NutrientBar (영양소 충족률)

5단계 색상 + 라벨 병기 (색맹 대응). 색만 X — 항상 색 + 라벨 + 수치 3중.

| 단계 | 색 | 라벨 | 너비 비율 |
|---|---|---|---|
| deficient | `danger` | "결핍" | 0~35% |
| low | `warning` | "약간 부족" | 35~70% |
| adequate | `success` | "충분" | 70~130% |
| excessive | `warning` | "많음" | 130~UL% |
| risky | `danger` | "주의" | UL 초과 |

바 높이 12dp, 라벨 우측, 수치 좌측.

### 4.7 MainShell — BottomNav 5탭 (구현 시)

- BottomNavigationBar 셸 + IndexedStack (탭 전환 시 상태 보존) — 또는 StatefulShellRoute.indexedStack.
- 활성 = `AppColor.brand`, 비활성 = `AppColor.inkTertiary`.
- 아이콘 Material rounded. 평면 (뉴모 X).
- 매일 사용 영역이라 깔끔함 우선.

5탭 라벨 결정 — §7.3 참조 (사용자와 같이 결정, Claude 단독 X).

### 4.8 만들 것 (2주차 우선)

- `OutputCard` (위 4.2 규격 위젯화)
- `EmptyState` (위 4.4 3종 위젯화)
- `ConfidenceBadge` (위 4.3)
- `MainShell` (위 4.7 5탭 셸)
- `AppMultilineField` / `AppNumberField` / `AppDateField` / `AppSearchBar`

관련 코드: `lib/utils/design_tokens_v2.dart`, `lib/widgets/common/app_modals.dart`

---

## §5. 화면 명세

### 5.1 Splash (S-01)

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/splash_screen.dart` |
| 목적 | 앱 부팅 + 세션 복구 + 라우팅 결정 |
| 진입 | 앱 콜드 / 웜 부팅 |
| 출구 | (인증 OK) `/home` · (인증 X) `/login` · (에러) `/login` + Snackbar |

**시스템 splash (Android 12+)** — 흰 배경만 (`values-v31/styles.xml` · `values-night-v31`). 아이콘 제거 — 원형 마스크 강제 회피.

**Flutter Splash 시퀀스**:
- 로티 `assets/animations/lemonaid_gold.json` · 280×280 · 1.5x 속도 (원본 6초 → 4초 사이클) · 무한 반복
- 워드마크 제거 — 로티 + 태그라인만
- 태그라인 `상큼하게 찍고, 톡 쏘게 채우는 스마트 헬스케어` (17px = `bodyLg`)
- 태그라인 한 자씩 타이핑 (120ms/자, 150ms 지연 후 시작)
- "상" / "톡" 위 노란 점 — 0 → 10pt → 4 → 7 → 6 스프링 + 위에서 떨어짐 + 글로우 링 확산 + 글자 색 노란 깜빡
- 글자 톡톡 — 회전 ±8° → 0 + y -12 → 0 → -2 → 0 + 스케일 0.6 → 1.08 → 0.97 → 1.0

**라우팅 분기**:
- **개발 빌드** (debug/profile) — 타이핑 끝 + 안착 + 머무름 보장 (`_minSplashDuration` 동적 계산, 최소 2.0초 — 50대 로고 인식 + Lottie 1사이클 보장)
- **배포 빌드** (release) — 인증 응답 도착 즉시 라우팅. 로티는 그동안 무한 반복. 최대 15초 timeout. (네트워크 응답 늦으면 무한 loop)

면책 / 의료법: 표시 없음 (Consent 화면에서 일괄 처리).
시니어 모드: 표시 시간 ~ 2.5s (확실히 보일 때까지). 워드마크 32 → 36, 태그라인 16 → 19.
TalkBack: "Lemon Aid 앱을 시작하고 있어요. 잠시 기다려주세요" (한 번만 읽음).
reduceMotion: 떠다니는 모션 끔 / 페이드인만 유지.

관련 코드: `lib/screens/splash_screen.dart`

### 5.2 Login (S-02) — LoginV3 (현재 메인)

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/auth/login_screen_v3.dart` |
| 목적 | 기존 사용자 인증 — 카카오 우선 (50대 한국 사용자 가장 익숙) |
| 진입 | Splash (세션 없음) / 로그아웃 / Signup 완료 후 |
| 출구 | 홈 (기존) / Consent (신규 OAuth) / Signup (이메일 신규) |
| 시각 언어 | Hybrid Flat 2.0 + 뉴모피즘 액센트 (§3.5 `neuPop`) |
| 폐기 | v1 (평면 단독) · v2 (뉴모 단독) — 2026-05-12 파일 삭제 |

**OAuth 우선순위 (위 → 아래)**:

| 순서 | 버튼 | 색 | 이유 |
|---|---|---|---|
| 1 | 카카오 풀폭 + "최근 로그인했어요" 동적 툴팁 | bg `#FEE500` / fg `#191919` | 한국 50대 친화 1순위 + 재로그인 학습 |
| 2 | 구글 풀폭 | bg `#FFFFFF` + border `#DADCE0` 1.5px + Google G 4색 | 보조 OAuth |
| 3 | Apple 풀폭 (iOS 출시 시) | bg `#000000` + 흰 텍스트·로고 | App Store 가이드라인 4.8 (소셜 로그인 있으면 필수) |
| 4 | 디바이더 "이메일로 시작하기" 인라인 라벨 (라벨 좌우 라인 분리) | — | OAuth ↔ 이메일 영역 시각 분리 |
| 5 | 회원가입 / 로그인 분할 1:2 | brand outline / brand solid | 기존 사용자(로그인) 우선 |

**레이아웃** (워드마크 좌측 정렬, 캐릭터 우상단, 호흡 공간 중앙):

```
┌─────────────────────────┐
│  레몬•Aid                │  워드마크 44/800 (Gmarket Sans)
│  사진 한 번, 영양 분석 끝   │  body 16/600 inkSoft
│                         │
│         (호흡 공간)       │
│                  🍋     │  레몬 캐릭터 200×200 양팔 따봉 PNG (우상단)
│                         │
│  ┌─ 최근 로그인했어요 ─┐    │  검은 말풍선 (위아래 ±3dp 바운스, 텍스트 #FACC15)
│  ┌─────────────────────┐│
│  │ 💬  카카오로 계속하기 ││  bg #FEE500 / 54dp / radius 12 / neuPop
│  └─────────────────────┘│
│  ┌─────────────────────┐│
│  │ G   구글로 계속하기   ││  bg #FFF / border / 54
│  └─────────────────────┘│
│  ┌─────────────────────┐│
│  │ 🍎  Apple로 계속하기  ││  bg #000 / fg #FFF / 54 (iOS만)
│  └─────────────────────┘│
│                         │
│  ── 이메일로 시작하기 ── │  디바이더 + 인라인 라벨
│                         │
│  [ 회원가입 ][  로그인  ]│  1:2 비율 / brand outline + brand solid
│                         │
│  © Lemon Aid · 약관 · 개인정보 │  caption inkMute
└─────────────────────────┘
```

**툴팁 정밀 — radius 10 / padding 14×7 / 부드러운 그림자 2단 / 화살표 좌측 24 위치 / 위아래 ±3dp 바운스 1.4s / 텍스트 #FACC15 (검정 배경 위).**

**상태별 처리**:

| 상태 | 화면 변화 |
|---|---|
| OAuth 진행 중 | 해당 버튼만 spinner (kakao_loading: 카카오 bg alpha 0.9), 나머지 비활성 |
| 이메일 로딩 | Primary 버튼 spinner + "로그인 중..." |
| 인증 실패 | TextField 아래 helper text 빨강 "이메일 또는 비밀번호가 일치하지 않아요" |
| 네트워크 에러 | Snackbar 하단 + 재시도 액션 |
| 카카오톡 미설치 | 웹 카카오 자동 폴백 + "카카오 앱이 없어 웹으로 진행해요" 알림 |
| 최근 로그인 (재방문) | 마지막 로그인 provider에 툴팁 자동 표시 (secure storage `last_login_provider`) |

**시니어 모드**: OAuth 버튼 54 → 60, 폰트 16 → 18, 아이콘 20 → 22.

**친화도 빈틈 → 추가 결정**:
- OAuth 3종 실패 시 → 이메일 폼 강조 + Snackbar
- 백버튼 = 앱 종료 다이얼로그 (Splash로 X)
- 비밀번호 틀려도 이메일 입력 유지

관련 코드: `lib/screens/auth/login_screen_v3.dart`, `lib/services/oauth_service.dart`, `lib/utils/oauth_config.dart`

### 5.3 Signup (S-03)

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/auth/signup_screen.dart` |
| 목적 | 이메일 신규 가입 (OAuth 사용자는 이 화면 안 봄) |
| 진입 | `/login` → "회원가입" 분할 버튼 |
| 출구 | `/verify-email` (성공) / 이전 (취소) |

**1페이지 4필드**:

| 필드 | 검증 | 에러 메시지 |
|---|---|---|
| email | 정규식 + 백엔드 중복 확인 (debounce 600ms) | "이메일 형식이 아니에요" / "이미 가입된 이메일이에요" |
| password | 8자+ / 영문 / 숫자 | "8자 이상, 영문+숫자를 섞어주세요" |
| passwordConfirm | password와 일치 (서버 전송 X) | "비밀번호가 일치하지 않아요" |
| display_name | 2~10자 / 한글·영문 | "2~10자로 입력해주세요" |

**픽셀 (2026-05-12)**:
- 본문 상단 32, 좌우 24
- 타이틀 "환영해요" 32pt / w800 / letterSpacing -1.2 (첫 진입 강한 인상)
- 서브 "이메일로 시작할게요" bodyLg 17 / inkSecondary
- 서브 ↔ 첫 인풋 64 (88 → 64 조정)
- 인풋 ↔ 인풋 24, 마지막 인풋 ↔ "다음" 32, 인풋 높이 56 (시니어 64)

**상태 변화**: Default (Primary 비활성) → 입력 (helper text) → 실시간 검증 통과 (체크 ✓) → 모든 OK (Primary 활성) → 제출 중 → 서버 에러 (Snackbar 원복).

**인터랙션**:
- 키보드 순서: email → password → confirm → name → 완료 → 자동 제출
- 600ms debounce 중복 확인 / 비밀번호 보기 토글 (3초 자동 ●●● 복귀)
- 백버튼: 입력 있으면 AppDialog "작성 중인 정보를 버릴까요?"
- 자동완성 활성화 (autofillHints) — 시니어 키보드 타이핑 부담 ↓

**시니어 모드**: TextField 56 → 64 / Primary 54 → 60 / 폰트 16 → 19 / 비밀번호 보기 기본 ON.

관련 코드: `lib/screens/auth/signup_screen.dart`

### 5.4 Verify Email (S-04)

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/auth/verify_email_screen.dart` |
| 목적 | 이메일 인증 코드 입력 (가입 직후 1회) |
| 출구 | `/consent` (성공) |

**OTP**: 6자리 숫자. 매직 링크 안 씀 (시니어 친화).
**유효 시간**: 10분 (만료 시 재발송 요구).
**발송**: Resend (개발/MVP). 운영은 도메인 인증 후 자체 도메인.
**재발송 쿨다운**: 60초 (TextLink 처음 10초 비활성).
**Rate Limit**: 24h 내 5회 (백엔드).

**OTP 필드 (별도 컴포넌트 `AppOTPField`)**:
- 각 칸 44×56dp (시니어 56×64), gap 4dp (3·4 칸 사이 8dp — 3·3 시각 분리), border 1.5 line, focus brand, radius 12, font 24/700 (시니어 28).
- 자동 채움 — SMS otpAutofill 가능하면.
- 6자리 입력 끝 → 자동 제출 (시니어도 직관적). 시니어 모드는 "확인" 버튼도 함께 노출.

**상태**:

| 상태 | 화면 |
|---|---|
| Default | OTP 6칸 빈, 타이머 10:00 카운트다운 |
| 입력 중 | 칸 채워지면 다음 칸 자동 포커스 |
| 6자리 완료 | 자동 제출 |
| 검증 중 | 모든 칸 비활성 + spinner overlay |
| 코드 틀림 | shake 200ms + 6칸 초기화 + 안내 "코드가 일치하지 않아요" |
| 만료 | 타이머 00:00 → OTP 비활성 + "재발송하기" CTA |
| 재발송 후 | "새 코드를 보냈어요" Snackbar + 타이머 리셋 + 재발송 10초 비활성 |
| 5회 초과 | "24시간 내 5회를 초과했어요" + Primary 비활성 |

**친화도 빈틈 → 추가 결정**:
- "이메일이 안 와요" Ghost 버튼 → AppBottomSheet (스팸함 확인 / 도메인 차단 / 재발송 / 문의)
- 재발송 횟수 1/5 표시
- 코드 만료 후에도 화면 떠나지 않게 — "재발송"으로 즉시 새 코드
- 인증 성공 후 (추후) AppCelebrateDialog "가입 완료!"

관련 코드: `lib/screens/auth/verify_email_screen.dart`, 백엔드 `POST /api/v1/auth/verify-email`

### 5.5 Consent (S-05/S-06)

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/auth/consent_screen.dart` |
| 목적 | 의료법·약사법·개인정보·AI 한계 고지 + 동의 |
| 진입 | Verify Email (이메일 가입) / OAuth 첫 로그인 |
| 출구 | `/onboarding` (필수 3개 체크 후) |

**핵심 원칙 — 일괄 동의 버튼 X. 개별 체크 강제.** 다크 패턴 + 의료 동의는 한 줄씩 의식해야 함.

**체크 항목 4종**:

| 순서 | 라벨 | 분류 | DB type |
|---|---|---|---|
| 1 | 서비스 이용약관 | 필수 | `privacy` |
| 2 | 개인정보 수집·이용 (건강 정보 포함) | 필수 | `privacy` |
| 3 | AI 권고의 한계 이해 ("진단·처방 아님") | 필수 | `ai_usage` |
| 4 | 마케팅 정보 수신 | 선택 | (별도 type) |

**5종 type 매핑** (시점별):
- `privacy` — Consent 화면
- `ai_usage` — Consent 화면
- `health_data` — 백엔드 권한 요청 시점
- `image_storage` — Camera 첫 사용 시
- `notifications` — 선택, Onboarding 또는 Settings

각 체크 → `INSERT INTO consents (user_id, type, accepted_at)`. 취소 → `revoked_at` 갱신 (행 삭제 X, 감사 추적). 약관 버전 변경 → 다음 로그인 시 재동의.

**레이아웃**:
- 면책 카드 — Pink Card 배경 `pinkLight #FFE6EA` + ⚠ + "Lemon Aid는 진단·처방을 하지 않아요" `LemonText.disclaimer`
- 각 행 ListTile — Checkbox (24dp / 시니어 32) + 라벨(필수/선택 chip) + 텍스트 + "자세히" → BottomSheet 풀스크린 약관
- Primary 하단 고정 — "동의하고 시작" 필수 3개 체크 시 활성 + 살짝 펄스 (주의 끌기 1회)
- 일괄 동의 버튼 없음

**시니어 모드**: 체크박스 24 → 32, 각 행 56 → 72, 폰트 16 → 19, 면책 카드 강조 색 진하게.

**친화도 빈틈 → 추가 결정**:
- 약관 텍스트 BottomSheet에 "쉽게 말하면" 요약 위쪽 — 시니어가 법률 문장 부담
- 필수 미체크 시 살짝 흔들림 (3회 시도 시)
- 동의 후 어디서 확인? — Settings → "이용약관" 항상 접근 가능 안내 caption

관련 코드: `lib/screens/auth/consent_screen.dart`

### 5.6 Onboarding (S-06/S-07)

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/onboarding_screen.dart` |
| 목적 | 분석 필수 최소 정보 수집 |
| 진입 | Consent 완료 |
| 출구 | `/home` (완료) — 중간 이탈 시 진행도 저장 |

**6단계 (한 단계 = 한 질문)**:

| Step | 질문 | 입력 |
|---|---|---|
| 1 | 성별을 알려주세요 | RadioCard 2개 (남/여) + "선택 안 함" |
| 2 | 나이가 어떻게 되세요? | NumberInput + 슬라이더 보조 (14~100) |
| 3 | 키와 체중을 알려주세요 | NumberInput × 2 (cm 100~220 / kg 30~200) |
| 4 | 관리하고 있는 만성질환이 있나요? | ChipMulti — 당뇨·고혈압·이상지질·갑상선·골다공증·기타 + "없음" |
| 5 | 복용 중인 영양제가 있나요? (선택) | 카메라 진입 또는 "건너뛰기" |
| 6 | 어떤 도움을 받고 싶으세요? | RadioCard 3개 (영양·복약·다이어트) |

**진행 상태 저장** — localStorage 진행도 (다음 로그인 시 "이어서 하기" 카드).
**스와이프 좌우 단계 이동** — 단, 입력 안 한 다음 단계로는 못 감.
**스텝 전환 모션** — 슬라이드 200ms easeInOut.

**면책**:
- Step 4 "만성질환" 위 caption — "이 정보는 영양 권고 정확도를 높이는 데만 써요. 진단 정보가 아니에요."
- Step 5 "영양제" 위 caption — "사진은 분석 참고용으로만 사용해요. 처방 정보가 아니에요."

**시니어 모드**: RadioCard 56 → 72, 질문 폰트 24 → 28, ChipMulti 36 → 48, 슬라이더 thumb 24 → 32.

**친화도 빈틈 → 추가 결정**:
- 각 단계 "왜 묻나요?" 도움말 한 줄 — 예: "성별별 권장량이 달라요"
- Step 4에 "선택 안 해도 돼요" 명시 — 부담 ↓
- Step 5 건너뛰기 강조 — "지금 안 해도 나중에 가능해요"
- 마지막 Step에서 "수정하기" 링크 — 이전 단계로 점프

관련 코드: `lib/screens/onboarding_screen.dart`

### 5.7 Dashboard / 5종 출력 (S-07/S-08)

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/dashboard_screen.dart` |
| 목적 | 오늘 상태 한눈에 + 빠른 액션 |
| 진입 | 인증 완료 / BottomNav 탭 1 |
| 출구 | `/camera` `/health` `/chat` `/raffle` `/score` `/settings` |

**구조 — 세로 스크롤 스택** (가로 스와이프 / 그리드 모두 거부 — 시니어 친화):
- AppBar: "오늘의 건강" (Pretendard w800, brand-less 톤다운)
- 상단: 날짜 (M월 D일 (요일)) + "오늘 챙겨야 할 5가지예요" 한 줄 요약
- 카드 5장 — 모두 `OutputCard` 위젯
- 카드 간격 `AppSpace.lg` (16dp)
- FAB 우하단 "사진 찍기" (brand 색, 카메라 아이콘) → /camera

**카드 5개 매핑 (1차 구현, 2026-05-14)**:

| # | 라벨 | 아이콘 | iconBg / iconFg |
|---|---|---|---|
| 1 | 부족한 영양소 | `Icons.eco_rounded` | success soft / success |
| 2 | 오늘 권장 섭취량 | `Icons.restaurant_rounded` | brand soft / brand |
| 3 | 체중 예측 | `Icons.trending_down_rounded` | yellow soft / warning |
| 4 | 오늘 활동 권고 | `Icons.directions_walk_rounded` | brand soft / brand |
| 5 | 목적별 분석 — 피로 | `Icons.battery_charging_full_rounded` | danger soft / danger |

**결과 카드 4요소 약속** (모든 결과 카드 공통):
1. 결과 큰 글씨 — 사용자가 먼저 봐야 할 핵심
2. 확신 정도 — ConfidenceBadge (≥80 success / 60~80 warning / <60 danger)
3. 출처 / 시간 — 공식 DB · 마지막 업데이트 시각
4. 다음 행동 — "저장 / 고치기 / 더 보기" 한 줄

**데이터**:
- 1차 구현은 mock (UI/UX 우선 검증)
- 백엔드 `GET /api/v1/dashboard/today` 합의 후 교체
- 카드 onTap → 영양소 단위 모달 / 그래프 / 상세 페이지 (각 카드별)
- "활동 권고 v4" — AI 팀 메타스펙 합의 후 source 표기 통일

**상태**: Empty (첫 진입) → "사진 한 번 찍어보세요" CTA / Loading → 5개 Skeleton shimmer / Normal / Pull-to-refresh / 부분 데이터 / Error 카드별 재시도 / 오프라인 배너 "마지막 동기화 N분 전".

**원 5출력 명세 (Score 화면 — §5.9 참조)** — Dashboard와 별개로 분석 직후 5장 표시 화면.

**시니어 모드**: 충족률 숫자 32 → 40 / FAB 56 → 64 / 카드 padding 16 → 20.

**친화도 빈틈**:
- 첫 진입 Empty Card에 "30초 만에 시작하기" CTA + 큰 카메라 아이콘
- Pull-to-refresh 안내 한 번 (상단 손가락 데모 모션 1.2s)
- 응모권 누적 변화 강조 — "+1" 표시

관련 코드: `lib/screens/dashboard_screen.dart`, 백엔드 (TODO) `GET /api/v1/dashboard/today`

### 5.8 Camera (S-08/S-09)

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/camera_screen.dart` |
| 목적 | 영양제 / 식단 / 검진지 / 체중계 사진 한 번 — 앱 핵심 입력 |
| 진입 | Dashboard FAB / QuickAction "사진" / Onboarding Step 5 / Health 수동입력 |
| 출구 | Score (분석 시작) / 이전 (취소) |

**레이아웃** (immersive 풀스크린, AppBar 없음):
- 상단 좌측 ✕ 닫기 (40dp 검정 원 위 흰 X) / 상단 우측 💡 플래시 토글
- Body 카메라 프리뷰 + 중앙 가이드 박스
- 하단 1 — CategoryChip 4종 (영양제 / 식단 / 검진지 / 체중) 가로 스크롤
- 하단 2 — 좌 갤러리 thumbnail / 가운데 셔터 72dp / 우 전후면 전환

**카테고리별 가이드 박스**:

| 카테고리 | 비율 | 가이드 텍스트 |
|---|---|---|
| 영양제 | 4:3 가로 | "라벨이 잘 보이게" |
| 식단 | 1:1 정사각 | "음식 전체가 들어오게" |
| 검진지 | A4 비율 | "표 영역이 모두 보이게" |
| 체중 | 16:9 가로 | "숫자가 잘 보이게" |

**분석 흐름 (PG.md 확정 — Agent X / 알고리즘)**:
1. **OCR + 라벨링** (영양제 라벨 사진 → 텍스트)
2. **CSV DB 매칭** (`SupplementCsvImport` 우선 — 식약처·농진청)
3. **API 보조** (CSV에 없으면 외부 API)
4. **Pydantic 스키마 강제** (`SupplementParseResult`)

저장: `Supplement` + `SupplementIngredient` insert / `Meal.foods` jsonb. 출처 표시 안 함 (챗봇 안에서만). 로컬 24시간 캐시.

**상태**:

| 상태 | 화면 |
|---|---|
| 권한 미요청 | Material 권한 요청 |
| 권한 거부 | 풀스크린 안내 + "설정 권한 허용" + "갤러리만 사용" Ghost |
| Ready | 프리뷰 + 셔터 활성 |
| Capturing | 셔터 0.9 scale + 화면 흰 플래시 80ms |
| Captured | 미리보기 풀스크린 + "다시 찍기" Ghost + "분석 시작" Primary |
| Uploading | "사진 업로드 중... 30%" 진행바 |
| 분석 시작 | Score 화면으로 이동 (back stack에서 제거) |
| 갤러리 모드 | 그리드 갤러리 (다중 선택 최대 5장) |

**면책**:
- 카테고리 "검진지" 선택 시 상단 배너 — "분석 참고용이에요. 의료 결정은 의사와 상의해주세요."
- 카테고리 "영양제" 선택 시 caption — "사진은 처방 정보가 아니에요"
- 의약품 식별 시 단호한 거부 (백엔드 모델 분리)

**시니어 모드**: 셔터 72 → 96, CategoryChip 36 → 48, 가이드 텍스트 16 → 20, 후면 카메라 자동 + 자동 초점 우선.

**친화도 빈틈**:
- 첫 진입 1회 코칭 — "라벨이 보이게" 박스 위 화살표 모션 (3초 후 자동 사라짐)
- 흔들림 감지 (자이로) → "조금 더 가만히 찍어주세요"
- 어두운 환경 → 자동 플래시 권유
- 분석 중 백버튼 = 취소 다이얼로그

관련 코드: `lib/screens/camera_screen.dart`

### 5.9 Score (S-09/S-10) — 5출력 분석 결과

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/score_screen.dart` |
| 목적 | AI 분석 5종 카드 표시 — 앱의 핵심 가치 |
| 진입 | Camera 분석 시작 / Dashboard 최근 분석 / Chat 답변 |
| 출구 | Chat (자세히) / Camera (다시 분석) / 공유 / 저장 |

**5출력 카드**:

| ID | 카드 | 컬러 | 핵심 표시 |
|---|---|---|---|
| ① | 영양소 충족률 | Blue Card | NutrientBar × 6~8개 |
| ② | 결핍 진단 (5단계) | Pink Card | "칼슘 결핍 가능성" + 권고 1줄 |
| ③ | 식단 권고 | Green Card | "저녁: 두부 100g 추가" + 식품 3개 |
| ④ | 체중 예측 (1주/1개월/3개월) | Sky Card | 3개 수치 + 그래프 (fl_chart) |
| ⑤ | 활동 점수 v4 | Lemon Card | 72/100 + 어제 대비 +4 |

**카드 entry stagger** — ①부터 순서대로 400ms (stagger 200ms). Reduce Motion 시 즉시.

**Rate limit** — 분석 5회/일. 초과 시 "오늘 분석 한도 초과. 내일 다시" + Primary 비활성.

**면책 (이 화면이 핵심)**:
- 모든 카드 하단 caption — "참고용 정보예요"
- 면책 배너 (5장 끝) — pink card + ⚠ + "이 결과는 의료 진단이나 처방이 아니에요. 의료 결정은 의사·약사와 상의해주세요."
- 결핍 카드(②)에 약 이름 X — 영양소·식품 이름만
- 식단 권고(③)는 영양 측면 — "치료" 표현 X
- 체중 예측(④) caption — "현재 패턴 유지 가정 — 의료 진단 아님"

**상호작용**:
- 카드 탭 → 각 카드 상세 BottomSheet (자세한 표·근거·관련 질문)
- 카드 우측 ⋯ 아이콘 = 공유 메뉴 (long-press X — 시니어 학습 부담)
- 그래프 dot 탭 → 툴팁
- "더 알아보기" 탭 → Chat 화면 + 자동 첫 메시지 (카드 컨텍스트 전달)
- 공유 시 의료법 면책 자동 첨부

**시니어 모드**: 카드 padding 16 → 20, 핵심 수치 17 → 22, 카드 간격 12 → 20, 5출력 한 카드씩 보기 옵션 (Settings 토글).

관련 코드: `lib/screens/score_screen.dart`

### 5.10 Health (S-10/S-11)

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/health_screen.dart` |
| 목적 | 걸음수 · 심박 · 체중 · 수면 트래킹 |
| 진입 | BottomNav 탭 2 / Dashboard "건강" 카드 |
| 출구 | Score (v4 활동점수) / Settings (권한) / Camera (체중계 사진) |

**Period Chip** 3개 (7일 / 30일 / 90일) — 기본 7일.

**4종 카드**:

| 카드 | 메인 수치 | 보조 | 시각화 |
|---|---|---|---|
| 걸음 | 오늘 6,234보 | 평균 5,820 / 목표 8,000 | 7일 bar chart |
| 심박 | 휴식 68 bpm | 평균 / 최대 | line chart |
| 체중 | 68.5 kg | 1주 -0.3 / 1개월 -0.8 | line chart |
| 수면 | 7시간 12분 | 평균 / 깊은 % | bar chart |

**데이터 출처**:
- steps / heart_rate / sleep — health 패키지 (**iOS HealthKit 우선**, Android Health Connect 검토 예정)
- weight — 수동 입력 또는 체중계 사진 OCR (Camera 카테고리 "체중")

**상태**:

| 상태 | 화면 |
|---|---|
| 권한 미요청 | 풀스크린 CTA — "Lemon Aid가 건강 데이터를 읽도록 허락해주세요" |
| 권한 거부 | 카드별 "허용 안 됨 — 권한 다시 / 수동 입력만" |
| 데이터 OK | 4개 카드 표시 |
| 일부 데이터 없음 | 해당 카드만 "데이터가 없어요 — 수동 입력" CTA |
| 오프라인 | 캐시 + "오프라인" 배너 |

FAB "+ 수동 입력" → 4종 선택 BottomSheet → 숫자 입력.

**면책**:
- 심박 — "참고용이에요. 이상 증상은 의료기관에"
- 체중 — "건강 관리 측면 — 의료 진단이 아니에요"
- 수면 — "참고용이며 수면 장애 진단이 아니에요"

**시니어 모드**: 차트 카드 4개 → 2개씩 페이지 (캐러셀), 차트 200 → 240, 수치 17 → 22.

**친화도 빈틈**:
- 권한 요청 화면 — "허락하면 자동으로 걸음을 보여드려요. 거절해도 수동 입력 가능해요"
- 큰 변동 감지 (체중 1주 -2kg) → "최근 변화가 커요. 의료기관 상의가 도움될 수 있어요"
- 차트 아래 caption — "이 데이터는 본인만 봐요" (개인정보 안심)

관련 코드: `lib/screens/health_screen.dart`

### 5.11 Chat (S-11/S-12) — AI Agent 챗봇 (앱 핵심)

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/chat_screen.dart` |
| 목적 | 영양·복약 질문 → `chat` Agent 답변 |
| 진입 | BottomNav 탭 3 / Score "더 알아보기" / Dashboard 빠른 액션 |
| 출구 | Score / Camera (사진 권유 시) / 이전 |

**Agent 구조 (PG.md §7.5 — 분석은 Agent X)**:

| Agent | 역할 | 화면 |
|---|---|---|
| (알고리즘) | OCR + CSV DB + Pydantic | Camera → Score 흐름 |
| `personalization` | 사용자 맥락 기반 권고 생성 | Score 5출력 |
| `chat` | 자유 대화 | S-11 Chat ← 여기 |
| `evaluation` | 결과 평가 + 코멘트 | DailyScore.agent_comment |

→ Score에서 "더 알아보기" → `chat` Agent에 컨텍스트 + AnalysisResult 전달.

**레이아웃**:
- AppBar 좌측 ← + 가운데 레몬 캐릭터 아이콘 + "AI 어시스턴트" + 우측 🗑
- 상단 고정 배너 — 면책 pink card "의료 진단·처방이 아니에요" (항상)
- Body ScrollView (역방향) — ChatBubble 리스트
- 하단 추천 질문 — Chip 가로 스크롤 (3~5개)
- 입력바 — TextField (radius 24 pill, filled brandSoft) + 🎤 마이크 + ⏵ 전송

**ChatBubble**:
- Bot 좌측 정렬 + 32dp 레몬 캐릭터 아바타 + brandSoft 배경 + radius 16 (좌상 4dp 꼬리)
- User 우측 정렬 + brand 배경 + 흰 텍스트 + radius 16 (우상 4dp 꼬리)
- System 가운데 + 회색 caption + 시간
- Streaming — Bot Bubble 안 ●●● dot 200ms blink loop

**출처 — 챗봇 안에서만**:
- Bot Bubble 끝에 `citations[]` 있으면 chip ("식약처", "농진청", "KDRIs 2020")
- chip 클릭 → BottomSheet "출처 정보" (URL / 문서명 / 접근일)
- Score 화면엔 출처 표시 X

**Rate limit**: 분당 5회 / 일일 50회. 초과 시 Snackbar "잠시 후 다시 시도해주세요" + 전송 60초 비활성.

**의료 진단 질문 감지 (백엔드 키워드)**:
- "약 처방" "치료" "진단" → Bot Bubble "이건 의료기관에 문의해주세요" + Disclaimer 강조 + "그래도 일반 정보는?" 옵션
- 응급 키워드 ("가슴 아파요", "숨이 안 쉬어져요") → 풀스크린 119 안내 + 1초 후 자동 진동·소리

**시니어 모드**: 본문 16 → 19, 입력바 56 → 64, SuggestedChip 36 → 48, 추천 질문 5 → 3, 마이크 우선 안내.

**친화도 빈틈**:
- 답변 길이 짧게 (3~5문장 기본, 자세히는 사용자 요청 시)
- 음성 입력 첫 사용 시 마이크 권한 안내 + 1초 데모 사운드
- 답변 끝 "도움이 됐어요?" 👍 👎 학습용 피드백

관련 코드: `lib/screens/chat_screen.dart`, 백엔드 `POST /api/v1/agents/chat`

### 5.12 Raffle (S-12/S-13) — 응모권 (차별점 보상)

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/raffle_screen.dart` |
| 목적 | 응모권 누적 + 응모 상품 — "점수 부담 없는 보상" |
| 진입 | BottomNav 탭 4 / Dashboard 응모권 배너 / Score 완료 시 적립 시트 |
| 출구 | 응모 상품 상세 (v2) / Camera (응모권 받기) / Chat (FAQ) |

**핵심 원칙 — 점수 경쟁 X.** 만성질환자가 다른 사용자와 비교당하면 부담. 응모권은 "내 일정한 행동의 자연스러운 보상".

**적립 규칙**:

| 조건 | 응모권 |
|---|---|
| 첫 사진 (앱 가입 후) | +1 |
| 7일 연속 기록 | +2 |
| 30일 연속 기록 | +5 |
| 영양제 신규 등록 | +1 |
| 검진지 분석 | +2 |
| 매주 일요일 정산 | +1 (활동 점수 기반) |

**상한**: 일일 +3, 월 +30 (남용 방지).

**헤더 카드**:
- citrusLight 배경 + radius 24 + padding 24
- 누적 큰 숫자 "3" `display` 64/800 (count-up 0→실제값 800ms)
- 게이지 "▰▰▰▰▰▰▱ 6/7 일" + pill + citrus 채움
- "하루만 더 하면 +2장" caption accentStrong
- 우측 레몬 캐릭터 80dp

**응모 상품 카드** — bgElev + 이미지 80×80 + 제목 + "D-3" 마감 caption danger + 응모하기 버튼 48dp (40 → 48 시니어 보장).

**응모 상품 = 비의약품 한정** (영양제·체크업·도서). 의약품·치료 관련 절대 X.

**시니어 모드**: 누적 숫자 64 → 80, 응모하기 40 → 56, 상품 카드 padding 16 → 24, 적립 규칙 BottomSheet 자동 1회 표시.

**친화도 빈틈**:
- 첫 진입 헤더 아래 BottomSheet "응모권은 어떻게 받나요?" 첫 1회 자동
- 응모 완료 직후 "오늘도 사진 찍으면 +1장" 다음 액션 유도
- 당첨 알림 — 푸시 + 앱 안 큰 모달
- 응모 마감 임박 — D-2부터 푸시 1회

관련 코드: `lib/screens/raffle_screen.dart`

### 5.13 Settings (S-13/S-14)

| 항목 | 값 |
|---|---|
| 파일 | `lib/screens/settings_screen.dart` |
| 목적 | 계정 · 알림 · 접근성 · 시니어 모드 · 법적 고지 · 로그아웃 |
| 진입 | BottomNav 탭 5 / Dashboard 프로필 |
| 출구 | `/login` (로그아웃) / 각 서브 화면 |

**그룹 구조**:

| 그룹 | 항목 |
|---|---|
| 계정 | 프로필 (아바타 + 이름 + 이메일) |
| 일반 | 알림 / 언어 / 시간대 |
| 접근성 | 시니어 모드 / 큰 글씨 / 모션 줄이기 / 햅틱 |
| 데이터 | 건강 권한 / 사진 저장 / 백업·복원 / 내 정보 다운로드 |
| 정보 | 이용약관 / 개인정보 / AI 한계 / 오픈소스 라이선스 |
| 도움 | 자주 묻는 질문 / 문의하기 / 앱 평가 |
| 위험 영역 | 로그아웃 / 계정 삭제 (v2 — deleted_at + 3개월 복구) |

**원칙**:
- 시니어 모드 = **명시 토글** (자동 감지 X). 자동은 잘못 맞춤.
- 시니어 모드 ON 시 "큰 글씨 + 큰 버튼으로 바뀌어요" 미리보기 다이얼로그.
- 위험 영역 (로그아웃) 맨 아래 + 색 약화 — 실수 방지.
- 로그아웃 → 백엔드 refresh 토큰 revoke + 로컬 secure storage 삭제 + 카카오 토큰 회수.
- 버전 long-press → 디버그 정보 (개발 빌드만).

**친화도 빈틈**:
- 알림 끄기 시 — "이걸 끄면 응모권 적립·복약 시간 등 놓칠 수 있어요" 안내
- 고령자 모드 토글 옆 "어떤 게 바뀌나요?" 도움말

관련 코드: `lib/screens/settings_screen.dart`

---

## §6. 인증 / 보안 정책 (2026-05-13 확정)

### 6.1 계정 매칭 / 중복 정책

- **OAuth ID 매칭 우선** — 같은 `google_id` / `kakao_id` 면 같은 사람으로 간주 (자동 로그인).
- **이메일 중복 차단** — 다른 방식이라도 같은 이메일이면 신규 가입 거부 (409 Conflict).
  - 예: 이메일로 자체 가입한 `a@b.com` 이 있으면, 같은 이메일의 카카오/구글 신규 가입 차단.
  - 안내문에 어떤 방식으로 가입돼 있는지 분기 노출 ("구글로 가입돼 있어요").
- **다른 이메일이면 OK** — 같은 사람이라도 서로 다른 이메일이면 별개 계정 허용.
- **이메일 동의 미수락 OAuth** (카카오 `kakao_account.email` 미동의) — `email=None`. 이 케이스는 이메일 중복 검사 스킵 (`kakao_id` 매칭만).

### 6.2 이메일 인증

- **시점**: 자체 회원가입 직후 강제. 미인증 유저는 보호 라우트 진입 시 verify-email로 redirect.
- **UX**: 6자리 숫자 코드. 매직 링크 안 씀 (시니어 친화).
- **유효 시간**: 10분. 만료 시 재발송 요구.
- **발송 채널**: Resend (개발/MVP). 운영 가면 도메인 인증 후 자체 도메인 발신자.
- **재사용**: 비밀번호 찾기 등 다른 흐름에서도 같은 코드 발송 인프라 (`purpose` 컬럼으로 구분).

### 6.3 Rate Limit (남용 방지) — 필수

이메일·SMS·푸시·외부 API 호출 모두 **백엔드에서 가드**. 모바일 가드는 보조 (UX 차원).

| 작업 | 동일 식별자 | 단기 제한 | 일일 제한 |
|---|---|---|---|
| 이메일 인증 코드 발송 | email | 1분에 1회 | 하루 5회 |
| 비밀번호 찾기 코드 발송 | email | 1분에 1회 | 하루 5회 |
| 로그인 시도 실패 | email + IP | 10분에 5회 | (계정 잠금 또는 captcha) |
| OAuth 토큰 검증 | IP | 1분에 10회 | — |

- 초과 시 응답 **429 Too Many Requests** + `Retry-After` 헤더.
- 모바일 메시지: "잠시 후 다시 시도해주세요 (N초 후 가능)".
- 카운터 저장소: Redis (docker-compose 포함). 키: `rl:{purpose}:{email}`, TTL 자동 만료.
- **개발 환경 우회**: `kDebugMode` + 특정 테스트 이메일 (`dev+*@lemonaid.test`) 만 면제. 운영에선 절대 우회 없음.

### 6.4 비밀번호 정책

- 최소 8자, 영문 + 숫자 혼합 (특수문자 권장 — 강제 아님).
- 평문 저장 금지 (bcrypt — 백엔드 `passlib`).
- 사용자 표시 입력 마스킹 기본, 토글 보이기 허용 (시니어 ON 기본).

### 6.5 세션 / 토큰

- JWT **access 30분 / refresh 7일**.
- access 만료 시 refresh로 자동 갱신 (api_client 인터셉터).
- refresh 만료 → 강제 로그아웃 `/login`.
- 로그아웃 시 백엔드 refresh 토큰 revoke + 로컬 secure storage 삭제.

### 6.6 iOS 합류 시 작업 목록 (2026-05-13 합의 — Android 끝나고 진행)

**책임**: 팀 Mac 보유자 + Apple Developer 계정 (팀이 발급).

**GCP 추가 작업**:
- iOS OAuth Client ID 발급 — Bundle ID `com.lemonaid.lemon_aid`
- 새 환경변수: `GOOGLE_IOS_CLIENT_ID` (Android와 별도)
- Web Client ID는 그대로 공용 (백엔드 검증용)

**카카오 추가 작업**:
- 디벨로퍼스 → 플랫폼 → iOS 등록, Bundle ID 입력
- Native App Key는 Android와 동일 값 (플랫폼 공용)

**iOS 측 코드**:
- `mobile/ios/Runner/Info.plist`:
  - URL Scheme: `kakao{KAKAO_NATIVE_APP_KEY}`
  - URL Scheme: 구글 `REVERSED_CLIENT_ID`
  - LSApplicationQueriesSchemes: `kakaokompassauth`, `kakaolink`
- 다트 코드는 변경 거의 없음 (`kakao_flutter_sdk_user`, `google_sign_in` 둘 다 iOS/Android 공용)

**Apple Sign-In (App Store 가이드라인 4.8 — 소셜 로그인 있으면 필수)**:
- `sign_in_with_apple` 패키지 추가
- 백엔드 `POST /api/v1/auth/apple` (apple_id 컬럼 추가 필요 — User.social_provider enum에 'apple')
- Apple Developer 콘솔에서 "Sign in with Apple" capability 활성화
- 로그인 화면 "Apple로 계속하기" 버튼 onPressed 연결

**현재 코드 준비 상태**:
- `OAuthConfig` 가 키 한 군데로 모음 — iOS 추가돼도 그대로 확장
- `OAuthService.signInWithKakao()` / `signInWithGoogle()` 플랫폼 무관 동작
- 백엔드 `/auth/kakao` `/auth/google` 토큰만 받아 검증 — 클라이언트 OS 무관
- Android 코드 (manifest / build.gradle) 외엔 iOS 합류로 인한 모바일 코드 변경 거의 없음

### 6.7 키 관리 (소스 안 박기)

- API 키 / OAuth Native App Key / Client Secret / DB 비번 — 어떤 키도 `.dart` 파일에 평문 X.
- 주입 방법: `--dart-define=KEY=value`. `lib/utils/oauth_config.dart` 처럼 `String.fromEnvironment()` 한 군데에서만.
- `.env` 는 깃 제외, `.env.example` 은 깃 포함 (실 키 X).
- 키 노출 발견 시 즉시 (1) 회전 (재발급), (2) 사용자/팀 알림, (3) 가능하면 history rewrite.

관련 코드: `lib/utils/oauth_config.dart`, `lib/services/oauth_service.dart`, `lib/services/auth_repository.dart`, 백엔드 `src/api/v1/auth/`

---

## §7. 라우팅 / 네비게이션

### 7.1 라우터 구조

`lib/utils/router.dart` — go_router 단일.

- `initialLocation = /` (Splash)
- 라우팅 결정은 Splash 내부 `_initRoute`

**라우트**:
- `/` — Splash
- `/login` — Login v3
- `/signup` — Signup
- `/verify-email` — Verify Email
- `/consent` — Consent
- `/onboarding` — Onboarding (6 step)
- `/shell/{home, camera, chat, score, settings}` — 인증 후 메인 셸 (StatefulShellRoute.indexedStack)
- `/camera` — Camera (FAB 또는 QuickAction)
- `/score` — Score 5출력 (Camera 분석 후 또는 Dashboard 카드 클릭)
- `/health` — Health
- `/raffle` — Raffle
- `/settings` — Settings

### 7.2 라우터 가드 (인증 / 미인증 분기)

- Splash `_initRoute` — secure storage `auth_token` 읽기 → `/auth/me` 검증 → 200 / 401 분기
- 보호 라우트 진입 시 미인증 → `/login` redirect
- 이메일 미인증 → 보호 라우트 진입 시 `/verify-email` redirect
- 약관 버전 변경 → 다음 로그인 시 재동의 화면 (백엔드가 사용자의 미동의 type 체크)

### 7.3 5탭 셸 (2주차 — 진행 중, 잦은 변경 예상)

**현재 가안 — 사용자와 같이 만들면서 바뀐다**:
- 홈 / 건강 / 챗 / 응모권 / 설정 (이름·순서·개수 모두 미확정)
- 카메라가 중앙 탭인지 중앙 FAB인지 — 미확정
- 점수 / 응모 / 헬스 등 보조 탭 위치 — 미확정

**구현 시 기본 골격** (§4.7 MainShell):
- BottomNavigationBar 셸 + IndexedStack (탭 전환 시 상태 보존)
- 활성 = `AppColor.brand`, 비활성 = `AppColor.inkTertiary`
- 아이콘 Material rounded

> **중요**: 5탭 구조는 **사용자와 같이 결정**. Claude 단독 결정 금지.

관련 코드: `lib/utils/router.dart`

---

## §8. 데이터 / 상태 관리

### 8.1 Riverpod

- `auth_controller_provider` — 인증 상태 / login / logout / refresh
- (추가 예정) `elderModeProvider`, `dashboardProvider`, `analysisProvider`, `chatProvider`

### 8.2 Secure storage

- `auth_token` — JWT access
- `refresh_token` — refresh
- `last_login_provider` — 최근 로그인 OAuth ("kakao" / "google" / "apple" / "email") — Login v3 툴팁 동적 노출용
- (추후) `onboarding_progress` — 중간 이탈 진행도

### 8.3 백엔드 API 명세 (간단)

| Method | Path | 용도 |
|---|---|---|
| POST | `/api/v1/auth/signup` | 이메일 회원가입 |
| POST | `/api/v1/auth/login` | 이메일 로그인 |
| POST | `/api/v1/auth/verify-email` | OTP 6자리 검증 |
| POST | `/api/v1/auth/resend-verification` | 인증 코드 재발송 (rate-limited) |
| POST | `/api/v1/auth/kakao` | 카카오 OAuth |
| POST | `/api/v1/auth/google` | 구글 OAuth |
| POST | `/api/v1/auth/apple` | Apple OAuth (TODO iOS) |
| POST | `/api/v1/auth/refresh` | refresh → access 갱신 |
| POST | `/api/v1/auth/logout` | refresh revoke |
| GET | `/api/v1/auth/me` | 현재 사용자 + email_verified 상태 |
| GET | `/api/v1/dashboard/today` | TODO Dashboard 5카드 |
| POST | `/api/v1/agents/chat` | TODO chat Agent |
| POST | `/api/v1/agents/personalization` | TODO personalization (Score 5출력) |

응답 메타 4키 (AI 팀 합의 대기): `confidence` · `source` · `editable_fields[]` · `fallback_text`.

### 8.4 모델 — 느슨한 컨테이너 + raw 보존

백엔드 응답 키명 차이 흡수 — 모델 클래스는 필수 필드 + `raw: Map<String, dynamic>` 같이 들고 다님. 알 수 없는 키는 raw에 보존.

핵심 테이블 (PG.md §11.1 일치):
- `User` — id, email, password_hash, display_name, email_verified_at, social_provider enum (email/kakao/google/apple), social_id, deleted_at (3개월 복구)
- `EmailVerification` — id, user_id, token (6자리), purpose, expires_at (10분), verified_at
- `Consent` — id, user_id, type enum (privacy/ai_usage/health_data/image_storage/notifications), accepted_at, revoked_at
- `Supplement` + `SupplementIngredient` + `SupplementCsvImport`
- `Meal` (foods jsonb)
- `AnalysisResult` (5출력)
- `AgentRun` (chat 메시지당 1 row, 비용 기록)
- `AgentMemory` (세션 요약)
- `DailyScore` (activity v4 + agent_comment)

관련 코드: `lib/models/`, `lib/services/api_client.dart`, 백엔드 `src/models/`

---

## §9. Figma 작업 룰

### 9.1 페이지 구조

```
0_Cover            — 표지·메타 정보
1_Wireframe        — 저화질 흐름
2_Component        — 디자인 시스템 라이브러리
3_Screens          — 고화질 시안
4_Prototype        — 인터랙션 연결
5_Handoff          — 개발자용 (Inspect)
```

### 9.2 컴포넌트 네이밍

`Component/Variant/State` 형식. 예: `Button/Primary/Default`, `Card/Supplement/Editing`.
크기 단위 추가 시: `Button/Primary/Default/M`.

### 9.3 모바일 해상도

- 기본: 390×844 (iPhone 15 Pro)
- 검증: 360×800 (Android 평균)
- 큰 화면: 430×932 (iPhone Pro Max)
- 시니어 친화 검증: 시뮬레이터에서 동적 글꼴 확대 200% 켜고 보기

### 9.4 Auto Layout 강제

모든 컴포넌트는 Auto Layout. 반응형 확장 가능하게.

### 9.5 Figma Variables 우선

Local Styles 대신 Variables — 다크 모드 / 시니어 모드 전환이 모드 스위치만으로 가능.
Figma Variables 값 → `mobile/lib/utils/design_tokens_v2.dart` 1:1 매핑.

### 9.6 Figma AI / Make 프롬프트

화면 코드가 끝날 때마다 Figma AI 프롬프트도 작성. 코드 ↔ Figma ↔ 다이어리 3방향 일치 유지.

**작성 룰**:
- 영문 (Figma AI 영문 더 잘 이해)
- 토큰 값은 Hex·dp 그대로 명시
- 좌표·간격 명시 (px)
- 폰트 Pretendard 또는 Gmarket Sans 명시
- 마지막에 "Mobile 390×844 viewport, Auto Layout, Korean text exactly as below" 박기

화면별 프롬프트 작성 상태 — 추후 누적 (현재 S-02 Login + Email Sheet + Login CTA 12 variant 완성).

관련 코드: (디자인) Figma URL, `mobile/lib/utils/design_tokens_v2.dart`

---

## §10. 도구 분담

| 도구 | 용도 | 결과물 |
|---|---|---|
| **Stitch** | 빠른 와이어프레임 · 랜딩 탐색 | 흐름 1차 안 |
| **Claude Design** | 컴포넌트 디테일 · 그라데이션 · 아이콘 · 모달 핸드오프 | 컴포넌트 2차 안 |
| **Figma** | 최종 시안 + 핸드오프 | 개발에 넘기는 결과물 |
| **VS Code + Claude Code** | 토큰 · 위젯 코드 작성 | `mobile/lib/` 안 |

**흐름**: Stitch / Claude Design 으로 탐색 → Figma에서 정리 → Claude Code로 Flutter 옮기기.

**UI vs UX 결정 워크플로 (2026-05-11)**:
- **UI 결정** = 발주처 자사 앱 (건강의신) 스크린샷 먼저 본다. 컬러·라운드·여백·아이콘·카드 배치.
- **UX 결정** = 가상폰에서 직접 써보고 결정. 화면 흐름·버튼 위치·면책 노출 방식·온보딩 길이.
- **두 영역 충돌 시 UI를 양보**. 만성질환자가 못 쓰는 UI는 발주처 톤이라도 거른다 (예: 너무 작은 칩 텍스트).

**속도 우선 워크플로**:
- 80% 완성도로 일단 띄운다
- 5분 결정 룰 (못 정하면 동전)
- 돌이킬 수 있는 결정은 그냥 / 돌이킬 수 없는 결정만 깊이 (Brand color, 핵심 흐름, 데이터 모델)
- 시간 박스: Lo-fi 와이어 15분 / Hi-fi 시안 60분 / 토큰 결정 10분 / 마이크로카피 5분 / 의료법 검수 10분
- 5명 중 3명 막힘 → 폐기

---

## §11. 운영 / 검증 정책 (출시 전 체크)

### 11.1 접근성 (WCAG 2.2 AA)

- 본문 16px+, 대비 4.5:1 (§3.1.7 표 참조)
- 모든 액션 키보드 접근 / 포커스 링 (border 2px brand)
- 아이콘 버튼 semanticLabel
- 화면 진입 시 첫 헤딩 자동 읽기 (TalkBack)
- iOS Dynamic Type 7단계 — 200% 확대해도 레이아웃 유지 (Auto Layout)
- Reduce Motion 시 fade만 (또는 0ms)
- 색맹 대응 — 색만으로 정보 전달 X → 색 + 아이콘 + 라벨 3중 (Deuteranopia 시뮬레이션 통과)
- 자동 토스트 X (명시 닫기)
- 폼 timeout 최소 60초

### 11.2 시니어 모드 (Settings 토글)

- 명시 토글 (자동 감지 X) — Settings → "시니어 모드"
- ON 시 미리보기 다이얼로그 "큰 글씨 + 큰 버튼으로 바뀌어요"
- 적용 — 폰트 · 터치 · 보더 · 비밀번호 마스킹 등 토큰 자동 swap (§3.1.8 / §3.2.3 / §4.1)

### 11.3 다크 모드

- v2 (운영 직전 별도 결정) — §3.1.9 원칙 미리 박음
- 시스템 설정 따름 + Settings 토글로 강제 가능

### 11.4 다국어 (v2)

- 한국어 기본 / 영어 v2 검토
- 마이크로카피는 한국어 자연스러움 우선 — 직역 X

### 11.5 의료법·약사법 면책 표시

- 첫 진입 1회 풀 모달 — Consent 화면 자체가 면책 화면
- 권고 화면 (Score / Chat) 하단 작은 배너 (접힘 가능)
- 주 1회 풀버전 재노출 (v2)
- 모든 결과 화면 하단 푸터 — "건강 참고용이며 진단·처방이 아닙니다" (한 줄 고정)
- 챗봇 상단 배너 영구 (스크롤 무관)
- 발표 / 브리핑 PDF — `Lemon_Aid_Week1_Integrated_Briefing.pdf` 1주차 최종본

### 11.6 응급 신호 감지 정책

- 키워드 "가슴 통증" "호흡곤란" "숨이 안 쉬어져요" "가슴 아파요" → 풀스크린 119 안내 + 1초 후 자동 진동·소리
- 닫기 friction (의도적 어렵게)
- BMI <17 등 섭식장애 신호 → 다이어트 권고 사라짐 + 1577-0199 / 한국섭식장애협회 버튼
- 응급 케이스 5개 단위 테스트 필수

### 11.7 핸드오프 체크리스트

#### Figma 측
- [ ] Auto Layout 전체
- [ ] Variables 정의 (Light 기본, Dark 토큰)
- [ ] Inspect 토큰 이름 노출
- [ ] Constraint 설정
- [ ] 5상태 Variant (Default / Hover / Pressed / Disabled / Loading)
- [ ] Empty State / Error State / Loading (Skeleton)

#### 코드 측 (`mobile/lib/`)
- [ ] design_tokens_v2.dart ↔ Figma Variables 매핑
- [ ] 화면별 5상태 처리
- [ ] Reduce Motion 대응
- [ ] Dynamic Type 200%
- [ ] Semantic 라벨
- [ ] 의료법 카피 검수
- [ ] 면책 고지
- [ ] 응급 신호 단위 테스트

#### QA 측 (W7)
- [ ] iOS 시뮬레이터 (15 / SE)
- [ ] Android (Pixel 7 / Galaxy A)
- [ ] 실기기 1대
- [ ] 50대 사용자 1명 시연
- [ ] 의료자문위 1회
- [ ] 응급 신호 케이스 5개

### 11.8 사용성 테스트 (W7)

- 내부 5명 + 멘토·자문위 3명
- 시나리오 5개 (각 5분): 신규 등록 / 영양제 등록 / 5종 출력 이해 / 챗봇 알림 / 설정 변경
- 측정: 완료 시간 / 막힌 지점 / 정성 코멘트 / SUS / "다시 쓰고 싶나" 5점
- 도와주지 X / 화면 녹화 (동의) / 5명 중 3명 막힘 = 수정
- 출력물: `docs/usability-w7.md`

### 11.9 A/B 실험 백로그

- EXP-001 Splash 2.0s vs 1.5s
- EXP-002 Consent 일괄동의 유무
- EXP-003 응모권 진입점 위치
- EXP-004 챗봇 자동 인사말 ON/OFF
- EXP-005 Dashboard 카드 순서
- EXP-006 시니어 모드 토글 위치
- EXP-007 면책 고지 모달 vs 인라인
- EXP-008 의료법 카피 권유형 vs 정보형
- EXP-009 사진 촬영 가이드
- EXP-010 알림 디폴트 시간

관련 코드: 응급 키워드 — 백엔드 `src/api/v1/agents/chat.py` (TODO), `lib/screens/chat_screen.dart`

---

## §12. 변경 로그 (간략)

상세는 본 챕터 안에 누적됨. 여기는 한 줄 색인.

| 날짜 | 챕터 | 변경 요약 |
|---|---|---|
| 2026-05-11 | §3 | 컬러 톤 재정의 — 건강의신 분석 (블루 메인 + 노랑 액센트 + 컬러 카드 시스템) |
| 2026-05-11 | §3.2 | 폰트 패밀리 확정 — Pretendard / Gmarket Sans Bold / Plus Jakarta Sans + 자동 설치 스크립트 |
| 2026-05-11 | §5.1 | Splash 노출 시간 1.5s → 2.0s (시니어 로고 인식 + Lottie 1사이클) / 시작하기 버튼 제거 |
| 2026-05-11 | §5.1 | 네이티브 splash 단순화 (로고 제거, 흰 배경만) — Flutter Splash만 유지 |
| 2026-05-11 | §5.2 | Login OAuth 3종 (카카오 / 구글 / 이메일) → Apple 추가 → 카카오·구글 풀폭 + 회원가입/로그인 분할 1:2 |
| 2026-05-11 | §5.2 | 워드마크에 노란 점 (건강의신 마이크로 디테일 모방) |
| 2026-05-11 | §5.2 | "최근 로그인했어요" 동적 툴팁 (`last_login_provider` 기반) |
| 2026-05-11 | §5.5 | Consent 일괄 동의 버튼 제거 — 개별 체크 강제 (다크패턴 방지 + 개인정보보호법) |
| 2026-05-11 | §5.8 | Camera 분석 흐름 — OCR → CSV DB 우선 → API 보조 → Pydantic 강제 (Agent X / 알고리즘) |
| 2026-05-11 | §5.11 | Chat — 3 Agent (chat / personalization / evaluation) + 알고리즘 분리 명시 |
| 2026-05-11 | §5.11 | 출처 — 챗봇 안에서만 (Score 화면 X) — citations chip + BottomSheet |
| 2026-05-11 | §8 | iOS HealthKit 우선 / Android Health Connect 검토 예정 |
| 2026-05-11 | §6.6 | iOS 합류 시 작업 목록 합의 (Apple Sign-In 필수 / Bundle ID / GCP iOS Client ID) |
| 2026-05-12 | §3 / §5.2 | 디자인 시스템 v1.0 (뉴모피즘) 채택 → v2.0 (Flat 2.0) 재채택 → 최종 v2.1 Hybrid (Flat 80~90% + 뉴모 10~20%) |
| 2026-05-12 | §5.2 | Login v3 메인 — v1·v2 파일 삭제 |
| 2026-05-12 | §3.2 | 워드마크 한글화 — "Lemon" → "레몬" / "레몬•Aid" |
| 2026-05-12 | §5.2 | 화면 배경 화이트 통일 (#FFFFFF) — 크림 #FEFAE0 폐기 |
| 2026-05-12 | §5.2 | 캐릭터 — 공식 Lemon-Aid 양팔 따봉 PNG / 앱 아이콘 — USAGE 시트 공식 아이콘 (라운드 사각 1024 + 어댑티브 비활성화) |
| 2026-05-12 | §3.1 | 컬러 시스템 확정 — `#4C7EF7` 브랜드 블루 + `#FFC700` 레몬 옐로 메인 2색 |
| 2026-05-12 | §4.1 | AppTextField 인풋 디자인 정의 (라벨 항상 노출 / CustomPaint 보더 / 4 상태) |
| 2026-05-12 | §4.5 | 모달 시스템 3종 — AppDialog Soft Hybrid / AppBottomSheet / AppCelebrateDialog |
| 2026-05-12 | §5.3 | Signup px 조정 — 서브 ↔ 첫 인풋 88 → 64 / 본문 상단 16 → 32 |
| 2026-05-13 | §6 | 인증 / 보안 정책 확정 — 계정 매칭 / 이메일 인증 / Rate Limit / 비밀번호 / 세션 / iOS 합류 |
| 2026-05-14 | §5.7 | Dashboard 5종 출력 카드 1차 구현 (세로 스크롤 스택, OutputCard 통일, mock 데이터, FAB 사진 찍기) |
| 2026-05-18 | §5.7 | Dashboard v3 shell (`dashboard_screen_v3.dart`) — LADS §13 / liquid-glass + AtoZ + canvas BG / 6섹션 (마스코트·카메라 CTA·영양 충족률·5출력 그리드·최근 분석·면책) / 만성질환 배지 차별화 §16 / Claude Design Export ZIP 도착 시 디테일 교체. 진입 `/dashboard-v3` 프리뷰. v2 `dashboard_screen.dart` 는 그대로 유지. |

---

> 본 문서는 **Lemon Aid 의 모든 UX/UI 결정의 단일 진실 원천**.
> 새 결정은 카테고리 안 내용으로 누적. 새 §X.X 만들지 않는다.
> §12 한 줄 색인에 날짜·챕터·요약만 추가.
> 코드만 바꾸고 이 문서를 안 갱신하면 작업 미완료.
