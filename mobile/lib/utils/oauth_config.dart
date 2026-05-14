// utils/oauth_config.dart — OAuth 키 한 군데로
//
// 보안 원칙:
//   1. 키는 절대 소스에 박지 않음. 깃에 키가 들어가는 순간 영구 노출 위험.
//   2. dart-define 으로 빌드 시 주입.
//      flutter run --dart-define=KAKAO_NATIVE_APP_KEY=xxxx \
//                  --dart-define=GOOGLE_SERVER_CLIENT_ID=xxxx
//   3. 키 미주입 상태에서도 컴파일/실행 가능 — 해당 OAuth 만 비활성화됨.
//
// 어디서 키를 받나:
//   - 카카오: https://developers.kakao.com → 내 애플리케이션 → 앱 키 → Native App Key
//   - 구글: https://console.cloud.google.com → APIs → OAuth 2.0 클라이언트 ID
//     · Android Client ID (앱 인증용, 콘솔에 SHA-1 등록 필요)
//     · Web Client ID (백엔드 ID 토큰 검증용 — google_client_id 와 동일)

class OAuthConfig {
  const OAuthConfig._();

  // ─── 카카오 ───
  // Native App Key. KakaoSdk.init() 에 필수.
  // 빈 값이면 카카오 로그인 버튼 자체가 비활성 (에러 안내).
  static const String kakaoNativeAppKey =
      String.fromEnvironment('KAKAO_NATIVE_APP_KEY');

  // 카카오 키가 주입됐는지
  static bool get hasKakaoKey => kakaoNativeAppKey.isNotEmpty;

  // ─── 구글 ───
  // 백엔드 토큰 검증용 (Web Client ID). google_sign_in 의 serverClientId 에 주입하면
  // id_token 의 aud 가 이 값으로 발급돼 백엔드 google_client_id 와 일치.
  static const String googleServerClientId =
      String.fromEnvironment('GOOGLE_SERVER_CLIENT_ID');

  static bool get hasGoogleKey => googleServerClientId.isNotEmpty;
}
