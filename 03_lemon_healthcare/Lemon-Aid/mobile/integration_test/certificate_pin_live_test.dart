import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  const bool runLiveTest = bool.fromEnvironment(
    'RUN_CERTIFICATE_PIN_LIVE_TEST',
  );
  const String host = String.fromEnvironment('CERTIFICATE_PIN_TEST_HOST');
  const int port = int.fromEnvironment(
    'CERTIFICATE_PIN_TEST_PORT',
    defaultValue: 443,
  );
  const String validPin = String.fromEnvironment(
    'CERTIFICATE_PIN_TEST_VALID_PIN',
  );
  const String invalidPin = String.fromEnvironment(
    'CERTIFICATE_PIN_TEST_INVALID_PIN',
    defaultValue: 'sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=',
  );
  const MethodChannel pinChannel = MethodChannel(
    'com.lemonaid.mobile/certificate_pins',
  );

  testWidgets('native certificate pin verifier matches and rejects pins', (
    WidgetTester tester,
  ) async {
    if (!runLiveTest) {
      return;
    }
    expect(host, isNotEmpty);
    expect(validPin, startsWith('sha256/'));

    final bool? matched = await pinChannel.invokeMethod<bool>(
      'verifyServerPins',
      <String, Object>{
        'host': host,
        'port': port,
        'pins': <String>[validPin],
      },
    );
    expect(matched, isTrue);

    await expectLater(
      pinChannel.invokeMethod<bool>('verifyServerPins', <String, Object>{
        'host': host,
        'port': port,
        'pins': <String>[invalidPin],
      }),
      throwsA(
        isA<PlatformException>().having(
          (PlatformException error) => error.code,
          'code',
          'certificate_pin_mismatch',
        ),
      ),
    );
  });
}
