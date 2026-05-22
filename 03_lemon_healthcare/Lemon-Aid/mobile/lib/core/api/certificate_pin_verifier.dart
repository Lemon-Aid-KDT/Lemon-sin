import 'package:flutter/services.dart';

/// Error raised when certificate pin verification cannot prove a match.
class CertificatePinException implements Exception {
  /// Creates a certificate pin exception.
  ///
  /// Args:
  ///   code: Bounded non-secret error code.
  ///   message: Safe diagnostic message.
  const CertificatePinException(this.code, this.message);

  /// Bounded non-secret error code.
  final String code;

  /// Safe diagnostic message.
  final String message;

  @override
  String toString() {
    return 'CertificatePinException($code): $message';
  }
}

/// Verifies configured certificate pins before API requests.
abstract interface class CertificatePinVerifier {
  /// Verifies that the TLS peer certificate chain matches at least one pin.
  ///
  /// Args:
  ///   uri: HTTPS URI whose host and port should be verified.
  ///   pins: Release certificate pins in `sha256/<base64>` format.
  ///
  /// Raises:
  ///   CertificatePinException: If verification fails or no pin matches.
  Future<void> verify(Uri uri, List<String> pins);
}

/// Native platform-channel backed certificate pin verifier.
class PlatformCertificatePinVerifier implements CertificatePinVerifier {
  /// Creates a platform certificate pin verifier.
  const PlatformCertificatePinVerifier({
    MethodChannel channel = const MethodChannel(
      'com.lemonaid.mobile/certificate_pins',
    ),
  }) : _channel = channel;

  final MethodChannel _channel;

  @override
  Future<void> verify(Uri uri, List<String> pins) async {
    if (uri.scheme != 'https') {
      throw const CertificatePinException(
        'certificate_pin_requires_https',
        'Certificate pin verification requires HTTPS.',
      );
    }
    if (pins.isEmpty) {
      throw const CertificatePinException(
        'certificate_pin_missing',
        'Certificate pins are required.',
      );
    }

    try {
      final bool? verified = await _channel.invokeMethod<bool>(
        'verifyServerPins',
        <String, Object>{
          'host': uri.host,
          'port': uri.hasPort ? uri.port : 443,
          'pins': pins,
        },
      );
      if (verified != true) {
        throw const CertificatePinException(
          'certificate_pin_mismatch',
          'The server certificate did not match the configured pins.',
        );
      }
    } on PlatformException catch (error) {
      throw CertificatePinException(
        error.code,
        error.message ?? 'Certificate pin verification failed.',
      );
    } on MissingPluginException catch (_) {
      throw const CertificatePinException(
        'certificate_pin_plugin_missing',
        'Certificate pin verifier is unavailable.',
      );
    }
  }
}
