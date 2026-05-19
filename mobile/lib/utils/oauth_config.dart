// utils/oauth_config.dart — OAuth 키 한 군데로
//
// 키 로딩 우선순위 (개발 편의):
//   1. dart-define (--dart-define=KEY=val) 최우선
//   2. .env 파일 (flutter_dotenv) — 일반 개발 시 사용
//   3. 둘 다 없으면 빈 문자열 → 해당 OAuth 비활성화 (안내 모달)
//
// .env 셋업:
//   cp mobile/.env.example mobile/.env
//   .env 에 실제 키 채우기 (깃에 안 올라감)
//
// 어디서 키를 받나:
//   - 카카오: https://developers.kakao.com → 내 애플리케이션 → 앱 키 → Native App Key
//   - 구글: https://console.cloud.google.com → APIs → OAuth 2.0 클라이언트 ID (Web)

import 'package:flutter_dotenv/flutter_dotenv.dart';

class OAuthConfig {
  const OAuthConfig._();

  /// dart-define 우선, 없으면 .env, 둘 다 없으면 빈 문자열.
  static String _resolve(String key) {
    const fromDefine = bool.hasEnvironment('KAKAO_NATIVE_APP_KEY');
    // dart-define 우선 — 컴파일 타임 상수라 직접 분기
    final fromDartDefine = switch (key) {
      'KAKAO_NATIVE_APP_KEY' =>
          const String.fromEnvironment('KAKAO_NATIVE_APP_KEY'),
      'GOOGLE_SERVER_CLIENT_ID' =>
          const String.fromEnvironment('GOOGLE_SERVER_CLIENT_ID'),
      'API_BASE_URL' =>
          const String.fromEnvironment('API_BASE_URL'),
      _ => '',
    };
    if (fromDartDefine.isNotEmpty) return fromDartDefine;
    // .env 폴백
    try {
      return dotenv.maybeGet(key) ?? '';
    } catch (_) {
      return '';
    }
  }

  // ─── 카카오 ───
  static String get kakaoNativeAppKey => _resolve('KAKAO_NATIVE_APP_KEY');
  static