# 🎨 UI/UX Design Diary

> 태동의 작업 노트 · Lemon Aid · 2026.05 ~
> 디자인·결정·실험·회고를 매일 한 줄씩 쌓는 자리

이 다이어리는 **개인 작업 기록**이다.
팀 공식 문서는 `PROJECT_GUIDE.md` — 큰 결정은 거기에 박고, 그 결정에 이르는 과정과 근거는 여기에 쌓는다.

세 가지 의도:
- 🪞 **거울** — 내 결정을 6개월 뒤 다시 보고 "왜 그랬더라?" 답할 수 있게
- 🌱 **씨앗** — 작은 실험·관찰을 묶어두면 큰 패턴이 보인다
- 🎒 **짐** — 다음 프로젝트로 들고 갈 디자인 시스템의 출발선

---SPLIT---

## 1. 다이어리 사용법

### 1.0 다이어리 vs PROJECT_GUIDE.md — 분리 원칙 (가장 중요)

| 다이어리 (UX_DIARY.md) | 팀 가이드 (PROJECT_GUIDE.md) |
|----------------------|--------------------------|
| 🛠 **작업장** (변동 잦음) | 📌 **공식 합의** (안정) |
| 본인 단독 수정 자유 | 변경 시 §17.10 파급 효과 검토 + 팀 리뷰 |
| 실험·고민·버린 대안 OK | 결정된 룰만 |
| 매일 수정해도 OK | 큰 변경만 PR로 |

#### 작업 흐름

```
1. 아이디어·실험·고민 → 다이어리에 자유롭게 쓴다
2. 며칠 굴려보면서 정리된다
3. "이건 팀에 공유할 만큼 굳어졌다" 판단되면
4. PG.md 해당 §에 정리해서 옮긴다 (별도 PR)
5. 다이어리에는 "PG.md §X로 이관 완료" 표시만 남김
```

> ✅ 다이어리는 본인 마음대로 수정해도 됨. PG.md는 안정된 합의만.
> 다이어리에서 매번 PG.md 갱신하려고 하지 말 것. 굳어진 다음에 한 번에.

### 1.0a 디자인 워크플로 대원칙 (2026-05-11 확정)

**UI = 건강의신 톤을 따른다 / UX = 앱을 만들면서 결정한다**

| 영역 | 결정 방식 | 근거 |
|------|----------|------|
| **UI** (컬러·타입·아이콘·일러스트·카드·버튼·여백) | 건강의신 스크린샷을 레퍼런스로 1:1에 가깝게 추종 | 발주처 자산 일관성 + 검수 통과율 우선 |
| **UX** (정보구조·플로우·상호작용·온보딩·면책 위치·고령자 모드) | 코드 만들면서 가상폰에서 직접 써보고 결정 | 만성질환 50대 + AI Agent라는 새 조합은 책상 위 설계만으로는 안 됨 |

**왜 이렇게 나누는가**

- 건강의신은 발주처가 이미 100억대로 굴리는 자산. 그 톤을 거스르는 새 앱은 검수 통과가 어렵다.
- 그러나 Lemon Aid는 건강의신에 없는 새 가치(AI Agent·5출력·만성질환 분석)를 가진다. 그 새 가치의 UX는 건강의신에 답이 없다 → 만들면서 발견해야 함.
- 그래서 외피(UI)는 발주처 톤 / 내장(UX)은 우리가 발견.

**구체 운영 룰**

1. **UI 결정 = 건강의신 스크린샷 먼저 본다.** 컬러·라운드·여백·아이콘 스타일·카드 배치 — 건강의신에 비슷한 게 있으면 그것을 따른다.
2. **UX 결정 = 가상폰에서 직접 써보고 결정한다.** 화면 흐름·버튼 위치·면책 노출 방식·온보딩 길이 — 코드 만들어 직접 손으로 만져본 다음에만 결정.
3. **다이어리에 둘을 분리해서 기록한다.**
   - §12.5 = UI 결정 (건강의신 참고)
   - §8 일지 + §14.8 누적표 = UX 결정 (앱 만들면서 발견한 것)
4. **두 영역이 충돌하면 UI를 양보한다.** 만성질환자가 못 쓰는 UI는 발주처 톤이라도 거른다 (예: 너무 작은 칩 텍스트).

### 1.0b 사용자 친화 7대 원칙 (UX 1순위 — 모든 결정의 상위 룰)

**전제: 사용자가 못 쓰면 UI도, 비즈니스도, AI도 의미 없다. 친화가 모든 결정의 상위 룰이다.**

대상 사용자 (구체화)

| 1차 | 만성질환 관리 중인 50~60대 — 당뇨·고혈압·이상지질 등 |
| 2차 | 부모님께 앱을 깔아드리는 30~40대 자녀 |
| 3차 | 일반 영양·식단 관리에 관심 있는 30~40대 |

**원칙 1 — 한 화면 한 일 (Hick의 법칙)**

각 화면은 사용자가 할 일이 **한 가지**여야 한다. 둘 이상이면 메인 1 + 보조 1 + 부가 0~1까지.

- 좋음: Dashboard는 "오늘 상태 확인" 이 핵심. 다른 것 다 보조.
- 나쁨: 한 화면에 입력 폼 + 차트 + 챗봇 + 광고 동시 → 50대 패닉

**원칙 2 — 큰 글씨 큰 터치 (Fitts의 법칙)**

- 본문 최소 16dp / 핵심 17~20dp / 고령자 모드 19~22dp
- 터치 최소 48×48dp / 고령자 56×56dp
- 두 버튼 사이 최소 8dp 간격 (오터치 방지)
- 비밀번호 보기 기본 ON (50대는 ●●● 안 보이면 답답)

**원칙 3 — 솔직한 면책 (의료법 + 신뢰)**

- 분석 결과·챗봇 답변엔 항상 "참고용" 명시
- "진단" "처방" "치료" 단어 X
- 응급 키워드 (가슴 통증·호흡곤란) → 즉시 119 안내
- 다크패턴 X — 일괄 동의 버튼·작게 숨긴 약관 등

**원칙 4 — 다음 액션 명확 (Doherty 0.4초)**

- 모든 화면에 primary 1개 — 사용자가 "다음 뭐 해야 하지?" 묻지 않게
- 로딩 1.5초 넘으면 progress bar + 진행 단계 텍스트
- 빈 상태 (Empty)는 절대 빈 화면 X — 다음 액션 CTA
- 에러는 친절한 한 줄 + 재시도 / 대안 액션

**원칙 5 — 폴백 항상 (네트워크 X / 권한 X / 데이터 X)**

- OCR 실패 → 수동 입력
- 카메라 권한 거부 → 갤러리 모드
- 건강 권한 거부 → 수동 숫자 입력
- API 실패 → 캐시된 결과 + "마지막 동기화 N분 전"
- AI 응답 실패 → "다시 시도" + Mock 답변
- 모든 화면은 인터넷 없어도 최소 1개 기능 동작

**원칙 6 — 빠른 학습 (50대 인지 부담 낮춤)**

- 첫 진입은 항상 안내 (코치마크 X — 너무 길면 닫고 잊어버림. 첫 빈 상태 CTA로 대체)
- 같은 아이콘은 같은 의미 (홈 = 집, 검색 = 돋보기, 카메라 = 카메라)
- 메뉴 명사는 사용자 언어 ("응모권" O / "리워드" X / "마일리지" △)
- 동일 액션은 동일 위치 (Primary 항상 하단, 닫기 항상 좌상)
- 학습 곡선 : 첫 3분 안에 핵심 가치 1회 경험 (사진 → 5출력)

**원칙 7 — 회복 가능 (실수 → 되돌리기)**

- 모든 위험 액션 (삭제·로그아웃·응모) → 확인 다이얼로그
- Snackbar로 액션 후 "되돌리기" 5초 제공
- 입력 중 백버튼 → "버릴까요?" 다이얼로그 (입력값 보호)
- 30일 데이터 저장 (실수로 지운 분석 복구)
- 자동 저장 — 입력 중 앱 죽어도 60% 복구

**친화도 체크표 (각 화면마다)**

| 항목 | OK 조건 |
|------|--------|
| 한 화면 한 일 | primary action 1개로 답할 수 있는가 |
| 큰 글씨 큰 터치 | 모든 텍스트 16+ / 터치 48+ 확인 |
| 면책 | 분석·권고에 caption 또는 배너 |
| 다음 액션 | primary 1개 시각적으로 가장 강함 |
| 폴백 | 인터넷·권한·데이터 없을 때 화면이 비지 않음 |
| 빠른 학습 | 첫 진입 사용자가 안내 없이 30초 내 핵심 발견 |
| 회복 가능 | 실수한 action에 되돌리기 또는 확인 |

→ 각 화면 명세 ⑫번 "결정·메모"에 친화도 체크 결과 추가.

### 1.1 무엇을 쓰나

- **결정**한 것 — 화면 길이, 버튼 위치, 컬러 선택
- **결정한 이유** — 공식·페르소나·관찰
- **버린 대안** — 왜 안 골랐는지
- **실험** — A/B 테스트, 사용자 5명 관찰, 본인 셀프 테스트
- **회고** — 1주일·1개월 후 그 결정이 잘 됐는지
- **고민 중인 것** — 아직 결정 못 한 사항도 쓰기 (도움됨)
- **버려도 되는 메모** — 잡생각·영감·링크

### 1.2 무엇을 안 쓰나

- 단순 to-do (Notion·Things 같은 데에)
- 코드 스니펫 (Gist·VS Code 안에)
- 일상 잡담 (그건 일기장에)

### 1.3 톤

1인칭으로 쓴다. "~했다", "~인 것 같다", "이거 마음에 든다". 보고서 톤 X.

### 1.4 PG.md 이관 시점 판단

다음 중 2개 이상이면 PG.md에 옮길 만큼 굳어진 것:

- [ ] 같은 결정을 1주일 이상 안 바꿨다
- [ ] 다른 팀원이 알아야 충돌이 안 난다 (예: 디자인 토큰, 화면 흐름)
- [ ] 코드에 이미 적용했고 잘 동작한다
- [ ] 회고 1회 이상 했고 후회 없다
- [ ] 5명 모두 따라야 하는 룰이다

→ 위 조건 충족 시 §해당 페이지에서 "PG.md §X로 이관" 메모 남기고 옮김.

### 1.5 형식

매 결정마다 5단 템플릿:

```
## YYYY-MM-DD — [화면 또는 컴포넌트]

### 결정
한 줄 요약.

### 근거
어느 공식·페르소나·관찰 따라 결정했나.

### 대안
고려했지만 버린 옵션 + 왜.

### 후속
- 코드 반영: lib/xxx
- PG.md 이관 후보: §X.X (굳어지면)
- 다음 검토 시점

### 회고 (나중에 채움)
실제 써보니 어땠는지.
```

---SPLIT---

## 2. 내가 외운 공식

검수할 때 옆에 펴놓고 본다.

### 2.1 Nielsen 10 Heuristics (1994)

UX 평가의 30년짜리 표준. 매 화면을 다음 10개로 자가 검수.

| # | 원칙 | Lemon Aid 적용 |
|---|------|---------------|
| 1 | 시스템 상태 가시성 | OCR·LLM 진행률·스피너·상태 라벨 |
| 2 | 현실 세계 매칭 | 영양제 = 약통, 음식 = 접시 그림 |
| 3 | 사용자 제어·자유 | AI 결과 미리보기 → 승인 (자동 저장 X) |
| 4 | 일관성·표준 | iOS HIG / Material 3 따라가기 |
| 5 | 오류 방지 | 상한 초과 영양제는 입력 단계에서 경고 |
| 6 | 기억보다 인지 | 만성질환은 칩, 약 이름은 자동완성 |
| 7 | 유연성·효율 | 카메라/갤러리/수동 입력 3옵션 |
| 8 | 미니멀 | 한 화면 한 메시지 |
| 9 | 오류 회복 | "다시 시도" + 수동 입력 폴백 |
| 10 | 도움말·문서 | "?" 토글로 인라인 설명 |

### 2.2 실전 3법칙

| 법칙 | 식 | Lemon Aid 룰 |
|------|------|------------|
| **Hick** | T = a + b·log₂(n) | 메뉴 7개↑ 이면 그룹화 |
| **Fitts** | T = a + b·log₂(D/W+1) | 50대 친화 = 큰 버튼·하단·48dp+ |
| **Doherty** | 0.4초 | LLM 2.5~6초라 로딩 스켈레톤·Streaming 필수 |

### 2.3 표준 가이드

- Apple HIG: https://developer.apple.com/design/human-interface-guidelines/
- Material Design 3: https://m3.material.io/
- WCAG 2.2 AA: https://www.w3.org/WAI/WCAG22/quickref/
- Nielsen Norman Group: https://www.nngroup.com/articles/

### 2.4 헬스케어 특화

- **Calm Technology** (Mark Weiser) — 알림 최소화, 주의 빼앗지 않기
- **Inclusive Design Toolkit** (Microsoft) — 일시·상황 장애 고려 (햇빛·진동하는 버스 안 등)

---SPLIT---

## 3. Lemon Aid UX 12 핵심 (체크리스트)

Figma 화면 끝낼 때마다 이 12개로 자가 검수.

### 3.1 만성질환자 50대+ 친화
- [ ] 본문 16px+, 핵심 17~20px
- [ ] 터치 영역 48dp+
- [ ] 색만으로 구분 X → 색 + 한국어 라벨 + 아이콘 3중
- [ ] 영문 약어 풀어쓰기 (UL → "상한")
- [ ] 자동 사라지는 토스트 X → 명시 닫기 버튼
- [ ] 햄버거·hidden nav X → 명시적 탭바

### 3.2 AI 미리보기 → 승인 패턴
- [ ] 분석 결과는 항상 편집 가능 카드
- [ ] [이대로 저장] / [수정하기] / [다시 분석] 3액션
- [ ] 저장 후에도 수정 진입점
- [ ] AI 자동 저장 절대 X (PG.md §7.8)

### 3.3 의료법 안전 표현
- [ ] "진단·처방·치료·보장" 0개
- [ ] 권유형 카피 ("어떠세요?" "권장드려요")
- [ ] 질병명 단정 X → 영양소 수치만
- [ ] PG.md §19.2 위반→대체 표 옆에 두고 검수

### 3.4 오프라인 대응
- [ ] 사진 촬영은 항상 가능
- [ ] 동기화 상태 표시 (📶 ☁️)
- [ ] 실패 시 "나중에 분석할게요" 큐
- [ ] 재시도 버튼 명확

### 3.5 "기억해주는 Agent" 느낌
- [ ] 두 번째 방문 시 "지난번 비타민D 부족했어요"
- [ ] 챗봇이 과거 데이터 자연스럽게 인용
- [ ] 최근 7일 추세 시각화
- [ ] 프로필 변경 시 인사

### 3.6 점수 부담 없이
- [ ] 점수보다 자연어 피드백 강조
- [ ] 낮은 점수에도 긍정 카피 + 개선 제안
- [ ] 응모권 = 참여 기반 (점수와 분리)

### 3.7 사용자 결정 주도
- [ ] 명령형 X → 권유형
- [ ] 선택지 제시 (예/아니오/나중에)
- [ ] 분석 결과는 편집 가능 카드

### 3.8 한 손 조작
- [ ] 핵심 버튼 화면 하단 1/3
- [ ] FAB 위치 일관 (오른쪽 하단)
- [ ] 스와이프만 의존 X

### 3.9 데이터 입력 부담 ↓
- [ ] 만성질환 = 다중선택 칩
- [ ] 약 이름 = 자동완성·검색
- [ ] 건너뛰기 가능
- [ ] 나중에 추가 가능

### 3.10 면책 고지 노출
- [ ] 첫 진입 1회 풀 모달
- [ ] 권고 화면 하단 작은 배너 (접힘 가능)
- [ ] 주 1회 풀버전 재노출
- [ ] "왜 표시되나" 토글

### 3.11 응급 신호 감지 (§18.3)
- [ ] 다이어트 권고 사라짐 (BMI <17 등)
- [ ] 부드러운 카피
- [ ] 1577-0199 / 한국섭식장애협회 버튼
- [ ] 닫기 어렵게 (의도적 friction)

### 3.12 사진 촬영 학습
- [ ] 카메라 진입 시 샘플 사진
- [ ] 흐림·각도 자동 감지 → "다시 촬영"
- [ ] 실패 시 수동 입력 폴백
- [ ] 갤러리 옵션 명확

---SPLIT---

## 4. 디자인 토큰 룰

### 4.1 W3C 3계층

```
Reference Tokens (원시 값, 의미 없음)
  color.lemon.600 = #CA8A04
  color.lemon.400 = #FACC15

System Tokens (역할 부여)
  color.brand.primary    = color.lemon.600
  color.brand.accent     = color.lemon.400
  color.semantic.danger  = #DC2626
  color.semantic.success = #16A34A

Component Tokens (컴포넌트 전용)
  button.primary.bg   = color.brand.primary
  button.primary.text = #FFFFFF
  card.bg             = color.surface.elevated
```

MVP는 System Tokens 위주. Component는 v2.

### 4.2 Figma Variables 우선

Local Styles 대신 Variables로 관리.
다크 모드·테마 교체가 Variables 모드 전환만으로 가능.

### 4.3 코드 동기화

Figma Variables 값을 `mobile/lib/utils/tokens.dart`의 `LemonColors`에 그대로 옮긴다.
Claude Code에 시킬 때:

```
@mobile/lib/utils/tokens.dart

Figma Variables에서 받은 새 토큰 갱신:
- accent: #B45309
- citrus: #FDE047
나머지는 유지.
```

### 4.4 컬러 토큰 (건강의신 톤 / Figma ↔ tokens.dart 1:1)

**2026-05-11 재정의** — 건강의신 스크린샷 9장 기준. 블루 메인 + 노랑 액센트(레몬 캐릭터) + 화이트 배경 + 컬러 카드.

**Reference (원시 팔레트 — 건강의신 추정값)**

| Figma 변수 | Hex | Flutter 상수 | 출처 |
|----------|-----|-------------|------|
| blue.50 | #EEF2FF | `LemonColors.brandSoft` | 카드 hover 배경 |
| blue.100 | #DBE4FF | `LemonColors.brandTint` | 선택된 chip |
| blue.500 | #4267EC | `LemonColors.brand` | 메인 CTA (걷기왕 헤더·버튼) |
| blue.700 | #2945C2 | `LemonColors.brandStrong` | pressed |
| blue.900 | #1E2E8E | `LemonColors.brandDeep` | 헤더 짙은 영역 |
| lemon.300 | #FFD93D | `LemonColors.citrus` | 레몬 캐릭터·액센트 |
| lemon.100 | #FFF4C2 | `LemonColors.citrusLight` | 노랑 카드 배경 |
| pink.300 | #FFB6C1 | `LemonColors.pink` | 분홍 카드 (마음일기 영역) |
| pink.100 | #FFE6EA | `LemonColors.pinkLight` | 분홍 카드 배경 |
| green.300 | #B8E994 | `LemonColors.green` | 연두 카드 |
| green.100 | #EAF7DA | `LemonColors.greenLight` | 연두 카드 배경 |
| sky.300 | #A4D8FF | `LemonColors.sky` | 연파랑 카드 |
| sky.100 | #E1F0FF | `LemonColors.skyLight` | 연파랑 카드 배경 |
| white | #FFFFFF | `LemonColors.bg` / `bgElev` | 베이스 |
| gray.50 | #F8F9FB | `LemonColors.bgPage` | Scaffold 배경 (살짝 회색) |
| gray.100 | #EEF0F4 | `LemonColors.line` | 옅은 구분선 |
| gray.300 | #C4C9D4 | `LemonColors.lineStrong` | 입력 필드 |
| ink.900 | #1A1F2E | `LemonColors.ink` | 본문 (블루 베이스 검정) |
| ink.600 | #4A5165 | `LemonColors.inkSoft` | 부제 |
| ink.400 | #8B92A4 | `LemonColors.inkMute` | 도움말·캡션 |

**System (의미 부여)**

| 시맨틱 토큰 | 값 | 용도 |
|----------|-----|------|
| color.brand.primary | brand #4267EC | 메인 CTA·강조 |
| color.brand.tint | brandTint #DBE4FF | hover·선택 chip |
| color.brand.soft | brandSoft #EEF2FF | 카드 배경 (홈 헤더 등) |
| color.brand.strong | brandStrong #2945C2 | pressed |
| color.brand.deep | brandDeep #1E2E8E | 진한 헤더 영역 |
| color.accent.lemon | citrus #FFD93D | 레몬 캐릭터·포인트 |
| color.accent.lemon.bg | citrusLight #FFF4C2 | 노랑 카드 (참여·이벤트) |
| color.accent.pink | pink #FFB6C1 | 감정·커뮤니티 |
| color.accent.pink.bg | pinkLight #FFE6EA | 분홍 카드 (마음일기) |
| color.accent.green | green #B8E994 | 자연·식단 |
| color.accent.green.bg | greenLight #EAF7DA | 연두 카드 |
| color.accent.sky | sky #A4D8FF | 정보·청구 |
| color.accent.sky.bg | skyLight #E1F0FF | 연파랑 카드 (청구의신 톤) |
| color.surface.page | bgPage #F8F9FB | Scaffold 배경 |
| color.surface.bg | bg #FFFFFF | 앱 베이스 |
| color.surface.elev | bgElev #FFFFFF | Card·Sheet |
| color.text.body | ink #1A1F2E | 본문 |
| color.text.soft | inkSoft #4A5165 | 부제 |
| color.text.mute | inkMute #8B92A4 | 도움말·캡션 |
| color.line.weak | line #EEF0F4 | 카드 테두리 |
| color.line.strong | lineStrong #C4C9D4 | 입력 필드 |
| color.semantic.success | #16A34A | 충분·정상 |
| color.semantic.warning | #F59E0B | 부족·많음 (블루 베이스에선 너무 빨간 #EA580C보다 호박색) |
| color.semantic.danger | #DC2626 | 결핍·UL 초과 |
| color.semantic.info | brand #4267EC | 정보 = 메인 컬러 재활용 |

**컬러 카드 시스템 (건강의신 핵심 패턴)**

화면에 정보를 4컬러 카드로 묶는다. 카드 배경은 연한 톤, 텍스트는 ink.

| 카드 | 배경 | 액센트 | 용도 |
|------|------|--------|------|
| Lemon Card | citrusLight #FFF4C2 | citrus #FFD93D | 참여·응모권·작은 기쁨 |
| Sky Card | skyLight #E1F0FF | sky #A4D8FF | 정보·청구·통계 |
| Pink Card | pinkLight #FFE6EA | pink #FFB6C1 | 감정·커뮤니티·격려 |
| Green Card | greenLight #EAF7DA | green #B8E994 | 식단·자연·건강 |
| Blue Card | brandSoft #EEF2FF | brand #4267EC | 메인 액션·강조 |

→ 한 화면에 같은 카드 색 연속 X. 정보 카테고리가 다르면 색도 다르게.

**대비비 (WCAG 2.2 AA)**

| 조합 | 비율 | 등급 |
|------|------|------|
| ink #1A1F2E on bg #FFFFFF | 16.1 | AAA |
| ink on bgPage #F8F9FB | 15.4 | AAA |
| brand #4267EC on white | 7.4 | AAA |
| white on brand | 7.4 | AAA (버튼 텍스트 ✓) |
| ink on citrusLight | 14.3 | AAA |
| ink on skyLight | 14.1 | AAA |
| ink on pinkLight | 13.9 | AAA |
| ink on greenLight | 14.0 | AAA |
| danger #DC2626 on white | 4.5 | AA |
| warning #F59E0B on white | 2.9 | ✗ — warning은 ink와 함께 (배경 컬러 + 라벨 텍스트) |

→ warning 단색 본문 X. 배경 + 검정 라벨 조합으로.

### 4.4a 기존 레몬 톤 (보존 — 보조 디자인 자료용)

PG.md §4.2에 적힌 기존 레몬 단독 톤은 다음 용도로만 보존:
- 마케팅 페이지·랜딩 페이지
- 응모권 당첨 축하 모달 (전체 노랑 그라데이션)
- Splash 첫 0.3초 (로고 등장 직전 노랑 → 흰 전환)

앱 본체 화면에서는 §4.4 (블루 메인) 사용.

### 4.5a 폰트 패밀리 (2026-05-11 확정 1안)

세 가지 폰트 + 한 가지 백업.

**한국어 본문 — Pretendard**

| 항목 | 값 |
|------|---|
| 용도 | 본문·라벨·카드 타이틀·서브헤딩·캡션·면책 (전체 70~80%) |
| 다운로드 | https://github.com/orioncactus/pretendard (OFL) |
| Weight | 100~900 (Variable + 정적 9단계) |
| 사용 weight | 400 / 500 / 600 / 700 / 800 |
| Flutter 적용 | `fontFamily: 'Pretendard'` |
| Asset 파일 | `assets/fonts/Pretendard-Regular.otf` `Medium`·`SemiBold`·`Bold`·`ExtraBold` |
| 라이선스 | SIL OFL 1.1 — 상업·재배포 자유 |
| 이유 | 한국어 디지털 최적 / 가변 weight / 영문 한자 조화 / Figma·웹 표준 |

**한국어 디스플레이 — Gmarket Sans Bold**

| 항목 | 값 |
|------|---|
| 용도 | 워드마크 "Lemon Aid" / 큰 헤드라인 / 응모권 큰 숫자 / 환영 메시지 |
| 다운로드 | https://corp.gmarket.com/fonts (무료 상업 사용 가능) |
| Weight | Light / Medium / Bold (3단) |
| 사용 weight | Bold (메인) / Medium (보조) |
| Flutter 적용 | `fontFamily: 'GmarketSans'` (디스플레이 전용 — 모든 텍스트에 X) |
| Asset 파일 | `assets/fonts/GmarketSansBold.otf` `Medium`·`Light` |
| 라이선스 | G마켓 폰트 라이선스 — 무료 + 상업 사용 (재판매·수정 제한) |
| 이유 | 건강의신 워드마크 (둥근 두꺼운 sans + 살짝 손글씨)에 가장 가까움 / 한국어 헬스앱 검증된 톤 / 50대 시인성 우수 |

**영문 — Plus Jakarta Sans**

| 항목 | 값 |
|------|---|
| 용도 | 워드마크 영문 부분 / 영문 라벨 / 외래어 (vitamin, OCR 등) |
| 다운로드 | https://fonts.google.com/specimen/Plus+Jakarta+Sans (OFL) |
| Weight | 200~800 (Variable) |
| 사용 weight | 400 / 600 / 700 / 800 |
| Flutter 적용 | `fontFamily: 'PlusJakartaSans'` |
| Asset 파일 | `assets/fonts/PlusJakartaSans-VariableFont_wght.ttf` |
| 라이선스 | SIL OFL 1.1 |
| 이유 | Pretendard와 곡률·x-height가 잘 맞음 / 살짝 둥글어서 친근 / 모던하면서 차갑지 않음 |

**백업 폰트 (사용자 폰에 없을 때)**

| 플랫폼 | 백업 순서 |
|-------|---------|
| iOS | Apple SD Gothic Neo → SF Pro |
| Android | Noto Sans KR → Roboto |
| 영문 백업 | Inter → -apple-system |

**폰트 사용 규칙**

| 토큰 | 폰트 | 이유 |
|------|------|------|
| `LemonText.display` (32+) | Gmarket Sans Bold | 큰 강조 → 디스플레이 |
| `LemonText.title` (24) | Gmarket Sans Bold | 화면 타이틀 → 디스플레이 |
| `LemonText.heading` (20) | Pretendard 700 | 섹션 헤딩 → 본문 폰트 |
| `LemonText.subheading` (17) | Pretendard 600 | 카드 제목 → 본문 |
| `LemonText.bodyEmphasis` (17/700) | Pretendard 700 | 핵심 수치 → 본문 |
| `LemonText.body` (16) | Pretendard 400 | 일반 본문 |
| `LemonText.caption` (13) | Pretendard 400 | 도움말 |
| `LemonText.disclaimer` (13) | Pretendard 400 | 면책 |

→ Gmarket Sans는 display·title 두 토큰에만. 나머지는 모두 Pretendard.

**워드마크 "Lemon Aid" 특수 처리**

워드마크는 영문이지만 디스플레이 위치 → 폰트 결정:

- 옵션 A: Gmarket Sans Bold (한·영 통일, 일관성 ↑)
- 옵션 B: Plus Jakarta Sans 800 (영문 본연의 톤, 모던)
- **선택 A — Gmarket Sans Bold** (건강의신 워드마크 톤 가장 가까움)
- Plus Jakarta Sans는 영문 본문·외래어에서만

**숫자 표시 폰트**

| 위치 | 폰트 | 이유 |
|------|------|------|
| 응모권 큰 누적 (64dp) | Gmarket Sans Bold | 디스플레이 강조 |
| Dashboard 충족률 (32dp) | Gmarket Sans Bold | 디스플레이 강조 |
| 분석 결과 핵심 수치 (17~22dp) | Pretendard 700 (tabular nums) | 본문 톤 + 숫자 정렬 |
| Health 차트 수치 | Pretendard 600 | 본문 톤 |

**라이선스 책임**

- 모든 폰트 무료 상업 사용 가능
- 앱 안 "Settings → 오픈소스 라이선스" 페이지에 다음 표시 의무:
  - Pretendard © orioncactus, SIL OFL 1.1
  - Gmarket Sans © Gmarket
  - Plus Jakarta Sans © Tokotype, SIL OFL 1.1
- assets/fonts/ 에 라이선스 파일 동봉 (LICENSE-Pretendard.txt 등)

**대안 검토 메모**

| 후보 | 검토 결과 |
|------|---------|
| 나눔손글씨 펜체 | 진짜 손글씨 → 50대 가독성 ↓ 거름 |
| Hahmlet (세리프) | 신뢰감 ↑이지만 톤 무거움 → 마케팅 페이지 후보 (앱 본체 X) |
| 이서윤체 | Gmarket Sans와 비슷한 톤 → 백업 후보 |
| Cafe24 단정해 | 단정한 세리프 → 의료 톤 강조 시 후보 (현재 거름) |
| Inter (영문) | Plus Jakarta Sans보다 살짝 차가움 → 백업 후보 |
| Geist (영문) | 최신 트렌드지만 한글과 조화 미검증 |

**검증 체크리스트**

- [ ] Pretendard 본문 16dp 가독성 — 50대 폰에서 확인
- [ ] Gmarket Sans 32dp 워드마크 — Splash·Login 미리보기에서 확인
- [ ] Plus Jakarta Sans 영문 라벨 — Pretendard와 같이 한 줄에 놨을 때 어색하지 않은지
- [ ] tabular nums (숫자 정렬) — 응모권 1자리 / 2자리 / 3자리에서 폭 일정한지

**자동 설치 스크립트**

```powershell
pwsh scripts/install_fonts.ps1
```

세 폰트를 `mobile/assets/fonts/` 에 자동 다운로드 + 라이선스 동봉 + LICENSES.md 작성.
실패 시 안내 표시 — Gmarket Sans는 공식 사이트 동적 페이지라 자동 다운로드가 불안정.

스크립트 동작:
1. Pretendard — GitHub Release zip 다운로드 → 정적 .otf 5종 추출 → LICENSE 동봉
2. Gmarket Sans — GitHub 미러에서 Bold/Medium/Light .ttf 3종 직접 다운로드
3. Plus Jakarta Sans — Google Fonts API zip → Variable .ttf 추출 → OFL.txt 동봉
4. LICENSES.md 작성 (출처·저작자·사용 weight)

설치 후 자동 안내:
```
cd mobile
flutter pub get
flutter run
```

### 4.5 타입 토큰

| Figma 스타일 | Flutter | size / weight / height | 폰트 | 용도 |
|-----------|---------|----------------------|------|------|
| type.display | `LemonText.display` | 32 / 800 / 1.2 | GmarketSans Bold | 큰 환영·랜딩 |
| type.title | `LemonText.title` | 24 / 800 / 1.3 | GmarketSans Bold | 화면 타이틀 |
| type.heading | `LemonText.heading` | 20 / 700 / 1.4 | Pretendard 700 | 섹션 헤딩 |
| type.subheading | `LemonText.subheading` | 17 / 600 / 1.5 | Pretendard 600 | 카드 제목 |
| type.body.emphasis | `LemonText.bodyEmphasis` | 17 / 700 / 1.5 | 핵심 수치 |
| type.body | `LemonText.body` | 16 / 400 / 1.6 | 본문 (기본) |
| type.caption | `LemonText.caption` | 13 / 400 / 1.5 | 도움말 |
| type.disclaimer | `LemonText.disclaimer` | 13 / 400 / 1.6 | 면책 고지 |

**고령자 모드 토글 (Settings에서 ON)**

| 토큰 | 기본 (`LemonText.*`) | 고령자 (`LemonTextElder.*`) |
|------|------|--------|
| body | 16 / 1.6 | 19 / 1.7 |
| bodyEmphasis | 17 / 1.5 | 20 / 1.6 |
| subheading | 17 / 1.5 | 20 / 1.5 |
| caption | 13 / 1.5 | 15 / 1.6 |
| touchTarget | `LemonSpace.touchTarget` 48 | `LemonSpaceElder.touchTarget` 56 |

구현: `final isElder = ref.watch(elderModeProvider);` → `isElder ? LemonTextElder.body : LemonText.body`

### 4.6 간격 토큰

| Figma | Flutter | dp | 용도 |
|-------|---------|----|------|
| space.xs | `LemonSpace.xs` | 4 | 아이콘 간격 |
| space.sm | `LemonSpace.sm` | 8 | 인라인 요소 |
| space.md | `LemonSpace.md` | 16 | 카드 padding (표준) |
| space.lg | `LemonSpace.lg` | 24 | 섹션 간격 |
| space.xl | `LemonSpace.xl` | 32 | 화면 마진 |
| space.xxl | `LemonSpace.xxl` | 48 | 큰 분리 |
| touch.min | `LemonSpace.touchTarget` | 48 | 모든 클릭 영역 |

4dp 그리드 — 모든 간격은 4의 배수.

### 4.7 라운드 토큰

