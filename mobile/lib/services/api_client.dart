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

import 'dart:io' show File, Platform;

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show kDebugMode, kIsWeb;

import '../models/supplement_analysis.dart';
import '../models/supplement_comprehensive.dart';
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

  /// 영양제 라벨 이미지를 백엔드로 업로드하여 OCR/파싱 preview 를 받는다.
  ///
  /// 백엔드 endpoint: `POST /api/v1/supplements/analyze`
  /// 응답 status: `202 Accepted` (preview, 사용자 확인 필요)
  ///
  /// Args:
  ///   imageFile: 촬영된 영양제 라벨 이미지 파일 (jpg/png/webp).
  ///   clientRequestId: 동일 이미지 중복 분석 방지용 idempotency key (없으면 자동 생성).
  ///   ocrProvider: 백엔드 OCR provider 선택 (`"configured"` / `"paddle_local"` 등).
  ///   barcodeText: 모바일 스캐너가 미리 읽은 바코드 (선택).
  ///   barcodeFormat: 바코드 포맷 라벨 (선택).
  ///
  /// Returns:
  ///   파싱된 [SupplementAnalysisPreview].
  ///
  /// Throws:
  ///   [SupplementAnalyzeException] - HTTP 4xx 또는 네트워크 실패 시.
  Future<SupplementAnalysisPreview> analyzeSupplementImage({
    required File imageFile,
    String? clientRequestId,
    String ocrProvider = 'configured',
    String? barcodeText,
    String? barcodeFormat,
  }) async {
    final fileName = imageFile.path.split('/').last;
    final formData = FormData.fromMap(<String, dynamic>{
      'image': await MultipartFile.fromFile(imageFile.path, filename: fileName),
      if (clientRequestId != null) 'client_request_id': clientRequestId,
      'ocr_provider': ocrProvider,
      if (barcodeText != null) 'barcode_text': barcodeText,
      if (barcodeFormat != null) 'barcode_format': barcodeFormat,
    });

    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/supplements/analyze',
        data: formData,
        options: Options(
          headers: <String, String>{'Content-Type': 'multipart/form-data'},
          // 4xx 도 직접 분기 처리 → validateStatus 는 base 와 동일하게 둠.
        ),
      );

      final statusCode = response.statusCode ?? 0;
      final payload = response.data ?? const <String, dynamic>{};

      if (statusCode == 202 || statusCode == 200) {
        return SupplementAnalysisPreview.fromJson(payload);
      }

      throw SupplementAnalyzeException(
        statusCode: statusCode,
        code: payload['code']?.toString() ?? 'http_${statusCode}',
        message: payload['message']?.toString() ?? '분석에 실패했어요',
      );
    } on DioException catch (e) {
      // 네트워크 타임아웃 / 연결 실패 / 서버 5xx
      final statusCode = e.response?.statusCode ?? 0;
      final payload = e.response?.data;
      throw SupplementAnalyzeException(
        statusCode: statusCode,
        code: (payload is Map<String, dynamic> ? payload['code']?.toString() : null) ??
            'dio_${e.type.name}',
        message: e.message ?? '네트워크 오류가 발생했어요',
      );
    }
  }

  /// OCR analyze 응답의 ingredient + 사용자 프로필을 보내 5-card 데이터를 받는다.
  ///
  /// 백엔드 endpoint: `POST /api/v1/supplements/analyze/comprehensive`
  /// 응답: `SupplementComprehensiveAnalysis` (deficient/excessive/cautions/score/purpose).
  ///
  /// Args:
  ///   analysisId: 선행 analyze 응답의 식별자 (감사 로그용).
  ///   ingredients: analyze 응답의 ingredient candidates 를 변환한 payload.
  ///   userProfile: KDRIs 룩업용 사용자 정보.
  ///   persona: A=예방·일반 / B=만성질환자 (점수 가중치).
  ///
  /// Returns:
  ///   [SupplementComprehensiveAnalysis].
  ///
  /// Throws:
  ///   [SupplementAnalyzeException] — HTTP 4xx 또는 네트워크 실패.
  Future<SupplementComprehensiveAnalysis> analyzeComprehensive({
    required List<ComprehensiveIngredientPayload> ingredients,
    required UserProfilePayload userProfile,
    String? analysisId,
    String persona = 'B',
  }) async {
    final body = <String, dynamic>{
      if (analysisId != null) 'analysis_id': analysisId,
      'ingredients': ingredients.map((i) => i.toJson()).toList(growable: false),
      'user_profile': userProfile.toJson(),
      'persona': persona,
    };
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/api/v1/supplements/analyze/comprehensive',
        data: body,
        options: Options(
          headers: <String, String>{'Content-Type': 'application/json'},
        ),
      );
      final statusCode = response.statusCode ?? 0;
      final payload = response.data ?? const <String, dynamic>{};
      if (statusCode == 200) {
        return SupplementComprehensiveAnalysis.fromJson(payload);
      }
      throw SupplementAnalyzeException(
        statusCode: statusCode,
        code: payload['code']?.toString() ?? 'http_${statusCode}',
        message: payload['message']?.toString() ?? '종합 분석에 실패했어요',
      );
    } on DioException catch (e) {
      throw SupplementAnalyzeException(
        statusCode: e.response?.statusCode ?? 0,
        code: 'dio_${e.type.name}',
        message: e.message ?? '네트워크 오류가 발생했어요',
      );
    }
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
