import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/core/api/api_error.dart';

void main() {
  test('parses backend consent-required detail', () {
    final ApiError error = ApiError.fromBody(
      statusCode: 403,
      body: jsonEncode(<String, Object?>{
        'detail': <String, Object?>{
          'code': 'consent_required',
          'message': 'Consent is required.',
          'required_consents': <String>[
            'ocr_image_processing',
            'sensitive_health_analysis',
          ],
        },
      }),
    );

    expect(error.statusCode, 403);
    expect(error.code, 'consent_required');
    expect(error.message, 'Consent is required.');
    expect(error.requiredConsents, <String>[
      'ocr_image_processing',
      'sensitive_health_analysis',
    ]);
  });

  test('does not surface raw response body as user message', () {
    final ApiError error = ApiError.fromBody(
      statusCode: 500,
      body: 'raw_ocr_text=Vitamin D\\nAuthorization: Bearer token',
    );

    expect(error.message, 'Request failed.');
    expect(error.toString(), isNot(contains('raw_ocr_text')));
    expect(error.toString(), isNot(contains('Bearer')));
  });

  test('redacts sensitive backend detail message', () {
    final ApiError error = ApiError.fromBody(
      statusCode: 422,
      body: jsonEncode(<String, Object?>{
        'detail': <String, Object?>{
          'code': 'ocr_provider_error',
          'message': 'provider_payload contained raw_ocr_text',
        },
      }),
    );

    expect(error.code, 'ocr_provider_error');
    expect(error.message, 'Request failed.');
  });

  test('redacts sensitive string detail', () {
    final ApiError error = ApiError.fromBody(
      statusCode: 400,
      body: jsonEncode(<String, Object?>{
        'detail': 'request_headers Authorization Bearer abc',
      }),
    );

    expect(error.message, 'Request failed.');
  });

  test('drops unsafe backend error code', () {
    final ApiError error = ApiError.fromBody(
      statusCode: 400,
      body: jsonEncode(<String, Object?>{
        'detail': <String, Object?>{'code': 'raw_ocr_text=secret'},
      }),
    );

    expect(error.code, isNull);
    expect(error.message, 'Request failed.');
  });

  test('keeps short safe backend detail string', () {
    final ApiError error = ApiError.fromBody(
      statusCode: 404,
      body: jsonEncode(<String, Object?>{'detail': 'Not found.'}),
    );

    expect(error.message, 'Not found.');
  });
}
