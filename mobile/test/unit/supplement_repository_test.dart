import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:lemon_aid_mobile/core/api/api_client.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';

void main() {
  test(
    'uses configured OCR provider by default on supplement upload',
    () async {
      final File image = _writeTinyPng();
      addTearDown(() {
        if (image.existsSync()) {
          image.deleteSync();
        }
      });
      late http.MultipartRequest capturedRequest;
      final ApiClient apiClient = ApiClient(
        baseUrl: 'http://localhost:8000/api/v1',
        httpClient: _CaptureMultipartClient(
          onRequest: (http.MultipartRequest request) {
            capturedRequest = request;
          },
        ),
      );
      addTearDown(apiClient.close);
      final BackendLemonAidRepository repository = BackendLemonAidRepository(
        apiClient: apiClient,
      );

      await repository.analyzeSupplementImage(image.path);

      expect(capturedRequest.fields['ocr_provider'], 'configured');
      expect(
        capturedRequest.fields['client_request_id'],
        startsWith('mobile-'),
      );
      expect(capturedRequest.files.single.field, 'image');
    },
  );

  test('passes selected OCR provider on supplement image upload', () async {
    final File image = _writeTinyPng();
    addTearDown(() {
      if (image.existsSync()) {
        image.deleteSync();
      }
    });
    late http.MultipartRequest capturedRequest;
    final ApiClient apiClient = ApiClient(
      baseUrl: 'http://localhost:8000/api/v1',
      httpClient: _CaptureMultipartClient(
        onRequest: (http.MultipartRequest request) {
          capturedRequest = request;
        },
      ),
    );
    addTearDown(apiClient.close);
    final BackendLemonAidRepository repository = BackendLemonAidRepository(
      apiClient: apiClient,
    );

    await repository.analyzeSupplementImage(
      image.path,
      ocrProvider: 'google_vision',
    );

    expect(capturedRequest.fields['ocr_provider'], 'google_vision');
    expect(capturedRequest.files.single.field, 'image');
  });

  test('adds development gateway token header on supplement upload', () async {
    final File image = _writeTinyPng();
    addTearDown(() {
      if (image.existsSync()) {
        image.deleteSync();
      }
    });
    late http.MultipartRequest capturedRequest;
    final ApiClient apiClient = ApiClient(
      baseUrl: 'https://example.ngrok.app/api/v1',
      devGatewayToken: 'debug-gateway-token',
      httpClient: _CaptureMultipartClient(
        onRequest: (http.MultipartRequest request) {
          capturedRequest = request;
        },
      ),
    );
    addTearDown(apiClient.close);
    final BackendLemonAidRepository repository = BackendLemonAidRepository(
      apiClient: apiClient,
    );

    await repository.analyzeSupplementImage(image.path);

    expect(
      capturedRequest.headers['X-Lemon-Dev-Gateway-Token'],
      'debug-gateway-token',
    );
    expect(capturedRequest.headers, isNot(contains('Authorization')));
  });

  test('adds configured JWT bearer token on supplement upload', () async {
    final File image = _writeTinyPng();
    addTearDown(() {
      if (image.existsSync()) {
        image.deleteSync();
      }
    });
    late http.MultipartRequest capturedRequest;
    final ApiClient apiClient = ApiClient(
      baseUrl: 'https://api.example.com/api/v1',
      bearerToken: 'jwt-access-token',
      httpClient: _CaptureMultipartClient(
        onRequest: (http.MultipartRequest request) {
          capturedRequest = request;
        },
      ),
    );
    addTearDown(apiClient.close);
    final BackendLemonAidRepository repository = BackendLemonAidRepository(
      apiClient: apiClient,
    );

    await repository.analyzeSupplementImage(image.path);

    expect(capturedRequest.headers['Authorization'], 'Bearer jwt-access-token');
    expect(capturedRequest.fields['ocr_provider'], 'configured');
  });
}

class _CaptureMultipartClient extends http.BaseClient {
  _CaptureMultipartClient({required this.onRequest});

  final void Function(http.MultipartRequest request) onRequest;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    onRequest(request as http.MultipartRequest);
    return http.StreamedResponse(
      Stream<List<int>>.value(utf8.encode(jsonEncode(_previewResponse))),
      202,
      headers: <String, String>{'content-type': 'application/json'},
    );
  }
}

final Map<String, Object?> _previewResponse = <String, Object?>{
  'analysis_id': '00000000-0000-0000-0000-000000000001',
  'status': 'requires_confirmation',
  'parsed_product': <String, Object?>{},
  'ingredient_candidates': <Object?>[],
  'matched_product_candidates': <Object?>[],
  'low_confidence_fields': <Object?>[],
  'warnings': <Object?>[],
  'algorithm_version': 'test',
  'source_manifest_version': null,
  'expires_at': '2026-05-21T00:00:00Z',
};

File _writeTinyPng() {
  final Directory directory = Directory.systemTemp.createTempSync(
    'lemon-aid-repository-test-',
  );
  final File file = File('${directory.path}/label.png');
  addTearDown(() {
    if (directory.existsSync()) {
      directory.deleteSync(recursive: true);
    }
  });
  file.writeAsBytesSync(
    base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=',
    ),
  );
  return file;
}
