# Lemon Healthcare 팀 공유 보고서 - 2026-05-20 작업 내용 정리 (taedong-design)

## 한 줄 요약

어제(5/19) 회원가입 10-step + 하단 5탭 + 메인 대시보드 헤더까지 했고, 오늘은 **메인 대시보드 본문 6섹션 + 카메라 화면 + 분석 결과 5종 + 챗·점수·설정 탭 + 만성질환/복약 입력 + 알림·캘린더** 까지 — 앱의 주요 화면 골격을 한 번에 채웠습니다. 카메라는 `camera` 패키지로 인앱 라이브 프리뷰 + 탭바 숨김까지 구현, 에뮬/실기기 분기를 위해 `device_info_plus` 도입했습니다.

## 기준 정보

- 작업 기준일: 2026-05-20
- 로컬 경로: `C:\Claude_Projects\lemon_healthcare\Lemon_Aid`
- 현재 브랜치: `taedong-design`
- 디자인 시스템: LADS v2 (`mobile/lib/utils/design_tokens_v2.dart`)
- 의존성 핀 유지: `flutter_riverpod 2.5.1`, `google_sign_in 6.2.2`, `intl ^0.20.0`
- 신규 의존성: `device_info_plus ^12.1.0` (health 패키지 호환 버전)

## 오늘 작업 목적

- 어제 골격만 잡힌 메인 대시보드 **본문 카드** 를 실제 콘텐츠로 채움
- 카메라 → 분석 결과로 이어지는 **핵심 사용 흐름** 화면 구현
- 5탭(홈·챗·카메라·점수·설정) 전부 LADS v2 톤으로 통일
- 만성질환·복약 입력, 알림·캘린더 등 부가 화면 골격 확보

## 구현 범위 요약

### 1. 메인 대시보드 본문 (dashboard_screen.dart) — 6섹션 완성

- **인사 카드**: 마스코트 + 시간대별 동적 인사 + 사용자 이름 + 부족 영양소 칩
- **오늘의 영양 진행률**: 칼로리 진행 바(1240/1840 kcal) + 탄단지 3종 막대
- **5종 분석 grid**: 부족·과다·주의·점수·목적 가로 스크롤 카드
- **복약 알람**: 오늘 복용 4건 (시간·이름·완료 체크)
- **최근 분석**: 3건 리스트 (이모지 + 제목 + 부제)
- **의료 면책**: brandSoft 박스
- 헤더 우측 아이콘 3개(캘린더·알림·프로필) 실제 라우트 연결

### 2. 카메라 화면 (camera_screen.dart) — 인앱 라이브 프리뷰

- `camera` 패키지로 **인앱 라이브 프리뷰** (시스템 카메라 앱 안 거침)
- 풀스크린 검정 + 가이드 프레임(4 모서리 강조) + 어두운 마스크 오버레이
- 모드 토글 (영양제 / 식단)
- 셔터 → `takePicture()` → 인앱 미리보기 → 분석하기 / 다시 촬영
- 갤러리 진입 (`image_picker`)
- **전후면 카메라 토글** (회전 아이콘) — 후면=촬영, 전면=셀카(실기기 전용)
- **카메라 탭일 때 하단 탭바 자동 숨김** (`MainShell` 처리)
- 라이프사이클 처리 (백그라운드 dispose / 복귀 재초기화)

### 3. 분석 결과 화면 (analysis_result_screen.dart) — 신규

- `?mode=supplement|meal` 쿼리 진입
- brand 그라데 헤더 카드 + 5종 결과 카드 (부족·과다·주의·점수·목적)
- 의료 면책 + 하단 저장 CTA

### 4. 챗 탭 (chat_screen.dart) — 재작성

- brand 헤더(레몬봇) + 인사 카드 + 추천 질문 칩 4종
- 메시지 버블 + 타이핑 인디케이터 + 둥근 입력바
- mock 1턴 응답 분기 (백엔드 API 연동 전)

### 5. 점수 탭 (score_screen.dart) — 재작성

- brand 헤더(이번 주 평균 78점) + 라운드 본문
- 주간 막대 그래프(7일, CustomPainter) + 카테고리별 4종 + 평가 코멘트

