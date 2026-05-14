// providers/auth_provider.dart — Riverpod 인증 상태
//
// 흐름:
//   AppLaunch
//     → authControllerProvider 부트스트랩 (TokenStorage 읽음)
//     → 토큰 있으면 AuthStatus.authenticated, 없으면 unauthenticated
//   Splash 가 이 상태 기다렸다가 /shell 또는 /login 으로 이동.
//
//   로그인 화면: ref.read(authControllerProvider.notifier).loginWithEmail(...)
//   → 성공 시 상태 authenticated 로 바뀌고, 라우터 refreshListenable 가 reload 트리거.

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../services/oauth_service.dart';
import '../services/token_storage.dart';

// ─────────── 인프라 Provider ───────────

final Provider<TokenStorage> tokenStorageProvider =
    Provider<TokenStorage>((ref) => TokenStorage());

final Provider<ApiClient> apiClientProvider = Provider<ApiClient>((ref) {
  final storage = ref.watch(tokenStorageProvider);
  final client = ApiClient.create(storage: storage);
  // 401 → refresh 실패 시 자동 로그아웃
  client.onSessionExpired = () {
    ref.read(authControllerProvider.notifier).forceSignOut();
  };
  return client;
});

final Provider<AuthService> authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(
    api: ref.watch(apiClientProvider),
    storage: ref.watch(tokenStorageProvider),
  );
});

final Provider<OAuthService> oauthServiceProvider =
    Provider<OAuthService>((ref) => OAuthService());

// ─────────── 상태 ───────────

enum AuthStatus {
  unknown,         // 부트스트랩 전 — Splash 가 기다림
  authenticated,   // 토큰 있음
  unauthenticated, // 로그인 필요
}

class AuthState {
  const AuthState({
    required this.status,
    this.errorMessage,
    this.isSubmitting = false,
  });

  final AuthStatus status;
  final String? errorMessage;
  final bool isSubmitting;

  bool get isAuthenticated => status == AuthStatus.authenticated;
  bool get isReady => status != AuthStatus.unknown;

  AuthState copyWith({
    AuthStatus? status,
    String? errorMessage,
    bool? isSubmitting,
    bool clearError = false,
  }) {
    return AuthState(
      status: status ?? this.status,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
      isSubmitting: isSubmitting ?? this.isSubmitting,
    );
  }

  static const initial = AuthState(status: AuthStatus.unknown);
}

// ─────────── Controller ───────────

final StateNotifierProvider<AuthController, AuthState> authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  final controller = AuthController(
    auth: ref.watch(authServiceProvider),
    oauth: ref.watch(oauthServiceProvider),
    storage: ref.watch(tokenStorageProvider),
  );
  controller.bootstrap();
  return controller;
});

class AuthController extends StateNotifier<AuthState> {
  AuthController({
    required AuthService auth,
    required OAuthService oauth,
    required TokenStorage storage,
  })  : _auth = auth,
        _oauth = oauth,
        _storage = storage,
        super(AuthState.initial);

  final AuthService _auth;
  final OAuthService _oauth;
  final TokenStorage _storage;

  /// 앱 시작 시 한 번 — 저장된 토큰 유무로 상태 결정.
  /// 토큰 실제 검증은 첫 보호 요청 시 401 → refresh 흐름이 담당.
  Future<void> bootstrap() async {
    final has = await _storage.hasTokens();
    state = state.copyWith(
      status: has ? AuthStatus.authenticated : AuthStatus.unauthenticated,
      clearError: true,
    );
  }

