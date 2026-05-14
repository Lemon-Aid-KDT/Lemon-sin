// services/api_client.dart — Dio 인스턴스 + 인터셉터
//
// 책임:
// 1. baseUrl 주입 (dart-define API_BASE_URL, 기본값:
//    - Android 에뮬레이터: 10.0.2.2 (호스트 localhost 매핑)
//    - iOS 시뮬레이터 / 데스크탑 / 웹: localhost)
// 2. 모든 요청에 Authorization: Bearer <access_token> 자동 첨부
//    (단 /auth/login, /signup, /kakao, /google, /refresh 는 제외)
// 3. 401 응답 시 refresh_token 으로 access 재발급 → 원 요청 재시도
//    refresh 도 실패하면 onSessionExpired 콜백 (→ AuthProvider 가 /login 으로 보냄)
//
// 참조: backend/src/api/auth.py

import 'dart:io' show Platform;

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show kDebugMode, kIsWeb;

import 'token_storage.dart';

class ApiClient {
  ApiClient._(this._dio, this._storage);

  final Dio _dio;
  final TokenStorage _storage;

  Dio get dio => _dio;

  /// 401 → refresh 실패 시 호출되는 외부 콜백.
  /// AuthProvider 가 주입 — 호출되면 토큰 모두 제거 + /login 으로 이동.
  void Function()? onSessionExpired;

  /// 동시에 여러 요청이 401 받았을 때 refresh 가 한 번만 돌도록 가드.
  Future<String?>? _refreshing;

  static ApiClient create({required TokenStorage storage}) {
    final dio = Dio(BaseOptions(
      baseUrl: _resolveBaseUrl(),
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
      headers: {'Content-Type': 'application/json'},
      // 4xx 는 에러로 throw 하지 않고 정상 응답으로 받음 — 핸들러에서 분기 처리
      validateStatus: (status) => status != null && status < 500,
    ));

    final client = ApiClient._(dio, storage);

    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        if (!_isAuthOpenPath(options.path)) {
          final access = await storage.readAccess();
          if (access != null && access.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $access';
          }
        }
        if (kDebugMode) {
          // ignore: avoid_print
          print('[API] → ${options.method} ${options.uri}');
        }
        handler.next(options);
      },
      onResponse: (response, handler) {
        if (kDebugMode) {
          // ignore: avoid_print
          print('[API] ← ${response.statusCode} ${response.requestOptions.uri}');
        }
        // 보호된 엔드포인트에서 401 → refresh 시도
        final path = response.requestOptions.path;
        if (response.statusCode == 401 && !_isAuthOpenPath(path)) {
          client._handle401(response, handler);
          return;
        }
        handler.next(response);
      },
      onError: (err, handler) {
        if (kDebugMode) {
          // ignore: avoid_print
          print('[API] ✗ ${err.requestOptions.uri} → ${err.message}');
        }
        handler.next(err);
      },
    ));

    return client;
  }

  /// 토큰 없이 호출 가능한 (또는 호출돼야 하는) 경로
  static bool _isAuthOpenPath(String path) {
    return path.contains('/auth/login') ||
           path.contains('/auth/signup') ||
           path.contains('/auth/kakao') ||
           path.contains('/auth/google') ||
           path.contains('/auth/refresh');
  }

  Future<void> _handle401(
    Response response,
    ResponseInterceptorHandler handler,
  ) async {
    final newAccess = await _tryRefresh();
    if (newAccess == null) {
      onSessionExpired?.call();
      handler.next(response);
      return;
    }
    final req = response.requestOptions;
    req.headers['Authorization'] = 'Bearer $newAccess';
    try {
      final retry = await _dio.fetch(req);
      handler.resolve(retry);
    } catch (_) {
      handler.next(response);
    }
  }

  Future<String?> _tryRefresh() async {
    _refreshing ??= _doRefresh();
    final result = await _refreshing;
    _refreshing = null;
    return result;
  }

  Future<String?> _doRefresh() async {
    final refresh = await _storage.readRefresh();
    if (refresh == null || refresh.isEmpty) return null;
    try {
      final resp = await _dio.post(
        '/api/v1/auth/refresh',
        data: {'refresh_token': refresh},
      );
      if (resp.statusCode == 200 && resp.data is Map) {
        final newAccess = resp.data['access_token'] as String?;
        if (newAccess != null) {
          await _storage.writeAccess(newAccess);
          return newAccess;
        }
      }
    } catch (_) {
      // 무시 — null 반환 시 세션 만료 처리
    }
    return null;
  }

  static String _resolveBaseUrl() {
    const fromEnv = String.fromEnvironment('API_BASE_URL');
    if (fromEnv.isNotEmpty) return fromEnv;
    if (kIsWeb) return 'http://localhost:8000';
    try {
      if (Platform.isAndroid) return 'http://10.0.2.2:8000';
    } catch (_) {/* 데스크탑·웹 빌드에서 Platform 접근 시 예외 — fall through */}
    return 'http://localhost:8000';
  }
}
