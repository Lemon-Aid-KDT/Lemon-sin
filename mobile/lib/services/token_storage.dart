// services/token_storage.dart — access / refresh JWT + 마지막 로그인 방식
//
// flutter_secure_storage 사용 (Android Keystore / iOS Keychain).
// SharedPreferences 보다 안전 — root / jailbreak 환경에서도 평문 노출 없음.

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// 마지막으로 사용한 로그인 방식. 로그인 화면 "최근 로그인" 말풍선 위치 결정용.
/// 로그아웃해도 보존 — UX 힌트일 뿐 자격 증명 아님.
enum AuthProvider { email, kakao, google, apple }

extension AuthProviderExt on AuthProvider {
  String get storageKey => switch (this) {
        AuthProvider.email => 'email',
        AuthProvider.kakao => 'kakao',
        AuthProvider.google => 'google',
        AuthProvider.apple => 'apple',
      };
  static AuthProvider? fromKey(String? key) => switch (key) {
        'email' => AuthProvider.email,
        'kakao' => AuthProvider.kakao,
        'google' => AuthProvider.google,
        'apple' => AuthProvider.apple,
        _ => null,
      };
}

class TokenStorage {
  TokenStorage([FlutterSecureStorage? storage])
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
            );

  final FlutterSecureStorage _storage;

  static const _kAccess = 'lemon.auth.access';
  static const _kRefresh = 'lemon.auth.refresh';
  static const _kLastProvider = 'lemon.auth.last_provider';
  // 2026-05-18: 회원가입 (signup_flow 10-step) 완료 플래그
  // OAuth (카카오/구글) 진입 후에도 이 플래그가 없으면 signup_flow 로 보냄
  static const _kSignupComplete = 'lemon.auth.signup_complete';

  Future<String?> readAccess() => _storage.read(key: _kAccess);
  Future<String?> readRefresh() => _storage.read(key: _kRefresh);

  Future<void> writeAccess(String value) =>
      _storage.write(key: _kAccess, value: value);
  Future<void> writeRefresh(String value) =>
      _storage.write(key: _kRefresh, value: value);

  Future<void> writePair({required String access, required String refresh}) async {
    await Future.wait([
      _storage.write(key: _kAccess, value: access),
      _storage.write(key: _kRefresh, value: refresh),
    ]);
  }

  /// 토큰만 제거 — last_login_provider 는 유지 (다음 로그인 화면 힌트용).
  Future<void> clear() async {
    await Future.wait([
      _storage.delete(key: _kAccess),
      _storage.delete(key: _kRefresh),
    ]);
  }

  /// 토큰 둘 다 있는지 확인 (로그인 여부 판단용 — 검증은 별도).
  Future<bool> hasTokens() async {
    final a = await readAccess();
    final r = await readRefresh();
    return a != null && a.isNotEmpty && r != null && r.isNotEmpty;
  }

  // ─── 마지막 로그인 방식 (UX 힌트) ───

  Future<void> writeLastProvider(AuthProvider provider) =>
      _storage.write(key: _kLastProvider, value: provider.storageKey);

  Future<AuthProvider?> readLastProvider() async {
    final v = await _storage.read(key: _kLastProvider);
    return AuthProviderExt.fromKey(v);
  }

  // ─── 회원가입 완료 플래그 (2026-05-18) ───
  // OAuth (카카오/구글) 인증 OK 후에도 이 플래그가 false 이면
  // signup_flow 10-step 으로 보냄. (라우터 redirect 에서 사용)
  Future<void> markSignupComplete() =>
      _storage.write(key: _kSignupComplete, value: '1');

  Future<bool> isSignupComplete() async {
    final v = await _storage.read(key: _kSignupComplete);
    return v == '1';
  }

  Future<void> clearSignupComplete() =>
      _storage.delete(key: _kSignupComplete);
}
