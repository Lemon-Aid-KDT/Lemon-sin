import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/core/config/app_config.dart';

void main() {
  test('defaults Android emulator runs to host loopback', () {
    final AppConfig config = AppConfig.fromEnvironment(
      platform: TargetPlatform.android,
    );

    expect(config.apiBaseUrl, 'http://10.0.2.2:8000/api/v1');
  });

  test('defaults iOS simulator runs to localhost backend', () {
    final AppConfig config = AppConfig.fromEnvironment(
      platform: TargetPlatform.iOS,
    );

    expect(config.apiBaseUrl, 'http://127.0.0.1:8000/api/v1');
  });

  test('keeps release defaults fail closed without explicit HTTPS pins', () {
    expect(
      () => AppConfig.fromEnvironment(
        platform: TargetPlatform.android,
        releaseMode: true,
      ),
      throwsA(isA<StateError>()),
    );
  });

  test('allows local development HTTP and token values', () {
    final AppConfig config = AppConfig.fromValues(
      apiBaseUrl: 'http://127.0.0.1:8000/api/v1/',
      apiToken: 'local-token',
    );

    expect(config.apiBaseUrl, 'http://127.0.0.1:8000/api/v1');
    expect(config.apiToken, 'local-token');
    expect(config.devGatewayToken, isNull);
    expect(config.certificatePins, isEmpty);
  });

  test('allows local development gateway token', () {
    final AppConfig config = AppConfig.fromValues(
      apiBaseUrl: 'https://example.ngrok.app/api/v1',
      devGatewayToken: ' local-gateway-token ',
    );

    expect(config.devGatewayToken, 'local-gateway-token');
  });

  test('requires HTTPS in release builds', () {
    expect(
      () => AppConfig.fromValues(
        apiBaseUrl: 'http://api.example.com/api/v1',
        releaseMode: true,
      ),
      throwsA(isA<StateError>()),
    );
  });

  test('rejects embedded release tokens', () {
    expect(
      () => AppConfig.fromValues(
        apiBaseUrl: 'https://api.example.com/api/v1',
        apiToken: 'must-not-ship',
        releaseMode: true,
      ),
      throwsA(isA<StateError>()),
    );
  });

  test('rejects embedded release gateway tokens', () {
    expect(
      () => AppConfig.fromValues(
        apiBaseUrl: 'https://api.example.com/api/v1',
        devGatewayToken: 'must-not-ship',
        releaseMode: true,
      ),
      throwsA(isA<StateError>()),
    );
  });

  test('requires api v1 suffix', () {
    expect(
      () => AppConfig.fromValues(apiBaseUrl: 'https://api.example.com'),
      throwsA(isA<StateError>()),
    );
  });

  test('requires certificate pins in release builds', () {
    expect(
      () => AppConfig.fromValues(
        apiBaseUrl: 'https://api.example.com/api/v1',
        releaseMode: true,
      ),
      throwsA(isA<StateError>()),
    );
  });

  test('allows HTTPS release config with certificate pins', () {
    final AppConfig config = AppConfig.fromValues(
      apiBaseUrl: 'https://api.example.com/api/v1',
      certificatePins: const <String>['pin-primary', 'pin-backup'],
      releaseMode: true,
    );

    expect(config.apiBaseUrl, 'https://api.example.com/api/v1');
    expect(config.apiToken, isNull);
    expect(config.devGatewayToken, isNull);
    expect(config.certificatePins, const <String>['pin-primary', 'pin-backup']);
  });
}
