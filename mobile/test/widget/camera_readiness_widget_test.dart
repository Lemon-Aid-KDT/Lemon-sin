import 'package:camera/camera.dart' as camera;
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/app_controller.dart';
import 'package:lemon_aid_mobile/features/consent/consent_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/dashboard_models.dart';
import 'package:lemon_aid_mobile/features/supplements/camera_readiness.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_flow_screen.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';

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
}

IconButton _iconButtonByTooltip(WidgetTester tester, String tooltip) {
  return tester
      .widgetList<IconButton>(find.byType(IconButton))
      .singleWhere((IconButton button) => button.tooltip == tooltip);
}

class _CameraWidgetRepository implements LemonAidRepository {
  @override
  Future<SupplementAnalysisPreview> analyzeSupplementImage(
    String imagePath, {
    String ocrProvider = 'configured',
  }) {
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
