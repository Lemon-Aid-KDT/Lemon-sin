import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/core/config/app_config.dart';

void main() {
  test('allows local development HTTP and token values', () {
    final AppConfig config = AppConfig.fromValues(
      apiBaseUrl: 'http://127.0.0.1:8000/api/v1/',
      apiToken: 'local-token',
    );

    expect(config.apiBaseUrl, 'http://127.0.0.1:8000/api/v1');
    expect(config.apiToken, 'local-token');
    expect(config.certificatePins, isEmpty);
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
    expect(config.certificatePins, const <String>['pin-primary', 'pin-backup']);
  });
}
