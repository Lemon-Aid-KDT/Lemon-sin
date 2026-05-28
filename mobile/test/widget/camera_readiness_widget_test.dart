import 'dart:convert';
import 'dart:io';

import 'package:camera/camera.dart' as camera;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/app_controller.dart';
import 'package:lemon_aid_mobile/core/api/api_error.dart';
import 'package:lemon_aid_mobile/features/consent/consent_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/dashboard_models.dart';
import 'package:lemon_aid_mobile/features/supplements/camera_readiness.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_flow_screen.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';
import 'package:image_picker/image_picker.dart';

void main() {
  testWidgets('iOS runtime with no cameras keeps gallery endpoint path open', (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _CameraWidgetRepository(),
    );
    addTearDown(controller.dispose);
    await controller.bootstrap();

    await tester.pumpWidget(
      MaterialApp(
        home: SupplementFlowScreen(
          controller: controller,
          cameraReadinessProbe: CameraReadinessProbe(
            platform: TargetPlatform.iOS,
            loader: () async => const <camera.CameraDescription>[],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('iOS 카메라 없음'), findsOneWidget);
    expect(find.textContaining('갤러리 이미지'), findsAtLeastNWidgets(1));

    final IconButton shutter = _iconButtonByTooltip(tester, '촬영');
    final IconButton gallery = _iconButtonByTooltip(tester, '갤러리');
    expect(shutter.onPressed, isNull);
    expect(gallery.onPressed, isNotNull);
  });

  testWidgets('Android runtime with camera enables direct capture control', (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _CameraWidgetRepository(),
    );
    addTearDown(controller.dispose);
    await controller.bootstrap();

    await tester.pumpWidget(
      MaterialApp(
        home: SupplementFlowScreen(
          controller: controller,
          cameraReadinessProbe: CameraReadinessProbe(
            platform: TargetPlatform.android,
            loader: () async {
              return const <camera.CameraDescription>[
                camera.CameraDescription(
                  name: '0',
                  lensDirection: camera.CameraLensDirection.back,
                  sensorOrientation: 90,
                ),
              ];
            },
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Android 카메라 연결됨'), findsOneWidget);
    final IconButton shutter = _iconButtonByTooltip(tester, '촬영');
    expect(shutter.onPressed, isNotNull);
  });

  testWidgets('analysis endpoint errors remain visible on camera tab', (
    WidgetTester tester,
  ) async {
    final File image = _writeTinyPng();
    addTearDown(() {
      if (image.existsSync()) {
        image.deleteSync();
      }
    });
    final AppController controller = AppController(
      repository: _CameraWidgetRepository(
        analyzeError: const ApiError(
          statusCode: 403,
          code: 'consent_required',
          message: 'Consent is required.',
          requiredConsents: <String>['ocr_image_processing'],
        ),
      ),
    );
    addTearDown(controller.dispose);
    await controller.bootstrap();

    await tester.pumpWidget(
      MaterialApp(
        home: SupplementFlowScreen(
          controller: controller,
          imagePicker: _FakeImagePicker(image.path),
          cameraReadinessProbe: CameraReadinessProbe(
            platform: TargetPlatform.iOS,
            loader: () async => const <camera.CameraDescription>[],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('갤러리'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('분석하기'));
    await tester.pumpAndSettle();

    expect(find.text('Request failed (403)'), findsOneWidget);
    expect(find.textContaining('Consent is required.'), findsOneWidget);
    expect(find.text('분석하기'), findsOneWidget);
  });

  testWidgets('selected OCR provider reaches real analysis flow', (
    WidgetTester tester,
  ) async {
    final File image = _writeTinyPng();
    addTearDown(() {
      if (image.existsSync()) {
        image.deleteSync();
      }
    });
    final _CameraWidgetRepository repository = _CameraWidgetRepository();
    final AppController controller = AppController(repository: repository);
    final _FakeImagePicker picker = _FakeImagePicker(image.path);
    addTearDown(controller.dispose);
    await controller.bootstrap();

    await tester.pumpWidget(
      MaterialApp(
        home: SupplementFlowScreen(
          controller: controller,
          imagePicker: picker,
          cameraReadinessProbe: CameraReadinessProbe(
            platform: TargetPlatform.android,
            loader: () async => const <camera.CameraDescription>[],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('갤러리'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Paddle'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('분석하기'));
    await tester.pumpAndSettle();

    expect(repository.lastImagePath, image.path);
    expect(repository.lastOcrProvider, 'paddleocr');
    expect(picker.lastMaxWidth, 2400);
    expect(picker.lastImageQuality, 95);
    expect(find.text('Preview'), findsOneWidget);
  });
}

IconButton _iconButtonByTooltip(WidgetTester tester, String tooltip) {
  return tester
      .widgetList<IconButton>(find.byType(IconButton))
      .singleWhere((IconButton button) => button.tooltip == tooltip);
}

class _FakeImagePicker extends ImagePicker {
  _FakeImagePicker(this.path);

  final String path;
  double? lastMaxWidth;
  int? lastImageQuality;

  @override
  Future<XFile?> pickImage({
    required ImageSource source,
    double? maxWidth,
    double? maxHeight,
    int? imageQuality,
    CameraDevice preferredCameraDevice = CameraDevice.rear,
    bool requestFullMetadata = true,
  }) async {
    lastMaxWidth = maxWidth;
    lastImageQuality = imageQuality;
    return XFile(path);
  }
}

class _CameraWidgetRepository implements LemonAidRepository {
  _CameraWidgetRepository({this.analyzeError});

  final ApiError? analyzeError;
  String? lastImagePath;
  String? lastOcrProvider;

  @override
  Future<SupplementAnalysisPreview> analyzeSupplementImage(
    String imagePath, {
    String ocrProvider = 'configured',
  }) async {
    lastImagePath = imagePath;
    lastOcrProvider = ocrProvider;
    final ApiError? error = analyzeError;
    if (error != null) {
      throw error;
    }
    return SupplementAnalysisPreview.fromJson(_previewResponse);
  }

  @override
  Future<MealImageAnalysisPreview> analyzeMealImage(
    String imagePath, {
    String mealType = 'unknown',
  }) {
    throw UnimplementedError();
  }

  @override
  Future<SupplementMultiImageAnalysisPreview> analyzeSupplementImages(
    List<SupplementImageUpload> images, {
    String ocrProvider = 'configured',
  }) {
    throw UnimplementedError();
  }

  @override
  Future<SupplementAnalysisSession> createSupplementAnalysisSession() {
    throw UnimplementedError();
  }

  @override
  Future<SupplementMultiImageAnalysisPreview>
  uploadSupplementAnalysisSessionImage(
    String analysisGroupId,
    SupplementImageUpload image, {
    String ocrProvider = 'configured',
    String? clientRequestId,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<SupplementMultiImageAnalysisPreview> finalizeSupplementAnalysisSession(
    String analysisGroupId,
  ) {
    throw UnimplementedError();
  }

  @override
  void close() {}

  @override
  Future<ConsentState> fetchConsents() async {
    return ConsentState(
      consents: <ConsentStatus>[
        _consent(AppController.ocrConsent),
        _consent(AppController.healthConsent),
      ],
    );
  }

  @override
  Future<ConsentAction> grantConsent(String consentType) async {
    return ConsentAction(
      consentType: consentType,
      policyVersion: 'test',
      granted: true,
      occurredAt: DateTime.utc(2026, 5, 25),
    );
  }

  @override
  Future<DashboardSummary> fetchDashboardSummary({int days = 30}) async {
    return DashboardSummary(
      asOf: DateTime.utc(2026, 5, 25),
      nutrition: const DashboardNutritionSummary(
        dataStatus: 'ready',
        lowCount: 0,
        highCount: 0,
        datasetVersion: 'test',
      ),
      activity: const DashboardActivitySummary(
        dataStatus: 'not_ready',
        latestSteps: null,
        latestActivityScore: null,
      ),
      weight: const DashboardWeightSummary(
        dataStatus: 'not_ready',
        latestWeightKg: null,
        predictedWeightKg: null,
      ),
      supplements: const DashboardSupplementSummary(
        registeredCount: 0,
        requiresReviewCount: 0,
      ),
      disclaimers: const <String>[],
      algorithmVersion: 'test',
    );
  }

  @override
  Future<SupplementImpactPreviewResponse>
  fetchLatestSupplementRecommendation() {
    throw UnimplementedError();
  }

  @override
  Future<SupplementRecommendationExplainResponse>
  explainSupplementRecommendation(
    SupplementImpactPreviewResponse preview, {
    bool useLocalLlm = false,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<SupplementRecommendationExplainResponse> explainSupplementAnalysis(
    String analysisId, {
    bool useLocalLlm = false,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<SupplementAnalysisPreview> parseOcrText({
    required String analysisId,
    required SupplementOCRTextParseRequest request,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<SupplementImpactPreviewResponse> previewSupplementImpact(
    SupplementImpactPreviewRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<UserSupplementResponse> registerSupplement(
    UserSupplementCreate request,
  ) {
    throw UnimplementedError();
  }

  ConsentStatus _consent(String consentType) {
    return ConsentStatus(
      consentType: consentType,
      policyVersion: 'test',
      title: consentType,
      required: true,
      granted: true,
      occurredAt: DateTime.utc(2026, 5, 25),
      revokedAt: null,
    );
  }
}

final Map<String, Object?> _previewResponse = <String, Object?>{
  'analysis_id': '00000000-0000-0000-0000-000000000010',
  'status': 'requires_confirmation',
  'parsed_product': <String, Object?>{},
  'ingredient_candidates': <Object?>[],
  'layout_available': false,
  'layout_fallback_reason': 'test',
  'label_sections': <Object?>[],
  'pipeline_metadata': <String, Object?>{
    'intake_completed': true,
    'vision_roi_used': false,
    'ocr_provider': 'paddleocr_local',
    'llm_parser_used': false,
    'raw_image_stored': false,
    'raw_ocr_text_stored': false,
  },
  'low_confidence_fields': <Object?>[],
  'warnings': <Object?>[],
  'algorithm_version': 'test',
  'source_manifest_version': null,
  'expires_at': '2026-05-25T00:00:00Z',
};

File _writeTinyPng() {
  final Directory directory = Directory.systemTemp.createTempSync(
    'lemon-aid-camera-widget-test-',
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
