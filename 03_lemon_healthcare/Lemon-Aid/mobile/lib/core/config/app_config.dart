import 'package:flutter/foundation.dart';

/// Runtime configuration loaded from Flutter compile-time definitions.
class AppConfig {
  /// Creates app configuration.
  ///
  /// Args:
  ///   apiBaseUrl: Backend API base URL ending at `/api/v1`.
  ///   apiToken: Optional bearer token. Local `AUTH_MODE=disabled` runs without it.
  const AppConfig({
    required this.apiBaseUrl,
    required this.apiToken,
    required this.certificatePins,
  });

  /// Backend API base URL ending at `/api/v1`.
  final String apiBaseUrl;

  /// Optional bearer token for JWT-backed environments.
  final String? apiToken;

  /// Release certificate pin configuration reserved for the hardened API client.
  final List<String> certificatePins;

  /// Builds configuration from `--dart-define` values.
  ///
  /// Returns:
  ///   AppConfig with a normalized base URL and optional token.
  factory AppConfig.fromEnvironment({bool releaseMode = kReleaseMode}) {
    const String rawBaseUrl = String.fromEnvironment(
      'LEMON_API_BASE_URL',
      defaultValue: 'http://127.0.0.1:8000/api/v1',
    );
    const String rawToken = String.fromEnvironment('LEMON_API_TOKEN');
    const String rawCertificatePins = String.fromEnvironment(
      'LEMON_CERTIFICATE_PINS',
    );

    return AppConfig.fromValues(
      apiBaseUrl: rawBaseUrl,
      apiToken: rawToken,
      certificatePins: _splitCommaSeparated(rawCertificatePins),
      releaseMode: releaseMode,
    );
  }

  /// Builds configuration from explicit values.
  ///
  /// Args:
  ///   apiBaseUrl: Backend API base URL ending at `/api/v1`.
  ///   apiToken: Optional local-development bearer token.
  ///   certificatePins: Certificate pin config required for release builds.
  ///   releaseMode: Whether release binary restrictions should be enforced.
  ///
  /// Returns:
  ///   Validated app configuration.
  ///
  /// Raises:
  ///   StateError: If release configuration contains unsafe values.
  factory AppConfig.fromValues({
    required String apiBaseUrl,
    String? apiToken,
    List<String> certificatePins = const <String>[],
    bool releaseMode = false,
  }) {
    final String normalizedBaseUrl = _withoutTrailingSlash(apiBaseUrl.trim());
    final String? normalizedToken = apiToken == null || apiToken.trim().isEmpty
        ? null
        : apiToken.trim();
    final List<String> normalizedCertificatePins = certificatePins
        .map((String value) => value.trim())
        .where((String value) => value.isNotEmpty)
        .toList(growable: false);

    if (releaseMode && normalizedToken != null) {
      throw StateError(
        'LEMON_API_TOKEN must not be embedded in release builds.',
      );
    }
    if (releaseMode && !normalizedBaseUrl.startsWith('https://')) {
      throw StateError('LEMON_API_BASE_URL must use HTTPS in release builds.');
    }
    if (!normalizedBaseUrl.endsWith('/api/v1')) {
      throw StateError('LEMON_API_BASE_URL must end with /api/v1.');
    }
    if (releaseMode && normalizedCertificatePins.isEmpty) {
      throw StateError(
        'LEMON_CERTIFICATE_PINS must be provided in release builds.',
      );
    }

    return AppConfig(
      apiBaseUrl: normalizedBaseUrl,
      apiToken: normalizedToken,
      certificatePins: List<String>.unmodifiable(normalizedCertificatePins),
    );
  }

  static List<String> _splitCommaSeparated(String value) {
    if (value.trim().isEmpty) {
      return const <String>[];
    }
    return value
        .split(',')
        .map((String item) => item.trim())
        .where((String item) => item.isNotEmpty)
        .toList(growable: false);
  }

  static String _withoutTrailingSlash(String value) {
    if (value.endsWith('/')) {
      return value.substring(0, value.length - 1);
    }
    return value;
  }
}
