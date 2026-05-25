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
  }) : _baseUrl = _normalizeBaseUrl(baseUrl),
       _bearerToken = bearerToken,
       _devGatewayToken = devGatewayToken,
       _httpClient = httpClient ?? http.Client();

  final String _baseUrl;
  final String? _bearerToken;
  final String? _devGatewayToken;
  final http.Client _httpClient;

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
    final http.Response response = await _httpClient.get(
      _uri(path, queryParameters: queryParameters),
      headers: _headers(),
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

    final http.Response response = await _httpClient.post(
      _uri(path),
      headers: headers,
      body: encodedBody,
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

    final http.StreamedResponse streamedResponse = await _httpClient.send(
      request,
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
    return MediaType('application', 'octet-stream');
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
