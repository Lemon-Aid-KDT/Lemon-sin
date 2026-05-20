import 'package:dio/dio.dart';

import '../config/app_config.dart';

class LemonApiClient {
  LemonApiClient({
    required AppConfig config,
    Dio? dio,
  }) : _dio = dio ?? Dio(BaseOptions(baseUrl: config.apiBaseUrl)) {
    if (config.hasAuthToken) {
      _dio.options.headers['Authorization'] = 'Bearer ${config.authToken}';
    }
    _dio.options.headers['Content-Type'] = 'application/json';
  }

  final Dio _dio;

  Future<Response<Map<String, dynamic>>> postJson(
    String path,
    Map<String, dynamic> body,
  ) {
    return _dio.post<Map<String, dynamic>>(path, data: body);
  }

  Future<Response<Map<String, dynamic>>> postMultipart(
    String path,
    FormData body,
  ) {
    return _dio.post<Map<String, dynamic>>(path, data: body);
  }
}
