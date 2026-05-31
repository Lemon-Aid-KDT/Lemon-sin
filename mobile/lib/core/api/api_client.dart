import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

import 'api_error.dart';

/// Minimal HTTP client for the Lemon Healthcare `/api/v1` contract.
class ApiClient {
  /// Creates an API client.
  ///
  /// Args:
  ///   baseUrl: Backend API base URL ending at `/api/v1`.
  ///   bearerToken: Optional JWT bearer token.
  ///   devGatewayToken: Optional local development gateway token.
  ///   httpClient: Injectable HTTP client for tests.
  ApiClient({
    required String baseUrl,
    String? bearerToken,
    String? devGatewayToken,
    http.Client? httpClient,
    Duration requestTimeout = const Duration(seconds: 30),
    Duration uploadTimeout = const Duration(seconds: 60),
    int maxUploadBytes = _defaultMaxUploadBytes,
  }) : _baseUrl = _normalizeBaseUrl(baseUrl),
       _bearerToken = bearerToken,
       _devGatewayToken = devGatewayToken,
       _httpClient = httpClient ?? http.Client(),
       _requestTimeout = requestTimeout,
       _uploadTimeout = uploadTimeout,
       _maxUploadBytes = maxUploadBytes;

  /// Default client-side cap for image uploads (10 MB). Failing fast avoids an
  /// indefinite hang and a server 413 with no user guidance.
  static const int _defaultMaxUploadBytes = 10 * 1024 * 1024;

  final String _baseUrl;
  final String? _bearerToken;
  final String? _devGatewayToken;
  final http.Client _httpClient;
  final Duration _requestTimeout;
  final Duration _uploadTimeout;
  final int _maxUploadBytes;

  /// Sends a JSON GET request and returns a decoded object map.
  ///
  /// Args:
  ///   path: API path below `/api/v1`.
  ///   queryParameters: Optional query parameters.
  ///
  /// Returns:
  ///   Decoded JSON object.
  ///
  /// Raises:
  ///   ApiError: If the backend returns a non-2xx status code.
  ///   FormatException: If the success body is not a JSON object.
  Future<Map<String, dynamic>> getJson(
    String path, {
    Map<String, String>? queryParameters,
  }) async {
    final http.Response response = await _withTimeout(
      _httpClient.get(
        _uri(path, queryParameters: queryParameters),
        headers: _headers(),
      ),
      _requestTimeout,
    );
    return _decodeObject(response, expectedStatusCodes: const <int>{200});
  }

  /// Sends a JSON POST request and returns a decoded object map.
  ///
  /// Args:
  ///   path: API path below `/api/v1`.
  ///   body: Optional JSON object body.
  ///   expectedStatusCodes: Status codes considered successful.
  ///
  /// Returns:
  ///   Decoded JSON object.
  ///
  /// Raises:
  ///   ApiError: If the backend returns an unexpected status code.
  ///   FormatException: If the success body is not a JSON object.
  Future<Map<String, dynamic>> postJson(
    String path, {
    Map<String, dynamic>? body,
    Set<int> expectedStatusCodes = const <int>{200, 201},
  }) async {
    final Map<String, String> headers = _headers();
    Object? encodedBody;
    if (body != null) {
      headers['Content-Type'] = 'application/json; charset=UTF-8';
      encodedBody = jsonEncode(body);
    }

    final http.Response response = await _withTimeout(
      _httpClient.post(_uri(path), headers: headers, body: encodedBody),
      _requestTimeout,
    );
    return _decodeObject(response, expectedStatusCodes: expectedStatusCodes);
  }

  /// Sends a multipart upload request and returns a decoded object map.
  ///
  /// Args:
  ///   path: API path below `/api/v1`.
  ///   fileField: Multipart file field name.
  ///   filePath: Local selected image path.
  ///   fields: Additional multipart form fields.
  ///   expectedStatusCodes: Status codes considered successful.
  ///
  /// Returns:
  ///   Decoded JSON object.
  ///
  /// Raises:
  ///   ApiError: If the backend returns an unexpected status code.
  ///   FormatException: If the success body is not a JSON object.
  Future<Map<String, dynamic>> postMultipart(
    String path, {
    required String fileField,
    required String filePath,
    Map<String, String> fields = const <String, String>{},
    Set<int> expectedStatusCodes = const <int>{202},
  }) async {
    await _ensureUploadableSize(filePath);
    final MediaType contentType = await _contentTypeForPath(filePath);
    final http.MultipartRequest request =
        http.MultipartRequest('POST', _uri(path))
          ..headers.addAll(_headers())
          ..fields.addAll(fields)
          ..files.add(
            await http.MultipartFile.fromPath(
              fileField,
              filePath,
              contentType: contentType,
            ),
          );

    final http.StreamedResponse streamedResponse = await _withTimeout(
      _httpClient.send(request),
      _uploadTimeout,
    );
    final String responseBody = await streamedResponse.stream.bytesToString();
    if (!expectedStatusCodes.contains(streamedResponse.statusCode)) {
      throw ApiError.fromBody(
        statusCode: streamedResponse.statusCode,
        body: responseBody,
      );
    }
    return _decodeBodyAsObject(responseBody);
  }

