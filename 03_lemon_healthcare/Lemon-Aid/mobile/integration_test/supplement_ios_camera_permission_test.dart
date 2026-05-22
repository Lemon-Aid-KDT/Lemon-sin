import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:integration_test/integration_test.dart';
import 'package:lemon_aid_mobile/app_controller.dart';
import 'package:lemon_aid_mobile/features/consent/consent_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/dashboard_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_flow_screen.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  const MethodChannel cameraPermissionChannel = MethodChannel(
    'com.lemonaid.mobile/camera_permission',
  );

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(cameraPermissionChannel, null);
  });

  testWidgets('iOS camera permission denial shows retry guidance', (
    WidgetTester tester,
  ) async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(cameraPermissionChannel, (
          MethodCall methodCall,
        ) async {
          expect(methodCall.method, 'requestCameraPermission');
          return 'denied';
        });

    final AppController controller = AppController(
      repository: _ConsentReadyRepository(),
    );
    await controller.bootstrap();

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SupplementFlowScreen(
            controller: controller,
            imagePicker: ImagePicker(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('촬영'));
    await tester.pumpAndSettle();

    expect(
      find.text('카메라 권한이 거부됐어요. 설정에서 카메라 접근을 허용하거나 갤러리 사진으로 다시 시도해주세요.'),
      findsOneWidget,
    );
  });
}

class _ConsentReadyRepository implements LemonAidRepository {
  @override
  Future<SupplementAnalysisPreview> analyzeSupplementImage(String imagePath) {
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
  Future<DashboardSummary> fetchDashboardSummary({int days = 30}) async {
    return DashboardSummary(
      asOf: DateTime.utc(2026, 5, 22),
      nutrition: const DashboardNutritionSummary(
        dataStatus: 'ready',
        lowCount: 0,
        highCount: 0,
        datasetVersion: 'integration-test',
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
      algorithmVersion: 'integration-test',
    );
  }

  @override
  Future<ConsentAction> grantConsent(String consentType) async {
    return ConsentAction(
      consentType: consentType,
      policyVersion: 'integration-test',
      granted: true,
      occurredAt: DateTime.utc(2026, 5, 22),
    );
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
  Future<SupplementImpactPreviewResponse>
  fetchLatestSupplementRecommendation() {
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
      policyVersion: 'integration-test',
      title: consentType,
      required: true,
      granted: true,
      occurredAt: DateTime.utc(2026, 5, 22),
      revokedAt: null,
    );
  }
}
