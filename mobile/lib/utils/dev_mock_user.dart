// utils/dev_mock_user.dart — Dev Bypass 진입 시 사용할 mock 사용자
//
// 참조: mobile/CLAUDE.md §4.2 + mobile/docs/integration_notes.md
// 사용자와 함께 디자인 결정 진행 중 — 마지막 디자인 협의 시점에 다시 손볼 것.
//
// 실제 인증 (AuthProvider) 가 붙으면 이 클래스는 제거하고
// AuthProvider 의 User 모델로 교체. mock 시점의 키 / 값은 합치기 시
// integration_notes.md 의 sunghoon-database `display_name` · `user_id (int)` 와
// yeong-tech `UUID` 둘 중 어느 쪽이 정본인지에 따라 정해짐.

class DevMockUser {
  /// 가짜 식별자. 실제 백엔드는 UUID 또는 int 사용 — integration_notes.md 참조.
  static const String id = 'dev-user-001';
  static const String email = 'dev@lemonaid.test';

  /// CLAUDE.md 가안 키명 `nickname` 사용. 백엔드는 `display_name` 일 수 있음.
  static const String nickname = '태동';

  /// 시니어 모드 토글 기본값 — 사용자와 같이 결정할 항목 (CLAUDE.md §3.1 60+ 동시 고려).
  static const bool seniorMode = false;

  /// 만 나이. 백엔드 UserProfile.age 와 동일 키.
  static const int age = 35;
}
