import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:lemon_aid_mobile/core/api/api_client.dart';
import 'package:lemon_aid_mobile/core/api/certificate_pin_verifier.dart';

const String pinPrimary = 'sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=';

void main() {
  test('verifies certificate pins before GET request', () async {
    final _RecordingCertificatePinVerifier verifier =
        _RecordingCertificatePinVerifier();
    final ApiClient client = ApiClient(
      baseUrl: 'https://api.example.com/api/v1',
      certificatePins: const <String>[pinPrimary],
      certificatePinVerifier: verifier,
      httpClient: MockClient((http.Request request) async {
        expect(verifier.calls, 1);
        expect(request.url.host, 'api.example.com');
        return http.Response('{"ok": true}', 200);
      }),
    );

    final Map<String, dynamic> response = await client.getJson('/health');

    expect(response['ok'], isTrue);
    expect(verifier.calls, 1);
    expect(verifier.lastUri?.path, '/api/v1/health');
    expect(verifier.lastPins, const <String>[pinPrimary]);
  });

  test('certificate pin mismatch fails before request is sent', () async {
    final ApiClient client = ApiClient(
      baseUrl: 'https://api.example.com/api/v1',
      certificatePins: const <String>[pinPrimary],
      certificatePinVerifier: _RejectingCertificatePinVerifier(),
      httpClient: MockClient((http.Request request) async {
        fail('HTTP request should not be sent after pin mismatch.');
      }),
    );

    expect(
      () => client.getJson('/health'),
      throwsA(isA<CertificatePinException>()),
    );
  });

  test('verifies certificate pins before POST request', () async {
    final _RecordingCertificatePinVerifier verifier =
        _RecordingCertificatePinVerifier();
    final ApiClient client = ApiClient(
      baseUrl: 'https://api.example.com/api/v1',
      certificatePins: const <String>[pinPrimary],
      certificatePinVerifier: verifier,
      httpClient: MockClient((http.Request request) async {
        expect(verifier.calls, 1);
        expect(request.method, 'POST');
        expect(request.url.path, '/api/v1/supplements');
        return http.Response('{"ok": true}', 201);
      }),
    );

    final Map<String, dynamic> response = await client.postJson(
      '/supplements',
      body: const <String, dynamic>{'name': 'vitamin-c'},
      expectedStatusCodes: const <int>{201},
    );

    expect(response['ok'], isTrue);
    expect(verifier.calls, 1);
    expect(verifier.lastUri?.path, '/api/v1/supplements');
  });

  test('verifies certificate pins before multipart upload', () async {
    final File image = File(
      '${Directory.systemTemp.createTempSync('lemon-aid-api-client-test-').path}/label.png',
    )..writeAsBytesSync(<int>[0x89, 0x50, 0x4E, 0x47]);
    addTearDown(() {
      final Directory parent = image.parent;
      if (parent.existsSync()) {
        parent.deleteSync(recursive: true);
      }
    });
    final _RecordingCertificatePinVerifier verifier =
        _RecordingCertificatePinVerifier();
    final ApiClient client = ApiClient(
      baseUrl: 'https://api.example.com/api/v1',
      certificatePins: const <String>[pinPrimary],
      certificatePinVerifier: verifier,
      httpClient: MockClient((http.Request request) async {
        expect(verifier.calls, 1);
        expect(request.method, 'POST');
        expect(request.url.path, '/api/v1/supplements/analyze-image');
        expect(
          request.headers['content-type'],
          contains('multipart/form-data'),
        );
        return http.Response('{"analysis_id": "a1"}', 202);
      }),
    );

    final Map<String, dynamic> response = await client.postMultipart(
      '/supplements/analyze-image',
      fileField: 'image',
      filePath: image.path,
    );

    expect(response['analysis_id'], 'a1');
    expect(verifier.calls, 1);
    expect(verifier.lastUri?.path, '/api/v1/supplements/analyze-image');
  });
}

class _RecordingCertificatePinVerifier implements CertificatePinVerifier {
  int calls = 0;
  Uri? lastUri;
  List<String>? lastPins;

  @override
  Future<void> verify(Uri uri, List<String> pins) async {
    calls += 1;
    lastUri = uri;
    lastPins = List<String>.unmodifiable(pins);
  }
}

class _RejectingCertificatePinVerifier implements CertificatePinVerifier {
  @override
  Future<void> verify(Uri uri, List<String> pins) async {
    throw const CertificatePinException(
      'certificate_pin_mismatch',
      'The server certificate did not match the configured pins.',
    );
  }
}
