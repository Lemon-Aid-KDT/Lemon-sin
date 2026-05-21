import 'dart:convert';

import 'package:http/http.dart' as http;

import 'api_error.dart';

/// Minimal HTTP client for the Lemon Healthcare `/api/v1` contract.
class ApiClient {
  /// Creates an API client.
  ///
  /// Args:
  ///   baseUrl: Backend API base URL ending at `/api/v1`.
  ///   bearerToken: Optional JWT bearer token.
  ///   httpClient: Injectable HTTP client for tests.
  ApiClient({
    required String baseUrl,
    String? bearerToken,
    http.Client? httpClient,
  }) : _baseUrl = _normalizeBaseUrl(baseUrl),
       _bearerToken = bearerToken,
       _httpClient = httpClient ?? http.Client();

  final String _baseUrl;
  final String? _bearerToken;
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
    final http.MultipartRequest request =
        http.MultipartRequest('POST', _uri(path))
          ..headers.addAll(_headers())
          ..fields.addAll(fields)
          ..files.add(await http.MultipartFile.fromPath(fileField, filePath));

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
}
