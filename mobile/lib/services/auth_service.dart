// services/auth_service.dart — 백엔드 /api/v1/auth/* 호출
//
// 백엔드 6 엔드포인트 (backend/src/api/auth.py):
//   POST /signup            { email, password, display_name? } → 201 {message}
//   POST /login             { email, password }                → 200 {access_token, refresh_token, token_type}
//   POST /kakao             { token }  (kakao access_token)    → 200 {access_token, refresh_token, token_type}
//   POST /google            { token }  (google id_token)       → 200 {access_token, refresh_token, token_type}
//   POST /refresh           { refresh_token }                  → 200 {access_token, token_type}
//   POST /logout            { refresh_token }                  → 200 {message}
//
// 모든 메서드는 정상이면 결과 객체, 실패면 AuthFailure throw.

import 'package:dio/dio.dart';

import 'api_client.dart';
import 'token_storage.dart';

/// 인증 토큰 쌍.
class AuthTokens {
  const AuthTokens({
    required this.access,
    required this.refresh,
    this.isNewUser,
  });
  final String access;
  final String refresh;
  // 백엔드 OAuth 응답의 'is_new_user' — 신규 가입자면 true.
  // 백엔드가 아직 안 내려주면 null → 호출 측이 로컬 플래그로 fallback.
  final bool? isNewUser;
}

/// 인증 실패 — 화면에서 잡아 SnackBar / 에러 라벨 표시.
class AuthFailure implements Exception {
  AuthFailure(this.message, {this.code, this.statusCode});
  final String message;
  final String? code;
  final int? statusCode;

  /// 이메일 중복 등 — 사용자가 "이미 가입된 계정" 케이스.
  /// 백엔드가 409 또는 400 으로 응답할 때 화면에서 다른 안내 분기 가능.
  bool get isConflict => statusCode == 409;

  /// 자격 증명 오류 (비번 틀림, 토큰 검증 실패 등)
  bool get isUnauthorized => statusCode == 401;

  @override
  String toString() => 'AuthFailure($statusCode/$code): $message';
}

class AuthService {
  AuthService({required ApiClient api, required TokenStorage storage})
      : _api = api,
        _storage = storage;

  final ApiClient _api;
  final TokenStorage _storage;

  static const _prefix = '/api/v1/auth';

  /// 이메일 회원가입. 성공 시 server message ("회원가입이 완료되었습니다.").
  /// 자동 로그인은 안 함 — 화면 측에서 이어서 [login] 호출 또는 verify-email 분기.
  Future<String> signup({
    required String email,
    required String password,
    String? displayName,
  }) async {
    final resp = await _post('$_prefix/signup', {
      'email': email,
      'password': password,
      if (displayName != null && displayName.isNotEmpty) 'display_name': displayName,
    });
    if (resp.statusCode == 201 || resp.statusCode == 200) {
      final data = resp.data;
      if (data is Map && data['message'] is String) return data['message'] as String;
      return '회원가입이 완료되었습니다.';
    }
    throw _failureFromResponse(resp, '회원가입에 실패했어요');
  }

  /// 이메일/비번 로그인. 성공 시 토큰 저장 후 [AuthTokens] 반환.
  Future<AuthTokens> login({
    required String email,
    required String password,
  }) async {
    final resp = await _post('$_prefix/login', {
      'email': email,
      'password': password,
    });
    return _consumeTokenResponse(
      resp,
      fallbackMessage: '로그인에 실패했어요',
      provider: AuthProvider.email,
    );
  }

  /// 카카오 SDK access_token → 백엔드가 카카오 서버에 검증 → JWT 발급.
  Future<AuthTokens> loginWithKakao(String kakaoAccessToken) async {
    final resp = await _post('$_prefix/kakao', {'token': kakaoAccessToken});
    return _consumeTokenResponse(
      resp,
      fallbackMessage: '카카오 로그인에 실패했어요',
      provider: AuthProvider.kakao,
    );
  }

  /// 구글 SDK id_token → 백엔드가 구글 tokeninfo 로 검증 → JWT 발급.
  Future<AuthTokens> loginWithGoogle(String googleIdToken) async {
    final resp = await _post('$_prefix/google', {'token': googleIdToken});
    return _consumeTokenResponse(
      resp,
      fallbackMessage: '구글 로그인에 실패했어요',
      provider: AuthProvider.google,
    );
  }