### 6. 설정 탭 + 마이페이지 (settings_screen.dart) — 재작성

- brand 헤더(프로필 카드) + 라운드 본문
- 그룹 카드: 내 건강 / 알림 / 계정 / 안내
- 로그아웃 다이얼로그 연결 (기존 로직 보존)

### 7. 만성질환·복약·목적·신체 입력 (health_profile_screen.dart) — 신규

- `?tab=disease|drug|goal|body` 4탭 segment
- 칩 선택 (질환 12종 / 약 10종 / 목적 9종) + 신체 폼(키·몸무게)

### 8. 알림·캘린더 (notifications_screen.dart / calendar_screen.dart) — 신규

- 알림: 오늘 / 이번 주 / 이전 그룹 + 안 읽음 dot
- 캘린더: 월간 그리드 + 분석 기록 dot + 오늘/선택 강조 + 일 요약 카드

### 9. 라우터 (router.dart)

- 신규 라우트 추가: `/analysis-result`, `/health-profile`, `/notifications`, `/calendar`

### 10. 에뮬/실기기 분기 (device_env.dart) — 신규

- `device_info_plus` 로 에뮬레이터/실기기 자동 감지 (Android·iOS 통합)
- 부트 시 warmUp → 동기 접근 가능
- (카메라 보정 시도 → 최종적으로 보정 제거. 에뮬 구도 이슈는 실기기에서 자연 해결)

## 변경된 파일 (이번 커밋 범위)

```
mobile/lib/screens/dashboard_screen.dart       (본문 6섹션)
mobile/lib/screens/camera_screen.dart          (인앱 라이브 프리뷰)
mobile/lib/screens/analysis_result_screen.dart (신규 — 분석 결과 5종)
mobile/lib/screens/chat_screen.dart            (재작성)
mobile/lib/screens/score_screen.dart           (재작성)
mobile/lib/screens/settings_screen.dart        (재작성 + 마이페이지)
mobile/lib/screens/health_profile_screen.dart  (신규 — 만성질환/복약)
mobile/lib/screens/notifications_screen.dart   (신규 — 알림)
mobile/lib/screens/calendar_screen.dart        (신규 — 캘린더)
mobile/lib/widgets/common/main_shell.dart      (카메라 탭 탭바 숨김)
mobile/lib/utils/router.dart                   (라우트 4종 추가)
mobile/lib/utils/device_env.dart               (신규 — 에뮬 감지)
mobile/lib/main.dart                           (device_env warmUp)
mobile/pubspec.yaml                            (device_info_plus 추가)
mobile/CLAUDE.md                               (§7 반응형 룰 추가)
```

## 다음 단계 (TODO)

- [ ] 카메라 → OCR API 연동 (영양제 팀원 API 받아서)
- [ ] 분석 결과 화면 실데이터 연결 (mock → 실 JSON)
- [ ] 챗 백엔드 연동 (mock 응답 → 실 API)
- [ ] 점수 데이터 모델 정의 + 실데이터
- [ ] 만성질환·복약 → 분석 결과 교차 점검 표시 (주의 성분 카드)
- [ ] iOS 빌드 검증 (mac 팀원 — IOS_SETUP.md 따라)
- [ ] 알림·캘린더 실데이터 연결

## 가드 (의료법 §27, 약사법 §65)

- 신규 화면 전체 금칙어("진단·처방·치료·효능·효과") 점검 완료
- "진단" 은 면책 문구("의사·약사·영양사의 진단을 대신하지 않아요") 컨텍스트에서만 사용
- 분석 결과 / 점수 / 챗 화면 모두 의료 면책 노출

## 반응형 룰 (CLAUDE.md §7 신규)

- 고정 px 하드코딩 금지 — 레이아웃은 `MediaQuery` / `Expanded` / `AspectRatio` / `LayoutBuilder`
- 카메라·이미지는 항상 `AspectRatio` + `LayoutBuilder`
- 새 화면마다 3 사이즈(360/390/768) 점검 체크리스트
- 모든 기기(소형 폰 ~ 태블릿, Android·iOS) 동일 코드 호환
