import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/app.dart';
import 'package:lemon_aid_mobile/app_controller.dart';
import 'package:lemon_aid_mobile/features/consent/consent_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/dashboard_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';

void main() {
  testWidgets('renders source dashboard shell with backend session wiring', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(LemonAidApp(repository: _FakeRepository()));
    await tester.pump(const Duration(seconds: 6));
    await tester.pumpAndSettle();

    expect(find.text('레몬'), findsOneWidget);
    expect(find.text('에이드'), findsOneWidget);
    expect(find.text('오늘의 건강 점수'), findsOneWidget);
    expect(find.text('오늘의 분석'), findsOneWidget);
    expect(find.text('홈'), findsOneWidget);
    expect(find.text('챗'), findsOneWidget);
    expect(find.text('점수'), findsOneWidget);
    expect(find.text('설정'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.add_rounded).last);
    await tester.pumpAndSettle();
    expect(find.text('영양제 촬영'), findsOneWidget);
    expect(find.text('식단 촬영'), findsOneWidget);
    await tester.tapAt(const Offset(20, 20));
    await tester.pumpAndSettle();

    await tester.drag(find.byType(Scrollable).first, const Offset(0, -500));
    await tester.pumpAndSettle();
    expect(find.text('최근 분석'), findsOneWidget);
  });
}

class _FakeRepository implements LemonAidRepository {
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
  Future<DashboardSummary> fetchDashboardSummary({int days = 30}) async {
    return DashboardSummary(
      asOf: DateTime.utc(2026, 5, 15),
      nutrition: const DashboardNutritionSummary(
        dataStatus: 'ready',
        lowCount: 1,
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
        registeredCount: 2,
        requiresReviewCount: 0,
      ),
      disclaimers: const <String>['Review OCR output before saving.'],
      algorithmVersion: 'test',
    );
  }

  @override
  Future<ConsentAction> grantConsent(String consentType) async {
    return ConsentAction(
      consentType: consentType,
      policyVersion: 'test',
      granted: true,
      occurredAt: DateTime.utc(2026, 5, 15),
    );
  }

  @override
  Future<SupplementAnalysisPreview> parseOcrText({
    required String analysisId,
    required SupplementOCRTextParseRequest request,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<UserSupplementResponse> registerSupplement(
    UserSupplementCreate request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<SupplementImpactPreviewResponse> previewSupplementImpact(
    SupplementImpactPreviewRequest request,
  ) {
    throw UnimplementedError();
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

  ConsentStatus _consent(String consentType) {
    return ConsentStatus(
      consentType: consentType,
      policyVersion: 'test',
      title: consentType,
      required: true,
      granted: true,
      occurredAt: DateTime.utc(2026, 5, 15),
      revokedAt: null,
    );
  }
}
