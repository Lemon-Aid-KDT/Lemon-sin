// services/oauth_service.dart — 카카오/구글 SDK 호출 추상화
//
// 책임: SDK 로 access_token (카카오) / id_token (구글) 받아오기까지.
// 그 토큰을 백엔드로 보내는 건 AuthService.loginWithKakao / loginWithGoogle 가 함.
//
// 보안: 키는 OAuthConfig 에서만 읽음. 이 파일에 키 절대 박지 않음.

import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

import '../utils/oauth_config.dart';

/// OAuth 흐름 실패 — 사용자 취소, 키 미주입, SDK 에러 등.
class OAuthFailure implements Exception {
  OAuthFailure(this.message, {this.cancelled = false});
  final String message;
  final bool cancelled;

  @override
  String toString() => 'OAuthFailure($message, cancelled=$cancelled)';
}

class OAuthService {
  OAuthService();

  /// 카카오 로그인 → access_token 반환.
  /// 카카오톡 설치돼 있으면 카카오톡으로, 아니면 카카오 계정 로그인 (웹).
  Future<String> signInWithKakao() async {
    if (!OAuthConfig.hasKakaoKey) {
      throw OAuthFailure('카카오 로그인 키가 설정되지 않았어요');
    }
    try {
      OAuthToken token;
      final installed = await isKakaoTalkInstalled();
      if (installed) {
        try {
          token = await UserApi.instance.loginWithKakaoTalk();
        } catch (e) {
          // 카카오톡 로그인 거부/실패 → 계정 로그인으로 폴백
          if (kDebugMode) debugPrint('[OAuth] KakaoTalk failed → fallback to account: $e');
          token = await UserApi.instance.loginWithKakaoAccount();
        }
      } else {
        token = await UserApi.instance.loginWithKakaoAccount();
      }
      return token.accessToken;
    } on KakaoClientException catch (e) {
      // 사용자 취소 등
      throw OAuthFailure(
        e.message ?? '카카오 로그인이 취소됐어요',
        cancelled: true,
      );
    } catch (e) {
      throw OAuthFailure('카카오 로그인 중 오류: $e');
    }
  }

  /// 구글 로그인 → id_token 반환.
  Future<String> signInWithGoogle() async {
    final googleSignIn = GoogleSignIn(
      // serverClientId 가 백엔드 google_client_id 와 일치해야
      // 백엔드 검증에서 aud 매칭됨.
      serverClientId: OAuthConfig.hasGoogleKey
          ? OAuthConfig.googleServerClientId
          : null,
      scopes: const ['email', 'profile'],
    );
    try {
      final account = await googleSignIn.signIn();
      if (account == null) {
        throw OAuthFailure('구글 로그인이 취소됐어요', cancelled: true);
      }
      final auth = await account.authentication;
      final idToken = auth.idToken;
      if (idToken == null || idToken.isEmpty) {
        throw OAuthFailure('구글 토큰을 가져오지 못했어요');
      }
      return idToken;
    } on OAuthFailure {
      rethrow;
    } catch (e) {
      throw OAuthFailure('구글 로그인 중 오류: $e');
    }
  }

  /// 카카오 SDK 측 로그아웃 (백엔드 JWT 와 별개)
  Future<void> signOutKakao() async {
    if (!OAuthConfig.hasKakaoKey) return;
    try {
      await UserApi.instance.logout();
    } catch (_) {/* 무시 */}
  }

  /// 구글 SDK 측 로그아웃
  Future<void> signOutGoogle() async {
    try {
      await GoogleSignIn().signOut();
    } catch (_) {/* 무시 */}
  }
}