| Figma | Flutter | dp | 용도 |
|-------|---------|----|------|
| radius.sm | `LemonRadius.sm` | 6 | Chip·Badge |
| radius.md | `LemonRadius.md` | 12 | Button·TextField |
| radius.lg | `LemonRadius.lg` | 16 | Card·Sheet |
| radius.xl | `LemonRadius.xl` | 24 | 모달·다이얼로그 |
| radius.pill | `LemonRadius.pill` | 999 | Pill·Avatar |

### 4.8 그림자 토큰 (5단)

ink 베이스 (#1A1F2E) 알파. 건강의신 톤 — 그림자 거의 안 보일 정도.

| Figma | Flutter | 값 | 용도 |
|-------|---------|---|------|
| shadow.none | `LemonShadow.none` | 없음 | 평면 |
| shadow.sm | `LemonShadow.sm` | `0 1 2 ink@4%` | Card (기본) |
| shadow.md | `LemonShadow.md` | `0 4 12 ink@8%` | 떠 있는 카드 |
| shadow.lg | `LemonShadow.lg` | `0 8 24 ink@12%` | 모달·BottomSheet |
| shadow.xl | `LemonShadow.xl` | `0 16 48 ink@16%` | 풀스크린 오버레이 |

50대 친화: 그림자 약하게. 너무 진하면 잡티처럼 보임.

### 4.9 모션 토큰

| 토큰 | Flutter | 값 | 용도 |
|------|---------|---|------|
| motion.fast | `LemonMotion.fast` | 80ms / `curvePress` (easeOut) | Press feedback |
| motion.base | `LemonMotion.base` | 200ms / `curveDefault` (easeInOut) | 표준 전환 |
| motion.slow | `LemonMotion.slow` | 320ms / `curveDefault` | 화면 전환 |
| motion.entry | `LemonMotion.entry` | 400ms / `curveEntry` cubic(0.2,0,0,1) | 카드 등장 (Score 5장) |
| motion.exit | `LemonMotion.exit` | 160ms / `curveExit` (easeIn) | 사라짐 |

만성질환자는 빠른 모션에 어지러움 호소 가능 → reduceMotion 시 100% → 0ms 단축.
구현: `MediaQuery.of(context).disableAnimations` 체크 후 0 또는 토큰값.

### 4.10 토큰 변경 절차

1. 다이어리 §14.8 결정 누적 표에 한 줄 추가
2. tokens.dart 동기 변경
3. Figma Variables 동기 변경 (또는 그 반대)
4. 1주일 안정되면 PG.md 부록에 반영
5. 팀 공유 채널 알림 (§16.13 템플릿 사용)

---SPLIT---

## 5. 화면별 핵심 결정 (가이드)

### 5.1 Splash
- 노출 1.5초 (Doherty 4배, 사용자 인내 한계)
- 로고 + 카피 1줄

### 5.2 Login
- 이메일·비밀번호 우선, 소셜 로그인 v2
- "비밀번호 찾기" 작은 텍스트 링크

### 5.3 Consent (의료법·개보법 가장 무거움)
- 필수/선택 명확 분리
- 각 항목 "자세히 보기" 토글
- 일괄 동의 버튼 X (개별 체크 강제)

### 5.4 Onboarding
- 4~5단계 분할 (한 화면 1~2 질문)
- 건너뛰기 옵션
- 진행률 표시 (4/5)

### 5.5 Camera
- 진입 즉시 카메라 미리보기
- 샘플 사진 보기 토글
- 갤러리 버튼 우측 상단

### 5.6 Dashboard (5종 출력) — 가장 어려운 화면
- 카드 5개 세로 스크롤
- 카드별 색 다름 (충족률)
- 상단에 한 줄 요약
- 자세히 보기 → 영양소 단위 모달

### 5.7 Chat
- 메시지 버블 (사용자 오른쪽 / Agent 왼쪽)
- 하단 입력 시트 (큰 글씨)
- Agent 응답에 액션 버튼 ([알림 등록] [캘린더 추가])

### 5.8 Settings
- 동의 관리 진입점 명확
- 탈퇴는 가장 아래 + 색 약화

---SPLIT---

## 6. Figma 작업 룰

### 6.1 페이지 구조

```
0_Cover            — 표지·메타 정보
1_Wireframe        — 저화질 흐름
2_Component        — 디자인 시스템 라이브러리
3_Screens          — 고화질 시안
4_Prototype        — 인터랙션 연결
5_Handoff          — 개발자용 (Inspect)
```

### 6.2 컴포넌트 네이밍

`Component/Variant/State` 형식.
예시: `Button/Primary/Default`, `Card/Supplement/Editing`.

### 6.3 모바일 해상도

- 기본: 390×844 (iPhone 15 Pro)
- 검증: 360×800 (Android 평균)
- 큰 화면: 430×932 (iPhone Pro Max)
- 50대 친화 검증: 시뮬레이터에서 동적 글꼴 확대 200% 켜고 보기

### 6.4 Auto Layout 강제

모든 컴포넌트는 Auto Layout. 반응형 확장 가능하게.

### 6.5 Figma Make / Figma AI 프롬프트 모음

각 화면마다 Figma AI 도구에 붙여넣을 프롬프트를 저장한다. 토큰·간격·문구가 다이어리와 코드와 일치하도록.

**프롬프트 작성 룰**

- 영문 작성 (Figma AI 영문 더 잘 이해)
- 토큰 값은 Hex·dp 그대로 명시
- 좌표·간격 명시 (px 단위)
- 폰트는 Pretendard 또는 SF Pro 명시
- 마지막에 "Mobile 390×844 viewport, Auto Layout, Korean text exactly as below" 박기

#### 6.5.1 S-02 Login (Lemon Aid)

```
Design a mobile login screen for a Korean health app called "Lemon Aid".

CONTEXT
- Target users: 50-60s with chronic diseases + adult children helping parents
- Tone: clean, trustworthy, friendly (not playful, not corporate)
- Follow Korean health app conventions (similar to KakaoTalk-first OAuth)
- Mobile viewport: 390x844px (iPhone 15 Pro)
- Use Auto Layout throughout

COLORS (use these exact hex values)
- Background: #FFFFFF
- Brand blue: #4267EC
- Brand blue tint (card bg): #EEF2FF
- Kakao yellow: #FEE500 (button bg)
- Kakao text: #191919
- Google border: #DADCE0
- Lemon accent (mascot, dots): #FFD93D
- Pink soft (mascot cheeks): #FFB6C1
- Green soft (mascot leaf): #B8E994
- Ink primary: #1A1F2E
- Ink soft (subtitle): #4A5165
- Ink mute (caption): #8B92A4
- Line: #EEF0F4

TYPOGRAPHY (Pretendard, fallback: Apple SD Gothic Neo)
- Wordmark "Lemon Aid": 36px / 800 weight / letter-spacing -1.2 / color ink
- Tagline: 16px / 600 weight / color inkSoft
- Button label: 16px / 700 weight
- Caption (footer): 12px / 400 weight / color inkMute
- Tooltip: 12px / 600 weight

LAYOUT (top to bottom, 24px horizontal margins)
1. Top section (left-aligned)
   - 48px top spacing
   - Wordmark "Lemon Aid" with a small yellow lemon dot (14px circle, #FFD93D with soft glow) inserted between "Lemon" and "Aid"
   - 12px gap
   - Tagline: "사진 한 번, 영양 분석 끝"
2. Middle section
   - Large empty breathing space (~35% of screen height)
   - In the bottom-right of this space, place a 3D lemon mascot illustration:
     - Round lemon body (radial gradient: light yellow center to deeper yellow edge)
     - Green leaf top-right
     - Two black dot eyes
     - Pink soft cheeks
     - Small black smile
     - Size: ~160dp wide
     - Subtle ground shadow below
3. Bottom CTA section (above safe area, 16px gap from edges)
   - Small black pill tooltip "최근 로그인했어요" (12px white text, 12px horizontal padding, 6px vertical, with a tiny downward arrow at the bottom-left pointing to the Kakao button)
   - 8px gap
   - Kakao button (full width, 52dp height, radius 12)
     - Background #FEE500, text #191919
     - Speech bubble icon (chat) on left + "카카오로 계속하기" text
   - 12px gap
   - Google button (full width, 52dp height, radius 12)
     - Background #FFFFFF, border 1.5px #DADCE0
     - Google G logo on left + "구글로 시작" text in #1F1F1F
   - 16px gap
   - Centered text link: "또는 이메일로 →" (15px / 500 / inkSoft)
   - 8px gap
   - Footer caption centered: "© Lemon Aid · 이용약관 · 개인정보" (12px / inkMute)
   - 16px bottom safe area padding

DESIGN PRINCIPLES (apply these)
- One screen, one goal: login
- Generous whitespace in the middle (no clutter)
- Large touch targets (all buttons 48dp+, height 52dp)
- Korean 50s users: clear hierarchy, no decorative noise
- Mascot is part of content, not decoration
- Kakao always first (Korean user familiarity)

DELIVERABLES
- 1 frame: 390x844, name "S-02 Login / Default"
- Use Auto Layout for the entire layout
- Group the mascot as a single component
- Group the wordmark (Lemon + lemon dot + Aid) as one Auto Layout horizontal frame
- Tooltip + Kakao button grouped together (anchor)

Output: Generate the frame directly. Korean text exactly as specified, do not translate.
```

#### 6.5.2 S-02 Login — Email BottomSheet 변종

```
Design a modal bottom sheet for email login in the "Lemon Aid" Korean health app.

CONTEXT
- Appears when user taps "또는 이메일로 →" on the login screen
- Sits on top of the login screen with a dimmed backdrop
- Mobile 390x844, sheet covers approximately the bottom 60%

COLORS
- Sheet bg: #FFFFFF
- Backdrop: #1A1F2E at 40% opacity
- Brand: #4267EC
- Ink primary: #1A1F2E
- Ink mute: #8B92A4
- Field border: #EEF0F4, focus border: #4267EC
- Line strong (drag handle): #C4C9D4

LAYOUT (bottom sheet, 24px horizontal padding)
- Top edge: rounded top corners 24px
- 16px top padding
- Drag handle: 40px wide × 4px tall centered, color #C4C9D4, radius 999
- 20px gap
- Title "이메일로 로그인": 22px / 800 / ink, left-aligned
- 20px gap
- Email field:
  - Label "이메일": 13px / 500 / inkSoft, 6px below
  - Input: 56dp height, radius 12, border 1.5px line, fill #FFFFFF
  - Placeholder "name@email.com" 17px / inkMute
- 16px gap
- Password field:
  - Label "비밀번호": 13px / 500 / inkSoft
  - Input: 56dp height, radius 12, eye toggle icon on right
  - Placeholder "8자 이상, 영문+숫자"
- 24px gap
- Primary button "로그인":
  - Full width, 52dp height, radius 12
  - Background #4267EC, white text 16px / 700
- 12px gap
- Text link centered: "처음이신가요? 회원가입 →" (15px / 600 / #4267EC)
- 24px bottom padding (account for safe area)

VARIANTS to produce
- Default (empty fields)
- Filled (email and password typed, primary button active)
- Error state (password field with 2px danger border #DC2626, helper text "이메일 또는 비밀번호가 일치하지 않아요" below in danger 13px / 500)
- Loading (primary button shows spinner, text "로그인 중...")

DELIVERABLES
- 4 frames showing each state, named "S-02 / Email Sheet / [State]"
- Use Auto Layout
- Korean text exactly as written
```

#### 6.5.2a Login 버튼 단독 프롬프트 (S-02 CTA만)

전체 화면이 아니라 로그인 CTA 버튼만 빠르게 다듬을 때 사용. Figma Make 같은 도구에 붙여넣어 1~3분 안에 시안.

```
Design login CTA buttons for the "Lemon Aid" Korean health app.
Mobile width 342px (390 viewport minus 24px side margins). Produce ALL buttons in one frame, stacked vertically.

DESIGN TOKENS (use exactly)
- Kakao yellow: #FEE500
- Kakao text: #191919
- Google bg: #FFFFFF, border #DADCE0 (1.5px)
- Google text: #1F1F1F
- Brand blue: #4267EC
- Brand strong: #2945C2
- Ink primary: #1A1F2E
- Ink soft: #4A5165
- Ink mute: #8B92A4
- Danger: #DC2626
- Line: #EEF0F4

TYPOGRAPHY
- All button labels: 16px / 700 weight
- Korean: Pretendard (fallback Apple SD Gothic Neo)
- English: Plus Jakarta Sans (fallback Inter)

COMMON BUTTON SPECS
- Width: 342px
- Height: 52dp
- Corner radius: 12px
- Horizontal padding: 24px
- Icon (when present) 20×20 on left, 8px gap before text
- Center-align contents (icon + text as a group)
- Auto Layout enabled

PRODUCE THESE VARIANTS (stack vertically with 16px gap, label each frame)

1) Kakao / Default
   - Background #FEE500
   - Black speech-bubble icon on left
   - Text "카카오로 계속하기" in #191919
   - Subtle 1px shadow optional

2) Kakao / With "Recent login" tooltip
   - Same as Default
   - Above the button, place a black pill tooltip:
     - Background #1A1F2E, padding 12×6, radius 999
     - Text "최근 로그인했어요" 12px / 600 / white
     - Small downward triangle (10×6) at the bottom-left of pill pointing toward the Kakao icon
   - 4px gap between tooltip arrow tip and the button top edge

3) Kakao / Loading
   - Background #FEE500 (slightly dimmed alpha 0.9)
   - White circular spinner 20×20 on left
   - Text "카카오 로그인 중..." in #191919

4) Google / Default
   - Background #FFFFFF
   - 1.5px border #DADCE0
   - Multicolor Google G logo on left (blue #4285F4, green #34A853, yellow #FBBC05, red #EA4335)
   - Text "구글로 시작" in #1F1F1F

5) Google / Loading
   - Same border
   - Gray spinner #4A5165 on left
   - Text "구글 로그인 중..." in #1F1F1F

6) Email Primary / Default
   - Background #4267EC (brand blue)
   - White text "로그인" 16/700
   - No icon

7) Email Primary / Pressed
   - Background #2945C2 (brand strong)
   - 0.97 scale visual hint
   - White text "로그인"

8) Email Primary / Disabled
   - Background #EEF0F4 (line)
   - Text #8B92A4 (ink mute) "로그인"

9) Email Primary / Loading
   - Background #4267EC
   - White spinner on left + text "로그인 중..."

10) Email Secondary / Outline
    - Background white
    - 1.5px border #4267EC
    - Text #4267EC "회원가입"

11) Email Ghost / Text link
    - Transparent background
    - Text "또는 이메일로 →" in #4A5165 (inkSoft) 15px / 500
    - Right arrow icon 16px after text
    - Center-aligned, no full-width fill

12) Danger / Logout
    - Background transparent
    - Text #DC2626 "로그아웃" 16/700
    - Center-aligned

ELDERLY MODE VARIANTS (separate row, label "Elderly")
- Same buttons but height 60dp, label 18/700, icon 22×22

DELIVERABLES
- One frame containing all 12 variants stacked vertically with labels above each
- One additional frame: same 12 in Elderly mode
- Use Auto Layout
- Korean text exactly as written, do not translate
```

#### 6.5.3 프롬프트 사용법

1. Figma 파일에서 "Figma AI" 또는 "Make" 버튼 클릭 (없으면 Figma First Draft / Magician 플러그인)
2. 위 프롬프트 통째 복사 → 붙여넣기
3. 생성된 시안과 다이어리 §14.7.W 와이어 비교
4. 다른 부분 1줄로 수정 요청 — "Mascot looks too small, scale to 180dp"
5. 최종 시안을 `3_Screens` 페이지에 배치
6. 토큰 매칭 검증 (Figma Variables vs §4.4)
7. 코드와 다른 부분 발견 시 §14.8 결정 누적표에 기록

#### 6.5.4 다른 화면 프롬프트 — 작성 예정

| 화면 | 상태 | 메모 |
|------|------|------|
| S-01 Splash | 미작성 | |
| S-02 Login | ✓ 위 6.5.1 | |
| S-02 Email Sheet | ✓ 위 6.5.2 | |
| S-03 Signup | 미작성 | |
| S-05 Verify Email | 미작성 | |
| S-06 Consent | 미작성 | |
| S-07 Onboarding (6단계) | 미작성 | 단계별 6장 |
| S-08 Dashboard | 미작성 | |
| S-09 Camera | 미작성 | |
| S-10 Score | 미작성 | 5출력 카드 |
| S-11 Health | 미작성 | |
| S-12 Chat | 미작성 | |
| S-13 Raffle | 미작성 | |
| S-14 Settings | 미작성 | |

→ 화면 코드가 끝날 때마다 프롬프트도 함께 작성. 코드 ↔ Figma ↔ 다이어리 3방향 일치 유지.

---SPLIT---

## 7. 도구 분담

| 도구 | 용도 | 결과물 |
|------|------|--------|
| **Stitch** | 빠른 와이어프레임·랜딩 탐색 | 흐름 1차 안 |
| **Claude Design** | 컴포넌트 디테일·그라데이션·아이콘 | 컴포넌트 2차 안 |
| **Figma** | 최종 시안 + 핸드오프 | 개발에 넘기는 결과물 |
| **VS Code + Claude Code** | 토큰·위젯 코드 작성 | mobile/lib/ 안 |

흐름: Stitch / Claude Design 으로 탐색 → Figma에서 정리 → Claude Code로 Flutter 옮기기.

---SPLIT---

## 8. 작업 일지 — Week 1

### 2026-05-13 (화) — UX 다이어리 시작

#### 결정
오늘부터 UX_DIARY.md 작성 시작. 매 디자인 결정을 5단(결정·근거·대안·후속·회고)으로 기록한다.

#### 근거
- 6개월 후 "왜 이 화면이 이렇게 생겼더라?" 답할 수 있어야 한다
- 디자인 시스템은 결정의 누적
- PG.md는 합의된 결과만, 그 합의 전 과정과 버린 대안은 이 다이어리에

#### 대안
- Notion에 따로 쓰기 → 코드 옆에 없으면 안 본다, 패스
- 코드 주석으로 남기기 → 흩어진다, 패스
- 안 쓰기 → 6개월 후 후회한다, 패스

#### 후속
- 매일 18시 스탠드업 후 5분 다이어리 쓰기 습관화
- 큰 결정 시 PG.md 갱신 같이

---

### 2026-05-13 (화) — 레몬 컬러 팔레트 확정

#### 결정
MVP 메인 팔레트 5색 확정.

| 토큰 | Hex | 용도 |
|------|-----|------|
| `brand.primary` | #CA8A04 (Lemon 600) | 주 액션 |
| `brand.accent` | #FACC15 (Lemon 400) | 보조 강조 |
| `surface.bg` | #FEFAE0 (Cream) | 앱 배경 |
| `surface.elevated` | #FFFFFF | 카드·시트 |
| `ink.primary` | #2A2410 (Dark brown-black) | 본문 |

#### 근거
- 발주처 = 레몬헬스케어 → 레몬 컬러 브랜딩 일관성
- 50대+ 친화: 채도 너무 높은 노랑은 눈 피로 → 약간 어두운 Lemon 600 선택
- 배경 따뜻한 크림 → 흰색 배경보다 50대 눈 부담 ↓
- ink는 순흑색(#000) 대신 #2A2410 (다크 브라운) → 인쇄물 같은 부드러움
- WCAG 검증: ink #2A2410 on bg #FEFAE0 = 12.4:1 (AAA 통과)

#### 대안
- 메인 더 진한 색 (Lemon 700 #A16207): 너무 칙칙
- 메인 시트러스 단독: 흰 배경에 안 보임 (대비 3.5:1 미만)
- 배경 순백(#FFF): 50대 눈부심 + 브랜드 정체성 없음

#### 후속
- ✅ `mobile/lib/utils/tokens.dart`의 `LemonColors`에 적용 완료
- ✅ guide.html 사이드바·시연 페이지에도 같은 팔레트
- ⏳ Figma Variables 만들고 동일 토큰 박기 — 내일

#### 회고
W2 끝나고 다시 검토.

---

### 2026-05-13 (화) — 본문 폰트 크기 16px 결정

#### 결정
모든 본문 텍스트 최소 16px. 핵심 정보는 17~20px.

#### 근거
- 페르소나 김건강 52세 = 노안 시작 연령
- WCAG 본문 권장 16px 이상
- Material 3 body 기본 14sp → 만성질환자엔 너무 작음
- Apple HIG: Dynamic Type 설정 200%까지도 깨지지 않게

#### 대안
- 15px (요즘 트렌드): 50대 가독성 X
- 18px 통일: 정보 밀도 너무 낮아 한 화면에 못 담음
- 사용자 설정으로 위임: 첫 진입에서 작게 보면 부정적 인상

#### 후속
- ✅ `tokens.dart` LemonText.body = 16
- ✅ LemonText.bodyEmphasis = 17 (분석 결과 핵심 수치)
- ⏳ Pretendard 폰트 패밀리 적용 (assets에 추가)

---

### 2026-05-13 (화) — Splash 노출 시간 1.5초

#### 결정
Splash 1.5초 후 자동 라우팅.

#### 근거
- Doherty 0.4초의 4배 = 사용자 인내 한계 근처
- Apple HIG: Splash 가능한 짧게
- 50대+ 사용자라 너무 짧으면 로고 인식 못 함

#### 대안
- 0.5초: 50대 못 보고 지나감
- 1.0초: 짧지만 안전
- 2.0초: 답답하다는 피드백 받을 위험

#### 후속
- ⏳ Timer로 1.5초 후 라우팅 구현 (D2)
- 인증 상태 따라 home 또는 login 분기

#### 회고
실제 50대 한 분께 보여주고 "충분히 보였나" 물어볼 것.

---

### 2026-05-13 (화) — Consent 화면 일괄 동의 버튼 제거

#### 결정
"모두 동의" 버튼 만들지 않는다. 개별 체크 강제.

#### 근거
- 개인정보보호법: 민감정보는 개별 동의 필수
- PG.md §20.5 — 만성질환·복약·검진기록·걸음수·심박수는 별도 동의
- 일괄 동의는 다크 패턴 (사용자가 안 읽음)
- 발주처가 의료 데이터 인프라 기업 → 동의 절차의 모범 보이는 게 브랜드 이미지에 ✅

#### 대안
- "필수만 일괄": 그래도 사용자가 선택 항목 안 읽고 넘김
- 진입 시 모두 체크된 상태 + 빼는 방식: 다크 패턴
- 한 줄씩 풀스크린 동의: 너무 친절해서 이탈

#### 후속
- ✅ `screens/auth/consent_screen.dart` 셸에 개별 체크 패턴 적용
- ⏳ 각 항목 "자세히 보기" 토글 (D2)
- ⏳ Stitch에서 와이어프레임

#### 회고
법무 검토는 W7에. 의료자문위 의견도 함께 받기.

---SPLIT---

## 9. 메모 · 아이디어

### 영감 모음

- Mobbin (모바일 패턴 모음): https://mobbin.com
- Dribbble 의료 앱 카테고리
- 굳이어플 (다이어리 시간 줌인 구조)
- 카카오미니 (50대+ 음성 인터페이스 사례)

### 미해결 질문

- 푸시 알림 시간 디폴트: 약 시간? 식사 시간?
- 다크 모드 v2 언제 도입할지
- 만성질환 5개 다 가진 사용자의 메인 화면은 어떻게 보일까
- 챗봇 자체에 음성 입력 추가하면 50대 친화 ↑
- 기본 모드 vs 큰 글씨 모드 — 토글 위치·자동 추천 트리거·이름 (고민 중)

### 잡생각

- 응모권 화면을 너무 게이미피케이션하면 의료 톤이 깨질 듯. 절제 필요.
- 영양제 라벨이 외국어인 경우 (특히 일본·미국 직구) UX 어떻게?
- 챗봇이 "잘 모르겠어요" 하는 상황을 어떻게 디자인할지 — 신뢰의 기반
- "큰 글씨 모드" 이름 후보: 돋보기 모드 / 시니어 모드 / 편안한 보기

---SPLIT---

## 10. 참고 링크

| 자료 | 링크 |
|------|------|
| Figma 작업 파일 | (만들면 여기 링크) |
| Stitch 작업 | (만들면 여기 링크) |
| 영감 보드 (Pinterest·Mobbin) | (만들면 여기 링크) |
| 만성질환자 UX 리서치 | (수집 시 여기) |
| 의료자문위 검토 의견 | docs/medical_review.md (W3 이후) |
| 페르소나 인터뷰 | docs/persona.md (수집 시) |

---SPLIT---

## 11. 페르소나 상세 (디자인 결정 기준점)

### 11.1 김건강 (52세 · 남 · 1차 핵심)

| 항목 | 내용 |
|------|------|
| 한 줄 | 고혈압 진단 2년차, 당뇨 전단계, 영양제 4종 |
| 디지털 친화도 | 중상 (카톡·유튜브·삼성헬스 능숙, 새 앱 5분 학습 한계) |
| 사용 맥락 | 아침 식사 후 거실 소파, 안경 안 쓰고 폰 들음, 노안 시작 |
| 동기 (JTBD) | 약과 영양제 충돌 확인, 가족 안심, 합병증 예방 |
| 페인포인트 | 영양제 라벨 영문, 약사 설명 잊어버림, 앱 글씨 작음 |
| 핵심 감정 | 불안 (재진단), 무게감 (가족 책임) |
| 자주 묻는 질문 | "같이 먹어도 돼?", "지난번 검사 어땠더라?" |

**디자인 함의**
- 첫 화면 = "지난번 비타민D 부족했어요" (기억해주는 느낌)
- 본문 17px+ (안경 없이도 읽힘)
- 챗봇 입구 명확 (탭바 중앙)
- 응급 표현 X — 부드러운 권유형

### 11.2 박직장 (38세 · 남 · 2차 확장)

| 항목 | 내용 |
|------|------|
| 한 줄 | 콜레스테롤·공복혈당 경계, 영양제 2종, 시간 부족 |
| 디지털 친화도 | 매우 높음 |
| 사용 맥락 | 출퇴근 지하철, 점심 후 5분, 한 손 조작 |
| 동기 (JTBD) | 최소 시간 예방, 3개월 후 미리 보기 |
| 페인포인트 | 정보 과잉, 잔소리, 광고 |
| 핵심 감정 | 효율 추구, 자기 통제 |
| 자주 묻는 질문 | "3개월 후 어떨까?", "이만큼이면 충분?" |

**디자인 함의**
- 한 손 조작 → 핵심 액션 하단 1/3
- 정보 밀도 높게 + Progressive Disclosure
- 다크 모드 v2
- 응모권 자연스러움 OK

### 11.3 두 페르소나 충돌 지점

| 지점 | 김건강 | 박직장 | 결정 |
|------|--------|--------|------|
| 글씨 크기 | 17px+ | 14px 익숙 | 16px 기본 + 큰 글씨 모드 토글 |
| 다크 모드 | 야간 부담 | 선호 | v2 |
| 정보 밀도 | 낮게 | 높게 | 카드 단위 접힘 |
| 알림 톤 | 격려 | 무덤덤 | 사용자 설정 |
| 게이미피케이션 | 부담 | 자연스러움 | 응모권만 가볍게 |

---SPLIT---

## 12. 무드보드 · 비주얼 방향

### 12.1 키워드 5개

`따뜻함` · `신뢰` · `명료` · `숨쉴 여백` · `작은 기쁨`

### 12.2 레퍼런스 매트릭스

| 톤 | 참고 | 가져올 점 | 버릴 점 |
|----|------|----------|---------|
| 의료 신뢰 | One Medical | 차분한 화이트·블루, 위계 분명 | 너무 차가움 |
| 시니어 친화 | 카카오미니 | 큰 버튼, 단순 흐름 | 노후화 인상 |
| 핀테크 명료 | 토스 | 정보 위계, 마이크로카피, 모션 절제 | 차가운 인디고 |
| 다이어리·기록 | 모트모트·굳이어플 | 따뜻한 종이·필기체 | 의료엔 너무 가벼움 |
| 헬스 게이미피케이션 | 캐시워크·삼성헬스 | 응모권 자연스러움 | 과한 보상 강조 |

→ Lemon Aid 자리: **One Medical 신뢰 × 토스 위계 × 다이어리 따뜻함**

### 12.3 컬러 키 메시지

| 색 | 사용처 | 감정 신호 |
|----|--------|----------|
| Lemon 600 #CA8A04 | 주 액션 | 신뢰·집중 |
| Lemon 400 #FACC15 | 보조·응모권 | 작은 기쁨 |
| Cream #FEFAE0 | 배경 | 숨쉴 여백 |
| Brown-Black #2A2410 | 본문 | 명료·안정감 |
| Success #16A34A | 적정 | 안심 |
| Warning #EA580C | 부족 | 주의 |
| Danger #DC2626 | 과다·위험 | 단호함 |

### 12.4 일러스트·아이콘

- 일러스트: 양식적(stylized) 단색 + 1포인트 색. 사진 X.
- 아이콘: Outlined 2px stroke, 라운드 2px, 면 채움 X.
- 사람 일러스트 표정 절제.

### 12.5 비주얼 레퍼런스 — 건강의신 (발주처 자사 앱)

**왜 건강의신을 따로 분석하는가**

발주처 (주)레몬헬스케어의 대표 자사 앱. Lemon Aid는 독립형 참조 앱이지만, 검수자 입장에서 "낯설지 않은 톤"을 유지해야 채택 가능성이 높음. 동시에 Lemon Aid만의 차별점(Agent 챗봇·응모권·5출력)이 분명히 보여야 새 앱을 만든 이유가 살아남.

**관찰 1차 (2026-05-11 스크린샷 9장 기준)**

| 항목 | 값 | 비고 |
|------|---|------|
| 메인 컬러 | 코발트 블루 #4267EC 추정 | 노랑 아님 — 우리 PG 토큰과 어긋남 |
| 보조 컬러 | 노랑(레몬) #FACC15 / 분홍 #FFB6C1 / 연두 / 연파랑 | 컬러 카드 시스템 |
| 배경 | 흰색 #FFFFFF + 컬러 카드 영역 | 크림 배경 아님 |
| 캐릭터 | **노란 레몬 마스코트 (3D)** | 건강의신의 핵심 자산 — Lemon Aid가 새로 만든 게 아님 |
| 일러스트 | 3D 렌더 + 명도 높음 | 양식적 단색 아님 — §12.4 수정 필요 |
| Bottom Nav | 5탭: 홈 / 걷기왕 / 커뮤니티 / 청구의신 / 메뉴 | 5탭 구조 검증됨 |
| 카드 라운드 | 16~20dp 추정 | 우리 16과 호환 |
| 그림자 | 거의 없음, 컬러 카드로 영역 구분 | 우리 shadow.sm 톤 OK |
| 타이포 | Pretendard 추정, 본문 14~16, 헤딩 18~22 | 우리 토큰과 호환 |
| 정보 밀도 | 화면당 카드 3~5개 | 우리 Dashboard 설계와 일치 |
| CTA 버튼 | 파란 솔리드, full-width, radius 8~12 | 우리 12 호환 |
| 게이미피케이션 | 레몬건강지수 100 / 포인트 95P / 챌린지 / 출석체크 / 친구초대 | 보상 시스템 매우 발달 |
| 면책 | 캡처본 미확인 | 청구의신·약제비 화면에 약사법 관련 확인 필요 |

**가져올 것 (▲ — 검수자 익숙함 확보)**

| 영역 | 빌릴 것 | 이유 |
|------|--------|------|
| 컬러 카드 시스템 | 노랑·파랑·분홍·연두 4컬러로 정보 묶기 | 50대 가독성·시각 위계 |
| Bottom Nav 5탭 | 5탭 구조 + 가운데 강조 없음 | 익숙한 패턴 |
| 레몬 마스코트 | 노란 레몬 캐릭터 — 같은 IP 활용 | 발주처 자산 재사용·세계관 통일 |
| CTA 패턴 | 파란 풀폭 버튼 + 라운드 12 | 한국 헬스앱 표준 |
| 3D 일러스트 | 카드별 3D 아이콘·캐릭터 | 발주처 톤 일관성 |
| 게이미피케이션 | 출석체크·포인트·챌린지 | Lemon Aid 응모권을 이 시스템 위에 얹기 |
| 청구의신 카드 패턴 | 진료비 청구 큰 카드 + 보조 카드 4분할 | Score 5출력 화면 응용 가능 |

**버릴 것 (▽ — 만성질환자 + AI에 안 맞음)**

| 영역 | 버릴 것 | 이유 |
|------|--------|------|
| 정보 밀도 | 한 화면에 너무 많은 위젯 (헤더·게이지·통계·미션·챌린지) | 만성질환 50대에 인지 부담 |
| 게이지 위주 시각화 | 큰 원형 게이지 3개 | 영양·복약은 게이지보다 5단계 라벨이 명확 |
| 작은 칩 텍스트 | "10P 받기" 같은 작은 텍스트 | 50대 가독성 13dp 이하 X |
| 친구·랭킹 경쟁 | 친구 랭킹·올해 랭킹 | 만성질환자 비교 부담 → 응모권으로 대체 |
| 마음일기 핑크 그라데이션 | 너무 캐주얼 | Lemon Aid는 의료 톤 |

**확실히 다르게 갈 것 (★ — 새 가치)**

| 영역 | Lemon Aid 방향 | 의도 |
|------|--------------|------|
| 핵심 인터랙션 | AI Agent 챗봇 (스트리밍) | 건강의신에 없는 진짜 신가치 |
| 메인 입력 | 사진 한 번 → 5출력 자동 | 건강의신은 수동 입력·검색 위주 |
| 보상 철학 | 응모권 (걷기 부담 X, 사진만으로 OK) | 건강의신 챌린지 점수 경쟁과 차별 |
| 영양·복약 분석 | 영양제 OCR·식단 사진·결핍 진단 | 건강의신은 걷기·청구 위주, 영양은 없음 |
| 캐릭터 활용 | 레몬 캐릭터를 **AI 어시스턴트로 의인화** (챗봇 아이콘) | 같은 IP를 새 역할로 |

**토큰 조정 결정 (§14.8 갱신)**

| 항목 | 기존 (PG.md) | 조정 후 |
|------|------------|--------|
| 메인 컬러 | 레몬 #CA8A04 (노랑) | **코발트 블루 (브랜드 호환) + 레몬 캐릭터 액센트** 재검토 필요 |
| 배경 | 크림 #FEFAE0 | **화이트 #FFFFFF + 컬러 카드** 재검토 필요 |
| 일러스트 | 양식적 단색 (§12.4) | **3D 렌더 또는 양식적 + 컬러풀** 재검토 필요 |

→ 이 3개는 다음 디자인 결정 회의 안건. 발주처 검수 통과율을 우선시한다면 톤을 건강의신 쪽으로 당겨야 함.

**남은 분석 (다음 캡처 필요 시)**

- 청구의신 진입 후 OCR 사진 등록 화면 → Lemon Aid Camera 화면 참고
- 챌린지 참여 후 진행 화면 → Lemon Aid 응모권 누적 화면 참고
- 알림·푸시 화면 → 톤 매너 확인
- 약제비 청구 영역의 약사법 면책 표시 방법
- 설정·계정 화면 톤
- 로딩·에러 상태 처리

### 12.5.1 건강의신 Login 화면 정밀 분석 (스크린샷 추가)

**구조 (위 → 아래)**

| 영역 | 내용 | 토큰 추정 |
|------|------|---------|
| 상단 | 워드마크 "건강의신" — 손글씨체 둥근 두꺼운 sans, 글자 안에 작은 노란 레몬 일러스트 | ~40~44dp / 800 / 좌측 정렬 |
| 태그라인 | "걷기, 건강과 이득을 더하다." | body 16/600 / 좌측 정렬 / 워드마크 아래 16dp |
| 중앙 | **큰 빈 여백** (화면 40~50%) | 의도된 호흡 공간 |
| 하단 1/3 | 레몬 캐릭터 3D 렌더 — 우측 정렬, ~160dp | 워드마크와 동일 IP |
| CTA 1 | 카카오 풀폭 버튼 + 말풍선 아이콘 + "카카오로 계속하기" | bg #FEE500, fg #191919, h ~56 |
| 툴팁 | "최근 로그인했어요" — 검정 말풍선 (카카오 버튼 위) | 사용자 기억 신호 |
| CTA 2 분할 | "회원가입" outline + "로그인" 파란 솔리드 — 1:2 비율 | brand #4267EC, h ~52 |

**컬러 추출**

| 항목 | Hex 추정 |
|------|--------|
| brand 메인 | #4267EC (코발트 블루) |
| brand 호버 | #2945C2 |
| 카카오 | #FEE500 (공식) |
| 카카오 텍스트 | #191919 |
| 배경 | #FFFFFF 순백 |
| 메인 텍스트 | #1A1F2E (거의 검정) |
| 회색 라인 | #E5E7EB |

**UX 디테일 발견**

1. "최근 로그인했어요" 툴팁 — 사용자 행동 학습 → 다음 액션 안내 (Doherty 원칙)
2. 카카오 풀폭 최상단 — 한국 50대 친화 1순위
3. 캐릭터가 콘텐츠의 일부 (장식 X) — 친근감 + 브랜드 정체성
4. 큰 빈 여백 — 50대 인지 부담 ↓
5. "회원가입" < "로그인" 비율 — 기존 사용자 우선
6. 카카오 버튼 위에 ⏷ 아래 화살표 미세하게 — 살짝 위로 솟은 말풍선 디자인 (마이크로 디테일)

### 12.5.2 Lemon Aid Login 리디자인 방향 (건강의신 추종 + 차별화)

**유지 (그대로)**

| 영역 | 이유 |
|------|------|
| 카카오 풀폭 최상단 | 한국 50대 친화 — 절대 양보 X |
| 큰 빈 여백 중앙 | 호흡 공간 |
| 캐릭터 우측 하단 배치 | 발주처 톤 일관 |
| 컬러 (브랜드 블루 + 카카오 노랑 + 화이트) | §4.4 토큰과 일치 |
| 라운드 12 | 토큰 일치 |

**수정 (Lemon Aid 차별점)**

| 영역 | 건강의신 | Lemon Aid | 이유 |
|------|--------|---------|------|
| 워드마크 | "건강의신" 손글씨체 | "Lemon Aid" Pretendard 800 + 작은 레몬 점 (의신의 ㅇ 자리 모방) | 영문 브랜드 + 동일 마이크로 디테일 |
| 태그라인 | "걷기, 건강과 이득을 더하다" | "사진 한 번, 영양 분석 끝" | 앱 핵심 가치 직접 전달 |
| 캐릭터 자세 | 캐주얼 걷기 포즈 | 손에 작은 알약 또는 영양제 들고 있는 포즈 (v2, 일단 가만히 서있는 포즈) | 영양·복약 정체성 |
| OAuth 추가 | 카카오만 | 카카오 + 구글 (2개) | 보조 옵션 |
| 회원가입/로그인 분할 | 건강의신 | **다른 흐름** — Lemon Aid는 OAuth 첫 클릭 = 가입+로그인 통합 | OAuth는 회원가입 따로 X. 이메일만 회원가입 분리. |
| 툴팁 "최근 로그인" | 검정 말풍선 | 동일 (참고 그대로) — 이전 OAuth 방법 기억 | UX 좋은 패턴 |
| 이메일 옵션 | 안 보임 (간소화) | 카카오·구글 아래 "또는 이메일로" Ghost 텍스트 링크 — 펼침 X 단순 추가 | 이메일 선택지 보존하되 강조 X |

**최종 레이아웃 (Lemon Aid Login v0.1)**

```
┌─────────────────────────┐
│                         │
│  Lemon🍋Aid              │  워드마크 32~36 / 800 / 좌측 정렬
│  사진 한 번, 영양 분석 끝    │  body 16/600 / inkSoft
│                         │
│                         │
│                         │
│         (큰 여백)         │  화면 35%
│                         │
│                         │
│                  🍋     │  레몬 캐릭터 ~140dp 우측 하단
│                 (서있음)  │
│                         │
│  ┌─ 최근 로그인했어요 ─┐   │  툴팁 (재로그인 시만)
│  │ 💬  카카오로 계속하기 │   │  bg #FEE500 / h 52
│  └────────────────────┘   │
│                         │
│  ┌────────────────────┐ │
│  │ G  구글로 시작       │ │  bg #FFF / border / h 52
│  └────────────────────┘ │
│                         │
│  ─────  또는 이메일로  ───  │  Ghost 링크 (작게)
│                         │
│  © Lemon Aid · 약관 · 개인정보 │  하단 caption
└─────────────────────────┘
```

**이메일 클릭 시 → 별도 화면 또는 BottomSheet?**

- BottomSheet으로 펼침 (이메일 폼 노출) — 같은 화면 컨텍스트 유지
- OR 별도 화면 `/login/email` — 단순함
- → **선택: BottomSheet** (메인 화면 시각 깔끔)

**친화도 7대 원칙 확인**

| 원칙 | 결과 |
|------|----|
| 한 화면 한 일 | ✓ "로그인" 한 가지 |
| 큰 글씨 큰 터치 | ✓ 카카오 52, 구글 52, 워드마크 32+ |
| 면책 | — (Consent에서) |
| 다음 액션 | ✓ 카카오 최상단·풀폭 = 가장 강한 시각 |
| 폴백 | ✓ OAuth 둘 다 실패 시 이메일 BottomSheet |
| 빠른 학습 | ✓ 카카오 = 학습 끝 + 캐릭터 친근 |
| 회복 가능 | ✓ 백버튼 = 앱 종료 다이얼로그 |



**분석 체크리스트 (스크린샷 확보 후)**

- [ ] 메인 컬러 팔레트 (Hex 추출)
- [ ] 타이포 위계 (제목/본문/캡션 사이즈 추정)
- [ ] 아이콘 스타일 (outlined / filled / 두께)
- [ ] 카드 라운드·그림자 깊이
- [ ] Bottom Nav 구조 (탭 수·아이콘 종류)
- [ ] 정보 밀도 (한 화면당 카드 수)
- [ ] 사진/일러스트 비율
- [ ] 면책 고지 표시 방법
- [ ] 알림·푸시 톤
- [ ] CTA 버튼 비율·위치

**분석 결과 → 토큰 조정 절차**

1. 스크린샷 5~10장 다이어리 §12.5 하위에 첨부
2. 위 표 채우기
3. Lemon Aid 토큰(§4)과 어긋나는 부분 식별
4. 어긋남이 의도된 차별인가 (★) / 우연한 어긋남인가 (조정 필요) 판단
5. 조정 필요 시 §14.8 결정 누적표에 기록

### 12.6 비주얼 금기

- 의약품 사진 직접 노출 X (약사법)
- 의료기관 로고·실제 의사 사진 X
- 빨간색 풀스크린 경고 (응급 외)
- 신체 부위 클로즈업 X

---SPLIT---

## 13. 보이스 · 톤 가이드

### 13.1 한 줄

> **친한 약사 친구의 메시지** — 친절하지만 의료적으로 정확, 잘난 척 X, 결정은 사용자에게.

### 13.2 4축

| 축 | Lemon Aid 위치 |
|----|--------------|
| 친근함 ↔ 격식 | 친근 70% ("~해요") |
| 가벼움 ↔ 진중 | 균형 50% (의료는 진중, 응모권은 가볍게) |
| 능동 ↔ 수동 | 능동 80% ("권장드려요") |
| 단정 ↔ 가능 | 가능 90% ("~일 수 있어요") |

### 13.3 상황별

| 상황 | 카피 | 금기 |
|------|------|------|
| 분석 완료 | "분석이 끝났어요. 함께 볼까요?" | "분석이 완료되었습니다." |
| 부족 영양소 | "비타민 D가 권장량의 35% 수준이에요." | "비타민 D가 부족합니다." |
| 챗봇 응답 | "약사와 상의해보시는 게 좋겠어요." | "이 약을 드시면 안 됩니다." |
| 응급 신호 | "혹시 어려움 겪고 계신가요?" | "위험한 상태입니다!" |
| 응모권 | "오늘 기록 완료! 응모권 1개 받았어요 🍋" | "축하합니다! +1 포인트!" |
| 에러 | "분석이 잘 안 됐어요. 다시 시도해볼까요?" | "오류 발생." |
| 환영 | "다시 오셨네요. 지난번 비타민 D 부족했어요." | "환영합니다!" |

### 13.4 마이크로카피 원칙

- **버튼 라벨**: 동사 + 명사 (예: "사진 찍기")
- **에러**: 무엇이 / 왜 / 어떻게 3단
- **빈 상태**: 다음 액션 제시
- **확인 모달**: 동사 명확 ("저장하기" / "확인" X)

---SPLIT---

## 14. 컴포넌트 명세 (디자인 시스템 v0)

### 14.1 Atom

| 컴포넌트 | Variant | 상태 |
|---------|---------|------|
| Button | Primary / Secondary / Ghost / Danger | Default / Hover / Pressed / Disabled / Loading |
| TextField | Outlined / Filled / Underlined | Default / Focus / Error / Disabled |
| Chip | Filter / Choice / Input | Default / Selected / Disabled |
| Avatar | XS·S·M·L | Image / Initial / Placeholder |
| Icon | 24/20/16px Outlined | Default / Active |
| Badge | Dot / Number / Label | — |
| Switch | — | Off / On / Disabled |
| Checkbox | — | Off / On / Indeterminate |
| Radio | — | Off / On / Disabled |
| ProgressBar | Linear / Circular | Determinate / Indeterminate |
| Skeleton | Card / Line / Avatar | — |

### 14.2 Molecule

| 컴포넌트 | 구성 | 용도 |
|---------|------|------|
| SearchBar | TextField + Icon | 약·식품 검색 |
| ListTile | Avatar + Title + Subtitle + Trailing | 영양제·설정 |
| Card | Header + Body + Footer | 5종 출력 |
| Tab | Tab + Indicator | 화면 탭 |
| Snackbar | Icon + Text + Action | 알림 (명시 닫기) |
| Dialog | Title + Body + Actions | 확인·동의 |
| BottomSheet | Handle + Body | 챗봇 입력 |
| Stepper | Steps + Indicator | 온보딩 |

### 14.3 Organism

| 컴포넌트 | 구성 | 화면 |
|---------|------|------|
| SupplementCard | Image + Name + Ingredients + Edit | Dashboard |
| MealCard | Photo + Foods + Nutrients + Score | Dashboard |
| ChatBubble | Avatar + Message + Actions | Chat |
| NutrientBar | Label + Bar + Value + Status | Dashboard |
| AppBar | Back + Title + Actions | 모든 화면 |
| TabBar | Tab[] | 메인 4탭 |
| Disclaimer | Icon + Text + Toggle | 권고 화면 |

### 14.4 5상태 매트릭스 (Button)

| 상태 | Background | Text | Border |
|------|-----------|------|--------|
| Default | brand.primary | white | — |
| Hover (web) | brand.primary.dark | white | — |
| Pressed | brand.primary.darker | white | — |
| Disabled | surface.disabled | text.disabled | — |
| Loading | brand.primary | white + spinner | — |

→ 모든 컴포넌트 5상태 필수.

### 14.5 명명

`Component/Variant/State/Size`
- `Button/Primary/Default/M`
- `Card/Supplement/Editing/Default`

### 14.6 컴포넌트 상세 명세 (수치 박힌 버전)

다이어리의 진짜 본체는 여기. Figma 작업 시작 전에 이 표를 먼저 채우고, 채워진 표가 곧 Figma 컴포넌트의 사양서다.

**Button** (건강의신 톤 — 블루 풀폭 솔리드)

| 속성 | Primary | Secondary | Ghost | Danger |
|------|---------|-----------|-------|--------|
| Background | brand #4267EC | bgElev #FFFFFF | transparent | danger #DC2626 |
| Text | #FFFFFF | brand #4267EC | brand #4267EC | #FFFFFF |
| Border | none | 1.5 brand | none | none |
| Height | 52dp (건강의신 추정) | 52dp | 52dp | 52dp |
| Padding H | 24dp | 24dp | 16dp | 24dp |
| Radius | 12 | 12 | 12 | 12 |
| Font | 16 / 700 | 16 / 700 | 16 / 700 | 16 / 700 |
| Min touch | 48×48 | 48×48 | 48×48 | 48×48 |

상태 변화

| 상태 | Primary 변경 |
|------|------------|
| Pressed | bg → brandStrong #2945C2, 0.97 scale 80ms |
| Disabled | bg → line #EEF0F4, text → inkMute #8B92A4 |
| Loading | bg 유지, spinner 16dp 좌측, text "처리 중..." |

**TextField**

| 속성 | 값 |
|------|---|
| Height | 56dp (label 포함) / 48dp (단독) |
| Border | 1.5px line #E7E5D8 |
| Border focus | 2px brand #CA8A04 |
| Border error | 2px danger #DC2626 |
| Padding | 16 H, 14 V |
| Radius | 12 |
| Label | 13 / 500 / inkSoft, 위 6dp |
| Hint | 15 / 400 / inkMute |
| Input | 17 / 400 / ink |
| Helper | 13 / 400 / inkMute, 아래 4dp |
| Error msg | 13 / 500 / danger, 아래 4dp |

**Card (영양제·식단)**

| 속성 | 값 |
|------|---|
| Background | bg.elev #FFFFFF |
| Border | 1px line #E7E5D8 |
| Radius | 16 |
| Padding | 16 |
| Shadow | 0 1px 2px rgba(42,36,16,0.04) |
| Tap state | scale 0.98 + bg → #FEFAE0 |

**Chip (필터·선택)**

| 속성 | Default | Selected |
|------|---------|----------|
| Background | bg.elev | brand.tint #FAEDCD |
| Text | ink | accentStrong #854D0E |
| Border | 1px line | 1.5px brand |
| Height | 36 | 36 |
| Padding H | 14 | 14 |
| Radius | 999 (pill) |

**NutrientBar (영양소 충족률)**

5단계 색상 + 라벨 병기 (색맹 대응)

| 단계 | 색 | 라벨 | 너비 비율 |
|------|---|------|--------|
| deficient | danger | "결핍" | 0~35% |
| low | warning | "약간 부족" | 35~70% |
| adequate | success | "충분" | 70~130% |
| excessive | warning | "많음" | 130~UL% |
| risky | danger | "주의" | UL 초과 |

바 높이 12dp, 라벨 우측, 수치 좌측.

### 14.7 화면별 UI / UX 상세 명세 (앱 전체 14개)

PG.md §13 파일구조 `mobile/lib/screens/` 와 1:1 매칭. 각 화면은 다음 12개 항목으로 명세한다.

**명세 템플릿**

| 영역 | 항목 |
|------|------|
| ① 정체성 | 화면 ID · 목적 (한 줄) · 진입 · 출구 |
| ② 레이아웃 | AppBar · Body 영역 · Bottom (Nav/Sheet/Button) · FAB |
| ③ UI 컴포넌트 | 모든 위젯 + 토큰 (color/type/size/radius/shadow) |
| ④ 데이터 | 표시 필드 · 입력 필드 · 검증 룰 |
| ⑤ 상태 변화 | Empty / Loading / Normal / Error / Partial |
| ⑥ 인터랙션 | 탭 / 스크롤 / 스와이프 / 키보드 / 햅틱 / 모션 |
| ⑦ 접근성 | TalkBack 라벨 / 터치 영역 / 대비 / 키보드 네비 |
| ⑧ 고령자 모드 | 변경 사항 (사이즈·간격·터치) |
| ⑨ 면책·의료법 | 표시 위치·문구·시점 |
| ⑩ 분석 이벤트 | 로깅할 이벤트 (스크린뷰·탭·완료·이탈) |
| ⑪ 와이어 | ASCII 골격 (§14.7.W) |
| ⑫ 결정·메모 | 왜 이 결정 / 버린 대안 / 회고 |

#### 화면 지도 (전체 흐름)

```
[Splash] ──(인증 없음)──> [Login] ─┬─> [Signup] ─> [Verify] ─> [Consent] ─> [Onboarding] ─┐
   │                              └─> [PW찾기 v2]                                          │
   └─(인증 있음)────────────────────────────────────────────────────────────────────────────┘
                                                                                           ▼
                                                                                       [Dashboard]
                                                                                           │
              ┌─────────┬─────────┬─────────┬─────────┬─────────────┬───────────┬────────┘
              ▼         ▼         ▼         ▼         ▼             ▼           ▼
          [Camera]  [Health]  [Score]   [Chat]   [Raffle]      [Settings]   (FAB→Camera)
```

Bottom Nav 5탭: Home / Health / Chat / Raffle / Settings

#### S-01 Splash

**① 정체성**

| 항목 | 값 |
|------|---|
| 화면 ID | S-01 Splash |
| 파일 | `screens/splash_screen.dart` |
| 목적 | 앱 부팅 + 세션 복구 + 라우팅 결정 |
| 진입 | 앱 콜드/웜 부팅 |
| 출구 | (인증 OK) `/home` / (인증 X) `/login` / (에러) `/login` + Snackbar |
| 최소 표시 시간 | **2.0초** (2026-05-11 결정 — 50대 로고 인식 + Lottie 1사이클 보장) |
| 최대 표시 시간 (개발) | 3.5초 timeout 후 강제 `/login` |
| 최대 표시 시간 (배포) | **무한 loop** — Lottie repeat: true / 인증·네트워크 응답까지 대기 |

**② 레이아웃**

| 영역 | 내용 |
|------|------|
| AppBar | 없음 (immersive) |
| StatusBar | 투명 + dark icon (밝은 배경) |
| Body | 중앙 정렬 단일 컬럼 — 로고·워드마크·태그라인·인디케이터 |
| FAB | 없음 |
| Bottom | 없음 |

**③ UI 컴포넌트**

| 컴포넌트 | 토큰 |
|---------|------|
| 배경 | `LemonColors.bg` #FFFFFF — 처음 80ms 동안만 `citrusLight` → white 페이드 (§4.4a 마케팅용 잔재) |
| 레몬 캐릭터 (3D) | 120dp 정사각 — assets/illustrations/lemon_hero.png |
| 워드마크 "Lemon Aid" | `LemonText.display` (32/800) `LemonColors.ink` |
| 태그라인 "내 손안의 영양 상담사" | `LemonText.body` (16/400) `LemonColors.inkSoft` |
| 인디케이터 | 폭 56 / 두께 3 / `brand` / pulse 1.2s loop |
| 캐릭터 ↔ 워드마크 간격 | `LemonSpace.lg` 24 |
| 워드마크 ↔ 태그라인 간격 | `LemonSpace.sm` 8 |
| 태그라인 ↔ 인디케이터 간격 | `LemonSpace.xxl` 48 |

**④ 데이터**

- 표시 필드: 없음 (정적)
- 백그라운드 작업:
  - SharedPreferences에서 `auth_token` 읽기
  - 토큰 있으면 `/auth/me` 호출 → 유효 검증
  - 응답 200 → `/home`, 401/만료 → `/login`
  - 네트워크 에러 → `/login` + "잠시 후 다시 시도해주세요" Snackbar
- 타임아웃: 1.5초 후에도 응답 없으면 강제로 `/login`

**⑤ 상태 변화**

| 상태 | 화면 |
|------|------|
| 시작 ~ 1.5s | 로고 + 인디케이터 |
| 1.5s 후 | (자동 라우팅, 화면 안 보임) |
| 네트워크 에러 | Login 진입 후 Snackbar 1회 |
| 강제 업데이트 필요 (v2) | 다이얼로그 + 스토어 링크 |
| 점검 중 (v2) | 풀스크린 안내 + 재시도 버튼 |

**⑥ 인터랙션**

- 사용자 입력 없음 — 1.5초 자동 진행
- 백 버튼: 무시 (Splash에선 못 빠져나감)
- 화면 탭: 무시 (Doherty 미만 단축 X — 너무 빨라서 50대 인식 못 함)
- 햅틱: 없음
- 모션: 캐릭터 살짝 떠다님 (translateY -4 → +4, 2.4s easeInOut loop)

**⑦ 접근성**

| 항목 | 값 |
|------|---|
| TalkBack | "Lemon Aid 앱을 시작하고 있어요. 잠시 기다려주세요" (전체 한 번만 읽음) |
| 캐릭터 이미지 | semanticLabel: "레몬 아이드 마스코트" |
| 대비 | ink 16.1:1 (AAA) on white |
| reduceMotion | 떠다니는 모션 끔 / 페이드인만 유지 |

**⑧ 고령자 모드 영향**

- 표시 시간 1.5s → 2.5s (확실히 보일 때까지)
- 워드마크 32 → 36
- 태그라인 16 → 19

**⑨ 면책·의료법**

- 표시 없음 (Consent 화면에서 일괄 처리)

**⑩ 분석 이벤트 (v2 도입 예정)**

| 이벤트 | 페이로드 |
|--------|---------|
| `splash_view` | timestamp |
| `splash_auth_success` | duration_ms |
| `splash_auth_fail` | reason (timeout/401/network) |
| `splash_force_route_login` | reason |

**⑪ 와이어 → §14.7.W S-01**

**⑫ 결정·메모**

- 1.5초 결정 근거 — §8 작업일지 2026-05-13 "Splash 1.5초"
- 떠다니는 모션 — 50대 한 분 사용자 테스트로 "살아있는 느낌" 피드백 받으면 유지, 어지러움이면 제거
- 첫 80ms citrusLight → white 페이드 — 브랜드 정체성 인사 (§4.4a)

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | "기다리세요" 한 일 |
| 큰 글씨 큰 터치 | ✓ | 워드마크 32, 인터랙션 없음 |
| 면책 | — | 이 화면엔 없음 (Consent에서) |
| 다음 액션 | ✓ | 자동 라우팅 (사용자 선택 X) |
| 폴백 | ⚠ | 인증 API 실패 → /login 으로 + Snackbar. **개선: 1.5초 후에도 화면 멈춤 방지 — 강제 라우팅 보장 코드 필요** |
| 빠른 학습 | ✓ | 로고 + 워드마크 = 앱명 학습 |
| 회복 가능 | — | 사용자 액션 없음 |

**S-02 Login (OAuth 3종 + 이메일/비밀번호)**

| 항목 | 값 |
|------|---|
| 목적 | 기존 사용자 인증 — 카카오 우선 (50대+ 한국 사용자 가장 익숙) |
| 진입 | Splash (세션 없음) / 로그아웃 / Signup 완료 후 |
| 출구 | 홈 (기존) / 동의 (신규 OAuth) / Signup (이메일 신규) |
| 핵심 컴포넌트 | OAuth 버튼 3종 + Divider("또는") + 이메일 폼 + 회원가입 링크 |
| 데이터 | (OAuth) provider_token / (이메일) email, password |
| 상태 | Default / OAuth 진행 중 / 이메일 로딩 / 인증 실패 / 네트워크 에러 |
| 다음 액션 | OAuth 3종 또는 이메일 로그인 |
| 키보드 | email → next, password → done → submit |
| 신규 vs 기존 | OAuth는 첫 클릭 = 가입+로그인 통합 (가입 화면 X) |

**버튼 우선순위 (위에서 아래로) — 2026-05-11 건강의신 추종 결정**

| 순서 | 버튼 | 색 | 이유 |
|-----|------|---|------|
| 1 | 카카오 로그인 (풀폭) + "최근 로그인했어요" 툴팁 | bg #FEE500 / fg #191919 | 한국 50대 친화 1순위 + 재로그인 학습 |
| 2 | 구글 로그인 | bg #FFF + border #DADCE0 | 보조 옵션 |
| 3 | "또는 이메일로" Ghost 링크 | inkSoft caption | 작게 — 강조 X |
| 4 | (이메일 클릭 시 BottomSheet) | brand 폼 | 같은 화면 컨텍스트 |

**레이아웃 변경 — 건강의신 분석 반영 (§12.5.1)**

- 워드마크 좌측 정렬 (가운데 X) — 건강의신 그대로
- 중앙 큰 빈 여백 (35%) — 호흡 공간
- 레몬 캐릭터 우측 하단 ~140dp
- CTA 영역 하단 1/3
- 회원가입은 별도 화면 X — OAuth는 첫 클릭이 가입+로그인, 이메일은 BottomSheet 안에 "처음이신가요?" 링크

**OAuth 버튼 디자인 룰**

- 모든 OAuth 버튼 가로 full-width, 높이 52dp, 라운드 12
- 좌측 아이콘 24dp + 텍스트 가운데 정렬
- 카카오: bg #FEE500, fg #191919 (공식 가이드)
- 구글: bg #FFFFFF, border 1.5 #DADCE0, fg #1F1F1F + Google G 4색 로고

**상태별 처리**

| 상태 | 화면 변화 |
|------|---------|
| OAuth 진행 중 | 해당 버튼만 spinner, 나머지 비활성 |
| 이메일 로딩 | Primary 버튼 spinner + text "로그인 중..." |
| 인증 실패 | TextField 아래 helper text 빨강 "이메일 또는 비밀번호가 일치하지 않아요" |
| 네트워크 에러 | Snackbar 하단 + 재시도 액션 |
| 카카오톡 미설치 (인앱 모드 시) | 웹 카카오 로그인 자동 폴백 + 알림 1회 |

**약사법·면책 처리**

- 로그인 화면 자체엔 면책 표시 X (Consent 화면이 별도)
- 단, 페이지 하단에 "© Lemon Aid · 약관 · 개인정보" 텍스트 (caption)

**고령자 모드 영향**

- OAuth 버튼 높이 52 → 60
- 폰트 16 → 18
- 카카오 버튼은 첫 번째 + 가장 큰 강조 유지

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | "로그인" 한 가지 (OAuth 3종은 같은 일) |
| 큰 글씨 큰 터치 | ✓ | 모든 버튼 52dp, 폰트 16/700 |
| 면책 | — | Login 화면엔 없음 (Consent에서) |
| 다음 액션 | ✓ | 카카오 = 가장 강한 시각적 우선 |
| 폴백 | ⚠ | **개선 필요** — 카카오톡 미설치 시 웹 폴백 자동 / 구글 미설치 시 안내. OAuth 전체 다운 시 이메일만 활성. |
| 빠른 학습 | ✓ | 카카오는 50대 학습 끝 — 다른 앱과 동일 |
| 회복 가능 | ⚠ | **개선 필요** — 비밀번호 틀리면 입력 유지 (이메일 살아있음). 백버튼이 Splash로 가지 않게 시스템 종료. |

**친화도 빈틈 → 추가 결정**

- 카카오톡 미설치 감지 → 웹 카카오 자동 시도 + 작은 알림 "카카오 앱이 없어 웹으로 진행해요"
- OAuth 3종 모두 실패 시 → 이메일 폼 노출 강조 + Snackbar
- 백버튼 정책 — Login에서 백버튼 = 앱 종료 다이얼로그

#### S-03 Signup (이메일 가입)

**① 정체성**

| 항목 | 값 |
|------|---|
| 화면 ID | S-03 Signup |
| 파일 | `screens/auth/signup_screen.dart` |
| 목적 | 이메일 신규 가입 (OAuth 사용자는 이 화면 안 봄) |
| 진입 | `/login` → "회원가입" 텍스트 링크 |
| 출구 | `/verify-email` (성공) / 이전 (취소) |

**② 레이아웃**

| 영역 | 내용 |
|------|------|
| AppBar | 좌측 ← + 타이틀 "회원가입" + 우측 비움 |
| Body | ScrollView — Stepper(1/1) + 4개 필드 + Primary 버튼 |
| Bottom safe area | 키보드 올라오면 Primary 버튼 위로 따라옴 |

**③ UI 컴포넌트**

| 컴포넌트 | 토큰 |
|---------|------|
| Stepper 인디케이터 | "1 / 1" — `LemonText.caption` `inkMute` (가입은 한 페이지) |
| 화면 타이틀 | "환영해요" `LemonText.title` 24/800 |
| 서브 타이틀 | "이메일로 시작할게요" `LemonText.body` `inkSoft` |
| TextField × 4 | 이메일 / 비밀번호 / 비밀번호 확인 / 이름 — 모두 56dp 높이 |
| 비밀번호 보기 토글 (👁) | 우측 suffixIcon — `inkMute` 색 |
| Helper text (실시간) | `LemonText.caption` 위치: 필드 아래 4dp |
| Primary 버튼 "다음" | brand 52dp 풀폭 — 모든 필드 OK일 때만 활성 |
| 화면 마진 | `LemonSpace.lg` 24 (좌우) |
| 필드 간 간격 | `LemonSpace.md` 16 |

**④ 데이터** (PG.md §11.1 User + EmailVerification 일치)

| 필드 | 저장 위치 | 검증 | 에러 메시지 |
|------|---------|------|----------|
| email | `User.email` (unique) | 정규식 + 백엔드 중복 확인 (debounce 600ms) | "이메일 형식이 아니에요" / "이미 가입된 이메일이에요" |
| password | `User.password_hash` (서버에서 bcrypt) | 8자+ / 영문 / 숫자 | "8자 이상, 영문+숫자를 섞어주세요" |
| passwordConfirm | (서버 전송 X) | password와 일치 | "비밀번호가 일치하지 않아요" |
| display_name | `User.display_name` | 2~10자 / 한글·영문 | "2~10자로 입력해주세요" |
| social_provider | 자동 = `'email'` | — | — |
| email_verified_at | 다음 단계 (Verify Email) 에서 결정 | — | — |

**⑤ 상태 변화**

| 상태 | 화면 |
|------|------|
| Default | 필드 4개 빈 상태 + Primary 비활성 (`disabled` 회색) |
| 입력 중 | Helper text 회색 안내 ("8자 이상 영문+숫자") |
| 실시간 검증 통과 | Helper text 사라짐, 체크 아이콘 우측 표시 |
| 실시간 검증 실패 | Helper danger 빨강 + 필드 border danger |
| 모든 OK | Primary 버튼 활성 |
| 제출 중 | Primary spinner + "가입 중..." + 모든 필드 비활성 |
| 서버 에러 | Snackbar + Primary 원복 |

**⑥ 인터랙션**

- 키보드 순서: email → password → passwordConfirm → name → 완료 → 자동 제출
- email 6초 안 움직이면 중복 확인 API 1회
- 비밀번호 ●●● 표시 / 👁 클릭 시 평문 (3초 후 자동 ●●● 복귀)
- 백 버튼: 입력 있으면 다이얼로그 "작성 중인 정보를 버릴까요?"
- 햅틱: 검증 실패 시 light impact 1회
- 모션: 필드 focus 시 border 1.5 → 2 px easeOut 80ms

**⑦ 접근성**

| 항목 | 값 |
|------|---|
| 모든 필드 | `Semantics(label: ...)` + `hintText` |
| 비밀번호 보기 | semanticLabel: "비밀번호 표시 토글" |
| 에러 메시지 | `liveRegion: true` (실시간 읽힘) |
| Primary | semanticLabel: "회원가입 다음 단계로" |

**⑧ 고령자 모드**

- TextField 높이 56 → 64
- Primary 52 → 60
- 폰트 16 → 19
- 비밀번호 보기 기본 ON (●●● 안 보이게 하면 입력이 너무 어려움)

**⑨ 면책·의료법**

- 표시 없음 (Consent 화면에서 처리)
- 단, "다음" 버튼 아래 caption 한 줄: "다음 단계에서 이용약관에 동의해야 가입이 완료돼요"

**⑩ 분석 이벤트**

- `signup_view`
- `signup_email_typed` `signup_password_typed`
- `signup_validation_fail` (어느 필드)
- `signup_submit_attempt`
- `signup_email_duplicated`
- `signup_complete` → /verify-email

**⑪ 와이어 → §14.7.W S-03**

**⑫ 결정·메모**

- 이메일 중복 실시간 확인 — 입력 끝나고 처음 보는 게 늦으면 사용자 짜증. 600ms debounce.
- 가입을 1페이지로 — Stepper로 나누면 50대가 중간에 이탈. 4개 필드는 한 페이지 OK.
- 비밀번호 정책 8자/영문/숫자 — 발주처 의료 데이터 보안 권고 + 너무 강하지 않게 (특수문자 강제 X).

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | "가입" 한 가지 |
| 큰 글씨 큰 터치 | ✓ | TextField 56dp |
| 면책 | ⚠ | 비밀번호 정책만 caption. **개선: "다음 단계에서 약관 동의 있어요" 안내 한 줄** (이미 추가됨) |
| 다음 액션 | ✓ | Primary "다음" 1개 |
| 폴백 | ⚠ | **개선 필요** — Firebase 가입 실패 시 친절한 메시지 + 이메일 폼 유지 |
| 빠른 학습 | ✓ | 실시간 검증 + 명확한 helper text |
| 회복 가능 | ✓ | 백버튼 시 입력 보호 다이얼로그 |

**친화도 빈틈 → 추가 결정**

- 이메일 자동 완성 활성화 (autofillHints) — 50대 키보드 타이핑 부담 ↓
- 비밀번호 자동 강도 측정 표시 (약함/보통/강함 색 단계)
- 가입 도중 앱 죽으면 입력값 60초 캐시 (자동 복원)

**S-04 Consent (만성질환자용 동의)**

| 항목 | 값 |
|------|---|
| 목적 | 의료법·개인정보 동의 + AI 한계 고지 |
| 진입 | Signup |
| 출구 | 온보딩 / 거절 시 이전 화면 |
| 핵심 컴포넌트 | Checkbox×4 (필수×3, 선택×1), Disclaimer 카드, Button(Primary "동의하고 시작") |
| 데이터 | 동의 4종 |
| 상태 | Default / 필수 미체크 |
| 다음 액션 | "동의하고 시작" (Primary, 필수 3개 체크 시) / "전체 동의" (Ghost) |
| 핵심 문구 | "Lemon Aid는 진단·처방을 하지 않습니다. AI 권고는 참고용이며..." |

#### S-05 Verify Email

**① 정체성**

| 항목 | 값 |
|------|---|
| 화면 ID | S-05 Verify Email |
| 파일 | `screens/auth/verify_email_screen.dart` |
| 목적 | 이메일 인증 코드 입력 (가입 직후 1회) |
| 진입 | Signup 완료 |
| 출구 | `/consent` (성공) / `/signup` (재발송 후 자동 복귀) |

**② 레이아웃**

| 영역 | 내용 |
|------|------|
| AppBar | 좌측 ← + 타이틀 "이메일 확인" |
| Body | 단일 컬럼 — 아이콘·안내·OTP·타이머·Primary·재발송 링크 |

**③ UI 컴포넌트**

| 컴포넌트 | 토큰 |
|---------|------|
| 메일 아이콘 | 64dp `brand` |
| 안내 텍스트 | "name@email.com 으로 6자리 코드를 보냈어요" — body, 이메일 부분 brand 강조 |
| OTPField (6칸) | 각 48×56dp, gap 8dp, border 1.5 `line`, focus 시 `brand`, radius 12, font 24/700 |
| 타이머 | "04 : 32 남음" — `LemonText.caption` `inkMute`, 30초 미만이면 danger 빨강 |
| Primary 버튼 "확인" | brand 52dp — 6자리 입력 시 자동 활성 |
| 재발송 TextLink | "코드 재발송" — `brand` underline, 처음 10초 비활성 (회색) |

**④ 데이터** (PG.md §11.1 EmailVerification 일치)

| 필드 | 저장 위치 | 검증 |
|------|---------|------|
| token (6자리 코드) | `EmailVerification.token` | 0-9 only, 6자리 |
| expires_at | `EmailVerification.expires_at` | 5분 후 만료 |
| verified_at | `EmailVerification.verified_at` 또는 `User.email_verified_at` | 성공 시 둘 다 timestamp |

- 재발송 카운트: 24시간 내 최대 5회 (백엔드에서 rate limit)
- 서버 호출: `POST /auth/verify-email {token}` → 성공 시 User.email_verified_at 갱신

**⑤ 상태 변화**

| 상태 | 화면 |
|------|------|
| Default | OTP 6칸 빈 상태, 타이머 5:00 카운트다운 |
| 입력 중 | 칸 채워지면 다음 칸 자동 포커스 |
| 6자리 완료 | 자동 제출 (Primary 안 눌러도 됨) |
| 검증 중 | 모든 칸 비활성 + 가운데 spinner overlay |
| 코드 틀림 | 빨간 진동 (shake 200ms) + 6칸 초기화 + 안내 "코드가 일치하지 않아요. 다시 입력해주세요" |
| 만료 | 타이머 00:00 → OTP 모두 비활성 + "시간이 만료됐어요. 재발송하기" CTA |
| 재발송 후 | "새 코드를 보냈어요" Snackbar + 타이머 리셋 5:00 + 재발송 버튼 다시 10초 비활성 |
| 5회 초과 | "24시간 내 5회를 초과했어요. 내일 다시 시도해주세요" + Primary 비활성 |

**⑥ 인터랙션**

- 자동 채움 (SMS otpAutofill 패키지) — 가능하면
- 백 버튼: 다이얼로그 "인증을 그만둘까요? 다시 받으려면 처음부터 진행해야 해요"
- 햅틱: 6자리 완료 시 success / 틀리면 medium
- 키보드: 자동 숫자 키패드

**⑦ 접근성**

- OTP 각 칸 semanticLabel: "1번째 숫자 칸" 등
- 코드 틀림 시 liveRegion 알림
- shake 모션은 reduceMotion 시 색 변화로 대체

**⑧ 고령자 모드**

- OTP 칸 48×56 → 56×64
- 폰트 24 → 28
- 안내 텍스트 16 → 19
- 자동 제출 후에도 "확인" 버튼 보여서 다시 누를 수 있게 (자동만 신뢰 X)

**⑨ 면책·의료법**

- 표시 없음

**⑩ 분석 이벤트**

- `verify_view`
- `verify_code_input_complete`
- `verify_success` / `verify_fail` (reason)
- `verify_resend_click` (count 차수)
- `verify_expired`

**⑪ 와이어 → §14.7.W S-04**

**⑫ 결정·메모**

- 자동 제출 — 6자리 입력 끝나면 "확인" 안 눌러도 자동. 50대도 직관적이어야 함.
- 재발송 10초 비활성 — 연타 방지 + 비용 절감
- shake 모션 — 카드 결제 실패 패턴과 동일, 사용자 학습된 시각 신호

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | "코드 입력" 한 가지 |
| 큰 글씨 큰 터치 | ✓ | OTP 칸 48×56, 폰트 24/700 |
| 면책 | — | 해당 없음 |
| 다음 액션 | ✓ | "확인" 자동 활성 + 자동 제출 |
| 폴백 | ⚠ | **개선 필요** — 메일 안 옴 시 "스팸함 확인" 안내 / 도메인 차단 시 안내 / 재발송 5회 후엔 고객센터 연결 CTA |
| 빠른 학습 | ✓ | 메일 아이콘 + 이메일 강조 = 즉시 이해 |
| 회복 가능 | ⚠ | **개선 필요** — 코드 틀려도 재시도 가능 명시 |

**친화도 빈틈 → 추가 결정**

- "이메일이 안 와요" Ghost 버튼 추가 → BottomSheet 안내 (스팸함 확인 / 도메인 차단 / 재발송)
- 재발송 횟수 1/5 표시 — 사용자가 한도 알게
- 코드 만료 후에도 화면 떠나지 않게 — "재발송"으로 즉시 새 코드

#### S-06 Consent

**① 정체성**

| 항목 | 값 |
|------|---|
| 화면 ID | S-06 Consent |
| 파일 | `screens/auth/consent_screen.dart` |
| 목적 | 의료법·약사법·개인정보·AI 한계 고지 + 동의 |
| 진입 | Verify Email (이메일 가입) / OAuth 첫 로그인 |
| 출구 | `/onboarding` (필수 3개 체크 후) / 모두 거절 시 `/login` + Snackbar |

**② 레이아웃**

| 영역 | 내용 |
|------|------|
| AppBar | 좌측 ← (확인 다이얼로그) + 타이틀 "약관 동의" |
| Body | ScrollView — 헤더·면책 카드·체크박스 그룹·여백 |
| Bottom 고정 | Primary 버튼 (스크롤 와 무관, 항상 하단 노출) |

**③ UI 컴포넌트**

| 컴포넌트 | 토큰 |
|---------|------|
| 화면 타이틀 | "Lemon Aid 이용 동의" `LemonText.title` |
| 면책 카드 | Pink Card 배경 (`pinkLight` #FFE6EA) + 아이콘 ⚠ + 본문 — "Lemon Aid는 진단·처방을 하지 않아요. AI 권고는 참고용이며 의료 결정은 전문가와 상의하세요." `LemonText.disclaimer` |
| Checkbox 4종 | 필수 ×3 + 선택 ×1 — 각 행 ListTile 패턴 |
| 각 항목 행 | Checkbox + 라벨(필수/선택 chip) + 텍스트 + "자세히" 우측 화살표 |
| 자세히 클릭 | BottomSheet (전체 약관 텍스트 풀스크린) |
| 구분선 | `LemonColors.line` 1dp |
| Primary 하단 고정 | brand 52dp · 필수 3개 체크 시 활성 |

**체크 항목**

| 순서 | 라벨 | 분류 |
|-----|------|------|
| 1 | 서비스 이용약관 | 필수 |
| 2 | 개인정보 수집·이용 (건강 정보 포함) | 필수 |
| 3 | AI 권고의 한계 이해 ("진단·처방 아님") | 필수 |
| 4 | 마케팅 정보 수신 | 선택 |

**④ 데이터** (PG.md §11.1 Consent 일치)

PG.md 확정 5종 `type`:

| 우리 화면 항목 | DB type 매핑 | 필수? |
|--------------|------------|------|
| 서비스 이용약관 | `privacy` | ✓ |
| 개인정보 수집·이용 | `privacy` | ✓ |
| AI 권고의 한계 이해 | `ai_usage` | ✓ |
| 건강 데이터 수집 동의 | `health_data` | (백엔드 권한 요청 시점에) |
| 이미지 저장 동의 | `image_storage` | (Camera 첫 사용 시) |
| 알림 동의 | `notifications` | (선택) |
| 마케팅 정보 수신 | (DB에 별도 type 추가 필요) | (선택) |

각 체크 시 `INSERT INTO consents (user_id, type, accepted_at)` 1 row.
취소 시 `revoked_at` 갱신 (행 삭제 X — 감사 추적용).

서버 저장: user_id + type + accepted_at (audit trail).
약관 버전 바뀌면 다음 로그인 시 재동의 화면 (백엔드가 사용자의 미동의 type 체크).

**⑤ 상태 변화**

| 상태 | 화면 |
|------|------|
| Default | 4개 모두 미체크 + Primary 비활성 + 면책 카드 표시 |
| 일부 체크 | Primary 비활성 유지 |
| 필수 3개 체크 | Primary 활성 + 살짝 펄스 (주의 끌기 1회) |
| 자세히 시트 열림 | 풀스크린 BottomSheet, 닫기 버튼 |
| 제출 중 | Primary spinner |
| 서버 에러 | Snackbar + 재시도 |

**⑥ 인터랙션**

- 체크박스 터치 영역 = 행 전체 (48dp 최소)
- "자세히" 클릭 시 햅틱 light
- 모든 필수 체크 후 Primary 활성 시 햅틱 success + 살짝 펄스
- 백 버튼: 다이얼로그 "동의 없이는 가입을 완료할 수 없어요. 그만둘까요?"
- 일괄 동의 버튼 없음 — 사용자가 한 번씩 의식적으로 체크 (다크패턴 방지)

**⑦ 접근성**

- 각 체크박스 semanticLabel: "필수 약관 N: ..."
- 상태 변경 announce: "필수 약관에 동의했어요"
- 면책 카드 liveRegion: false (정적)
- 자세히 BottomSheet 안에 닫기 버튼 키보드 도달 가능

**⑧ 고령자 모드**

- 체크박스 24 → 32dp
- 각 행 높이 56 → 72
- 폰트 16 → 19
- 면책 카드 강조 색 진하게 (pinkLight → 더 진한 pink 30%)

**⑨ 면책·의료법**

- 이 화면 자체가 면책 — 핑크 카드에 표시
- 약관 버전 변경 시 재동의 강제
- 약사법 관련 — "AI는 약 처방을 하지 않으며, 영양제 권고도 의약품 진단을 대체하지 않아요"

**⑩ 분석 이벤트**

- `consent_view`
- `consent_check` (which)
- `consent_uncheck`
- `consent_detail_view` (which)
- `consent_submit_success`
- `consent_abort` (백 버튼)

**⑪ 와이어 → §14.7.W S-05 (기존 번호 + 1)**

**⑫ 결정·메모**

- 일괄 동의 버튼 X — 다크패턴 + 의료 동의는 한 줄씩 의식해야 함
- 핑크 카드 — 빨강은 위협, 핑크는 주의·돌봄. 톤이 부드러움.
- 자세히 BottomSheet — 풀스크린 페이지 이동보다 가벼움. 동의 화면 컨텍스트 유지.

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | "동의" 한 가지 |
| 큰 글씨 큰 터치 | ✓ | 행 56dp, 체크박스 터치 = 행 전체 |
| 면책 | ✓ | 핑크 카드로 강조 — 이 화면이 면책 화면 자체 |
| 다음 액션 | ✓ | "동의하고 시작" Primary |
| 폴백 | ⚠ | **개선 필요** — 약관 서버에서 못 받음 시 캐시된 텍스트 + "최신 약관은 다음 로그인 시" |
| 빠른 학습 | ✓ | "필수/선택" 라벨 명확 |
| 회복 가능 | ✓ | 백버튼 다이얼로그 |

**친화도 빈틈 → 추가 결정**

- 약관 텍스트 BottomSheet에 "쉽게 말하면" 요약 위쪽 — 50대가 법률 문장 부담
- 체크박스 한 번 더 강조 — 필수 미체크 시 살짝 흔들림 (3회 시도 시)
- 동의 후 약관 어디서 확인? → Settings → "이용약관" 항상 접근 가능 안내 caption 하단에

#### S-07 Onboarding (프로필 입력)

**① 정체성**

| 항목 | 값 |
|------|---|
| 화면 ID | S-07 Onboarding |
| 파일 | `screens/onboarding_screen.dart` |
| 목적 | 분석 필수 최소 정보 수집 (성별·나이·키·체중·만성질환·목적) |
| 진입 | Consent 완료 |
| 출구 | `/home` (완료) — 중간 이탈 시 진행도 저장하고 다음 로그인 때 이어서 |

**② 레이아웃**

| 영역 | 내용 |
|------|------|
| AppBar | 좌측 ← + 진행도 "3 / 6" + 우측 "건너뛰기" (선택 단계만) |
| Body | 한 단계 = 한 페이지 — 큰 질문 + 입력 + 도움말 |
| Bottom 고정 | "이전" Ghost + "다음" Primary (마지막은 "시작") |

**6단계 흐름**

| Step | 질문 | 입력 |
|------|------|------|
| 1 | 성별을 알려주세요 | RadioCard 2개 (남/여) + "선택 안 함" |
| 2 | 나이가 어떻게 되세요? | NumberInput + 슬라이더 보조 |
| 3 | 키와 체중을 알려주세요 | NumberInput × 2 (cm/kg) |
| 4 | 관리하고 있는 만성질환이 있나요? | ChipMulti — 당뇨·고혈압·이상지질·갑상선·골다공증·기타 + "없음" |
| 5 | 복용 중인 영양제가 있나요? (선택) | 카메라 진입 또는 "건너뛰기" |
| 6 | 어떤 도움을 받고 싶으세요? | RadioCard 3개 (영양·복약·다이어트) |

**③ UI 컴포넌트**

| 컴포넌트 | 토큰 |
|---------|------|
| Stepper bar | 6개 dot — 현재 brand, 완료 brand 채움, 미완 line |
| 큰 질문 텍스트 | `LemonText.title` 24/800 |
| 도움말 | `LemonText.body` `inkSoft` — 왜 묻는지 한 줄 설명 |
| RadioCard | 56dp 카드 — 좌측 라디오 + 라벨 + 우측 이모지/아이콘 |
| NumberInput | 큰 숫자 + 단위 + 슬라이더 |
| ChipMulti | 16dp pill — 선택 시 brandTint |
| 이전/다음 버튼 | bottom safearea 위 가로 분할 (이전 1 : 다음 2) |

**④ 데이터**

| 필드 | 타입 | 검증 |
|------|------|------|
| gender | enum (male/female/none) | 필수 |
| age | int | 14~100 |
| height_cm | int | 100~220 |
| weight_kg | double | 30~200 |
| conditions[] | list | 0개 가능 (일반 사용자 모드) |
| supplement_photos[] | list | 선택 |
| goal | enum | 필수 |

**⑤ 상태 변화**

| 상태 | 화면 |
|------|------|
| Step Default | 입력 빈 상태 + 다음 비활성 |
| 입력 | 다음 활성 |
| 마지막 Step | "시작" 라벨 변경 + spinner on submit |
| 제출 중 | "프로필을 만들고 있어요..." + Loading 카드 |
| 서버 에러 | 다이얼로그 + 재시도 |
| 중간 이탈 | localStorage 진행도 저장 (다음 로그인 시 "이어서 하기" 카드) |

**⑥ 인터랙션**

- 스와이프 좌우로 단계 이동 (가능 시) — 단, 입력 안 한 다음 단계로는 못 감
- 슬라이더 햅틱 — 25/50/75/100 지점에서 light
- 키보드 단계: 숫자 입력 시 자동 done → 다음 활성화 시 자동 진행
- 백버튼: 직전 단계로 / Step 1에서 백 = 다이얼로그
- 모션: 단계 전환 슬라이드 200ms easeInOut

**⑦ 접근성**

- 진행도 announce: "3단계 중 6단계"
- 모든 입력 semanticLabel + hintText
- RadioCard 활성 상태 announce

**⑧ 고령자 모드**

- RadioCard 56 → 72
- 폰트 24 → 28 (질문)
- ChipMulti 36 → 48
- 슬라이더 thumb 24 → 32

**⑨ 면책·의료법**

- Step 5 "복용 중인 영양제" 위에 caption — "사진은 분석 참고용으로만 사용해요. 처방 정보가 아니에요."
- Step 4 "만성질환" 위에 caption — "이 정보는 영양 권고 정확도를 높이는 데만 써요. 진단 정보가 아니에요."

**⑩ 분석 이벤트**

- `onboarding_view` (step)
- `onboarding_step_complete` (step, value_summary)
- `onboarding_back` (from_step)
- `onboarding_skip` (which_optional)
- `onboarding_complete` (총 소요시간)
- `onboarding_abort` (마지막 step)

**⑪ 와이어 → §14.7.W S-06**

**⑫ 결정·메모**

- 6단계가 많다 vs 적다 — 한 페이지 몰아넣으면 50대 답답함. 6단계는 한 단계당 한 질문 = 부담 X.
- 만성질환 "없음" 명시적 옵션 — 일반 사용자도 명확히 선택. 빈 채로 넘어가면 의도 불명확.
- Step 5 카메라 — 영양제 인식 OCR 흐름의 첫 노출. 이때 사용해보면 앱 활용도 ↑

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | 단계당 질문 1개 |
| 큰 글씨 큰 터치 | ✓ | RadioCard 56dp, 질문 폰트 24 |
| 면책 | ✓ | Step 4·5 caption |
| 다음 액션 | ✓ | "다음" 1개 |
| 폴백 | ⚠ | **개선 필요** — 중간 이탈 시 진행도 저장 (이미 명세), 서버 fail 시 로컬 저장 후 재시도 |
| 빠른 학습 | ⚠ | **개선 필요** — Step 1 "성별 왜 물어요?" 도움말 한 줄 (50대 거부감 ↓) |
| 회복 가능 | ✓ | 이전 단계로 자유롭게 이동 |

**친화도 빈틈 → 추가 결정**

- 각 단계마다 "왜 묻나요?" 도움말 한 줄 (50대 사생활 우려 해소) — 예: "성별별 권장량이 달라요"
- 만성질환 선택 화면에 "선택 안 해도 돼요" 명시 — 부담 ↓
- Step 5 (카메라) 건너뛰기 강조 — "지금 안 해도 나중에 가능해요"
- 마지막 Step에서 "수정하기" 링크 — 이전 단계로 점프 가능

#### S-08 Dashboard (Home)

**① 정체성**

| 항목 | 값 |
|------|---|
| 화면 ID | S-08 Dashboard |
| 파일 | `screens/dashboard_screen.dart` |
| 목적 | 오늘의 상태 한눈에 + 빠른 액션 + 응모권 누적 |
| 진입 | 인증 완료 / BottomNav 탭 1 / 화면 어디서든 홈 버튼 |
| 출구 | `/camera` `/health` `/chat` `/raffle` `/score` (분석 카드 클릭) `/settings` |

**② 레이아웃**

| 영역 | 내용 |
|------|------|
| AppBar | 좌측 ☰ (메뉴) + 가운데 "Lemon Aid" + 우측 알림 🔔 / 프로필 👤 |
| Body | ScrollView — 5개 카드 세로 스택 |
| BottomNav | 5탭 — 홈 활성 |
| FAB | 우하단 카메라 아이콘 (응모권 적립 진입점) |

**카드 5개 (위에서 아래)**

| 순서 | 카드 | 컬러 | 콘텐츠 |
|-----|------|-----|--------|
| 1 | Today Card | Blue Card | 오늘 날짜 + 격려 한 줄 + 충족률 % |
| 2 | Nutrient Bar 3개 | bgElev | 단백 / 탄수 / 핵심 결핍 영양소 |
| 3 | Quick Action 2×2 | 4컬러 | 사진+ / 약먹기+ / 물+ / 체중+ |
| 4 | 응모권 배너 | Lemon Card | 누적 수 + 다음 단계 게이지 |
| 5 | 최근 분석 (있을 때만) | bgElev | 사진 thumbnail + 결과 요약 |

**③ UI 컴포넌트**

| 컴포넌트 | 토큰 |
|---------|------|
| Today Card | brandSoft 배경 / brand 액센트 / radius 16 / padding 16 |
| 날짜 | "2026년 5월 11일 화요일" `LemonText.caption` `inkSoft` |
| 격려 | "잘 챙기고 있어요" `LemonText.subheading` `ink` |
| 충족률 큰 숫자 | "78%" `display` (32/800) `brand` |
| 부제 | "오늘 영양 충족률" `caption` `inkMute` |
| Nutrient Bar | 12dp 높이 + 라벨 좌측 + 5단계 색 + 수치 우측 |
| Quick Action 카드 | 2×2 그리드 / 80dp 정사각 / 각 카드 색 다름 (citrusLight/skyLight/pinkLight/greenLight) |
| QA 아이콘 | 32dp 채움 / 카드 액센트 색 |
| QA 라벨 | `LemonText.body` 14/600 |
| 응모권 배너 | citrusLight 배경 + 우측 노란 레몬 캐릭터 (반신) + "3장" 큰 숫자 + 게이지 |
| 게이지 | 8dp 두께 + radius pill + citrus 채움 |
| 최근 분석 카드 | 좌측 thumbnail 64dp + 우측 텍스트 (시간·요약·점수) |
| FAB | 56dp brand 솔리드 + 카메라 아이콘 흰색 + shadow.md |

**④ 데이터**

| 필드 | 출처 |
|------|------|
| today_summary | API `/dashboard/today` |
| nutrient_fulfillment | 최근 24시간 합산 |
| raffle_total | 응모권 누적 |
| raffle_next_milestone | 1일/7일/30일 다음 단계 |
| recent_analysis | 최근 7일 5출력 |

**⑤ 상태 변화**

| 상태 | 화면 |
|------|------|
| Empty (첫 진입, 데이터 0) | Today Card "사진 한 번 찍어보세요" CTA + Nutrient 회색 + Quick Action만 활성 |
| Loading | 5개 카드 모두 Skeleton (shimmer 200ms loop) |
| Normal | 모든 카드 데이터 |
| 부분 데이터 | 데이터 있는 카드만 표시, 없는 건 회색 placeholder |
| Pull-to-refresh | 인디케이터 + API 재호출 |
| Error | 카드별 "재시도" 버튼 (전체 fail X) |
| 오프라인 | 상단 배너 "오프라인 — 마지막 동기화 N분 전" + 캐시 표시 |

**⑥ 인터랙션**

- Pull-to-refresh — 위에서 아래로 80dp 끌면 새로고침
- Today Card 탭 → Score (오늘 자세히)
- Nutrient Bar 탭 → Score (해당 영양소 자세히)
- Quick Action 탭 → 해당 입력 화면
- 응모권 배너 탭 → Raffle
- 최근 분석 탭 → Score (그 분석)
- FAB 탭 → Camera
- BottomNav 탭 → 각 화면
- 스크롤 시 AppBar elevation 0 → 1
- 모션: 카드 entry 시 페이드+슬라이드up 200ms (stagger 80ms)

**⑦ 접근성**

- 충족률 큰 숫자 semanticLabel: "오늘 영양 충족률 78퍼센트"
- Nutrient Bar semanticLabel: "단백질 78%, 충분"
- FAB semanticLabel: "사진으로 영양 분석 시작"
- BottomNav 활성 탭 announce

**⑧ 고령자 모드**

- 충족률 숫자 32 → 40
- Quick Action 카드 80 → 96
- FAB 56 → 64
- 카드 padding 16 → 20
- "최근 분석" thumbnail 64 → 80

**⑨ 면책·의료법**

- Today Card 하단 caption — "참고용 정보예요"
- 분석 결과 카드 자세히 들어가면 면책 배너 (Score 화면에서 처리)

**⑩ 분석 이벤트**

- `dashboard_view` (session count)
- `dashboard_card_tap` (which)
- `dashboard_fab_tap`
- `dashboard_refresh`
- `dashboard_empty_cta_tap` (첫 진입)
- `dashboard_offline_view`

**⑪ 와이어 → §14.7.W S-07**

**⑫ 결정·메모**

- Today Card 큰 % 숫자 — 50대 첫 눈에 "잘하고 있나?" 답 가능
- Quick Action 2×2 — 4탭 한 화면 (스크롤 X)
- 응모권을 5번째 카드가 아닌 4번째 — 매일 보이는 보상이 동기부여 ↑
- FAB는 카메라 — 앱 핵심 액션 = 사진. 다른 후보(챗봇)는 BottomNav에 있음.

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | "오늘 상태 확인" 메인 + 카메라 진입 보조 |
| 큰 글씨 큰 터치 | ✓ | 큰 % 숫자 32, FAB 56dp |
| 면책 | ✓ | Today Card caption |
| 다음 액션 | ✓ | FAB 카메라 = 가장 시각적 강조 |
| 폴백 | ✓ | 오프라인 배너 + 캐시 / 부분 데이터만 표시 |
| 빠른 학습 | ⚠ | **개선 필요** — Empty 상태 첫 진입 시 가이드 1회 ("사진 한 번이면 5가지 결과를 보여드려요") |
| 회복 가능 | — | 위험 액션 없음 |

**친화도 빈틈 → 추가 결정**

- 첫 진입 사용자 Empty Today Card에 "30초 만에 시작하기" CTA + 큰 카메라 아이콘
- Pull-to-refresh 안내 한 번 (상단에서 손가락 아이콘 1.2s 데모 모션)
- Quick Action "약먹기" 탭 시 약 추가 화면 (v2 — MVP는 알림으로 폴백)
- 응모권 배너에 누적 변화 강조 — 어제 2장 → 오늘 3장이면 "+1" 표시 (작은 동기부여)

#### S-09 Camera

**① 정체성**

| 항목 | 값 |
|------|---|
| 화면 ID | S-09 Camera |
| 파일 | `screens/camera_screen.dart` |
| 목적 | 영양제·식단·검진지·체중계 사진 한 번에 — 앱 핵심 입력 |
| 진입 | Dashboard FAB / QuickAction "사진" / Onboarding Step 5 / Health 수동입력 |
| 출구 | Score (분석 시작) / 이전 (취소) |

**② 레이아웃**

| 영역 | 내용 |
|------|------|
| AppBar | 없음 (immersive 카메라 풀스크린) |
| 상단 좌측 | ✕ 닫기 (40dp 검정 원 위 흰 X) |
| 상단 우측 | 💡 플래시 토글 |
| Body (풀스크린) | 카메라 프리뷰 + 중앙 가이드 박스 |
| 하단 1 | CategoryChip 4종 (영양제/식단/검진지/체중) 가로 스크롤 |
| 하단 2 | 좌: 갤러리 thumbnail / 가운데: 셔터 72dp / 우: 전후면 전환 |

**③ UI 컴포넌트**

| 컴포넌트 | 토큰 |
|---------|------|
| 카메라 프리뷰 | 풀스크린 + 위·아래 검정 오버레이 (정사각형 가이드) |
| 가이드 박스 | 흰 라운드 사각 (1.5dp 라인) — 카테고리별 비율 다름 |
| 카테고리 라벨 | 박스 위 흰 텍스트 + 어두운 배경 — "영양제 라벨이 보이게 찍어주세요" |
| CategoryChip | 검정 30% 배경 + 흰 라벨 + 선택 시 brand 배경 |
| 셔터 | 72dp 흰 원 + 내부 64dp brand 원 + tap 시 scale 0.9 (80ms) |
| 갤러리 thumbnail | 48dp + 라운드 8 + 최근 사진 1장 미리보기 |
| 플래시 토글 | 32dp 흰 아이콘 + 활성 시 citrus |

**카테고리별 가이드 박스 비율**

| 카테고리 | 비율 | 가이드 텍스트 |
|---------|------|-------------|
| 영양제 | 4:3 가로 | "라벨이 잘 보이게" |
| 식단 | 1:1 정사각 | "음식 전체가 들어오게" |
| 검진지 | A4 비율 | "표 영역이 모두 보이게" |
| 체중 | 16:9 가로 | "숫자가 잘 보이게" |

**④ 데이터** (PG.md §11.2 Supplement·Meal + §11.3 AnalysisResult 일치)

- 출력 페이로드: `image` (jpeg, 1080p 압축), `category` ('supplement'|'meal'|'checkup'|'weight'), `captured_at`
- 권한: CAMERA, READ_EXTERNAL_STORAGE
- 분석 흐름 (PG.md 확정 — 4 Agent X / 알고리즘):
  1. **OCR + 라벨링** (영양제 라벨 사진 → 텍스트)
  2. **CSV DB 매칭** (`SupplementCsvImport` 우선 — 식약처·농진청)
  3. **API 보조** (CSV에 없으면 외부 API)
  4. **Pydantic 스키마 강제** (`SupplementParseResult`)
- 저장: 분석 완료 후 `Supplement` + `SupplementIngredient` insert / `Meal.foods` jsonb 저장
- 출처 표시 안 함 (PG.md 결정 — 챗봇 안에서만)
- 로컬 24시간 캐시 (재분석용)

**⑤ 상태 변화**

| 상태 | 화면 |
|------|------|
| 권한 미요청 | 권한 요청 화면 (Material 표준) |
| 권한 거부 | 풀스크린 안내 + "설정에서 권한 허용" 버튼 + "갤러리만 사용" Ghost |
| Ready | 프리뷰 + 셔터 활성 |
| Capturing | 셔터 0.9 scale + 화면 흰 플래시 80ms |
| Captured | 미리보기 풀스크린 + "다시 찍기" Ghost + "분석 시작" Primary (둘 다 하단) |
| Uploading | 미리보기 + "사진 업로드 중... 30%" 진행바 |
| 분석 시작 | Score 화면으로 이동 (back stack에서 제거) |
| 갤러리 모드 | 카메라 프리뷰 영역 → 그리드 갤러리 |

**⑥ 인터랙션**

- 카테고리 좌우 스와이프 / 탭 — 가이드 박스 크기 즉시 변경
- 셔터 long-press → 연속 촬영 X (오작동 방지)
- 핀치 줌 (가능 시)
- 갤러리 thumbnail 탭 → 시스템 갤러리 열기 + 다중 선택 가능 (최대 5장)
- 햅틱: 셔터 success / 카테고리 변경 light
- 백버튼: 다이얼로그 없이 즉시 닫기 (촬영 안 함)

**⑦ 접근성**

- 셔터 semanticLabel: "사진 촬영" + hint "두 번 탭"
- 카테고리 semanticLabel: "영양제 카테고리 선택됨"
- 플래시 semanticLabel: "플래시 켜기/끄기"
- TalkBack 모드 시 음성 안내 "라벨이 잘 보이는지 확인 후 촬영해주세요"

**⑧ 고령자 모드**

- 셔터 72 → 96
- CategoryChip 36 → 48
- 가이드 텍스트 16 → 20
- 후면 카메라 자동 선택 + 자동 초점 우선

**⑨ 면책·의료법**

- 카테고리 "검진지" 선택 시 상단 배너 — "이 사진은 분석 참고용이에요. 의료 결정은 의사와 상의해주세요."
- 카테고리 "영양제" 선택 시 caption — "사진은 처방 정보가 아니에요"
- 의약품 식별 시 단호한 거부 메시지 (백엔드 모델 분리)

**⑩ 분석 이벤트**

- `camera_view` (entry_point)
- `camera_permission_grant` / `deny`
- `camera_category_select` (which)
- `camera_capture`
- `camera_retake`
- `camera_gallery_select`
- `camera_submit` (category)
- `camera_close` (방법)

**⑪ 와이어 → §14.7.W S-08**

**⑫ 결정·메모**

- 단일 카메라 → 4카테고리 한 화면 — 각자 화면 분리하면 50대가 헤맴. 가이드 박스로 시각 구분.
- 셔터 72dp — Material 가이드 56dp보다 큼. 핵심 액션이라 강조.
- 분석 시작 = Score로 즉시 이동 — "기다리세요" 화면 따로 안 만들고 Score에서 스트리밍 카드.

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | "사진 찍기" |
| 큰 글씨 큰 터치 | ✓ | 셔터 72dp, CategoryChip 36dp |
| 면책 | ✓ | 검진지/영양제 모드별 caption |
| 다음 액션 | ✓ | 셔터 = 가장 큰 액션 |
| 폴백 | ✓ | 권한 거부 → 갤러리 모드 / OCR 실패 → 수동 입력 |
| 빠른 학습 | ✓ | 가이드 박스 + 카테고리별 텍스트 |
| 회복 가능 | ✓ | "다시 찍기" 무한 가능 |

**친화도 빈틈 → 추가 결정**

- 첫 카메라 진입 시 1회 코칭 — "라벨이 보이게 찍어주세요" 박스 위 화살표 모션 (3초 후 자동 사라짐)
- 흔들림 감지 → "조금 더 가만히 찍어주세요" 안내 (자이로 활용)
- 어두운 환경 감지 → 자동 플래시 권유 안내
- 갤러리 다중 선택 시 최대 5장 안내 + 초과 시 알림
- 분석 중 백버튼 = 분석 취소 다이얼로그 (잘못 누름 방지)

#### S-10 Score (5출력 분석 결과)

**① 정체성**

| 항목 | 값 |
|------|---|
| 화면 ID | S-10 Score |
| 파일 | `screens/score_screen.dart` |
| 목적 | AI 분석 5종 카드 표시 — 앱의 핵심 가치 |
| 진입 | Camera 분석 시작 / Dashboard 최근 분석 카드 / Chat 답변에서 |
| 출구 | Chat (자세히 묻기) / Camera (다시 분석) / 공유 / 저장 |

**② 레이아웃**

| 영역 | 내용 |
|------|------|
| AppBar | 좌측 ← + 가운데 "분석 결과" + 우측 📤 공유 / ⋯ |
| Body | ScrollView — 5개 카드 stagger entry + 면책 배너 |
| Bottom 고정 | Primary "더 알아보기" (챗봇 자동 질문) + Ghost "저장" |

**5출력 카드 (PG.md §7.2)**

| ID | 카드 | 컬러 | 핵심 표시 |
|----|------|-----|----------|
| ① | 영양소 충족률 | Blue Card | 5단계 NutrientBar × 6~8개 |
| ② | 결핍 진단 (5단계) | Pink Card | "칼슘 결핍 가능성" + 권고 1줄 |
| ③ | 식단 권고 | Green Card | "저녁: 두부 100g 추가" + 식품 3개 |
| ④ | 체중 예측 (1주/1개월/3개월) | Sky Card | 3개 수치 + 그래프 |
| ⑤ | 활동 점수 v4 | Lemon Card | 72/100 + 어제 대비 +4 |

**③ UI 컴포넌트**

| 컴포넌트 | 토큰 |
|---------|------|
| 카드 공통 | radius 16 / padding 16 / shadow.sm / 좌측 4dp 액센트 바 |
| 카드 헤더 | 라벨 "① 영양소 충족률" `LemonText.subheading` |
| 카드 본문 | `LemonText.body` 16/400 |
| 핵심 수치 | `LemonText.bodyEmphasis` 17/700 |
| 결핍·권고 강조 | accent 색 단어 (예: "칼슘") |
| 그래프 (체중 예측) | fl_chart line + 3개 dot |
| 면책 배너 | 카드 5개 끝나고 하단 — pink card 배경 + 아이콘 + 텍스트 |
| Primary "더 알아보기" | brand 52dp |
| Ghost "저장" | brand outline 52dp |

**④ 데이터**

| 카드 | 입력 → 출력 |
|------|-----------|
| ① | 사진/만성질환/프로필 → 영양소 충족률 dict |
| ② | 충족률 → 결핍 5단계 + 권고 1줄 |
| ③ | 결핍 + 사용자 식습관 → 식품 3개 + 시간대 |
| ④ | BMR + 활동 + 섭취 → 7-step 체중 |
| ⑤ | 걸음 + 심박 + 만성질환 → v4 점수 |

**⑤ 상태 변화**

| 상태 | 화면 |
|------|------|
| 분석 시작 (Camera에서 진입) | 상단 progress 0~100% + 카드 5개 Skeleton |
| 카드 시퀀셜 등장 | ①부터 순서대로 entry 400ms (stagger 200ms) |
| 모든 카드 도착 | bottom button 활성 + 햅틱 success |
| 일부 출력 누락 | 회색 placeholder + "이 카드는 데이터가 부족해요" |
| 전체 실패 | 풀스크린 에러 + "다시 시도" + "수동 입력" |
| Rate limit 도달 | "오늘 분석 한도 초과 (5/일). 내일 다시 시도" + Primary 비활성 |
| 캐시된 결과 (재진입) | 즉시 모든 카드 (entry 없이) |

**⑥ 인터랙션**

- 카드 탭 → 각 카드 상세 (BottomSheet) — 자세한 표·근거·관련 질문
- 카드 long-press → 공유 메뉴 1개
- 그래프 dot 탭 → 툴팁
- "더 알아보기" 탭 → Chat 화면 + 자동 첫 메시지 (카드 컨텍스트 전달)
- 위에서 아래로 스크롤 시 헤더 elevation 0 → 1
- Pull-to-refresh 비활성 (이미 받은 분석, 재분석은 Camera로)
- 모션: 카드 entry curveEntry 400ms — 부드럽게 위에서 내려옴

**⑦ 접근성**

- 각 카드 semanticLabel: "1번 카드. 영양소 충족률. 단백질 충분..."
- NutrientBar 텍스트 우선 (색맹 대응)
- 그래프 — 대체 텍스트로 수치 3개 읽음
- 면책 배너 liveRegion: false (정적이지만 항상 보이게)

**⑧ 고령자 모드**

- 카드 padding 16 → 20
- 핵심 수치 17 → 22
- 카드 간 간격 12 → 20
- 5출력 한 카드씩 보기 (스와이프 캐러셀) 옵션 — Settings에서 토글
- Primary 52 → 60

**⑨ 면책·의료법 (이 화면이 핵심)**

- 모든 카드 하단 caption — "참고용 정보예요"
- 면책 배너 (5장 끝) — pink card + ⚠ + "이 결과는 의료 진단이나 처방이 아니에요. 의료 결정은 의사·약사와 상의해주세요." 
- 결핍 카드(②)에 약 이름 X — 영양소·식품 이름만
- 식단 권고(③)는 영양 측면 — "치료" 표현 X
- 체중 예측(④) caption — "현재 패턴 유지 가정 — 의료 진단 아님"
- 활동 점수(⑤) caption — "건강한 활동 측면 — 운동 처방 아님"

**⑩ 분석 이벤트**

- `score_view` (entry_point, has_cache)
- `score_card_view` (which) — 가시 영역 확인
- `score_card_tap` (which)
- `score_chat_cta` — Chat으로 갈 때
- `score_share` (method)
- `score_save`
- `score_retry`

**⑪ 와이어 → §14.7.W S-09**

**⑫ 결정·메모**

- 5장 한 화면 vs 한 장씩 — 한 화면이 "사진 한 번 → 다 보임" 가치 명확. 50대 모드만 한 장씩.
- 카드 컬러 다섯 가지 — 정보 위계가 색으로 즉시 구분. 건강의신 패턴 추종.
- 면책을 5장 끝에 큰 카드로 — 카드마다 작게 넣으면 시각 노이즈. 한 번에 강조.
- 체중 예측 그래프 — fl_chart 가장 가벼움. Plotly·D3 과함.

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | "분석 결과 확인" |
| 큰 글씨 큰 터치 | ✓ | 카드 padding 16, 핵심 수치 17/700 |
| 면책 | ✓ | 5장 끝 + 각 카드 caption |
| 다음 액션 | ✓ | "더 알아보기" Primary |
| 폴백 | ✓ | 부분 출력만 표시 / Rate limit 시 명시 |
| 빠른 학습 | ⚠ | **개선 필요** — 5출력의 의미 첫 진입 시 1회 안내 (각 카드 한 줄 설명 BottomSheet) |
| 회복 가능 | ✓ | "다시 분석" 가능 |

**친화도 빈틈 → 추가 결정**

- 첫 분석 결과 화면에 "이 화면이 처음이에요?" 작은 도움말 → BottomSheet "5종 카드 한 줄 설명"
- 카드 long-press = 공유 — 50대에 long-press 학습 부담. **변경: 우측 ⋯ 아이콘으로 명시**
- "더 알아보기" 챗봇 이동 시 컨텍스트 자동 전달 — 어떤 카드 보고 가는지 챗봇이 알게
- 결과 저장 — 자동 저장 (서버) + 명시적 "저장" 버튼은 즐겨찾기 표시 역할
- "공유" 시 의료법 면책 자동 첨부 — 사용자 외 누군가에게 전달 시 오해 방지

#### S-11 Health (건강 데이터)

**① 정체성**

| 항목 | 값 |
|------|---|
| 화면 ID | S-11 Health |
| 파일 | `screens/health_screen.dart` |
| 목적 | 걸음수·심박·체중·수면 트래킹 |
| 진입 | BottomNav 탭 2 / Dashboard "건강" 카드 |
| 출구 | Score (v4 활동점수 자세히) / Settings (권한) / Camera (체중계 사진) |

**② 레이아웃**

| 영역 | 내용 |
|------|------|
| AppBar | 좌측 ← + 타이틀 "건강" + 우측 ⚙ |
| 상단 | Period Chip 3개 (7일/30일/90일) — 기본 7일 |
| Body | ScrollView — 차트 카드 4개 (걸음/심박/체중/수면) |
| BottomNav | 활성 |
| FAB | "+ 수동 입력" |

**③ UI 컴포넌트**

| 컴포넌트 | 토큰 |
|---------|------|
| Period Chip | pill 36dp · 선택 시 brandTint |
| 차트 카드 | bgElev radius 16 padding 16 shadow.sm |
| Chart | fl_chart line/bar — 각 카드 200dp 높이 |
| Chart 색 | 항목별 — 걸음 brand / 심박 pink / 체중 sky / 수면 deepBlue |
| Stat 행 | 3분할 — 오늘 / 평균 / 목표 대비 |
| 큰 수치 | bodyEmphasis 17/700 |
| 라벨 | caption inkMute |
| FAB | brand 56dp + "+" 아이콘 |

**4종 카드**

| 카드 | 메인 수치 | 보조 | 시각화 |
|------|---------|------|--------|
| 걸음 | 오늘 6,234보 | 평균 5,820 / 목표 8,000 | 7일 bar chart |
| 심박 | 휴식 68 bpm | 평균 / 최대 | line chart |
| 체중 | 68.5 kg | 1주 -0.3 / 1개월 -0.8 | line chart |
| 수면 | 7시간 12분 | 평균 / 깊은 % | bar chart |

**④ 데이터**

| 필드 | 출처 |
|------|------|
| steps[] | health 패키지 (**iOS HealthKit 우선 확정** — PG.md / Android Health Connect 검토 예정) |
| heart_rate[] | health 패키지 |
| weight[] | 수동 입력 또는 체중계 사진 OCR |
| sleep[] | health 패키지 |
| date_range | 7/30/90일 |

**⑤ 상태 변화**

| 상태 | 화면 |
|------|------|
| 권한 미요청 | 풀스크린 CTA — "Lemon Aid가 건강 데이터를 읽도록 허락해주세요" + 권한 버튼 |
| 권한 거부 | 카드별 "허용 안 됨 — 권한 다시 요청 / 수동 입력만" |
| 데이터 OK | 4개 카드 모두 표시 |
| 일부 데이터 없음 | 해당 카드만 "데이터가 없어요 — 수동 입력" CTA |
| 신규 사용자 (첫 진입) | 첫 카드만 안내 카드 — "휴대폰에서 걸음을 기록하면 자동으로 보여요" |
| 오프라인 | 캐시 데이터 + "오프라인" 배너 |

**⑥ 인터랙션**

- Period Chip 탭 → 차트 4개 모두 즉시 갱신
- 차트 dot tap → 툴팁 (날짜·수치)
- 차트 pinch → 줌 (가능 시)
- Pull-to-refresh — 헬스 데이터 재동기
- FAB → 수동 입력 BottomSheet (걸음/심박/체중/수면 선택 후 숫자)
- 햅틱: Period 변경 light / FAB success / 수동 입력 저장 success
- 모션: Period 전환 시 차트 재그리기 320ms easeInOut

**⑦ 접근성**

- 차트 대체 텍스트 — "최근 7일 평균 걸음 5,820. 오늘 6,234"
- Period Chip 활성 상태 announce
- 수치 + 라벨 병기 (색맹 대응)

**⑧ 고령자 모드**

- 차트 카드 4개 → 2개씩 페이지 (캐러셀)
- 차트 높이 200 → 240
- 수치 큰 글씨 17 → 22
- 수동 입력 BottomSheet — 한 항목씩 풀스크린

**⑨ 면책·의료법**

- 심박 카드 caption — "참고용이에요. 이상 증상은 의료기관에"
- 체중 카드 caption — "건강 관리 측면 — 의료 진단이 아니에요"
- 수면 카드 caption — "참고용이며 수면 장애 진단이 아니에요"

**⑩ 분석 이벤트**

- `health_view`
- `health_period_change` (which)
- `health_card_tap` (which)
- `health_permission_request` / `grant` / `deny`
- `health_manual_input` (type)
- `health_chart_tooltip` (which, date)

**⑪ 와이어 → §14.7.W S-10**

**⑫ 결정·메모**

- 카드 4종이지만 우선순위 걸음 → 심박 → 체중 → 수면. 만성질환 50대에 걸음·심박이 가장 의미.
- 권한 거부 폴백 = 수동 입력 — 50대는 권한 거부율 높음. 절대 막힘 X.
- 체중 OCR 카메라 진입 — Camera 카테고리 "체중"으로.

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | "건강 추이 확인" |
| 큰 글씨 큰 터치 | ✓ | 차트 200dp, FAB 56dp |
| 면책 | ✓ | 각 카드 caption |
| 다음 액션 | ✓ | "+ 수동 입력" FAB |
| 폴백 | ✓ | 권한 거부 → 수동 / 데이터 없음 → 안내 |
| 빠른 학습 | ⚠ | **개선 필요** — 첫 진입 시 권한 허용 안내 + 왜 필요한지 한 줄 |
| 회복 가능 | ✓ | 수동 입력 수정/삭제 가능 |

**친화도 빈틈 → 추가 결정**

- 권한 요청 화면 — "허락하면 자동으로 걸음을 보여드려요. 거절해도 수동 입력 가능해요" 두 옵션 동등하게
- 차트 아래 caption — "이 데이터는 본인만 봐요. 외부 공유 안 해요" (개인정보 안심)
- 큰 변동 감지 (체중 1주 -2kg 등) → 부드러운 알림 "최근 변화가 커요. 의료기관 상의가 도움될 수 있어요"
- 수동 입력 시 단위 명확 — kg/bpm/시간 라벨 큰 글씨

#### S-12 Chat (AI Agent 챗봇 — 앱 핵심)

**① 정체성**

| 항목 | 값 |
|------|---|
| 화면 ID | S-12 Chat |
| 파일 | `screens/chat_screen.dart` |
| 목적 | 영양·복약 질문 → **`chat` Agent** 답변 (PG.md §7.5 — 3개 Agent 중 하나) |
| 진입 | BottomNav 탭 3 / Score "더 알아보기" / Dashboard 빠른 액션 |
| 출구 | Score (분석으로) / Camera (사진 권유 시) / 이전 |

**Agent 구조 (PG.md §7.5 확정 — 분석은 Agent 아님)**

| Agent | 역할 | 우리 화면 |
|-------|------|--------|
| (알고리즘) | OCR + CSV DB + Pydantic 매칭 (분석) | Camera → Score 흐름 |
| `personalization` | 사용자 맥락 기반 권고 생성 | Score 5출력 |
| `chat` | 자유 대화 (이 화면) | S-12 Chat ← 여기 |
| `evaluation` | 결과 평가 + 코멘트 | DailyScore.agent_comment |

→ Score 5출력에서 "더 알아보기" 누르면 `chat` Agent에 컨텍스트 + AnalysisResult 같이 전달 (PG.md §11.3).

**② 레이아웃**

| 영역 | 내용 |
|------|------|
| AppBar | 좌측 ← + 가운데 레몬 캐릭터 아이콘 + "AI 어시스턴트" + 우측 🗑 |
| 상단 고정 배너 | 면책 — pink card 작게 — "의료 진단·처방이 아니에요" |
| Body | ScrollView (역방향) — ChatBubble 리스트 |
| 하단 추천 질문 | 입력바 위 — Chip 가로 스크롤 (3~5개) |
| 입력바 하단 고정 | TextField + 🎤 + ⏵ 전송 버튼 |

**③ UI 컴포넌트**

| 컴포넌트 | 토큰 |
|---------|------|
| 면책 배너 | pinkLight 배경 + ⚠ 아이콘 (16dp) + 텍스트 caption / 닫기 X 없음 (항상) |
| Bot Bubble | 좌측 정렬 / 좌측 32dp 레몬 캐릭터 아바타 / 본문 brandSoft 배경 / radius 16 (좌상 4dp 꼬리) |
| User Bubble | 우측 정렬 / brand 배경 / 본문 흰색 / radius 16 (우상 4dp 꼬리) |
| System Bubble | 가운데 정렬 / 회색 caption / 시간 표시 |
| Streaming | Bot Bubble 안에서 ●●● dot 200ms blink loop |
| SuggestedChip | brandSoft 배경 + brand 텍스트 + radius pill + 36dp 높이 |
| 입력바 | bgElev + 상단 라인 1dp + padding 8 |
| TextField | radius 24 (pill) + filled brandSoft + 우측 마이크/전송 56dp |
| 마이크 | inkMute → 녹음 중 brand pulse |
| 전송 | brand 채워진 원 + 입력 없으면 회색 |

**④ 데이터** (PG.md §11.3 AgentRun · AgentMemory 일치)

| 필드 | 타입 | 백엔드 매핑 |
|------|------|----------|
| messages[] | {id, role: user/bot/system, content, ts, citations[]?} | (메모리 — 세션 종료 시 요약을 AgentMemory.summary 로 저장) |
| suggested_questions[] | 컨텍스트 기반 추천 (Score AnalysisResult 참고) | `chat` Agent 시스템 프롬프트 |
| context | 최근 AnalysisResult + Profile + chronic_diseases (AES-256) | DB 조회 + LLM 컨텍스트 주입 |
| streaming_buffer | 실시간 token 누적 | SSE 스트림 |
| run_id | `AgentRun.id` | 매 메시지 호출당 1 row (성공/실패/비용 기록) |

**출처 표시 — 챗봇 안에서만** (PG.md 결정):
- Bot Bubble 메시지 끝에 `citations[]` 있으면 작은 chip으로 표시 ("식약처", "농진청", "KDRIs 2020")
- Score 화면엔 출처 표시 X
- 출처 chip 클릭 시 → BottomSheet "출처 정보" (URL/문서명/접근일)

**⑤ 상태 변화**

| 상태 | 화면 |
|------|------|
| Empty (첫 진입) | 안내 메시지 + SuggestedChip 5개 ("칼슘 결핍이래요" "비타민 D 어떻게 챙겨요" 등) |
| 메시지 입력 중 | 전송 버튼 활성 + 글자수 카운터 (450/500부터) |
| 전송 직후 | User Bubble 즉시 표시 + Bot Bubble Skeleton + Streaming dot |
| Streaming | Bot Bubble 안 텍스트 token 단위 표시 |
| 답변 완료 | SuggestedChip 갱신 + 햅틱 light |
| Rate limit 분당 5회 초과 | Snackbar "잠시 후 다시 시도해주세요" + 전송 비활성 60초 |
| 의료 진단 질문 감지 | Bot Bubble — "이건 의료기관에 문의해주세요" + Disclaimer 카드 강조 |
| 약 처방 질문 | 단호하게 거절 + Disclaimer + 의료법 안내 |
| Network 에러 | Bot Bubble 자리에 "다시 시도" 버튼 |
| 일일 한도 (50회) | "오늘 한도 도달 — 내일 다시" |

**⑥ 인터랙션**

- 메시지 long-press → 복사 / 공유 / 신고
- Streaming 중 정지 — 입력바 X 버튼 (전송 자리 임시) → 즉시 중단
- SuggestedChip 탭 → 자동 전송
- 마이크 탭 → 음성 입력 (Web Speech API 또는 시스템) — 50대 친화
- 키보드 enter → 전송 (멀티라인은 shift+enter)
- 스크롤 위로 → 이전 메시지 페이지네이션
- 햅틱: 전송 light / 답변 완료 success / 에러 medium
- 모션: Bubble entry 슬라이드up + fade 200ms

**⑦ 접근성**

- ChatBubble role 명시 — TalkBack "사용자 메시지: ..." / "AI 메시지: ..."
- Streaming 시 점진적 announce X (완료 후 한 번에 읽음)
- SuggestedChip semanticLabel: "추천 질문: 칼슘 결핍이래요. 두 번 탭하여 전송"
- 마이크 권한 거부 시 알림 메시지

**⑧ 고령자 모드**

- 본문 16 → 19
- 입력바 56 → 64
- SuggestedChip 36 → 48
- 마이크 우선 안내 — "음성으로도 물어볼 수 있어요" 첫 진입 시 1회
- 추천 질문 5개 → 3개로 줄임 (인지 부담)

**⑨ 면책·의료법 (이 화면이 가장 민감)**

- 상단 배너 항상 표시 (스크롤 무관)
- 모든 Bot 메시지 끝에 caption — "참고용이에요"
- 의료 진단 질문 감지 키워드 (백엔드) — "약 처방", "치료", "진단" 등
- 답변에 약 이름 직접 X (성분명·식품명만)
- 응급 키워드 ("가슴 아파요", "숨이 안 쉬어져요") → 119 안내 + 응급 화면 분리

**⑩ 분석 이벤트**

- `chat_view` (entry_point)
- `chat_message_send` (length, has_voice)
- `chat_response_complete` (duration_ms, tokens)
- `chat_streaming_cancel`
- `chat_suggested_tap` (which)
- `chat_voice_input`
- `chat_rate_limit_hit`
- `chat_disclaimer_triggered` (reason)
- `chat_emergency_triggered` (keyword)

**⑪ 와이어 → §14.7.W S-11**

**⑫ 결정·메모**

- 레몬 캐릭터를 AI 어시스턴트로 의인화 — 건강의신 IP 새 역할 + 친근함
- Streaming 답변 — 토스·ChatGPT 패턴 익숙. 50대도 "답하고 있구나" 신호 인식.
- 음성 입력 우선 안내 (고령자 모드) — 50대 타이핑 어려움.
- 면책 배너 영구 — 의료법 위험 가장 큰 화면. 한 화면에서 가장 자주 보임.
- 추천 질문 컨텍스트 기반 — Dashboard 최근 분석 알면 "칼슘 결핍" 같은 즉시 가치 질문 제시.

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | "AI에게 묻기" |
| 큰 글씨 큰 터치 | ✓ | 입력바 56dp, 음성 56dp |
| 면책 | ✓ | 상단 배너 항상 + Bot 메시지 caption |
| 다음 액션 | ✓ | SuggestedChip 또는 입력 |
| 폴백 | ✓ | Rate limit / Network / Mock 답변 |
| 빠른 학습 | ✓ | 추천 질문 5개로 첫 진입 막막함 ↓ |
| 회복 가능 | ✓ | 메시지 long-press 복사 / 삭제 가능 |

**친화도 빈틈 → 추가 결정**

- 의료 진단 질문 감지 → 단순 거절 X → "이건 의료기관 상의가 좋아요" + "그래도 일반 정보는?" 옵션 (단호함 + 친절)
- 응급 키워드 → 풀스크린 119 안내 + 1초 후 자동 진동·소리 (놓치지 않게)
- 답변 길이 — 50대 친화 위해 짧게 (3~5문장 기본, 자세히는 사용자가 요청 시)
- 음성 입력 첫 사용 시 마이크 권한 안내 + 1초 데모 사운드 (마이크 작동 확인)
- 챗봇 답변 "도움이 됐어요?" 👍 👎 — 학습용 피드백 + 사용자 의견 반영 신호

#### S-13 Raffle (응모권 — 차별점 보상)

**① 정체성**

| 항목 | 값 |
|------|---|
| 화면 ID | S-13 Raffle |
| 파일 | `screens/raffle_screen.dart` |
| 목적 | 응모권 누적 + 응모 상품 노출 — "점수 부담 없는 보상" |
| 진입 | BottomNav 탭 4 / Dashboard 응모권 배너 / Score 완료 시 응모권 적립 시트 |
| 출구 | 응모 상품 상세 (v2) / Camera (응모권 받기) / Chat (FAQ) |

**② 레이아웃**

| 영역 | 내용 |
|------|------|
| AppBar | 좌측 ← + 타이틀 "응모권" + 우측 ❓ (도움말) |
| 상단 헤더 | citrusLight 큰 카드 — 누적 큰 숫자 + 게이지 + 레몬 캐릭터 |
| Body | 응모 가능 상품 카드 리스트 + 응모 내역 접힘 영역 |
| BottomNav | 활성 |

**③ UI 컴포넌트**

| 컴포넌트 | 토큰 |
|---------|------|
| 헤더 카드 | citrusLight 배경 + radius 24 + padding 24 |
| 누적 큰 숫자 | "3" `display` 64/800 `ink` (압도적 크기) |
| "응모권" 라벨 | `LemonText.body` `inkSoft` 아래 |
| 게이지 | "▰▰▰▰▰▰▱ 6/7 일" + radius pill + citrus 채움 + line 미채움 |
| 게이지 라벨 | "하루만 더 하면 +2장" `caption` `accentStrong` |
| 레몬 캐릭터 | 헤더 우측 80dp |
| 응모 상품 카드 | bgElev + radius 16 + shadow.sm + 16 padding |
| 상품 이미지 | 좌측 80×80 |
| 상품 정보 | 우측 — 제목 subheading + 마감 caption danger ("D-3") |
| 응모하기 버튼 | brand 40dp pill (작게) |
| 내역 토글 | 텍스트 + 우측 ▾ — 탭하면 펼침 |

**적립 규칙 (요약)**

| 조건 | 응모권 |
|------|------|
| 첫 사진 (앱 가입 후) | +1 |
| 7일 연속 기록 | +2 |
| 30일 연속 기록 | +5 |
| 영양제 신규 등록 | +1 |
| 검진지 분석 | +2 |
| 매주 일요일 정산 | +1 (활동 점수 기반) |

상한: 일일 +3, 월 +30 (남용 방지)

**④ 데이터**

| 필드 | 출처 |
|------|------|
| total_tickets | 누적 |
| daily_streak | 연속 기록 일수 |
| next_milestone | 다음 적립까지 |
| available_prizes[] | 진행 중 응모 상품 |
| history[] | 응모 내역 (최근 6개월) |

**⑤ 상태 변화**

| 상태 | 화면 |
|------|------|
| Empty (응모권 0) | 헤더 "0장" + "사진 1장으로 시작하세요" CTA → Camera |
| Normal | 헤더 + 게이지 + 상품 3~5개 |
| 응모 완료 (직후) | 상품 카드에 "응모 완료 · 발표 예정일 5/20" 표시 + 응모 버튼 비활성 |
| 당첨 (v2) | Snackbar/Dialog "당첨! 비타민 D 패키지" |
| 응모 마감 직전 | 카드에 빨간 D-1 badge + 살짝 pulse |
| 응모 가능 상품 없음 | "다음 응모 상품 곧 공개" placeholder |

**⑥ 인터랙션**

- 헤더 long-press → "응모권은 어떻게 얻나요?" BottomSheet (적립 규칙)
- 상품 카드 탭 → 상세 시트 (이미지·내용·응모 조건)
- 응모하기 탭 → 다이얼로그 "응모권 1장을 사용해서 응모하시겠어요?"
- 응모 완료 → 햅틱 success + 카드 흔들림 (좋은 진동) 200ms
- 내역 ▾ 탭 → expansion 320ms
- Pull-to-refresh
- 모션: 큰 숫자 입장 시 0→실제값 count-up 800ms

**⑦ 접근성**

- 누적 큰 숫자 semanticLabel: "응모권 3장 보유"
- 게이지 semanticLabel: "7일 중 6일 완료. 하루 남았어요"
- 응모하기 semanticLabel: "응모권 1장 사용하여 응모"
- count-up 모션은 reduceMotion 시 즉시 표시

**⑧ 고령자 모드**

- 누적 숫자 64 → 80
- 응모하기 버튼 40 → 56 (작은 버튼 X)
- 상품 카드 padding 16 → 24
- 적립 규칙 BottomSheet 자동 한 번 표시 (첫 진입)

**⑨ 면책·의료법**

- 응모 상품 = 비의약품 (영양제·체크업·도서 등) 한정
- 의약품·치료 관련 상품 절대 X
- 헤더 하단 caption — "응모권은 영양·건강 정보 활용으로 자연스럽게 모여요. 점수 경쟁이 아니에요."

**⑩ 분석 이벤트**

- `raffle_view`
- `raffle_prize_tap` (which)
- `raffle_apply` (prize_id, tickets_used)
- `raffle_apply_confirm` / `cancel`
- `raffle_milestone_reached` (which)
- `raffle_help_view`
- `raffle_history_open`

**⑪ 와이어 → §14.7.W S-12**

**⑫ 결정·메모**

- 점수 경쟁 X — 만성질환자가 다른 사용자와 비교당하면 부담. 응모권은 "내 일정한 행동의 자연스러운 보상".
- 누적 숫자 매우 크게 — 첫 진입 시 가장 큰 시각 임팩트. 모았다는 만족감.
- 상한 일 3장 / 월 30장 — 남용 방지 + 매일 꾸준한 인센티브.
- 레몬 캐릭터 헤더 — 응모권의 친근한 가치 전달.

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | "응모권 확인" 또는 "응모하기" |
| 큰 글씨 큰 터치 | ✓ | 큰 숫자 64, 응모하기 40dp (작아서 보강 필요) |
| 면책 | ✓ | 비의약품 한정 + caption |
| 다음 액션 | ✓ | 헤더 + 첫 상품 카드 응모하기 |
| 폴백 | ⚠ | **개선 필요** — 응모 상품 없을 때 "곧 새 상품" placeholder 명확화 |
| 빠른 학습 | ⚠ | **개선 필요** — 첫 진입 시 "응모권 = 사진의 보상" 한 줄 안내 |
| 회복 가능 | ✓ | 응모 확인 다이얼로그 |

**친화도 빈틈 → 추가 결정**

- 응모하기 버튼 40dp → 48dp (터치 최소 보장)
- 첫 진입 시 헤더 아래 BottomSheet — "응모권은 어떻게 받나요?" 첫 1회만 자동 표시
- "응모 완료" 직후 동기부여 메시지 — "오늘도 사진을 찍으면 +1장" 다음 액션 유도
- 당첨 알림 — 푸시 + 앱 안 큰 모달 (놓치지 않게)
- 응모 마감 임박 알림 — D-2부터 푸시 1회

#### S-14 Settings

**① 정체성**

| 항목 | 값 |
|------|---|
| 화면 ID | S-14 Settings |
| 파일 | `screens/settings_screen.dart` |
| 목적 | 계정·알림·접근성·고령자 모드·법적 고지·로그아웃 |
| 진입 | BottomNav 탭 5 / Dashboard 프로필 아이콘 |
| 출구 | `/login` (로그아웃) / 각 서브 화면 |

**② 레이아웃**

| 영역 | 내용 |
|------|------|
| AppBar | 좌측 ← + 타이틀 "설정" |
| Body | ScrollView — 그룹별 ListTile 구획 |
| BottomNav | 활성 |

**그룹 구조**

| 그룹 | 항목 |
|------|------|
| 계정 | 프로필 (아바타 + 이름 + 이메일) |
| 일반 | 알림 / 언어 / 시간대 |
| 접근성 | 고령자 모드 / 큰 글씨 / 모션 줄이기 / 햅틱 |
| 데이터 | 건강 권한 / 사진 저장 / 백업·복원 |
| 정보 | 이용약관 / 개인정보 / AI 한계 / 오픈소스 라이선스 |
| 도움 | 자주 묻는 질문 / 문의하기 / 앱 평가 |
| 위험 영역 | 로그아웃 / 계정 삭제 (v2) |

**③ UI 컴포넌트**

| 컴포넌트 | 토큰 |
|---------|------|
| 계정 카드 | 64dp 아바타 (브랜드 letter avatar) + 우측 → |
| 그룹 헤더 | `LemonText.caption` `inkMute` 좌측 정렬 |
| ListTile | 64dp 높이 / 좌측 아이콘 24 brand / 라벨 body / 우측 ⏵ 또는 Switch |
| Switch | brand 채움 / inkMute 미선택 |
| 구분선 | line 1dp |
| 로그아웃 버튼 | Ghost danger 풀폭 52dp |
| 버전 | 하단 가운데 "v 0.1.0 (1)" caption |

**④ 데이터**

| 필드 | 출처 |
|------|------|
| user | provider |
| settings | localStorage + 서버 sync |
| version | package_info |

**⑤ 상태 변화**

| 상태 | 화면 |
|------|------|
| Normal | 모든 항목 표시 |
| Switch toggle | 즉시 반영 + 짧은 햅틱 |
| 권한 변경 항목 | 시스템 설정 외부 진입 |
| 로그아웃 | 다이얼로그 → 인증 정리 → /login |
| 계정 삭제 (v2) | 풀스크린 경고 + 비밀번호 재확인 |

**⑥ 인터랙션**

- ListTile 탭 → 해당 서브 화면 / Switch 토글
- Switch 토글 → 햅틱 light + 즉시 저장
- 고령자 모드 토글 시 → 다음 라우팅부터 토큰 변경 + Snackbar "큰 글씨로 바뀌었어요"
- 로그아웃 탭 → 다이얼로그 "정말 로그아웃하시겠어요?"
- 버전 long-press → 디버그 정보 (개발 빌드만)

**⑦ 접근성**

- 모든 ListTile semanticLabel
- Switch 상태 announce ("고령자 모드 켜짐/꺼짐")
- 그룹 헤더 heading role

**⑧ 고령자 모드**

- ListTile 64 → 72
- 폰트 16 → 19
- 아이콘 24 → 28
- Switch 트랙 더 큰 사이즈
- 고령자 모드 항목 자체는 항상 큰 폰트 표시 (자기 자신 강조)

**⑨ 면책·의료법**

- "AI 한계 안내" 항목 → 전용 페이지 (Consent 화면의 텍스트와 동일)
- 의료법 면책 전문 페이지 별도 (v2)

**⑩ 분석 이벤트**

- `settings_view`
- `settings_item_tap` (which)
- `settings_toggle` (which, value)
- `settings_logout`
- `settings_elder_mode_on/off`

**⑪ 와이어 → §14.7.W S-13**

**⑫ 결정·메모**

- 고령자 모드 = 명시 토글 (자동 감지 X) — 자동은 잘못 맞춤. 본인이 명시 선택.
- 위험 영역 (로그아웃) 맨 아래 + 색 — 실수 방지
- 계정 삭제는 v2 — 의료 정보 삭제는 법적 절차 필요. 1차 출시 보류.
- 버전 long-press 디버그 — 개발자 모드. 50대 사용자에 안 보임.

**친화도 체크 (§1.0b 7대 원칙)**

| 원칙 | OK | 메모 |
|------|----|----|
| 한 화면 한 일 | ✓ | "설정 조정" — 그룹별 분리로 부담 ↓ |
| 큰 글씨 큰 터치 | ✓ | ListTile 64dp |
| 면책 | ✓ | "AI 한계 안내" 항목 별도 |
| 다음 액션 | — | 사용자 자유 선택 |
| 폴백 | ✓ | 권한 변경 X 시 안내 |
| 빠른 학습 | ⚠ | **개선 필요** — 고령자 모드 토글에 "어떤 게 바뀌나요?" 도움말 |
| 회복 가능 | ✓ | 로그아웃·삭제 확인 다이얼로그 |

**친화도 빈틈 → 추가 결정**

- 고령자 모드 ON 시 "큰 글씨 + 큰 버튼으로 바뀌어요" 미리보기 다이얼로그 (시각 확인 후 적용)
- 알림 끄기 시 — "이걸 끄면 응모권 적립·복약 시간 등 놓칠 수 있어요" 안내
- 로그아웃 후 자동 카카오 토큰도 회수 — 다음 로그인 시 새로 인증
- 사용자 데이터 다운로드 항목 추가 (개인정보 권리 보장) — Settings → "내 정보 다운로드"

### 14.7.W 와이어프레임 (ASCII 골격)

Figma 들어가기 전 골격 잠금용. 한 칸 = 4dp 가정. `=` 는 헤더/푸터, `─` 는 일반 라인, `▢` 는 카드, `▣` 는 selected, `[ ]` 는 버튼, `( )` 는 chip, `__` 는 입력 필드.

**S-01 Splash**
```
┌─────────────────────────┐
│                         │
│                         │
│         🍋 (120)        │  ← 로고
│       Lemon Aid          │  ← 워드마크 32/800
│  내 손안의 영양 상담사     │  ← tagline 15/400 inkMute
│                         │
│         ●━━━━━           │  ← 인디케이터 (얇게)
│                         │
└─────────────────────────┘
```

**S-02 Login (건강의신 추종 + 차별화 — 2026-05-11)**
```
┌─────────────────────────┐
│                         │
│  Lemon🍋Aid              │  좌측 정렬 / 32~36 / 800
│  사진 한 번, 영양 분석 끝    │  body 16/600 inkSoft
│                         │
│                         │
│                         │
│       (호흡 공간 35%)     │
│                         │
│                         │
│                         │
│                    🍋   │  레몬 캐릭터 ~140dp 우측 하단
│                  (서있음)│
│                         │
│  ┌─ 최근 로그인했어요 ─┐    │  검은 말풍선 툴팁 (재방문 시만)
│  ┌─────────────────────┐│
│  │ 💬  카카오로 계속하기 ││  bg #FEE500 / 52dp / radius 12
│  └─────────────────────┘│
│                         │
│  ┌─────────────────────┐│
│  │ G   구글로 시작        ││  bg #FFF / border #DADCE0 / 52
│  └─────────────────────┘│
│                         │
│       또는 이메일로 →       │  Ghost 텍스트 링크 (작게)
│                         │
│  ─────────────────────  │
│  © Lemon Aid · 약관 · 개인정보 │  caption inkMute
└─────────────────────────┘
```

**이메일 BottomSheet (이메일 링크 탭 시)**
```
              ┌─────────────────────────┐
              │       (드래그 핸들)       │
              ├─────────────────────────┤
              │  이메일로 로그인            │  title 22/800
              │                         │
              │  ┌─ 이메일 ─────────┐    │
              │  │ name@email.com  │    │
              │  └─────────────────┘    │
              │  ┌─ 비밀번호 ───────┐    │
              │  │ ●●●●●●●●    👁  │    │
              │  └─────────────────┘    │
              │                         │
              │  [    로그인         ]   │  Primary 52
              │                         │
              │  처음이신가요? 회원가입 →    │  Ghost link
              │                         │
              │  비밀번호를 잊으셨나요?     │  caption (v2)
              └─────────────────────────┘
```

**OAuth 진행 중 상태**
```
│  ┌─────────────────────┐│
│  │ ◐  카카오 로그인 중...││  spinner + 텍스트 변경
│  └─────────────────────┘│
│  (다른 버튼·이메일 링크 모두 비활성 50%)
```

**이메일 인증 실패 (BottomSheet 내부)**
```
              │  ┌─ 비밀번호 ───────┐    │
              │  │ ●●●●●●●●    👁  │    │  border danger 2px
              │  └─────────────────┘    │
              │  ⚠ 이메일 또는 비밀번호가  │  helper danger
              │    일치하지 않아요         │
```

**S-03 Signup**
```
┌─────────────────────────┐
│ ←  회원가입               │  AppBar
├─────────────────────────┤
│ 1 / 1                   │  Stepper dot
│                         │
│  이메일                  │
│  ┌───────────────────┐ │
│  │ name@email.com    │ │
│  └───────────────────┘ │
│                         │
│  비밀번호                │
│  ┌───────────────────┐ │
│  │ ●●●●●●●●          │ │
│  └───────────────────┘ │
│  8자 이상 · 영문 + 숫자   │  caption
│                         │
│  비밀번호 확인            │
│  ┌───────────────────┐ │
│  └───────────────────┘ │
│                         │
│  이름                   │
│  ┌───────────────────┐ │
│  └───────────────────┘ │
│                         │
│  [    다 음        ]    │
└─────────────────────────┘
```

**S-04 Verify Email**
```
┌─────────────────────────┐
│ ←  이메일 확인            │
├─────────────────────────┤
│                         │
│  📧  name@email.com     │
│  으로 6자리 코드 전송      │
│                         │
│  ┌─┐┌─┐┌─┐┌─┐┌─┐┌─┐    │  OTPField 6칸
│  │3││9││ ││ ││ ││ │    │
│  └─┘└─┘└─┘└─┘└─┘└─┘    │
│                         │
│  04 : 32  남음            │  Timer caption
│                         │
│  [    확 인        ]    │
│                         │
│  코드 재발송               │  TextLink
└─────────────────────────┘
```

**S-05 Consent**
```
┌─────────────────────────┐
│ ←  동의                  │
├─────────────────────────┤
│  Lemon Aid 이용 동의      │  title 24/800
│                         │
│  ⚠ Lemon Aid는 진단·     │  Disclaimer Card
│   처방을 하지 않습니다.    │  warning tint
│   AI 권고는 참고용이며...  │
│                         │
│  ☐ 전체 동의              │  Master checkbox
│  ────────────────────── │
│  ☐ [필수] 서비스 이용약관  │
│  ☐ [필수] 개인정보 수집    │
│  ☐ [필수] AI 한계 이해     │
│  ☐ 마케팅 정보 수신 (선택)  │
│                         │
│  [  동의하고 시작   ]    │  비활성 → 활성
└─────────────────────────┘
```

**S-06 Onboarding (6 step Stepper)**
```
┌─────────────────────────┐
│ ←  3 / 6                 │  진행도
├─────────────────────────┤
│                         │
│  키와 몸무게를 알려주세요   │  heading 20
│                         │
│  키                      │
│  ┌───────────────┐ cm   │
│  │ 165           │      │
│  └───────────────┘      │
│                         │
│  체중                    │
│  ┌───────────────┐ kg   │
│  │ 62            │      │
│  └───────────────┘      │
│                         │
│        (Spacer)          │
│  [ 이전 ]  [   다음    ] │
└─────────────────────────┘
```

**S-07 Dashboard (Home)**
```
┌─────────────────────────┐
│ ☰  Lemon Aid     🔔 👤  │  AppBar
├─────────────────────────┤
│ ┌─ 오늘 ───── 2026-05-11 ─┐ │  TodayCard
│ │ 잘 챙기고 있어요          │ │
│ │ 충족률 78% · 잔여 2팩    │ │
│ └────────────────────────┘ │
│                         │
│ ┌─ 영양 ────────────────┐ │
│ │ 단백 ▰▰▰▱▱ 충분        │ │  NutrientBar×3
│ │ 칼슘 ▰▱▱▱▱ 결핍        │ │
│ │ 철  ▰▰▱▱▱ 부족        │ │
│ └────────────────────────┘ │
│                         │
│ 빠른 액션                  │
│ [📷 사진][💊 약][💧 물][⚖️] │  QuickAction×4
│                         │
│ ┌─ 응모권 ────────── 3장 ─┐ │
│ │ 일주일 더 채우면 +2장   │ │
│ └────────────────────────┘ │
├─────────────────────────┤
│ 🏠   ❤   💬   🎁   ⚙   │  BottomNav 5
└─────────────────────────┘
       (FAB 📷 우하단)
```

**S-08 Camera**
```
┌─────────────────────────┐
│ ✕                  💡   │  닫기 / 플래시
├─────────────────────────┤
│                         │
│                         │
│      [카메라 프리뷰]      │
│                         │
│   ┌───────────────┐     │
│   │   가이드 박스   │     │  영양제 라벨 가이드
│   └───────────────┘     │
│                         │
│                         │
├─────────────────────────┤
│ (영양제)(식단)(검진지)(체중) │  CategoryChip
│                         │
│  🖼              ⚪    🔄  │  갤러리 / 셔터 72 / 전환
└─────────────────────────┘
```

**S-09 Score (5출력)**
```
┌─────────────────────────┐
│ ←  분석 결과         📤   │  공유
├─────────────────────────┤
│ ┌─ ① 영양소 충족률 ─────┐ │
│ │ 단백 ▰▰▰▱▱ 78%       │ │
│ │ 칼슘 ▰▱▱▱▱ 32% 결핍   │ │  Card.elev
│ │ ...                  │ │  shadow.sm
│ └──────────────────────┘ │
│ ┌─ ② 결핍 진단 ─────────┐ │
│ │ 칼슘 결핍 가능성        │ │
│ │ 권고: 우유 1잔 / D 보충 │ │
│ └──────────────────────┘ │
│ ┌─ ③ 식단 권고 ─────────┐ │
│ │ 저녁: 두부 100g 추가   │ │
│ └──────────────────────┘ │
│ ┌─ ④ 체중 예측 ─────────┐ │
│ │ 1주 후 -0.3kg          │ │
│ └──────────────────────┘ │
│ ┌─ ⑤ 활동 점수 ─────────┐ │
│ │ 72 / 100 (어제보다 +4) │ │
│ └──────────────────────┘ │
│ ⚠ 참고용 정보 (의료 X)    │  면책 배너
│                         │
│ [💬 더 알아보기][💾 저장] │
└─────────────────────────┘
```

**S-10 Health**
```
┌─────────────────────────┐
│ ←  건강 데이터      ⚙    │
├─────────────────────────┤
│ (7일)(30일)(90일)         │  Period Chip
│                         │
│  📊 일별 걸음              │
│  ┌──────────────────┐   │
│  │      ╱╲    ╱╲    │   │  fl_chart
│  │  ╱╲╱  ╲╱╲╱  ╲   │   │
│  └──────────────────┘   │
│                         │
│ ┌─ 오늘 ────┬ 평균 ─┬ 목표 ┐│
│ │ 6,234   │ 5,820 │ 8,000│  Stat 3분할
│ └─────────┴───────┴──────┘│
│                         │
│ ┌─ 심박 ──────────┐       │
│ │ 휴식 68 / 운동 124       │
│ └─────────────────┘       │
│                         │
│ [+ 수동 입력]              │  FAB
└─────────────────────────┘
```

**S-11 Chat**
```
┌─────────────────────────┐
│ ←  AI 챗봇      🗑      │
├─────────────────────────┤
│ ⚠ 의료 조언 X · 참고용     │  고정 배너
├─────────────────────────┤
│                         │
│           안녕하세요 🤖    │  Bot bubble
│           무엇을 도와드릴까요│
│                         │
│   칼슘 부족 어떻게 하죠?   │  User bubble
│                         │
│           ●●● (타이핑)    │  Streaming
│                         │
│           유제품·녹황색채소 │
│           을 권장합니다... │
│                         │
│ ┌─ 추천 질문 ──────────┐ │
│ │ (비타민 D는?) (우유?)    │ │  SuggestedChip
│ └────────────────────────┘ │
├─────────────────────────┤
│ ┌──────────────┐  🎤 ⏵  │  InputBar
│ │ 메시지 입력...  │       │
│ └──────────────┘        │
└─────────────────────────┘
```

**S-12 Raffle**
```
┌─────────────────────────┐
│ ←  응모권              ❓ │
├─────────────────────────┤
│                         │
│         3               │  대형 카운트 64/800
│       응모권              │  caption
│                         │
│  ▰▰▰▰▰▰▱  6 / 7 일       │  주간 streak gauge
│  하루만 더 하면 +2장        │
│                         │
│ 응모 가능 상품              │  heading
│ ┌─ 비타민 D 패키지 ────┐ │
│ │ 🎁 응모 마감 D-3       │ │
│ │ [응모하기]             │ │  Card×N
│ └─────────────────────┘ │
│ ┌─ 종합 비타민 ────────┐ │
│ │ [응모하기]             │ │
│ └─────────────────────┘ │
│                         │
│ ─ 응모 내역 (3) ▾ ─       │
└─────────────────────────┘
```

**S-13 Settings**
```
┌─────────────────────────┐
│ ←  설정                  │
├─────────────────────────┤
│ 계정                     │
│ 👤  김태동                │
│     name@email.com   →  │
│ ─────────────────────── │
│ 일반                     │
│ 🔔  알림              ⏵  │
│ ♿  접근성            ⏵  │
│ 👁  고령자 모드      [○━] │  Switch ON/OFF
│ ─────────────────────── │
│ 정보                     │
│ 📄  이용약관          ⏵  │
│ 🔒  개인정보 처리방침   ⏵ │
│ ⚠  AI 한계 안내       ⏵ │
│ ─────────────────────── │
│ 도움                    │
│ 💬  문의하기          ⏵  │
│ ⭐  앱 평가 남기기    ⏵  │
│                         │
│        v 0.1.0 (1)       │  caption
│                         │
│       [ 로그아웃 ]        │  Ghost danger
└─────────────────────────┘
```

### 14.8 UI 결정 누적 (라이브 업데이트)

작업하면서 결정된 UI 변경은 여기 누적. PG.md 갱신 기준 (1주 안정 + 5명 동의 + 코드 적용) 충족 시 PG.md로 승격.

| 날짜 | 결정 | 영향 화면 | PG.md 승격 |
|------|------|---------|----------|
| 2026-05-11 | 첫 진입 1.5초 Splash 후 즉시 라우팅 | S-01 | 대기 |
| 2026-05-11 | 모든 Primary Button 48dp 고정 (고령자 모드도 동일) | 전체 | 대기 |
| 2026-05-11 | NutrientBar 색 + 라벨 병기 (색맹 대응) | Home/Analysis | 대기 |
| 2026-05-11 | Consent 화면 필수 3 + 선택 1 구조 | S-04 | 대기 |
| 2026-05-11 | 건강의신 비주얼 1차 분석 (스크린샷 9장) | 전체 | 정보 |
| 2026-05-11 | **메인 컬러 재검토** — 노랑 단독 → 블루+노랑 조합 검토 | 전체 | 안건 ⚠ |
| 2026-05-11 | **배경 재검토** — 크림 → 화이트 + 컬러카드 검토 | 전체 | 안건 ⚠ |
| 2026-05-11 | **3D 일러스트 도입 검토** — 양식적 단색 → 발주처 톤 매칭 | 전체 | 안건 ⚠ |
| 2026-05-11 | Bottom Nav 5탭 라벨 후보 확정 | 전체 | 대기 |
| 2026-05-11 | 레몬 캐릭터를 AI 어시스턴트로 의인화 (챗봇 아이콘) | S-12 Chat | 대기 |
| 2026-05-11 | Login OAuth 3종 — 카카오 우선 / 구글 보조 / 이메일 최후 | S-02 Login | 대기 |
| 2026-05-11 | OAuth 첫 클릭 = 가입+로그인 통합 (가입 화면 X for OAuth 사용자) | S-02 / S-03 | 대기 |
| 2026-05-11 | 카카오 버튼 공식 가이드 색 준수 (#FEE500 / 검정 텍스트) | S-02 Login | 대기 |
| 2026-05-11 | Login 레이아웃 건강의신 추종 — 워드마크 좌측·캐릭터 우하단·중앙 큰 여백 | S-02 Login | 대기 |
| 2026-05-11 | 이메일 로그인을 BottomSheet로 — 메인 화면 시각 깔끔 + 컨텍스트 유지 | S-02 Login | 대기 |
| 2026-05-11 | "최근 로그인했어요" 툴팁 도입 (재로그인 시) — 건강의신 패턴 차용 | S-02 Login | 대기 |
| 2026-05-11 | 워드마크 "Lemon Aid"에 작은 레몬 점 박기 (건강의신 마이크로 디테일 모방) | S-02 Login | 대기 |
| 2026-05-11 | 태그라인 "사진 한 번, 영양 분석 끝" — 앱 핵심 가치 직접 | S-02 Login | 대기 |
| 2026-05-11 | Figma Make로 Login CTA 12 variant 1차 시안 완성 — 명세 거의 그대로 채택 | S-02 Login | 시안 |
| 2026-05-11 | 카카오 툴팁 화살표 좌측 정렬 — Figma 시안 따름 | S-02 Login | 대기 |
| 2026-05-11 | 카카오 로딩 스피너 색은 검정 유지 (Figma 시안 — 노란 바탕 대비 OK) | S-02 Login | 대기 |
| 2026-05-11 | Figma JSON 12 variant 추출 → 코드와 1:1 비교 → Default Mode 100% 일치 확인 | S-02 Login | 검증 ✓ |
| 2026-05-11 | Elderly Mode 토큰 갱신 — touchTarget 56→60, fontSize 16→18, iconSize 20→22 | 전체 | 코드 적용 ✓ |
| 2026-05-11 | LemonButton에 elderMode prop 추가 — height/fontSize/spinnerSize 자동 분기 | 전체 | 코드 적용 ✓ |
| 2026-05-11 | kakao_loading 카카오 bg alpha 0.9 (rgba(254,229,0,0.9)) — Figma 시안 따라 살짝 디밍 | S-02 Login | 검토 필요 |
| 2026-05-11 | email_primary_pressed scale 0.97 — Figma 시안 GestureDetector animation에 반영 예정 | 전체 Button | 대기 |
| 2026-05-11 | Login 하단 구조 변경 — 카카오 + 디바이더 + (회원가입·로그인 분할 1:2) + 구글 Ghost | S-02 Login | 적용 ✓ |
| 2026-05-11 | 건강의신 패턴 추종 — 이메일 BottomSheet 폐기, 분할 버튼이 더 직관적 | S-02 Login | 결정 |
| 2026-05-11 | 구글 로그인은 작은 Ghost로 강등 — 한국 사용자 친화 / 카카오·이메일 우선 | S-02 Login | 결정 |
| 2026-05-11 | 구글 풀폭으로 다시 올림 — 카카오 바로 아래 (OAuth 2개 풀폭 → 디바이더 → 분할 가입/로그인) | S-02 Login | 결정 ✓ |
| 2026-05-11 | CTA 전체 위로 올림 — 마스코트 중앙 정렬 + 하단 약관 아래 40dp 호흡 공간 | S-02 Login | 적용 ✓ |
| 2026-05-11 | Splash 시작하기 버튼 제거 → 1.5초 자동 라우팅 + 떠다니는 로고 모션 | S-01 Splash | 적용 ✓ |
| 2026-05-11 | 앱 아이콘 — Splash 로고와 동일 (1024px SVG → flutter_launcher_icons로 mipmap 자동 생성) | 전체 | 적용 ✓ |
| 2026-05-11 | 네이티브 splash 교체 — 기본 흰 화면 → 레몬 로고 + 크림 배경 (#FEFAE0) | S-01 Splash | 적용 ✓ (Android) |
| 2026-05-11 | iOS는 Xcode 스캐폴딩 부재로 보류 — Mac 팀원 합류 시 `flutter create --platforms=ios .` 후 동일 명령 재실행 | 전체 | iOS 보류 |
| 2026-05-11 | SVG→PNG 변환 — cairo DLL 부재로 cairosvg 실패 → PIL 도형 직접 재현 스크립트(render_icon.py)로 우회 | 전체 | 적용 ✓ |
| 2026-05-11 | Apple 로그인 버튼 추가 (LemonButton.apple variant) — 검정 #000 + 흰 텍스트·로고 | S-02 Login | 적용 ✓ |
| 2026-05-11 | 카카오·구글 라벨 통일 → "카카오로 계속하기" / "구글로 계속하기" / "Apple로 계속하기" | S-02 Login | 적용 ✓ |
| 2026-05-11 | 디바이더에 "이메일로 시작하기" 인라인 라벨 — 라벨 좌우로 라인 분리 (시안 매칭) | S-02 Login | 적용 ✓ |
| 2026-05-11 | 툴팁 정밀 매칭 — radius 10 / padding 14×7 / 부드러운 그림자 2단 / 화살표 좌측 24 위치 | S-02 Login | 적용 ✓ |
| 2026-05-11 | main 머지 — 데이터베이스 구조 + 4 Agent→3 Agent + 알고리즘 분리 + Apple 추가 확정 | 전체 | 머지 ✓ |
| 2026-05-11 | PG.md User.social_provider enum에 'apple' 추가 (iOS 출시 필수) | S-02 / 백엔드 | PG.md 적용 ✓ |
| 2026-05-11 | S-12 Chat — 4 Agent → 3 Agent + 알고리즘 구분 명시 (chat·personalization·evaluation) | S-12 Chat | 적용 ✓ |
| 2026-05-11 | S-12 Chat 출처는 챗봇 안에서만 (Score 화면 X) — citations chip + BottomSheet | S-10 / S-12 | 적용 ✓ |
| 2026-05-11 | S-09 Camera 분석 흐름 — OCR → CSV DB 우선 → API 보조 → Pydantic 강제 | S-09 Camera | 적용 ✓ |
| 2026-05-11 | S-03/S-05/S-06 데이터 필드 PG.md §11.1 일치 (User/EmailVerification/Consent 5종) | S-03 / S-05 / S-06 | 적용 ✓ |
| 2026-05-11 | S-11 Health — iOS HealthKit 우선 / Android Health Connect 검토 예정 | S-11 Health | 적용 ✓ |
| 2026-05-12 | **Login UI 시각 언어 최종 선정 — 뉴모피즘(v2) 채택** | 전체 (시각 언어) | 결정 ★ |
| 2026-05-12 | LoginScreenV2 가 메인 `/login` 로 라우팅. v1 은 `/login-v1` 아카이브 보존 | S-02 Login | 적용 ✓ |
| 2026-05-12 | 워드마크 한글화 — "Lemon" → "레몬", "Aid" 유지 → "레몬•Aid" | S-02 / 전체 브랜드 | 적용 ✓ |
| 2026-05-12 | 캐릭터 — Lemon-Aid 공식 캐릭터 PNG (양팔 따봉, SVG→누끼) Login 우측 상단 | S-02 Login | 적용 ✓ |
| 2026-05-12 | 앱 아이콘 — USAGE 시트의 공식 앱 아이콘 캐릭터 (상반신) + 라운드 사각 1024 + 어댑티브 비활성화 | 전체 | 적용 ✓ |
| 2026-05-12 | "최근 로그인했어요" 툴팁 — 위아래 ±3dp 바운스 (1.4s) + 텍스트 #FACC15 노랑 (검정 배경 위) | S-02 Login | 적용 ✓ |
| 2026-05-12 | 화면 배경 화이트 통일 (#FFFFFF) — 크림(#FEFAE0) 폐기. 시스템 바도 화이트 강제 | 전체 | 적용 ✓ |
| 2026-05-11 | 삭제 정책 — deleted_at + 3개월 복구 → S-14 Settings "계정 삭제" 흐름에 반영 예정 | S-14 Settings | 안건 |
| 2026-05-11 | Splash 최소 노출 800ms → **2초** (50대 로고 인식 + Lottie 1사이클 보장) | S-01 Splash | 적용 ✓ |
| 2026-05-11 | Splash 최대 — 개발 3.5초 timeout / **실제 배포 시 무한 loop** (Lottie repeat:true + 인증 응답까지 대기) | S-01 Splash | 결정 ✓ |
| 2026-05-11 | Lottie 도입 시점 — 백엔드 인증 연결 후. 그 전엔 Flutter 내장 모션으로 유지 | S-01 Splash | 안건 |
| 2026-05-11 | taedong-design 첫 디자인 사이클 커밋 (3d14c07) — 140 files, +15,763 / -743 | 전체 | 커밋 ✓ |
| 2026-05-11 | .gitignore — .claude/ + character/*.zip 제외 (개인 로컬 + 임시 ZIP) | 전체 | 적용 ✓ |
| 2026-05-11 | 네이티브 splash 로고·아이콘 완전 제거 — Flutter Splash 가 유일한 로고 화면 | S-01 Splash | 적용 ✓ |
| 2026-05-11 | launch_background.xml / values-v31/styles.xml / night-v31 — 배경색만 (#FEFAE0) | S-01 Splash | 적용 ✓ |
| 2026-05-11 | Flutter Splash 화면 자체 제거 — 네이티브 앱 아이콘 splash만 (사용자 시각 splash 한 장) | S-01 Splash | 적용 ✓ |
| 2026-05-11 | initialLocation /splash → /login 직진 | S-01 / S-02 | 적용 ✓ |
| 2026-05-11 | 인증 체크 로직은 백엔드 연결 시 별도 화면 또는 main.dart 부팅 단계로 옮김 | 전체 | 안건 |

---

### 14.9 디자인 시스템 v1.0 — 뉴모피즘 채택 (2026-05-12 확정 ★)

**Login 화면 v1 (평면) vs v2 (뉴모피즘) 비교 결과 — v2 채택.**

#### 14.9.1 결정 근거

| 항목 | v1 평면 | v2 뉴모피즘 (채택) |
|------|--------|---------------------|
| 베이스 컬러 | 화이트 (#FFFFFF) | 라이트 그레이 (#EEF1F6) |
| 버튼 표현 | 단순 컬러 카드 (그림자 한 단) | 좌상단 화이트 하이라이트 + 우하단 어두운 그림자 (입체) |
| 카드/입력 | 평면 + 보더 라인 | 뉴모 셰도우, 보더 없음 |
| 분위기 | 모던·미니멀 | 따뜻함·물성·고급감 |
| 가독성 | 매우 높음 | 높음 (대비 충분, 텍스트 굵게) |
| 접근성 | A | A− (셰도우 대비 약간 떨어짐 — 다크 모드 별도 토큰 필요) |
| 적합도 | 일반 서비스 무난 | **건강·웰니스·시니어 친화 톤에 부합** |

**채택 이유 (3가지):**

1. **시니어 친화** — 명확한 입체감으로 "이게 버튼이다"라는 시각적 단서가 평면보다 강함. 50대 페르소나(다이어리 §12) 첫 진입 인지율 ↑.
2. **건강·따뜻함 톤** — 노란 레몬 캐릭터 + 부드러운 그레이 베이스 = 의료기기 차가운 느낌 회피 + 일상 친근.
3. **차별화** — 건강의신 평면 톤과 시각적으로 구분됨. "Lemon-Aid 만의 톤" 형성 가능.

#### 14.9.2 뉴모피즘 토큰 명세

```
Background base:       #EEF1F6  (LemonColors.bg 재정의 검토)
Surface elev:          #FFFFFF
Ink:                   #1A1F2E

Shadow (튀어나옴, 모든 버튼/카드 공통):
  - 우하단:  rgba(177, 183, 194, 0.55)  blur 12  offset(4, 6)
  - 좌상단:  #FFFFFF                     blur 10  offset(-4, -4)

Shadow (눌림 inset — pressed 상태):
  - inner 우하단:  rgba(177, 183, 194, 0.45)  blur 8  inset
  - inner 좌상단:  rgba(255, 255, 255, 0.85)  blur 8  inset

Radius:
  - Button:   14
  - Card:     20
  - Input:    12
  - Modal:    24

Color overrides (뉴모 카드 위에 올라가는 컬러 surface):
  - Primary blue:   #4267EC  (건강의신 톤 유지)
  - Kakao yellow:   #FEE500
  - Apple black:    #1A1F2E
  - Google white:   #FFFFFF
```

#### 14.9.3 다음 화면 적용 순서

| 화면 | 작업 | 우선도 |
|------|------|--------|
| S-03 Signup | 뉴모 입력 필드 + Apple/Google/Kakao + 약관 체크 | ★★★ |
| S-05 Consent | 뉴모 토글/체크박스 4종 (필수 3 + 선택 1) | ★★★ |
| S-06 Onboarding | 뉴모 슬라이더(나이) + 라디오(성별) + 카드 4종 (식이 선호) | ★★★ |
| S-07 Home | 뉴모 5탭 BottomNav + 뉴모 영양 카드 5종 | ★★★★ |
| S-09 Camera | 뉴모 셔터 + 안내 카드 | ★★ |
| S-10 Score | 뉴모 점수 카드 + 출처 chip | ★★ |
| S-11 Health | 뉴모 토글 + 차트 카드 | ★★ |
| S-12 Chat | 뉴모 입력바 + 메시지 카드 | ★★ |

#### 14.9.4 v1 아카이브 (보존)

- 파일: `mobile/lib/screens/auth/login_screen.dart` (LoginScreen 클래스)
- 라우트: `/login-v1` (devtools 진입 가능)
- 보존 이유: 평면 디자인 비교·롤백·발표 시 before/after 자료
- 삭제 시점: 베타 출시 후 1개월 안정 시 검토

---

---SPLIT---

### 14.10 디자인 시스템 v2.1 — Hybrid: Flat 2.0 베이스 + 뉴모피즘 액센트 (최종 ★★★★, 2026-05-12)

> **한 줄 요약**: 기본 구조는 Flat 2.0 기반으로 설계하고, 주요 인터랙션 요소에 뉴모피즘 감성을 더해 부드럽고 현대적인 UI 를 구현한다.
>
> 이 섹션은 **단순 결정 기록이 아니라 Lemon Aid 의 UI/UX 가이드라인** 이다.
> 외부에 "왜 이 톤을 골랐는가" 를 설명하는 문서이자 팀이 화면을 새로 만들 때 펴 보는 기준선이다.
>
> 외부 앱 이름은 시각 참조 보조용으로만 표기하며, 채택 논리는 전적으로 Lemon Aid 의 정체성·정보 구조에서 도출한다.

#### 14.10.−1 비율 — 80~90 / 10~20

| 비율 | 구성 | 목적 |
|------|------|------|
| **80~90% Flat 2.0** | 전체 화면 구조 / 카드 / 리스트 / 텍스트 / 네비게이션 / Divider / AppBar | 정보 구조 안정성·가독성·시중 학습된 패턴 |
| **10~20% 뉴모피즘 액센트** | 메인 CTA 버튼 / 토글 / 입력창 (selective) / 상태 위젯 / 캐릭터 주변 인터랙션 / 특정 대시보드 카드 | 감성·고급감·부드러운 터치감 / Lemon Aid 캐릭터·브랜드 톤과 호응 |

> ❌ 모든 버튼·카드에 뉴모 깊은 음영을 넣지 않는다.
> ❌ 정보량 많은 화면에서 뉴모를 과하게 쓰지 않는다 (가독성 손실).
> ❌ 배경과 요소 톤이 너무 비슷해 경계가 사라지지 않게 한다.

#### 14.10.−0.5 적용 매트릭스 (어디에 무엇)

| 컴포넌트 | 베이스 / 액센트 | 시각 톤 | 비고 |
|---------|---------------|--------|-----|
| 화면 배경 | 베이스 (Flat) | #FFFFFF | 흰색 통일 |
| AppBar / 백 버튼 | 베이스 (Flat) | 평면 + Material splash | iOS / Android 통일 |
| Card (정보) | 베이스 (Flat) | 흰 + elev 1 그림자 | 보더 X 또는 1px |
| List Item | 베이스 (Flat) | 평면 + Divider | 그림자 X |
| Text Field (일반) | 베이스 (Flat) | sunken #F7F8FA + focus 보더 | 평면 |
| Text Field (감성 폼: 회원가입 첫 진입) | **액센트 (뉴모)** | inset shadow + 부드러운 진입 | 진입 첫 화면 인상 |
| Secondary Button | 베이스 (Flat) | 흰 + 1px 보더 | 평면 |
| **Primary CTA Button (메인 액션)** | **액센트 (뉴모)** | brand 솔리드 + neuPop 그림자 | 부드러운 입체감 |
| **OAuth Buttons (카카오/Apple)** | **액센트 (뉴모)** | 컬러 솔리드 + neuPop | 진입 첫 화면 인상 |
| Google OAuth | 베이스 (Flat) | 흰 + 1px 보더 | 평면 (균형) |
| Divider / 라인 | 베이스 (Flat) | #EEF1F6 | 평면 |
| BottomNav 5탭 | 베이스 (Flat) | 평면 + active 색 | 매일 사용 - 깔끔 |
| 메인 대시보드 카드 (영양 요약) | 액센트 일부 (뉴모) | 부드러운 elev + 살짝 라이트 그라데이션 | 진입 시 인상적 |
| 부분 대시보드 카드 (식사 기록 리스트) | 베이스 (Flat) | 평면 | 정보 우선 |
| 토글 스위치 | **액센트 (뉴모)** | inset 트랙 + pop knob | 터치감 강조 |
| 모달 / BottomSheet | 베이스 (Flat) | elev 3 | 평면 |
| 캐릭터 주변 말풍선·툴팁 | **액센트 (뉴모)** | 부드러운 그림자 | 감성 요소 |
| 챗봇 메시지 버블 | 베이스 (Flat) | 평면 + 라디우스 | 정보 우선 |
| 결과 점수 카드 (S-10) | **액센트 (뉴모)** | 큰 원형 + neuPop | 임팩트 |

#### 14.10.0 앱 정체성 분석 — Lemon Aid 는 무엇을 하는 앱인가

| 정의 항목 | Lemon Aid |
|---------|-----------|
| **카테고리** | AI 헬스케어 / 영양 분석 / 건강 관리 플랫폼 |
| **핵심 동사** | "찍는다 → 분석한다 → 기록한다 → 본다" |
| **사용 빈도** | 하루 3~5회 짧은 진입 (식사·간식·운동) + 주 1회 점수 회고 |
| **사용 시간** | 1회당 30초~2분 (사진 한 장이면 끝) |
| **사용 상황** | 식탁 위·외출 중·운동 직후 — 한 손, 짧은 시간, 정보 즉각 확인 |
| **정보 종류** | 영양소 수치 + 추천 텍스트 + 시계열 그래프 + 식품 카드 + AI 챗봇 응답 |
| **사용자 기대** | "내 몸 상태가 한눈에" / "오늘 잘 먹었나?" / "이 음식 괜찮나?" |
| **사용자 우려** | 의료법·민감정보·체중/건강 수치 노출 → **신뢰감 필수** |
| **주 사용자** | 20~50대 일반 + 50대+ 시니어 친화 모드 (다이어리 §12 페르소나) |

**핵심 키워드 (이 세 단어가 시각 언어를 결정):**
1. **신뢰** — 헬스 데이터를 다루므로 의료 톤과 가까워야 함 (장난스러우면 안 됨)
2. **빠른 스캔** — 짧은 진입·즉각 정보 확인 → 한눈에 보이는 카드·라벨
3. **반복 사용** — 매일 들어와도 피로하지 않은 톤 (장식 X, 콘텐츠 우선)

---

#### 14.10.1 모바일 앱 UI 시스템 분류 매트릭스

앱은 **목적·정보 유형·사용 빈도** 에 따라 시각 언어가 결정된다.
카테고리별 정보 특징에서 어떤 UI 시스템이 도출되는지의 일반론:

| 카테고리 | 정보 특징 | 도출되는 UI 시스템 | 시각 원칙 |
|--------|---------|------------------|--------|
| 금융 | 숫자·계좌·청구서 — 정보 우선순위, 빠른 클릭성, 신뢰 | **Flat 2.0 + 카드** | 화이트스페이스 넓음 / 카드·리스트 분명 / 그림자 미세 / 보더 약함 |
| 이커머스·숙박 | 상품·가격·후기 — 스캔, 비교, 쇼핑 충동 | **Flat 2.0 + 카드 + 강한 컬러 액센트** | 카드 그리드 / 컬러 chip / CTA 굵게 |
| SNS | 사진·텍스트·인터랙션 — 콘텐츠 자체가 주인공 | **Stealth Flat (거의 무 UI)** | 흰/검 배경 / UI 요소 최소 / 콘텐츠 풀폭 |
| 소셜 게임 | 점수·랭킹·아이템 — 재미·도파민 | **Skeuomorphism + 컬러풀** | 입체 버튼 / 그라데이션 / 일러스트 강함 |
| 생산성 | 텍스트·구조·작업 — 집중·편집 | **Minimal Flat + 그리드** | 보더 명확 / 컬러 절제 / 타이포 강함 |
| 명상·웰니스 | 동영상·사운드·짧은 카드 — 진정·일상화 | **Soft Flat + 그라데이션** | 부드러운 색 / 그림자 거의 없음 / 일러스트 사용 |
| 의료·병원 | 증상·약·예약 — 정확·신뢰·안전 | **Flat + 카드 + 차분한 블루** | 흰 배경 / 정보 카드 강조 / 채도 낮음 |

(주: 매트릭스는 일반화된 패턴 정리이며, 같은 카테고리 안에서도 앱마다 변형은 다양함.)

#### 14.10.2 Lemon Aid 를 어디에 위치시키나

Lemon Aid 는 **단일 카테고리에 속하지 않는다.** 동시에 세 카테고리의 성격을 가짐:

```
        ┌─────────────────────────────┐
        │  의료·병원 (신뢰)            │
        │  ↓ 영양 데이터·체중 수치     │
        ├─────────────────────────────┤
        │  Lemon Aid                  │  ← 교집합
        ├─────────────────────────────┤
        │  금융 (정보 스캔)            │  웰니스 (반복 사용)
        │  ↓ 영양소 그래프·           │  ↓ 매일 진입·캐릭터·
        │     기록 시계열·점수         │     긴장 X 톤
        └─────────────────────────────┘
```

**시각 언어 도출 (카테고리별 강점만 가져옴):**

- 의료 카테고리에서 → **흰 배경 + 카드 + 정보 명확성** (단, 차가운 의료 블루 톤은 피함)
- 금융 카테고리에서 → **Flat 2.0 + 카드 그리드 + 정보 우선순위 + 빠른 스캔**
- 웰니스 카테고리에서 → **노란 캐릭터 액센트로 따뜻함 추가, 일러스트는 강조 영역만**

**Lemon Aid 의 시각 언어 =**

> 카드 기반의 명확한 정보 그룹화 + 헬스 데이터에 맞는 신뢰 톤(차분한 블루·흰 배경) + 캐릭터 한 컷의 친근함.

자기 정체성에서 도출한 시스템이며, 위 매트릭스의 어느 한 앱을 모방한 결과가 아니다.

#### 14.10.3 채택: Hybrid — Flat 2.0 베이스 + 뉴모피즘 액센트

전체 톤 갈래는 둘이다. 우리 앱 정체성(헬스+신뢰+감성+캐릭터)을 고려하면 **양쪽 강점을 비율로 섞는 게 가장 적합**.

| 톤 | 강점 | 약점 | Lemon Aid 적용 |
|----|------|------|--------------|
| Flat 2.0 | 정보 구조 안정 / 가독성 / 사용성 / 시중 학습된 패턴 | 차가움·평이함 | 화면 80~90% (구조·카드·리스트·텍스트·네비) |
| 뉴모피즘 | 감성 / 부드러움 / 고급 터치감 | 그림자 의존·가독성·접근성 약함 | 화면 10~20% (메인 CTA·토글·감성 인터랙션) |

**왜 하이브리드인가:**

- **헬스케어·웰니스·플래너·명상·감성 금융·프리미엄 라이프스타일** 카테고리는 정보 구조 + 감성 두 축이 동시에 필요 — Lemon Aid 도 정확히 이 자리.
- Flat 2.0 단독 → 차갑고 평이함. 매일 진입하지만 "내 데이터를 다정하게 들어주는" 톤이 부족.
- 뉴모 단독 → 가독성·접근성 손실. 정보량 많은 화면(영양 분석·식사 로그) 에서 사용자 인지 과부하.
- 혼합 → 정보 카드는 깔끔하게(Flat), 사용자가 손가락으로 누르는 CTA·토글·감성 요소는 부드럽게(뉴모) → 양쪽 강점만 흡수.



**Flat 2.0** 이란?
- 원조 Flat(2013, iOS 7) 의 "그림자·물성 완전 제거" 에서 한 발 뒤로 — 미세 그림자(elev 1~2)·미세 보더(1px)·라이트한 색 변화 정도는 허용해 입체감을 살짝 살림.
- 정보 그룹화는 **카드 단위** 로 — 동시대 모바일 앱이 정보 밀도가 높을 때 가장 자주 채택하는 형태.

**Lemon Aid 에 Flat 2.0 + 카드가 맞는 이유 (정체성 매핑):**

| 정체성 요구 | Flat 2.0 + 카드가 푸는 방식 |
|----------|------------------------|
| 신뢰 (의료 톤) | 화이트 베이스 + 차분한 블루 #3182F6 + 장식 최소 → 의료기기·금융 앱과 같은 안정감 |
| 빠른 스캔 | 카드 그리드 + 명확한 라벨 + 그림자로 카드 경계 시각화 → 손가락 진입 1회당 0.5초 안에 영양 상태 파악 |
| 반복 사용 (매일 3~5회) | 장식 최소·콘텐츠 우선 → 매일 봐도 피로 X. 캐릭터는 강조 영역에만 → 친근함은 유지 |
| 헬스 데이터 시각화 | 카드 안에서 NutrientBar / Chart / Score 컴포넌트가 독립적으로 동작 → 정보 단위 명확 |
| 시니어 친화 모드 호환 | Flat 2.0 은 입체감이 약해 시니어 모드(고대비·큰 폰트)로 토큰만 바꿔도 자연스럽게 전환 가능 (뉴모는 그림자 의존성이 강해 모드 전환 어려움) |

**기각된 대안과 사유:**

| 대안 | 검토 | 기각 사유 |
|-----|------|--------|
| 뉴모피즘 (v1.0 검토) | 따뜻함·고급감 매력 | 그림자 의존성 강함 → 다크 모드·시니어 모드 양립 어려움 / 모바일 헬스·금융 영역의 학습된 패턴(흰 배경 + 평면 카드)과 충돌 / 콘텐츠보다 장식이 두드러져 매일 진입 시 피로 |
| Skeuomorphism (입체 버튼) | 직관성 | 의료 톤과 충돌 (장난스러움), 매일 진입 시 피로 |
| 거의 무 UI (Stealth Flat, 인스타) | 콘텐츠 우선 | Lemon Aid 콘텐츠 = 사용자 본인 데이터인데 SNS 와 달리 그 데이터를 **해석·강조** 해줘야 함. UI 가 너무 빠지면 "내가 잘 먹었는지" 모름 |
| Material Design 표준 | 안정성 | 너무 일반적, "Lemon Aid 만의 톤" 부족 / Floating Action Button 등 의료 톤에 거슬리는 요소 |
| Cupertino (iOS) 표준 | iOS 친화 | Android 점유율 무시 못함 / 통일 톤 필요 |

#### 14.10.4 채택 결과 — 디자인 원칙 5조 (UX 근거 포함)

각 원칙은 **무엇을(WHAT)** 하는지 + **왜 이게 사용자에게 더 나은가(WHY)** + **그래서 화면에서 어떻게 보이는가(HOW)** 로 정의한다.

##### 원칙 1 — 콘텐츠 우선

- **WHAT**: UI 요소(버튼·박스·라인)는 콘텐츠를 위한 도구. 장식적 시각 요소 금지. 사용자 데이터(영양·점수·기록)가 화면에서 가장 시각적으로 강한 위치를 차지함.
- **WHY (UX 근거)**:
  - Lemon Aid 사용자는 1회 진입당 30초~2분 안에 "내 식단 어떤가?" 를 판단한다 (정체성 §14.10.0). 짧은 시간 안에 답을 얻으려면 시선이 **콘텐츠로 즉시** 가야 한다.
  - 장식이 강한 UI(그라데이션·과한 그림자·과한 컬러)는 시선이 분산돼 의사결정 시간이 늘어남. 인지 부하 관점에서 손실.
  - 매일 3~5회 진입 (반복 사용) 인데 매번 화려하면 시각 피로가 누적됨.
- **HOW**:
  - 영양 수치·점수·차트는 18pt+ 굵은 폰트, 본문 검정 #191F28
  - 버튼·카드 보더는 #EEF1F6 옅은 회색만, 그림자는 elev 1 한 단
  - 배경은 #FFFFFF (콘텐츠 외 시각 노이즈 최소화)

##### 원칙 2 — 카드로 묶는다

- **WHAT**: 정보 단위 = 카드 한 장. 한 카드 = 한 가지 주제 (오늘 영양 / 점수 / 최근 식사 / 챗봇 응답 등). 카드 안에서만 그래프·텍스트·CTA 가 결합.
- **WHY (UX 근거)**:
  - Gestalt 의 **근접성 법칙** — 가까이 있는 요소는 한 묶음으로 인식됨. 카드는 시각적 경계로 "이건 한 묶음" 을 즉시 알려줌.
  - 헬스 데이터는 종류가 많음 (탄단지·칼로리·영양소·체중·운동). 묶지 않으면 무엇이 어디 속하는지 파싱 불가.
  - 모바일 작은 화면에서 스크롤 시 카드가 끊어야 할 단위가 됨 → 끝까지 안 봐도 카드 하나 단위로 정보 흡수 가능.
- **HOW**:
  - 카드 라디우스 16, 패딩 16~20, 카드 사이 간격 16dp+
  - 카드 안에서 타이틀(상) → 데이터(중) → CTA(하) 위계
  - 카드 단위로 page-break 자연스러움

##### 원칙 3 — 그림자 1단

- **WHAT**: 모든 카드에 같은 elev 1 그림자만 사용 (rgba 0,0,0,0.04 / blur 12 / y 4). 떠 있는 카드(BottomSheet 등) 는 elev 2, 모달은 elev 3.
- **WHY (UX 근거)**:
  - 그림자 단계가 많으면 사용자는 어떤 게 더 중요한지 시각 위계를 추측해야 함 → 인지 부하.
  - 한 단으로 통일하면 모든 카드가 동등하게 "탭 가능한 콘텐츠 단위" 로 인식됨.
  - 그림자가 미세하면 **저시력·시니어·다크 모드** 사용자에게도 카드 경계가 무너지지 않음 (그림자 의존하지 않고 보더와 여백으로 구분).
- **HOW**:
  - elev 1 외 다른 그림자 두께 금지
  - 다크 모드 시 그림자 alpha 를 0.04 → 0.30 로 자동 증가 (눈에 안 보이면 보더로 대체)

##### 원칙 4 — 컬러는 의미만

- **WHAT**: 컬러는 장식이 아니라 **약속된 의미** 를 전달함.
  - 브랜드 블루 #3182F6 = "탭 가능한 메인 액션"
  - 노란 #FFC700 = 캐릭터·하이라이트 (감정 톤)
  - 초록 #00C471 = 성공/긍정 영양
  - 빨강 #E53E3E = 위험/주의 영양·에러
  - 주황 #FF9500 = 경고·중간 영양
  - 회색 = 비활성·보조 정보
- **WHY (UX 근거)**:
  - Lemon Aid 가 보여주는 데이터(영양 점수 등) 가 **컬러로 의미를 전달** 해야 함 — "이 음식 점수가 좋다/나쁘다" 를 0.3초 안에 판단해야 하기 때문.
  - 만약 컬러가 장식이면 정보 컬러와 충돌해 의미 전달이 안 됨 (사용자: "이 빨강이 위험인지 그냥 디자인인지?")
  - 색맹·시니어 사용자를 위해 컬러만으로 의미 전달 X. 항상 컬러 + 텍스트 라벨 병기 (예: 빨강 점 옆에 "주의" 텍스트).
- **HOW**:
  - 위 5색 외 컬러 신규 추가 시 다이어리 결정 필요
  - 영양 카드 NutrientBar 는 색 + 라벨 + 수치 3중 표기 (§14.8 결정)

##### 원칙 5 — 8 그리드

- **WHAT**: 모든 간격·라디우스가 4 또는 8 의 배수. xs 4 / sm 8 / md 12 / lg 16 / xl 24 / xxl 32 / xxxl 48.
- **WHY (UX 근거)**:
  - Material/HIG 모두 8 그리드 기반 — 사용자가 이미 다른 앱에서 학습한 시각 리듬과 일치 → 익숙함.
  - 8 의 배수는 다양한 화면 밀도(mdpi/hdpi/xhdpi) 에서 픽셀 정렬이 깨지지 않음 → 시각적 깔끔함.
  - 임의 간격(13dp, 17dp 등) 이 섞이면 화면 사이 일관성이 사라져 "디자이너가 만든 듯" 안 보임.
- **HOW**:
  - 간격 토큰만 사용 (AppSpace.xs ~ xxxl)
  - 라디우스도 8 그리드 베이스 (8, 12, 16, 20, 24)
  - 폰트 크기는 의미적 위계 (display 32, title 24, subtitle 18, body 15) — 그리드와 별개

#### 14.10.5 토큰 사전 (코드 매핑 → `mobile/lib/utils/design_tokens_v2.dart`)

```
─── 컬러 ──────────────────────────────
Base bg:              #FFFFFF  (전체 화면 배경)
Surface elev:         #FFFFFF  (카드)
Surface sunken:       #F7F8FA  (인풋 필드 베이스 — 살짝 회색)
Surface section:      #F2F4F6  (섹션 구분 배경)

Border:               #EEF1F6  (카드 보더 1px 또는 0px + 그림자)
Border strong:        #DEE2E8  (인풋 보더 1px)
Border focus:         #3182F6  (브랜드 블루, 인풋 focus)
Border error:         #E53E3E
Border ok:            #00C471  (Toss 톤 그린)

Ink primary:          #191F28  (본문)
Ink secondary:        #4E5968  (부제, 본문 보조)
Ink tertiary:         #8B95A1  (캡션, placeholder)
Ink disabled:         #C5C8CE

Brand primary:        #3182F6  (Toss 블루)
Brand pressed:        #1B64DA  (눌림)
Brand bg soft:        #EBF3FE  (배경 박스, chip)

Accent yellow:        #FFC700  (캐릭터/하이라이트만, 메인 X)
Kakao yellow:         #FEE500
Apple black:          #1A1F2E

Success:              #00C471
Warning:              #FF9500
Danger:               #E53E3E

─── 그림자 ────────────────────────────
Elev 1 (카드):
  rgba(0, 0, 0, 0.04)  blur 12  offset (0, 4)
Elev 2 (떠있는 카드 / BottomSheet 상단):
  rgba(0, 0, 0, 0.06)  blur 20  offset (0, 8)
Elev 3 (모달):
  rgba(0, 0, 0, 0.12)  blur 40  offset (0, 16)

─── 라디우스 ──────────────────────────
xs:   8   (chip, 작은 태그)
sm:   12  (인풋, 작은 버튼)
md:   16  (카드, 메인 버튼)
lg:   20  (큰 카드)
xl:   24  (모달, BottomSheet 상단)
full: 999 (pill, 아바타)

─── 간격 ──────────────────────────────
xs:   4
sm:   8
md:   12
lg:   16
xl:   24
2xl:  32
3xl:  48

─── 타이포 (Pretendard) ────────────────
display:  32 / 700 / -1.2  (히어로 타이틀)
title:    24 / 700 / -0.8  (화면 타이틀)
subtitle: 18 / 600 / -0.5
body lg:  17 / 500
body:     15 / 500
caption:  13 / 500
micro:    11 / 600
```

#### 14.10.6 컴포넌트 원칙

**Card**
- 흰 배경 + Elev 1 그림자 (보더 X 또는 1px #EEF1F6)
- 라디우스 16
- 패딩 16~20
- 콘텐츠를 박스로 묶는 기본 단위

**Primary Button**
- Brand #3182F6 솔리드 + 흰 텍스트
- 라디우스 12
- 높이 54 (모바일 표준)
- 그림자 없음
- pressed: opacity 0.85 또는 색 #1B64DA
- 폭: 풀폭 (모달 안에선 자체 폭)

**Secondary Button**
- 흰 배경 + 1px #DEE2E8 보더 + Ink primary 텍스트
- 그림자 없음

**Input**
- Surface sunken (#F7F8FA) 베이스 + 보더 없음
- focus: 보더 #3182F6 1.5px (또는 베이스 → 흰 + 보더)
- 라디우스 12
- 높이 56
- placeholder Ink tertiary
- label 위에 caption 으로 표시 (안쪽 floating X)

**List Item**
- 좌측 16 / 우측 16 / 상하 14 패딩
- 구분선 1px #EEF1F6 (마지막 X)
- pressed Ripple Brand bg soft

**Bottom Sheet**
- 상단 라디우스 24, 하단 0
- 드래그 핸들 4px × 36px Pill #C5C8CE
- Elev 3

**App Bar**
- 높이 56
- 좌측 백 ← 평면 (Material), 가운데 타이틀 18/600, 우측 액션
- 그림자 없음 (스크롤 시 1px #EEF1F6 보더)

#### 14.10.7 적용 순서

| 화면 | 작업 | 우선도 |
|------|------|--------|
| Login v3 | 새 톤 (Flat 2.0) | ★★★★ |
| Signup v2 | 새 톤 | ★★★★ |
| S-04 Verify Email | 새 톤 | ★★★ |
| S-05 Consent | 카드형 약관 4종 + 하단 확정 | ★★★ |
| S-06 Onboarding | 스텝 카드형 | ★★★ |
| S-07 Home | **Toss 홈 같은 카드 그리드** | ★★★★★ |

#### 14.10.8 캐릭터 정책

- 캐릭터(Lemon-Aid 공식)는 **장식·강조 영역에만** 사용 (Login 우상단, Splash, Empty State, 챗봇 아이콘, 알림)
- 일반 UI 요소(버튼·카드·인풋)에는 캐릭터 안 씀
- 색 강조도 캐릭터 옆에서만 노란색(#FFC700) 사용, 메인 액션은 브랜드 블루(#3182F6)

#### 14.10.9 v1.0 / v2.0 비교 (이력)

| 항목 | v1.0 뉴모 | **v2.0 Flat (채택)** |
|------|---------|---------------------|
| 배경 | 흰색 + 양면 그림자 | 흰색 + 카드별 미세 그림자 |
| 버튼 | 그림자 양면 | 솔리드 색 + 그림자 X |
| 인풋 | inset 셰도우 | sunken 베이스 + focus 보더 |
| 카드 | 그림자만 | 보더 1px + 미세 그림자 |
| 모서리 | 14~20 | 12~24 (역할별 분리) |
| 시각 언어 | 물성·고급감 | 명확·실용·시중 앱 패턴 |

#### 14.10.10 아카이브 (마지막 갱신: 2026-05-12)

| 버전 | 톤 | 파일 | 상태 |
|-----|----|----|----|
| v3 (최종 채택) | Hybrid: Flat 2.0 + 뉴모 액센트 | `login_screen_v3.dart` | **메인 사용** |
| v2 (폐기) | 뉴모피즘 단독 | ~~`login_screen_v2.dart`~~ | **2026-05-12 파일 삭제** |
| v1 (폐기) | 초기 평면 | ~~`login_screen.dart`~~ | **2026-05-12 파일 삭제** |

폐기 사유:
- v2 뉴모 단독 → §14.10.3 기각된 대안 표 참조 (가독성·접근성·콘텐츠 우선 원칙 위배)
- v1 평면 단독 → 차가움·평이함 (정체성 §14.10.0 의 "따뜻함" 부족)

---SPLIT---

### 14.11 인풋·라벨 디자인 정의 (AppTextField, 2026-05-12 ★★★★ 최우선)

> Lemon Aid 의 모든 텍스트 입력은 `AppTextField` (design_tokens_v2.dart) 만 사용한다.
> 화면별로 색·크기 재정의 금지 — 일관성·접근성·시니어 모드 동시 호환을 위해.

#### 14.11.0 왜 인풋이 이 앱에서 가장 중요한 컴포넌트인가

**Lemon Aid 는 본질적으로 "사용자 데이터 입력 앱" 이다.**
일반 미디어 소비형 앱(SNS·동영상·뉴스)이 콘텐츠를 "보여주는" 데 무게를 둔다면, Lemon Aid 는 사용자가 **자기 데이터를 직접 적는** 비중이 압도적이다.

| 입력 시점 | 빈도 |
|---------|-----|
| 가입 (이메일·비번·닉네임·동의·신체 정보) | 1회 / 약 8필드 |
| 매일 식사 기록 (음식명·양·시간·메모) | 일 3~5회 / 회당 1~4필드 |
| 주간 체중·운동 기록 | 주 1~2회 |
| AI 챗봇 질문 | 일 0~3회 / 자유 텍스트 |
| 프로필 수정 | 비정기 |
| 검색·필터 | 비정기 |

> **누적**: 평균 사용자 1주 = **20~40회 인풋 진입**.
> 인풋 1개의 작은 마찰(라벨 안 보임, 보더 깨짐, focus 모호함, 키보드 동선 어색) 이 **누적 시 이탈로 직결**.

**인풋이 실패하면 앱 전체가 실패한다.**

- 가입 1단계에서 비번 검증 실패 → 사용자 60% 이탈 (업계 통계)
- 매일 식사 기록 입력이 어색 → 1주 안에 사용 중단
- 챗봇 입력바 가독성 ↓ → AI 가치를 못 전달

따라서 **인풋·라벨은 다른 어떤 컴포넌트보다 디자인·검증·접근성·시니어 모드 호환에 가장 먼저 손이 가야 함.**

#### 14.11.0.1 인풋 디자인 5대 우선순위 (Lemon Aid 전용)

| # | 원칙 | 이유 (UX 근거) |
|---|------|--------------|
| 1 | **즉시 인지 (Affordance)** | 인풋 박스가 0.3초 안에 "여기 적는다" 라는 시각 단서를 줘야 함 — 회색 베이스 + 보더 + 라벨 항상 노출 |
| 2 | **명확한 피드백 (Feedback)** | 입력 도중 OK/Error 즉시 보임 → 사용자가 "잘 하고 있나?" 의문 없이 진행 |
| 3 | **실패해도 회복 가능 (Recovery)** | 에러 메시지가 "왜 틀렸는지" 명확히 + 어떻게 고치는지 안내 (예: "8자 이상, 영문+숫자") |
| 4 | **모든 사람 다 쓸 수 있음 (Accessibility)** | 시니어·저시력·키보드 사용자 모두 인풋 도달 가능 — 라벨 크기·보더 대비·자동 포커스 |
| 5 | **반복해도 피로 없음 (Endurance)** | 매일 진입해도 시각 노이즈 X — 평소 톤 차분, 액션 시점에만 색 강조 |

이 5가지 모두 충족해야 하는 이유는 위 §14.11.0 의 "주 20~40회 진입" 때문.

---

#### 14.11.1 구조

```
┌─────────────────────────┐
│  라벨 (인풋 위, 좌측 2dp)  │  fontSize 13 / w600 또는 w700
│                         │  ↕ 8dp
│ ┌─────────────────────┐ │
│ │ [hint or value]   ✓ │ │  높이 56 / radius 12 / 좌우 padding 18
│ └─────────────────────┘ │  보더 1.2~1.5px (상태별)
│                         │  ↕ 6dp
│  helper / error         │  fontSize 13 / inkTertiary or danger
└─────────────────────────┘
```

#### 14.11.2 상태표 (4 상태)

| 상태 | 베이스 색 | 보더 | 라벨 색 | 라벨 굵기 | 우측 아이콘 |
|------|---------|------|-------|---------|----------|
| **평소 (default)** | `#FFFFFF` 흰색 | `#E5E9F0` 1.2px (옅음) | `#4E5968` inkSecondary | w600 | 없음 |
| **Focus** | `#FFFFFF` 흰색 | **`#3182F6` brand 1.5px** | **`#3182F6` brand** | **w700** | 없음 |
| **OK** (검증 통과) | `#FFFFFF` 흰색 | **`#00C471` success 1.5px** | `#4E5968` inkSecondary | w700 | ✓ 초록 20dp |
| **Error** | **`#FFF5F5` 옅은 빨강** | **`#E53E3E` danger 1.5px** | **`#E53E3E` danger** | **w700** | 사용자 정의 (👁 토글 등) |

상태 전환은 `AnimatedDefaultTextStyle` + `AnimatedContainer` 120ms — 색·굵기 부드럽게.

#### 14.11.3 라벨 명세

- 폰트: Pretendard 13pt / letterSpacing -0.3 / height 1.0 (박스에 안 차게)
- 위치: 인풋 상단 8dp, 좌측 2dp (인풋 모서리와 정렬)
- 동적 색: 상태에 따라 변화 (위 상태표)
- 굵기 변화는 시각 단서 강화 목적 (특히 시니어 모드)
- **금지**: 라벨에 절대 placeholder 안 넣음. 라벨 = 항상 표시되는 필드명. 입력 안 한 상태에서도 라벨이 보임 → 50대 페르소나가 "지금 어디에 뭘 쓰는지" 즉시 인지.

#### 14.11.4 인풋 본체 명세

- 높이: 56dp (모바일 터치 표준, 시니어 모드 64dp)
- 라디우스: 12 (AppRadius.sm)
- 좌우 padding: 18dp
- 보더: **CustomPaint (_OutlinedBorderDecoration)** 로 직접 그림 — Flutter 의 BoxDecoration / ShapeDecoration border 가 모서리에서 누락되는 렌더링 버그 회피.
- 보더 두께: 평소 1.2px / 상태별(focus·error·ok) 1.5px → 시각 단서 강화
- 보더 색은 상태에 따라 (위 상태표). 두께 변화는 1.2 ↔ 1.5 만 사용 (모서리 흔들림 최소화).
- 폰트: Pretendard 17pt / w600 / `#191F28` ink
- placeholder: 17pt / `#8B95A1` inkTertiary

#### 14.11.5 helper / error 명세

- 인풋 하단 6dp, 좌측 4dp
- 폰트: 13pt / 평소 inkTertiary `#8B95A1` / error 시 danger `#E53E3E`
- helper 는 입력 안 한 상태에서만 보이고, 입력 시작하면 사라지거나 검증 메시지로 교체
- error 우선순위 최고 — helper 가 있어도 error 가 떴으면 error 만 표시

#### 14.11.6 비밀번호 / 마스킹 필드 추가 명세

- `obscure: true` 일 때 우측 `IconButton` 으로 👁 토글
- 토글 아이콘 색: `inkTertiary`, size 22
- 토글 후 3초 자동 마스킹 복귀 (보안 기본값 — TODO D2 추후 구현)
- 시니어 모드: 토글 기본 ON (마스킹 풀린 상태)

#### 14.11.7 UX 근거 요약

| 디자인 결정 | UX 근거 |
|-----------|--------|
| 라벨 항상 노출 (floating X) | 50대 시니어가 입력 후 "여기에 뭘 적었지?" 다시 확인 가능 / placeholder 만 있는 floating 패턴은 채워지면 라벨이 안 보여 인지 부담 |
| 평소 보더 옅게 (1.2px 옅은 회색) | 콘텐츠 우선 원칙 (§14.10.4) — 평소엔 시각 노이즈 최소 |
| Focus 시 라벨·보더 동시 강조 (브랜드 색 + w700) | 사용자가 현재 어느 필드에 입력 중인지 즉시 인지 (시각 + 색상 단서) |
| Error 시 베이스 옅은 빨강 추가 | 보더만으로는 약함, 배경 색 변화가 강한 시각 경고 |
| OK ✓ 우측 표시 | 입력 도중에도 "이미 통과" 즉시 피드백 → 진행감 |
| AnimatedDefaultTextStyle 120ms | 너무 빠르면 깜빡임, 너무 느리면 답답함. Material 표준 |

#### 14.11.8 시니어 모드 자동 분기

| 토큰 | 일반 | 시니어 |
|------|-----|------|
| 인풋 높이 | 56 | 64 |
| 폰트 (입력값) | 17 | 19 |
| 라벨 폰트 | 13 | 15 |
| 보더 두께 평소 | 1.2 | 1.5 |
| 보더 두께 상태 | 1.5 | 2.0 |
| 비밀번호 마스킹 | 기본 ON | 기본 OFF (보이게) |

(시니어 토큰은 `AppText.elderly*` 및 `AppTextField.elderMode` prop 로 추후 추가 예정)

#### 14.11.9 화면별 인풋 사용 매핑 (14개 전체)

> 14개 화면 중 **12개가 인풋을 포함**. 인풋 디자인 변경 시 영향 범위 = 앱 전체.

| 화면 | 인풋 개수 | 종류 | 중요도 | 비고 |
|------|--------|-----|------|-----|
| S-01 Splash | 0 | — | — | 자동 라우팅 |
| S-02 Login | 1 | 이메일·비번 (BottomSheet 안) | ★★ | OAuth 우선이라 직접 입력은 줄임 |
| **S-03 Signup** | **4** | 이메일·비번·비번확인·닉네임 | ★★★★ | 첫 진입 — 실패 시 이탈 직결 |
| S-04 Verify Email | 1 (OTP) | 6자리 코드 (별도 컴포넌트) | ★★★ | AppTextField 미사용, 별도 OTPField |
| S-05 Consent | 0 | 체크박스 4 | ★ | 체크 토글만 |
| **S-06 Onboarding** | **5+** | 키·체중·생년월일·성별·식이 선호·알레르기 | ★★★★ | 신체 데이터 — 신뢰감 필수 |
| **S-07 Home** | **1** | 검색바 | ★★★ | 매일 진입, 음식 찾기 |
| S-08 Profile | 3+ | 닉네임·자기소개·목표 | ★★ | 비정기 |
| **S-09 Camera** | **1** | 음식 메모 (선택) | ★★★ | 사진 분석 후 보정 |
| **S-10 Score** | **2** | 음식 양·시간 수정 | ★★★ | 분석 결과 보정 |
| S-11 Health | 2 | 체중·운동 시간 | ★★★ | 주 1~2회 |
| **S-12 Chat** | **1** | AI 챗봇 입력바 (멀티라인) | ★★★★ | AI 가치 전달 핵심 |
| S-13 Settings | 비정기 | 비번 변경 등 | ★ | 가끔 |
| S-14 Raffle | 1 | 응모 정보 | ★ | 이벤트 |

**합계**: 12개 화면 × 평균 2.5 필드 = **30+ 인풋 인스턴스** 가 앱 안에 존재.
모두 동일한 `AppTextField` 위젯 + 동일한 디자인 토큰을 따른다.

#### 14.11.10 인풋 변형 (AppTextField 확장)

| 변형 | 용도 | 차이 |
|------|----|----|
| 기본 AppTextField | 단일 라인 | §14.11.4 |
| AppTextField (obscure) | 비밀번호 | 마스킹 + 👁 토글 |
| AppMultilineField (TODO) | 챗봇 입력바 / 메모 | minLines 1, maxLines 5, 자동 높이 확장 |
| AppNumberField (TODO) | 체중·키·양 | 숫자 키패드 + 단위(kg, g) suffix |
| AppDateField (TODO) | 생년월일·기록 시간 | 탭하면 시스템 DatePicker |
| AppOTPField | 6자리 인증 코드 | §14.7 S-04 별도 명세 |
| AppSearchBar (TODO) | 음식 검색 | 좌측 돋보기 + 우측 X clear + 자동 완성 |

**확장 원칙**: 위 변형 모두 `AppTextField` 의 토큰(보더·라디우스·라벨)을 그대로 상속. 색·크기 재정의 금지.

---SPLIT---

### 14.12 컬러 시스템 확정 (2026-05-12 ★★★★)

> **메인 2색**: `#4C7EF7` 브랜드 블루 + `#FFC700` 레몬 옐로
> 이 두 색만이 Lemon Aid 의 정체성을 시각화한다. 나머지는 그레이 + 시맨틱 표준.

#### 14.12.1 메인 2색

| 색 | HEX | 역할 | UX 근거 |
|----|-----|-----|--------|
| **브랜드 블루** | `#4C7EF7` | 모든 액션·CTA·링크·focus 단서·로그인·Primary 버튼 | 헬스/금융 카테고리의 학습된 패턴 = 푸른계열 = 신뢰. 채도 높은 라이트 블루로 차가움 톤다운 (의료기기 블루 회피). 흰 배경 위 대비비 4.52 (AA 본문 통과) |
| **레몬 옐로** | `#FFC700` | 캐릭터·하이라이트·축하·성취 단서·로고 점 | Lemon Aid 의 브랜드 정체성. 블루(이성)와 옐로(감정) 가 보완색 관계 — 양극 강조로 시선 끌고 동시에 따뜻함 유지. 본문엔 안 쓰고 강조 영역에만 |

#### 14.12.2 보조 톤 (메인 2색의 변형)

| 토큰 | HEX | 용도 |
|------|-----|-----|
| `brandPressed` | `#2F66E2` | 버튼 눌림 / hover state |
| `brandSoft` | `#EDF3FF` | chip 배경, 옅은 강조 영역 (예: 폴백 안내 번호 박스) |
| `yellowSoft` | `#FFF6CC` | 노란 chip / 캐릭터 후광 / 성취 카드 배경 |

#### 14.12.3 시맨틱 컬러 (의미 전달용)

| 토큰 | HEX | 의미 | 사용 |
|------|-----|------|-----|
| `success` | `#00C471` | 성공·통과·긍정 영양 | OK 보더 / 점수 양호 / 체크 아이콘 |
| `warning` | `#FF9500` | 경고·중간 영양 | 점수 보통 / 주의 chip |
| `danger`  | `#E53E3E` | 위험·에러 | error 보더 / 점수 위험 / 삭제 |

> 시맨틱 컬러는 **반드시 텍스트·아이콘과 함께** 사용 (색맹 대응). 색만으로 의미 전달 금지.

#### 14.12.4 그레이 스케일 (잉크 + 표면)

| 토큰 | HEX | 용도 |
|------|-----|-----|
| `ink` | `#191F28` | 본문 / 타이틀 |
| `inkSecondary` | `#4E5968` | 부제 / 라벨 |
| `inkTertiary` | `#8B95A1` | 캡션 / placeholder / 비활성 백 버튼 |
| `inkDisabled` | `#C5C8CE` | 비활성 텍스트 |
| `borderStrong` | `#DEE2E8` | 강조 보더 (사용 X — 옅게 가는 중) |
| `border` | `#EEF1F6` | 카드 보더 |
| `sunken` | `#F7F8FA` | 인풋 평소 베이스 (사용 안 함, 흰색 통일) |
| `section` | `#F2F4F6` | 섹션 구분 배경 |
| `surface` | `#FFFFFF` | 카드·인풋 평소 |
| `bg` | `#FFFFFF` | 화면 전체 배경 |

#### 14.12.5 사용 매핑 (어디에 어떤 색)

| UI 요소 | 컬러 |
|--------|------|
| 화면 배경 | `bg` 흰색 |
| 카드·인풋 평소 | `surface` 흰색 |
| 본문 텍스트 | `ink` |
| 라벨·부제 | `inkSecondary` |
| placeholder | `inkTertiary` |
| 백 버튼·캡션 | `inkTertiary` |
| **메인 CTA Primary 버튼** | `brand #4C7EF7` |
| 버튼 누름 | `brandPressed #2F66E2` |
| 텍스트 링크 / focus 라벨 | `brand` |
| Focus 인풋 보더 | `brand` 1.5px |
| 캐릭터 / 로고 점 / 강조 chip | `yellow #FFC700` |
| 카카오 버튼 | `kakao #FEE500` (외부 가이드) |
| Apple 버튼 | `appleBlack #1A1F2E` (외부 가이드) |
| 영양 점수 양호 / OK 보더 / 체크 | `success` |
| 점수 보통 / 경고 chip | `warning` |
| Error 보더 / 위험 / 삭제 | `danger` |
| Error 인풋 배경 | `#FFF5F5` (danger 의 옅은 변형) |

#### 14.12.6 접근성 (대비비)

흰 배경(#FFFFFF) 기준 WCAG AA (4.5:1) 본문 통과 여부:

| 색 vs 흰 | 대비비 | AA 본문 | AA 큰 글자 |
|---------|--------|--------|---------|
| ink #191F28 | 16.6:1 | ✓ | ✓ |
| inkSecondary #4E5968 | 8.8:1 | ✓ | ✓ |
| inkTertiary #8B95A1 | 3.7:1 | ✗ | ✓ (큰 글자만) |
| brand #4C7EF7 | 4.52:1 | ✓ | ✓ |
| yellow #FFC700 | 1.7:1 | ✗ | ✗ — **본문 색으로 사용 금지** (배경·아이콘만) |
| success #00C471 | 2.7:1 | ✗ | ✓ (큰 글자만) |
| danger #E53E3E | 4.1:1 | ✗ (4.5 직전) | ✓ |

> ⚠ **노란색을 텍스트로 사용 금지** — 대비 1.7 로 본문 가독성 X. 캐릭터·로고 점·배경 chip 에만.

#### 14.12.7 시니어 모드 (대비 강화)

시니어 모드 활성화 시 토큰 자동 swap:

| 일반 → 시니어 |
|--------------|
| `inkSecondary #4E5968` → `ink #191F28` (라벨도 본문 검정) |
| `inkTertiary #8B95A1` → `inkSecondary #4E5968` (캡션도 짙게) |
| `border #EEF1F6` → `borderStrong #DEE2E8` (보더 진하게) |
| `brand #4C7EF7` (본문 링크) → `brandPressed #2F66E2` (더 진한 블루) |

#### 14.12.8 다크 모드 (추후)

원칙:
- 배경 `#0F1419` (순흑 아닌 따뜻한 검정)
- 카드 `#1A1F28`
- 잉크 반전 (`#FFFFFF` 본문)
- 브랜드 블루는 **더 밝게** `#7BA4FA` (어두운 배경 대비)
- 노란 그대로 (`#FFC700` 는 다크에서도 잘 보임)
- 시맨틱은 모두 채도 ↓ 명도 ↑ 톤 보정

#### 14.12.9 사용 원칙 (한 줄)

> **메인은 두 색뿐.** 블루 = 액션, 옐로 = 정체성. 나머지는 그레이.

---SPLIT---

### 14.13 모달·다이얼로그 디자인 정의 (2026-05-12 ★★★)

> 출처: Claude Design Handoff `Lemon Aid Modals.html` (2026-05-12)
> 채택 시안: **02 Soft Hybrid** / **04 BottomSheet** / **06 Celebrate**
> 톤 원칙: **"명확하고 직관적인 Flat 2.0 구조 + 뉴모피즘 부드러운 감성"**

#### 14.13.0 왜 별도 모달 시스템인가

모달은 "사용자의 흐름을 잠시 멈추고 결정을 묻는" 공간이다. 본 화면의 정보 카드와는 **시각 무게가 달라야** 한다 — 그래야 "지금 결정이 필요하다" 라는 인지가 즉시 일어남.

| 본 화면 | 모달 |
|--------|------|
| Flat 2.0 (콘텐츠 우선) | Hybrid (뉴모 감성 더 강조) |
| 카드 그림자 elev 1 (옅음) | 모달 그림자 elev 3 (강) + Backdrop blur |
| 컬러 차분 | Primary 글로우 / 노란 캐릭터 컬러 적극 |

즉, **모달에서만 뉴모피즘 비율을 30~40% 까지 올린다.** 일상 화면(10~20%) 보다 감성 강도 ↑.

#### 14.13.1 3종 위젯 매트릭스

| # | 위젯 | 용도 | 등장 | 그림자 |
|---|------|------|-----|------|
| 1 | **AppDialog** (Soft Hybrid) | Confirm / Alert — 결정 묻기 | 중앙 / scale + fade | section bg + 흰 inset border + soft drop |
| 2 | **AppBottomSheet** | 옵션 리스트 / 폴백 안내 / 멀티 액션 | 하단 슬라이드 + scrim 0.5 | 상단 라디우스 28 + 위쪽 그림자 |
| 3 | **AppCelebrateDialog** | 성취·축하 (가입 완료·목표 달성) | 중앙 / scale-back + blur 6px | 노란 글로우 + confetti 점 |

#### 14.13.2 토큰 (Claude 시안 기반)

```
─── Scrim ──────────────────────
Default:   rgba(20, 26, 44, 0.45)
Soft:      rgba(20, 26, 44, 0.35)  + backdropFilter blur 2px
Celebrate: rgba(20, 26, 44, 0.50)  + backdropFilter blur 6px

─── Container ──────────────────
Dialog bg:      section #F2F4F6  + 흰 inset border (Soft Hybrid)
Sheet bg:       section #F2F4F6
Celebrate bg:   surface #FFFFFF
Inner card:     surface #FFFFFF  (Sheet 내부 행 컨테이너)

Radius:   Dialog 28 / Sheet top 28 / Celebrate 28
Padding:  Dialog 24/28 / Sheet 20+12+28

─── Shadow ─────────────────────
Modal drop:   0 30px 60px -10px rgba(20, 26, 44, 0.35)
Sheet up:     0 -20px 40px -10px rgba(20, 26, 44, 0.25)
Celebrate:    0 24px 60px -12px rgba(20, 26, 44, 0.28)

─── Buttons ────────────────────
Primary:  brand solid + glow blur 14 spread -4 / alpha 0.55
Inset:    section bg + 내부 어둠 4px (Secondary)
Danger:   text-only red (Confirm 의 secondaryDanger=true)
Celebrate Primary: ink #171A22 + 옅은 ink 그림자
```

#### 14.13.3 사용 매핑 (어떤 상황에 어떤 모달)

| 상황 | 모달 종류 | 예시 |
|------|---------|-----|
| 작성 중 데이터 날아감 경고 | **AppDialog** (Soft) + Primary "계속 작성" / Secondary danger "나가기" | Signup 백 버튼 |
| 단순 확인 (Yes/No) | **AppDialog** + Primary "확인" / Secondary "취소" | 알림 끄기 / 로그아웃 |
| 단일 안내 (OK) | **AppDialog** + Primary "확인" 만 | 인증 완료·서버 에러 |
| 다중 옵션 (3+) | **AppBottomSheet** + 옵션 리스트 | 이메일 폴백·정렬 옵션·공유 |
| 위험 결정 (계정 삭제 등) | **AppDialog Hero** (03 시안, 추후 추가) | 노란 경고 아이콘 + 강조 |
| 성취·축하 | **AppCelebrateDialog** + confetti | 가입 완료 / 목표 달성 / 7일 연속 기록 |

#### 14.13.4 인터랙션·모션

| 동작 | 사양 |
|------|-----|
| Dialog 등장 | fade + scale 0.96→1.0, 220ms easeOutCubic |
| Celebrate 등장 | scale 0.85→1.0, 280ms **easeOutBack** (살짝 튀는 느낌) |
| Sheet 등장 | slide-up, 시스템 기본 (showModalBottomSheet) |
| Backdrop 탭 | Dialog/Sheet — 닫힘 (`barrierDismissible: true`). Celebrate — 닫힘 X (꼭 액션 눌러야) |
| 키보드 | Sheet 자동 따라옴 (`isScrollControlled: true`) |
| 햅틱 | Primary lightImpact / Danger Secondary mediumImpact (추후) |

#### 14.13.5 UX 근거 (왜 이렇게 설계했나)

| 결정 | UX 근거 |
|------|---------|
| Dialog 만 뉴모 액센트 강조 | 일상 화면(평면) ↔ 모달(부드러운 입체) 시각 무게 차이로 "결정 필요" 즉시 인지 |
| Soft Hybrid Primary 우측·flex 1.4 | 한국어 권장 방향 — 긍정 액션이 시선 끝(우측), 약간 더 크게 강조 |
| Secondary 좌측 inset | 눌림 자체로 "되돌리는 액션" 시각 단서 |
| Danger 는 text-only (빨강) | 빨강 솔리드는 위험 강조이지만 매번 쓰면 둔감화. 빨강 텍스트 = 부드럽지만 명확 |
| Celebrate scale-back (easeOutBack) | 살짝 튀는 모션 = 긍정 감정 강화. 220ms 보다 살짝 길게(280ms) |
| Celebrate barrierDismissible false | 사용자가 성취 화면을 충분히 보고 결정을 내리도록 |
| BottomSheet 흰 카드 + 뉴모 그림자 | 모바일 한 손 사용 시 하단 = 손가락 도달 영역. 카드 안에 리스트로 묶어 스캔성 ↑ |
| Confetti 점 6개 | 너무 많으면 키치, 너무 적으면 단조. 6개가 시각 임팩트 + 단정함 균형 |

#### 14.13.6 코드 매핑

| 위젯 | 파일 | API |
|------|----|-----|
| AppDialog | `widgets/common/app_modals.dart` | `showAppDialog(context, title, body, primaryLabel, secondaryLabel, dangerSecondary)` → Future<bool?> |
| AppBottomSheet | 동일 | `showAppBottomSheet(context, title, subtitle, items: [AppBottomSheetItem(...)])` |
| AppCelebrateDialog | 동일 | `showAppCelebrateDialog(context, title, body, primaryLabel, icon, onPrimary)` |

#### 14.13.7 적용 화면

| 화면 | 모달 | 비고 |
|------|------|----|
| S-03 Signup | AppDialog "나가시겠어요?" | 백 버튼 + 작성 중일 때 |
| S-04 Verify Email | AppBottomSheet "이메일이 안 와요" | 4 옵션 (재발송·주소 수정·스팸함·문의) |
| S-04 Verify Email | (추후) AppCelebrateDialog "가입 완료!" | 인증 성공 후 |
| S-05 Consent | (추후) AppDialog "필수 동의가 빠졌어요" | 약관 미동의 |
| S-07 Home | (추후) AppCelebrateDialog "7일 연속 기록!" | 성취 트리거 |

#### 14.13.8 폐기된 시안

| 시안 | 폐기 사유 |
|------|--------|
| 00 Current Material | Material 기본 너무 평이, Lemon Aid 정체성 약함 |
| 01 Flat 2.0 Pure | 너무 차가움. 뉴모 감성 미반영 |
| 03 Hero Icon | 일상 사용에는 과함. 계정 삭제 등 고감정 결정 시점에 검토 (추후 추가) |
| 05 Action Sheet | iOS 스타일 강함. Android 사용자 다수라 BottomSheet 로 통합 |

---SPLIT---

### 14.14 UI px 가이드 (라이브 문서, 함께 만들어가는 중)

> **이 페이지는 화면을 만지면서 함께 결정해 가는 공간이다.**
> 모든 px 값은 한번 정해진 뒤에도 사용자 피드백·실기기 검증을 거쳐 미세 조정될 수 있다.
> 변경 시 날짜와 이유를 같이 기록.

#### 14.14.0 작성 원칙

- 화면 단위로 섹션 구분 (Login / Signup / Verify Email …)
- 각 행: **요소 ↔ 위/아래/좌/우 px** + **결정 이유** + **마지막 변경 날짜**
- 토큰 시스템(§14.10.5) 와 충돌 시 — 토큰 우선. 토큰 변경은 별도 결정 필요.
- "여기 좀 더 내려" / "5px 올려" 같은 미세 조정은 모두 여기 누적.

#### 14.14.1 S-02 Login

| 영역 | 값 | 결정 이유 | 마지막 |
|------|----|--------|------|
| 화면 좌·우 패딩 | 24 (xl) | 표준 모바일 좌우 24 — 시니어 모드 28 검토 | 2026-05-12 |
| Status bar ↔ 워드마크 | 48 + 13 = 61 | 시각적 안정감, 워드마크 강조 | 2026-05-12 |
| 워드마크 폰트 | 한글 44 / Aid 44 / w800 / letterSpacing -1.8 | 한·영 동일 크기로 통일된 로고 인상 | 2026-05-12 |
| 워드마크 ↔ 태그라인 | 12 | — | 2026-05-12 |
| 태그라인 → Spacer → 캐릭터 | Flex Spacer | 화면 크기 무관 | 2026-05-12 |
| 캐릭터 크기 | 200×200 | 양손 다 보이는 최소 크기 | 2026-05-12 |
| 캐릭터 Transform.translate | (0, 28) | 카카오 버튼 위 18px 여유 | 2026-05-12 |
| 캐릭터 ↔ 툴팁 | 8 | — | 2026-05-12 |
| OAuth 버튼 간 | 12 (md) | — | 2026-05-12 |
| Apple ↔ 디바이더 | 24 (xl) | OAuth 영역 ↔ 이메일 영역 시각 분리 | 2026-05-12 |
| 디바이더 ↔ 회원가입·로그인 분할 | 12 (md) | — | 2026-05-12 |
| 분할 버튼 ↔ 약관 캡션 | 24 (xl) | — | 2026-05-12 |
| 회원가입 : 로그인 비율 | 1 : 2 | 기존 사용자(로그인) 우선 | 2026-05-12 |
| 버튼 높이 | 54 | 모바일 터치 표준 (시니어 60) | 2026-05-12 |
| 버튼 라디우스 | 12 (sm) | — | 2026-05-12 |

#### 14.14.2 S-03 Signup

| 영역 | 값 | 결정 이유 | 마지막 |
|------|----|--------|------|
| 상단 바 (백 + 1/1) | 좌 8 / 상 8 / 우 16 / 하 4 | 백 아이콘 splashRadius 22 | 2026-05-12 |
| 백 아이콘 색 | inkTertiary #8B95A1 | 진한 검정 부담스러움 | 2026-05-12 |
| 본문 상단 패딩 | 32 | 상단 바 ↔ 타이틀 호흡 공간 | 2026-05-12 |
| 본문 좌·우 패딩 | 24 (xl) | 화면 표준 | 2026-05-12 |
| 타이틀 "환영해요" | 32pt / w800 / letterSpacing -1.2 | 첫 진입 강한 인상 | 2026-05-12 |
| 타이틀 ↔ 서브 | 10 | — | 2026-05-12 |
| 서브 "이메일로 시작할게요" | bodyLg 17pt / inkSecondary | — | 2026-05-12 |
| 서브 ↔ 첫 인풋 | **64** | 88 → 64 (너무 멀어서 살짝 위로) | 2026-05-12 |
| 인풋 ↔ 인풋 | 24 (xl) | 라벨·에러 메시지 호흡 공간 | 2026-05-12 |
| 마지막 인풋 ↔ "다음" 버튼 | 32 (xxl) | 결정 액션 강조 | 2026-05-12 |
| "다음" 버튼 ↔ 캡션 | 12 (md) | — | 2026-05-12 |
| 인풋 높이 | 56 | 모바일 표준 (시니어 64) | 2026-05-12 |
| 인풋 라벨 ↔ 인풋 박스 | 8 | — | 2026-05-12 |
| 인풋 ↔ helper/error | 6 | — | 2026-05-12 |
| 라벨 폰트 | 13pt / 평소 w600 / focus·error w700 | §14.11.3 | 2026-05-12 |
| 인풋 입력값 폰트 | 17pt / w600 / ink | §14.11.4 | 2026-05-12 |

#### 14.14.3 S-04 Verify Email

| 영역 | 값 | 결정 이유 | 마지막 |
|------|----|--------|------|
| 본문 상단 패딩 | 16 → (조정 예정) | TODO 확인 | 2026-05-12 |
| 타이틀 "이메일 확인" | 32pt / w800 | Signup 과 동일 | 2026-05-12 |
| 타이틀 ↔ 이메일 강조 텍스트 | 12 | — | 2026-05-12 |
| 안내 → OTP | 40 | OTP 위 호흡 공간 | 2026-05-12 |
| OTP 칸 크기 | 44 × 56 | 한 손 엄지 도달 | 2026-05-12 |
| OTP 칸 사이 | 4 (3·4 칸 사이 8) | 6자리를 3·3 으로 시각 분리 | 2026-05-12 |
| OTP ↔ 타이머·에러 | 14 | — | 2026-05-12 |
| 타이머·에러 ↔ "확인" | 32 (xxl) | — | 2026-05-12 |
| "확인" ↔ 재발송·도움 | 16 (lg) | — | 2026-05-12 |

#### 14.14.4 AppDialog (모달)

| 영역 | 값 | 결정 이유 | 마지막 |
|------|----|--------|------|
| 카드 너비 | 320 | 한 화면에서 명확한 비율 | 2026-05-12 |
| 카드 라디우스 | 28 | 부드러운 감성 (뉴모 액센트) | 2026-05-12 |
| 카드 내부 패딩 | 좌 24 / 상 28 / 우 24 / 하 22 | — | 2026-05-12 |
| 타이틀 폰트 | 20pt / w800 / letterSpacing -0.4 | — | 2026-05-12 |
| 타이틀 ↔ 본문 | 8 | — | 2026-05-12 |
| 본문 폰트 | 14.5pt / w500 / inkSecondary / lineHeight 1.55 | — | 2026-05-12 |
| 본문 ↔ 버튼 | 24 | — | 2026-05-12 |
| 버튼 높이 | 50 | 일반 Primary(54)보다 살짝 작게, 카드 안 비율 | 2026-05-12 |
| 버튼 라디우스 | 16 | 카드 28 ↔ 버튼 16 위계 | 2026-05-12 |
| Primary : Secondary 비율 | 6 : 4 | Primary 살짝 강조 | 2026-05-12 |
| 버튼 사이 간격 | 10 | — | 2026-05-12 |

#### 14.14.5 변경 로그

| 날짜 | 변경 | 화면 |
|------|------|----|
| 2026-05-12 | Signup 서브타이틀 ↔ 첫 인풋 88 → 64 | S-03 |
| 2026-05-12 | Signup 본문 상단 16 → 32 | S-03 |
| 2026-05-12 | AppDialog Primary:Secondary 14:1 → 6:4 | Modal |
| 2026-05-12 | Login 워드마크 위 SizedBox 48 → 63 (= xxxl+15) | S-02 |

#### 14.14.6 워크플로

1. 화면 조정 요청 (예: "5px 올려")
2. 코드 수정 + hot reload 확인
3. **여기에 변경 기록** (날짜·요소·전→후·이유)
4. 1주 안정되면 토큰화 검토 — 같은 값이 3+ 화면에서 반복 사용 시 토큰으로 승격

> 라이브 문서이므로 모든 px 결정이 여기에 누적된다. 다음 화면 추가 시 같은 형식으로 섹션 신설.

- v1.0 뉴모 화면: `login_screen_v2.dart` 보존 (`/login-v2` devtools 라우트, 별도 보존용)
- v0 평면 LoginScreen: 이미 `/login-v1` 으로 보존됨

---SPLIT---

## 15. 인터랙션 · 모션

### 15.1 원칙

| 원칙 | 적용 |
|------|------|
| 의도 있는 모션만 | 장식 X |
| 빠르게 시작, 느리게 정착 | `easeOutCubic` |
| 짧게 | 200~300ms, 500ms↑ 의심 |
| Reduce Motion | 시스템 설정 시 fade만 |

### 15.2 Duration

| 모션 | Duration | Easing |
|------|----------|--------|
| 버튼 ripple | 100ms | linear |
| 탭 전환 | 200ms | easeOutCubic |
| 모달 열림 | 250ms | easeOutCubic |
| 모달 닫힘 | 200ms | easeInCubic |
| BottomSheet | 280ms | easeOutCubic |
| 화면 전환 | 300ms | easeInOutCubic |
| 토스트 등장 | 200ms | easeOutBack |
| Skeleton shimmer | 1500ms | linear 반복 |

### 15.3 햅틱 (iOS)

| 상황 | 햅틱 |
|------|------|
| 버튼 탭 | Light |
| 토글 | Medium |
| 분석 완료 | Success notification |
| 오류 | Warning notification |
| 응급 모달 | Heavy |

### 15.4 인터랙션 패턴

| 패턴 | 적용 |
|------|------|
| Pull to refresh | Dashboard·식단 목록 |
| Swipe to delete | 영양제·식단 항목 (확인 모달) |
| Long press | 메시지 복사·삭제 |
| Pinch to zoom | 영양제 라벨 사진 |
| Double tap | 사용 안 함 |

### 15.5 로딩·대기

| 시간 | UI |
|------|----|
| <0.4초 | 즉시 표시 |
| 0.4~1초 | Spinner |
| 1~4초 | Skeleton + 진행률 |
| 4~10초 | Skeleton + Streaming + 취소 |
| >10초 | 백그라운드 옵션 |

LLM (2.5~6초) → **Skeleton + Streaming + 취소**

---SPLIT---

## 16. 접근성 (WCAG 2.2 AA)

### 16.1 색 대비

| 텍스트 | 최소 | Lemon Aid |
|--------|------|-----------|
| 본문 16px | 4.5:1 | 12.4:1 ✅ |
| 큰 텍스트 18px+ | 3:1 | 12.4:1 ✅ |
| 아이콘 | 3:1 | 검수 필요 |

### 16.2 키보드 · 보이스오버

- 모든 액션 키보드 접근
- 포커스 링 (border 2px accent)
- 아이콘 버튼 `aria-label`
- 화면 진입 시 첫 헤딩 자동 읽기

### 16.3 Dynamic Type

- iOS Dynamic Type 7단계
- 200% 확대해도 레이아웃 유지 (Auto Layout)
- 비례 확대

### 16.4 동작 · 시간

- 자동 토스트 X
- 폼 timeout 최소 60초
- Reduce Motion 시 fade만

### 16.5 컬러블라인드

- 색만으로 정보 전달 X → 색 + 아이콘 + 라벨 3중
- Deuteranopia 시뮬레이션 통과 필요

---SPLIT---

## 17. A/B 실험 로그

### 17.1 템플릿

```
## EXP-001 — 짧은 제목

### 가설
"X 하면 Y가 좋아질 것 (Z만큼)"

### 변인
- A: 기존
- B: 변경

### 측정
- 지표 / 표본 N / 기간 D

### 결과
- A / B / p값

### 결정
- 채택안과 이유

### 회고
```

### 17.2 백로그

- EXP-001: Splash 1.5초 vs 1초
- EXP-002: Consent 일괄동의 유무
- EXP-003: 응모권 진입점 위치
- EXP-004: 챗봇 자동 인사말 ON/OFF
- EXP-005: 대시보드 카드 순서
- EXP-006: 큰 글씨 모드 토글 위치
- EXP-007: 면책 고지 모달 vs 인라인
- EXP-008: 의료법 카피 권유형 vs 정보형
- EXP-009: 사진 촬영 가이드
- EXP-010: 알림 디폴트 시간

---SPLIT---

## 18. 사용성 테스트

### 18.1 W7 — 내부 5명 + 멘토·자문위 3명

### 18.2 시나리오 5개 (각 5분)

1. **신규 등록** — 회원가입 → 동의 → 온보딩 → 홈
2. **영양제 등록** — 카메라 → 분석 → 미리보기 → 저장
3. **5종 출력 이해** — Dashboard 진입 → 부족 영양소 → 자세히
4. **챗봇 알림** — "매일 8시 혈압약 알림" → 승인
5. **설정 변경** — 큰 글씨 모드 ON·OFF, 동의 철회

### 18.3 측정

- 완료 시간
- 막힌 지점
- 정성 코멘트
- SUS 설문 (참고)
- "다시 쓰고 싶나" 5점

### 18.4 룰

- 도와주지 X
- 화면 녹화 (동의)
- "왜 안 되지?" = 디자인 실패
- 5명 중 3명 막힘 = 수정

### 18.5 출력물

- `docs/usability-w7.md`
- 다이어리 §17 EXP-XXX
- 큰 변경은 PG.md §4.2 PR

---SPLIT---

## 19. 디자인 결정 추적 (Decision Log)

| ID | 날짜 | 결정 | 상태 | 위치 |
|----|------|------|------|------|
| DL-001 | 05-13 | 다이어리 시작 | ✅ | §8 |
| DL-002 | 05-13 | 레몬 팔레트 5색 | ✅ | tokens.dart |
| DL-003 | 05-13 | 본문 16px | ✅ | tokens.dart |
| DL-004 | 05-13 | Splash 1.5초 | 🟡 구현 예정 | splash |
| DL-005 | 05-13 | Consent 일괄동의 X | ✅ | consent |
| DL-006 | — | 큰 글씨 모드 토글 | ⏳ 고민 중 | §9 |
| DL-007 | — | 다크 모드 v2 | 🟡 합의됨 | tokens 주석 |

**상태**: ⏳ 고민 / 🟡 합의 / ✅ 적용 / 📦 PG.md 이관 / 🗑 폐기

---SPLIT---

## 20. 속도 우선 워크플로

수정 잦음 + 시간 부족 = 완벽 X, **빠른 결정 → 빠른 폐기 → 빠른 반복**

### 20.1 5원칙

1. **80% 완성도로 일단 띄운다**
2. **버릴 것 같은 안도 만들어 본다**
3. **결정 5분 룰** — 5분 안에 못 정하면 동전
4. **돌이킬 수 있는 결정은 그냥** — 토론 X
5. **돌이킬 수 없는 결정만 깊이** — Brand color, 핵심 흐름, 데이터 모델

### 20.2 화면당 시간 박스

| 작업 | 권장 | 넘기면 |
|------|------|--------|
| Lo-fi 와이어프레임 | 15분 | 다음 화면 |
| Hi-fi 시안 | 60분 | 의사결정 보류 |
| 토큰 결정 | 10분 | 임시로 진행 |
| 마이크로카피 | 5분 | TODO 마킹 |
| 컴포넌트 1개 | 30분 | inline 스타일 |
| 의료법 검수 | 10분 | ⚠️ 마킹 + 자문위 |

### 20.3 의사결정 도구

#### 동전 (Reversible)
비슷한 두 안이면 동전. 1주일 후 회고에서 안 맞으면 바꿈.

#### RICE
`Reach × Impact × Confidence ÷ Effort`

#### Parking
확신 없으면 §19에 `⏳`로 박아두고 다른 화면 진행.

### 20.4 디자인 시스템 빠르게

| 단계 | 빠른 방법 |
|------|---------|
| 1. 색 | Variables 5개만 |
| 2. 타이포 | 5단계만 |
| 3. 간격 | 8px 그리드 (4·8·16·24·32·48) |
| 4. 컴포넌트 | Button·Card·Input·ListTile 4개 |
| 5. 확장 | 화면 만들면서 필요한 것만 |

처음에 모든 토큰 정의 X. **만들면서 채운다.**

### 20.5 Claude Code 위임 패턴

#### 일괄 셸 생성
```
@PROJECT_GUIDE.md §13
mobile/lib/screens/*.dart 13개 셸 만들어줘.
Scaffold + AppBar + 빈 Body. 토큰은 tokens.dart.
```

#### Figma → 코드
```
[Figma 스크린샷]
이 시안대로 lib/screens/dashboard_screen.dart 재작성.
tokens.dart 토큰만 사용. Auto Layout = Column + Row + Expanded.
```

#### 토큰 갱신
```
@mobile/lib/utils/tokens.dart
LemonColors 다음으로:
- primary: #ca8a04
- citrus: #facc15
```

#### 마이크로카피 일괄 검수
```
@mobile/lib/screens
모든 screens 사용자 텍스트에서 의료법 표현 검사.
위반 시 권유형 변환. diff 보여줘.
```

### 20.6 폐기 빠르게

- 30분 이상 안 본 시안 → 보류
- "왜 만들었지?" → 폐기
- A·B 못 정하면 둘 다 버리고 C
- 5명 중 3명 막힘 → 폐기

§19에 `🗑` 기록.

### 20.7 변경 알림

| 종류 | 알림 |
|------|------|
| 미세 조정 | 다이어리 §8만 (본인) |
| 컴포넌트 변경 | 채팅 + Figma |
| 토큰 변경 | 채팅 + commit |
| 화면 흐름 | 채팅 + Figma + §19 |
| 큰 방향 | PG.md PR + 스탠드업 |

미세는 본인, 큰 변경만 공지.

### 20.8 컨디션

- 2시간 작업 → 15분 휴식
- 하루 새 화면 3개 이상 X
- 금요일 오후는 회고만
- 다음날 아침 어제 결정 5분 검토

### 20.9 "완벽한 다이어리"

> **6개월 후 "왜 이렇게 디자인했지?" 답할 수 있는 최소 흔적**

5단 풀템플릿 X — **결정·근거 2단**도 충분:

```
## 2026-05-14 — Dashboard 카드 순서

### 결정
부족 영양소 가장 위, 점수 두 번째.

### 근거
김건강 JTBD = 약·영양제 충돌 확인. 점수보다 부족 영양소가 즉시 행동으로 연결.
```

---SPLIT---

## 21. 핸드오프 체크리스트

### 21.1 Figma 측

- [ ] Auto Layout 전체
- [ ] Variables 정의 (Light 기본, Dark 토큰)
- [ ] Inspect 토큰 이름 노출
- [ ] Constraint 설정
- [ ] 5상태 Variant
- [ ] Empty State
- [ ] Error State
- [ ] Loading (Skeleton)

### 21.2 코드 측 (mobile/lib/)

- [ ] tokens.dart Figma Variables 매핑
- [ ] 화면별 5상태 처리
- [ ] Reduce Motion 대응
- [ ] Dynamic Type 200%
- [ ] Semantic 라벨
- [ ] 의료법 카피 검수
- [ ] 면책 고지
- [ ] 응급 신호 단위 테스트

### 21.3 QA 측 (W7)

- [ ] iOS 시뮬레이터 (15 / SE)
- [ ] Android (Pixel 7 / Galaxy A)
- [ ] 실기기 1대
- [ ] 50대 사용자 1명 시연
- [ ] 의료자문위 1회
- [ ] 응급 신호 케이스 5개

---

> 본 다이어리는 태동 개인 작업 기록.
> 자유롭게 수정·실험·메모. PG.md는 안정된 합의만.
> §1.4 이관 시점 판단 기준 보고 굳어진 것만 PG.md로 옮긴다.
> 매일 한 줄이라도 쓴다. 안 쓴 날은 안 쓴 채로 둔다.
