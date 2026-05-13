import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

// 로컬에서 테스트할 때: 'http://10.0.2.2:8000' (Android 에뮬레이터 → 로컬호스트)
// 실제 기기에서 테스트할 때: 'http://[컴퓨터 IP]:8000'
const String _baseUrl = 'http://10.0.2.2:8000';

class AuthService {
  static const _storage = FlutterSecureStorage();
  static final _googleSignIn = GoogleSignIn();

  // ── 토큰 저장/조회 ──────────────────────────────────────────────

  static Future<void> saveTokens(String accessToken, String refreshToken) async {
    await Future.wait([
      _storage.write(key: 'access_token', value: accessToken),
      _storage.write(key: 'refresh_token', value: refreshToken),
    ]);
  }

  static Future<String?> getAccessToken() => _storage.read(key: 'access_token');

  static Future<void> clearTokens() async {
    await Future.wait([
      _storage.delete(key: 'access_token'),
      _storage.delete(key: 'refresh_token'),
    ]);
  }

  // ── 구글 로그인 ─────────────────────────────────────────────────

  static Future<void> signInWithGoogle() async {
    // 1. 구글 팝업 띄우기 → 사용자가 계정 선택
    final account = await _googleSignIn.signIn();
    if (account == null) throw Exception('구글 로그인이 취소되었습니다.');

    // 2. 구글로부터 ID 토큰 받기
    final auth = await account.authentication;
    final idToken = auth.idToken;
    if (idToken == null) throw Exception('구글 토큰을 가져올 수 없습니다.');

    // 3. 우리 서버로 ID 토큰 전송 → 서버에서 검증 후 JWT 발급
    await _sendTokenToServer('/auth/google', idToken);
  }

  // ── 카카오 로그인 ────────────────────────────────────────────────

  static Future<void> signInWithKakao() async {
    OAuthToken token;

    // 카카오톡 앱이 설치되어 있으면 앱으로, 없으면 웹으로 로그인
    if (await isKakaoTalkInstalled()) {
      token = await UserApi.instance.loginWithKakaoTalk();
    } else {
      token = await UserApi.instance.loginWithKakaoAccount();
    }

    // 우리 서버로 액세스 토큰 전송 → 서버에서 카카오 API 호출 후 JWT 발급
    await _sendTokenToServer('/auth/kakao', token.accessToken);
  }

  // ── 공통: 서버에 토큰 전송 ──────────────────────────────────────

  static Future<void> _sendTokenToServer(String path, String token) async {
    final response = await http.post(
      Uri.parse('$_baseUrl$path'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'token': token}),
    );

    if (response.statusCode != 200) {
      final body = jsonDecode(response.body);
      throw Exception(body['detail'] ?? '로그인에 실패했습니다.');
    }

    final data = jsonDecode(response.body);
    await saveTokens(data['access_token'], data['refresh_token']);
  }

  // ── 로그아웃 ────────────────────────────────────────────────────

  static Future<void> signOut() async {
    // 구글 로그아웃 (연결된 경우)
    await _googleSignIn.signOut().catchError((_) {});
    await clearTokens();
  }
}
