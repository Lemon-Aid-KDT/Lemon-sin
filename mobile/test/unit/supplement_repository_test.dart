import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:lemon_aid_mobile/core/api/api_client.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
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
      expect(capturedRequest.files.single.contentType.mimeType, 'image/png');
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
    expect(capturedRequest.files.single.contentType.mimeType, 'image/png');
  });

  test(
    'sniffs image content type when selected path has no extension',
    () async {
      final File image = _writeTinyPng(fileName: 'label');
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

      expect(capturedRequest.files.single.contentType.mimeType, 'image/png');
    },
  );

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

  test(
    'requests local Ollama explanation through the existing endpoint',
    () async {
      late http.Request capturedRequest;
      final ApiClient apiClient = ApiClient(
        baseUrl: 'http://localhost:8000/api/v1',
        httpClient: _CaptureJsonClient(
          onRequest: (http.Request request) {
            capturedRequest = request;
          },
        ),
      );
      addTearDown(apiClient.close);
      final BackendLemonAidRepository repository = BackendLemonAidRepository(
        apiClient: apiClient,
      );
      final SupplementImpactPreviewResponse preview =
          SupplementImpactPreviewResponse.fromJson(_impactPreviewResponse);

      final SupplementRecommendationExplainResponse response = await repository
          .explainSupplementRecommendation(preview, useLocalLlm: true);

      final Map<String, dynamic> body =
          jsonDecode(capturedRequest.body) as Map<String, dynamic>;
      expect(
        capturedRequest.url.path,
        '/api/v1/supplements/recommendations/explain',
      );
      expect(body['use_local_llm'], isTrue);
      expect(response.llmUsed, isTrue);
    },
  );
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

class _CaptureJsonClient extends http.BaseClient {
  _CaptureJsonClient({required this.onRequest});

  final void Function(http.Request request) onRequest;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final http.Request jsonRequest = request as http.Request;
    onRequest(jsonRequest);
    return http.StreamedResponse(
      Stream<List<int>>.value(utf8.encode(jsonEncode(_explainResponse))),
      200,
      headers: <String, String>{'content-type': 'application/json'},
    );
  }
}

final Map<String, Object?> _previewResponse = <String, Object?>{
  'analysis_id': '00000000-0000-0000-0000-000000000001',
  'status': 'requires_confirmation',
  'parsed_product': <String, Object?>{},
  'ingredient_candidates': <Object?>[],
  'pipeline_metadata': <String, Object?>{
    'intake_completed': true,
    'vision_roi_used': false,
    'ocr_provider': 'intake-only',
    'llm_parser_used': false,
    'raw_image_stored': false,
    'raw_ocr_text_stored': false,
  },
  'matched_product_candidates': <Object?>[],
  'low_confidence_fields': <Object?>[],
  'warnings': <Object?>[],
  'algorithm_version': 'test',
  'source_manifest_version': null,
  'expires_at': '2026-05-21T00:00:00Z',
};

final Map<String, Object?> _impactPreviewResponse = <String, Object?>{
  'calculation_version': 'supplement-impact-v1.0.0',
  'reference_version': '2025',
  'source_manifest_version': null,
  'data_status': 'partial',
  'current_supplement_contributions': <Object?>[],
  'deficiency_support_candidates': <Object?>[],
  'excess_or_duplicate_risks': <Object?>[],
  'missing_profile_fields': <Object?>[],
  'safe_user_message': 'Review current supplement intake.',
  'clinical_disclaimer': 'Reference information only.',
  'warnings': <Object?>[],
  'requires_user_confirmation': true,
};

final Map<String, Object?> _explainResponse = <String, Object?>{
  'safe_user_message': 'Local explanation is ready.',
  'explanation_bullets': <String>['Review duplicate supplement sources.'],
  'clinical_disclaimer': 'Reference information only.',
  'blocked_terms_detected': <Object?>[],
  'llm_used': true,
  'warnings': <Object?>[],
};

File _writeTinyPng({String fileName = 'label.png'}) {
  final Directory directory = Directory.systemTemp.createTempSync(
    'lemon-aid-repository-test-',
  );
  final File file = File('${directory.path}/$fileName');
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