  Future<bool> signUpWithEmail({
    required String email,
    required String password,
    String? displayName,
  }) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      await _auth.signup(email: email, password: password, displayName: displayName);
      // signup 만 함 — 자동 로그인은 화면 측 정책으로 (verify-email 후 또는 바로 login)
      state = state.copyWith(isSubmitting: false, clearError: true);
      return true;
    } on AuthFailure catch (e) {
      state = state.copyWith(isSubmitting: false, errorMessage: e.message);
      return false;
    } catch (_) {
      state = state.copyWith(
        isSubmitting: false,
        errorMessage: '회원가입 중 오류가 발생했어요',
      );
      return false;
    }
  }

  Future<bool> loginWithEmail({
    required String email,
    required String password,
  }) async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      await _auth.login(email: email, password: password);
      state = state.copyWith(
        isSubmitting: false,
        status: AuthStatus.authenticated,
        clearError: true,
      );
      return true;
    } on AuthFailure catch (e) {
      state = state.copyWith(isSubmitting: false, errorMessage: e.message);
      return false;
    } catch (_) {
      state = state.copyWith(
        isSubmitting: false,
        errorMessage: '로그인 중 오류가 발생했어요',
      );
      return false;
    }
  }

  /// 카카오 SDK → access_token → 백엔드 검증 → JWT 발급 → 상태 갱신.
  /// 한 메서드로 전체 흐름 처리. 화면 측은 buttonOnPressed 에서 이 하나만 호출.
  Future<bool> signInWithKakao() async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      final kakaoToken = await _oauth.signInWithKakao();
      await _auth.loginWithKakao(kakaoToken);
      state = state.copyWith(
        isSubmitting: false,
        status: AuthStatus.authenticated,
        clearError: true,
      );
      return true;
    } on OAuthFailure catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        // 사용자가 취소한 경우엔 에러 메시지 안 띄우는 게 깔끔
        errorMessage: e.cancelled ? null : e.message,
      );
      return false;
    } on AuthFailure catch (e) {
      state = state.copyWith(isSubmitting: false, errorMessage: e.message);
      return false;
    } catch (_) {
      state = state.copyWith(
        isSubmitting: false,
        errorMessage: '카카오 로그인 중 오류가 발생했어요',
      );
      return false;
    }
  }

  /// 구글 SDK → id_token → 백엔드 검증 → JWT 발급 → 상태 갱신.
  Future<bool> signInWithGoogle() async {
    state = state.copyWith(isSubmitting: true, clearError: true);
    try {
      final googleIdToken = await _oauth.signInWithGoogle();
      await _auth.loginWithGoogle(googleIdToken);
      state = state.copyWith(
        isSubmitting: false,
        status: AuthStatus.authenticated,
        clearError: true,
      );
      return true;
    } on OAuthFailure catch (e) {
      state = state.copyWith(
        isSubmitting: false,
        errorMessage: e.cancelled ? null : e.message,
      );
      return false;
    } on AuthFailure catch (e) {
      state = state.copyWith(isSubmitting: false, errorMessage: e.message);
      return false;
    } catch (_) {
      state = state.copyWith(
        isSubmitting: false,
        errorMessage: '구글 로그인 중 오류가 발생했어요',
      );
      return false;
    }
  }

  Future<void> logout() async {
    try {
      await _auth.logout();
    } finally {
      // OAuth SDK 측 세션도 정리 — 다음 로그인 때 계정 선택 화면이 다시 뜨도록
      await _oauth.signOutKakao();
      await _oauth.signOutGoogle();
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  // ─── 이메일 인증 ───

  /// 코드 재발송 (또는 처음 발송). 성공 메시지 또는 throw.
  Future<String> sendEmailCode({
    required String email,
    String purpose = 'signup',
  }) async {
    return _auth.sendEmailCode(email: email, purpose: purpose);
  }

  /// 코드 검증. signup 인 경우 토큰 자동 발급 + 인증 상태 authenticated 로 갱신.
  Future<String> verifyEmailCode({
    required String email,
    required String code,
    String purpose = 'signup',
  }) async {
    final result = await _auth.verifyEmailCode(
      email: email,
      code: code,
      purpose: purpose,
    );
    if (result.tokens != null) {
      // signup → 토큰 받음 → 즉시 로그인 상태로
      state = state.copyWith(
        status: AuthStatus.authenticated,
        clearError: true,
      );
    }
    return result.message;
  }

  /// 마지막 로그인 방식 (UX 힌트용). 토큰 지워져도 보존됨.
  Future<AuthProvider?> readLastProvider() => _storage.readLastProvider();

  /// 토큰 만료 — api_client onSessionExpired 콜백.
  void forceSignOut() {
    _storage.clear();
    state = const AuthState(
      status: AuthStatus.unauthenticated,
      errorMessage: '세션이 만료됐어요. 다시 로그인해주세요.',
    );
  }

  void clearError() {
    state = state.copyWith(clearError: true);
  }
}