  /// Sends a multipart request with multiple files using the same field name.
  ///
  /// Args:
  ///   path: API path below `/api/v1`.
  ///   fileField: Multipart file field name repeated for every file.
  ///   filePaths: Local selected image paths.
  ///   fields: Additional multipart form fields.
  ///   expectedStatusCodes: Status codes considered successful.
  ///
  /// Returns:
  ///   Decoded JSON object.
  ///
  /// Raises:
  ///   ApiError: If the backend returns an unexpected status code.
  ///   FormatException: If the success body is not a JSON object.
  Future<Map<String, dynamic>> postMultipartFiles(
    String path, {
    required String fileField,
    required List<String> filePaths,
    Map<String, String> fields = const <String, String>{},
    Set<int> expectedStatusCodes = const <int>{202},
  }) async {
    final http.MultipartRequest request =
        http.MultipartRequest('POST', _uri(path))
          ..headers.addAll(_headers())
          ..fields.addAll(fields);
    for (final String filePath in filePaths) {
      await _ensureUploadableSize(filePath);
      request.files.add(
        await http.MultipartFile.fromPath(
          fileField,
          filePath,
          contentType: await _contentTypeForPath(filePath),
        ),
      );
    }

    final http.StreamedResponse streamedResponse = await _withTimeout(
      _httpClient.send(request),
      _uploadTimeout,
    );
    final String responseBody = await streamedResponse.stream.bytesToString();
    if (!expectedStatusCodes.contains(streamedResponse.statusCode)) {
      throw ApiError.fromBody(
        statusCode: streamedResponse.statusCode,
        body: responseBody,
      );
    }
    return _decodeBodyAsObject(responseBody);
  }

  /// Releases the underlying HTTP client.
  void close() {
    _httpClient.close();
  }

  Map<String, dynamic> _decodeObject(
    http.Response response, {
    required Set<int> expectedStatusCodes,
  }) {
    if (!expectedStatusCodes.contains(response.statusCode)) {
      throw ApiError.fromBody(
        statusCode: response.statusCode,
        body: response.body,
      );
    }
    return _decodeBodyAsObject(response.body);
  }

  Map<String, dynamic> _decodeBodyAsObject(String body) {
    final Object? decoded = jsonDecode(body);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    throw const FormatException('Expected a JSON object response.');
  }

  /// Awaits [future] but converts a timeout into a user-safe [ApiError].
  Future<T> _withTimeout<T>(Future<T> future, Duration timeout) async {
    try {
      return await future.timeout(timeout);
    } on TimeoutException {
      throw const ApiError(
        statusCode: 408,
        message: '서버 응답이 지연되고 있어요. 네트워크 상태를 확인한 뒤 다시 시도해주세요.',
      );
    }
  }

  /// Rejects oversized uploads before sending so the user gets clear guidance
  /// instead of an indefinite hang or a bare server 413.
  Future<void> _ensureUploadableSize(String filePath) async {
    final int length = await File(filePath).length();
    if (length > _maxUploadBytes) {
      final int limitMb = (_maxUploadBytes / (1024 * 1024)).round();
      throw ApiError(
        statusCode: 413,
        message: '이미지가 너무 커요(최대 ${limitMb}MB). 더 작은 사진으로 다시 시도해주세요.',
      );
    }
  }

  Map<String, String> _headers() {
    final Map<String, String> headers = <String, String>{
      'Accept': 'application/json',
    };
    if (_bearerToken != null && _bearerToken.trim().isNotEmpty) {
      headers['Authorization'] = 'Bearer ${_bearerToken.trim()}';
    }
    if (_devGatewayToken != null && _devGatewayToken.trim().isNotEmpty) {
      headers['X-Lemon-Dev-Gateway-Token'] = _devGatewayToken.trim();
    }
    return headers;
  }

  Uri _uri(String path, {Map<String, String>? queryParameters}) {
    final String normalizedPath = path.startsWith('/') ? path : '/$path';
    return Uri.parse(
      '$_baseUrl$normalizedPath',
    ).replace(queryParameters: queryParameters);
  }

  static String _normalizeBaseUrl(String value) {
    final String trimmed = value.trim();
    if (trimmed.endsWith('/')) {
      return trimmed.substring(0, trimmed.length - 1);
    }
    return trimmed;
  }

  static Future<MediaType> _contentTypeForPath(String filePath) async {
    final MediaType? detectedFromHeader = await _sniffImageContentType(
      filePath,
    );
    if (detectedFromHeader != null) {
      return detectedFromHeader;
    }
    final String lowerPath = filePath.toLowerCase();
    if (lowerPath.endsWith('.png')) {
      return MediaType('image', 'png');
    }
    if (lowerPath.endsWith('.jpg') || lowerPath.endsWith('.jpeg')) {
      return MediaType('image', 'jpeg');
    }
    if (lowerPath.endsWith('.webp')) {
      return MediaType('image', 'webp');
    }
    throw const ApiError(
      statusCode: 415,
      message: '지원하지 않는 이미지 형식이에요. JPEG·PNG·WEBP 사진으로 다시 시도해주세요.',
    );
  }

  static Future<MediaType?> _sniffImageContentType(String filePath) async {
    RandomAccessFile? file;
    try {
      file = await File(filePath).open();
      final List<int> header = await file.read(16);
      if (_startsWith(header, const <int>[
        0x89,
        0x50,
        0x4E,
        0x47,
        0x0D,
        0x0A,
        0x1A,
        0x0A,
      ])) {
        return MediaType('image', 'png');
      }
      if (_startsWith(header, const <int>[0xFF, 0xD8, 0xFF])) {
        return MediaType('image', 'jpeg');
      }
      if (_startsWith(header, 'RIFF'.codeUnits) &&
          header.length >= 12 &&
          _startsWith(header.sublist(8), 'WEBP'.codeUnits)) {
        return MediaType('image', 'webp');
      }
    } on FileSystemException {
      return null;
    } finally {
      await file?.close();
    }
    return null;
  }

  static bool _startsWith(List<int> value, List<int> prefix) {
    if (value.length < prefix.length) {
      return false;
    }
    for (int index = 0; index < prefix.length; index += 1) {
      if (value[index] != prefix[index]) {
        return false;
      }
    }
    return true;
  }
}