  /// 로그아웃 — 서버에 refresh 토큰 무효화 요청 + 로컬 토큰 삭제.
  /// 서버가 실패해도 로컬은 무조건 지움.
  Future<void> logout() async {
    final refresh = await _storage.readRefresh();
    if (refresh != null && refresh.isNotEmpty) {
      try {
        await _post('$_prefix/logout', {'refresh_token': refresh});
      } catch (_) {/* 무시 — 로컬은 어차피 지움 */}
    }
    await _storage.clear();
  }

  // ─── 이메일 인증 ───

  /// 인증 코드 발송 요청.
  /// 백엔드 rate-limit 적용 — 1 분에 1 회 / 하루 5 회.
  Future<String> sendEmailCode({
    required String email,
    String purpose = 'signup',
  }) async {
    final resp = await _post('$_prefix/email/send-code', {
      'email': email,
      'purpose': purpose,
    });
    if (resp.statusCode == 200 && resp.data is Map) {
      final msg = (resp.data as Map)['message'];
      return msg is String ? msg : '인증 코드를 보냈어요.';
    }
    throw _failureFromResponse(resp, '인증 코드 발송에 실패했어요');
  }

  /// 6 자리 코드 검증.
  ///
  /// purpose='signup' 인 경우 백엔드가 토큰을 같이 발급 — secure storage 에 저장하고
  /// AuthTokens 반환. 'password_reset' 인 경우 메시지만 반환 (토큰 null).
  ///
  /// 반환: (tokens, message) — tokens null 이면 메시지만 있는 케이스.
  Future<({AuthTokens? tokens, String message})> verifyEmailCode({
    required String email,
    required String code,
    String purpose = 'signup',
  }) async {
    final resp = await _post('$_prefix/email/verify-code', {
      'email': email,
      'code': code,
      'purpose': purpose,
    });
    if (resp.statusCode == 200 && resp.data is Map) {
      final data = resp.data as Map;
      final access = data['access_token'] as String?;
      final refresh = data['refresh_token'] as String?;
      if (access != null && refresh != null) {
        // signup 흐름 — 토큰 같이 도착. 자체 이메일 가입이라 provider = email.
        await Future.wait([
          _storage.writePair(access: access, refresh: refresh),
          _storage.writeLastProvider(AuthProvider.email),
        ]);
        return (
          tokens: AuthTokens(access: access, refresh: refresh),
          message: '이메일 인증이 완료됐어요.',
        );
      }
      // password_reset 등 — 메시지만
      final msg = data['message'] is String ? data['message'] as String : '인증이 완료됐어요.';
      return (tokens: null, message: msg);
    }
    throw _failureFromResponse(resp, '인증에 실패했어요');
  }

  // ───────── 내부 헬퍼 ─────────

  Future<Response> _post(String path, Map<String, dynamic> body) async {
    try {
      return await _api.dio.post(path, data: body);
    } on DioException catch (e) {
      throw AuthFailure(
        e.message ?? '네트워크 오류가 발생했어요',
        code: 'network',
      );
    }
  }

  /// 토큰 응답 처리 + 저장 + last_login_provider 기록.
  Future<AuthTokens> _consumeTokenResponse(
    Response resp, {
    required String fallbackMessage,
    required AuthProvider provider,
  }) async {
    if (resp.statusCode == 200 && resp.data is Map) {
      final data = resp.data as Map;
      final access = data['access_token'] as String?;
      final refresh = data['refresh_token'] as String?;
      if (access != null && refresh != null) {
        await Future.wait([
          _storage.writePair(access: access, refresh: refresh),
          _storage.writeLastProvider(provider),
        ]);
        // 백엔드가 'is_new_user' 내려주면 사용 — 없으면 null
        final isNew = data['is_new_user'];
        return AuthTokens(
          access: access,
          refresh: refresh,
          isNewUser: isNew is bool ? isNew : null,
        );
      }
    }
    throw _failureFromResponse(resp, fallbackMessage);
  }

  AuthFailure _failureFromResponse(Response resp, String fallback) {
    String message = fallback;
    final data = resp.data;
    if (data is Map) {
      final detail = data['detail'];
      if (detail is String) {
        message = detail;
      } else if (detail is List && detail.isNotEmpty) {
        // pydantic ValidationError — [{loc, msg, type}, ...]
        final first = detail.first;
        if (first is Map && first['msg'] is String) {
          message = first['msg'] as String;
        }
      }
    }
    return AuthFailure(message, statusCode: resp.statusCode);
  }
}
