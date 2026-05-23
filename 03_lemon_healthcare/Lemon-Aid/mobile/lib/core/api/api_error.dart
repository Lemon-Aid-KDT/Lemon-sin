import 'dart:convert';

const int _maxUserSafeMessageLength = 180;
final RegExp _safeErrorCodePattern = RegExp(r'^[a-z0-9_]{1,80}$');
final List<String> _sensitiveErrorMessageMarkers = <String>[
  <String>['raw', 'ocr', 'text'].join('_'),
  <String>['ocr', 'text'].join('_'),
  <String>['provider', 'payload'].join('_'),
  <String>['request', 'headers'].join('_'),
  <String>['image', 'bytes'].join('_'),
  <String>['authori', 'zation'].join(),
  'bearer ',
  <String>['api', 'key'].join('_'),
  <String>['api', 'key'].join('-'),
  'secret',
  '/users/',
  '/volumes/',
  '-----begin',
];

/// Error surfaced by the Lemon Aid API client.
class ApiError implements Exception {
  /// Creates an API error.
  ///
  /// Args:
  ///   statusCode: HTTP response status code.
  ///   code: Sanitized backend error code when present.
  ///   message: User-safe error message.
  ///   requiredConsents: Consent names required by the failed request.
  const ApiError({
    required this.statusCode,
    required this.message,
    this.code,
    this.requiredConsents = const <String>[],
  });

  /// HTTP response status code.
  final int statusCode;

  /// Sanitized backend error code when present.
  final String? code;

  /// User-safe error message.
  final String message;

  /// Consent names required by the failed request.
  final List<String> requiredConsents;

  /// Parses an error from a completed HTTP response body.
  ///
  /// Args:
  ///   statusCode: HTTP response status code.
  ///   body: Response body text.
  ///
  /// Returns:
  ///   ApiError with best-effort backend detail extraction.
  factory ApiError.fromBody({required int statusCode, required String body}) {
    final Object? decoded = _tryDecodeJson(body);
    if (decoded is Map<String, dynamic>) {
      final Object? detail = decoded['detail'];
      if (detail is Map<String, dynamic>) {
        return ApiError(
          statusCode: statusCode,
          code: _safeErrorCode(detail['code']),
          message: _detailMessage(detail),
          requiredConsents: _stringList(detail['required_consents']),
        );
      }
      if (detail is String) {
        return ApiError(
          statusCode: statusCode,
          message: _safeUserMessage(detail),
        );
      }
    }

    return ApiError(statusCode: statusCode, message: 'Request failed.');
  }

  static Object? _tryDecodeJson(String body) {
    try {
      return jsonDecode(body);
    } on FormatException {
      return null;
    }
  }

  static String? _safeErrorCode(Object? value) {
    if (value is! String) {
      return null;
    }
    final String trimmed = value.trim();
    return _safeErrorCodePattern.hasMatch(trimmed) ? trimmed : null;
  }

  static String _detailMessage(Map<String, dynamic> detail) {
    final Object? message = detail['message'];
    if (message is String && message.trim().isNotEmpty) {
      return _safeUserMessage(message);
    }
    final String? code = _safeErrorCode(detail['code']);
    if (code != null) {
      return code;
    }
    return 'Request failed.';
  }

  static String _safeUserMessage(String value) {
    final String trimmed = value.trim();
    if (trimmed.isEmpty ||
        trimmed.length > _maxUserSafeMessageLength ||
        _containsSensitiveMarker(trimmed)) {
      return 'Request failed.';
    }
    return trimmed;
  }

  static bool _containsSensitiveMarker(String value) {
    final String normalized = value.toLowerCase();
    return _sensitiveErrorMessageMarkers.any(normalized.contains);
  }

  static List<String> _stringList(Object? value) {
    if (value is! List<Object?>) {
      return const <String>[];
    }
    return value.whereType<String>().toList(growable: false);
  }

  @override
  String toString() {
    final String codePart = code == null ? '' : ' code=$code';
    return 'ApiError(status=$statusCode$codePart, message=$message)';
  }
}
