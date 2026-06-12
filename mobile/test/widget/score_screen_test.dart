import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:lemon_aid_mobile/app_controller.dart';
import 'package:lemon_aid_mobile/core/api/api_client.dart';
import 'package:lemon_aid_mobile/features/ai_coaching/ai_coaching_repository.dart';
import 'package:lemon_aid_mobile/features/consent/consent_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/dashboard_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/home_models.dart';
import 'package:lemon_aid_mobile/features/supplements/comprehensive_analysis_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';
import 'package:lemon_aid_mobile/screens/score_screen.dart';

class _FakeClient extends http.BaseClient {
  _FakeClient(this.handler);

  final Future<http.StreamedResponse> Function(http.Request request) handler;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    return handler(request as http.Request);
  }
}

http.StreamedResponse _jsonResponse(Map<String, dynamic> body, int status) {
  return http.StreamedResponse(
    Stream<List<int>>.value(utf8.encode(jsonEncode(body))),
    status,
    headers: const <String, String>{'content-type': 'application/json'},
  );
}

Map<String, dynamic> _coachingResponse() {
  return <String, dynamic>{
    'status': 'ok',
    'approval_status': 'not_required',
    'requires_user_approval': false,
    'message': '오늘 단백질이 조금 부족했어요.',
    'findings': <Map<String, dynamic>>[],
    'recommendations': <Map<String, dynamic>>[
      <String, dynamic>{
        'category': 'meal',
        'title': '저녁에 단백질 반찬 추가하기',
        'rationale': '오늘 단백질 섭취가 적었어요.',
        'priority': 1,
      },
    ],
    'actions': <Map<String, dynamic>>[],
    'safety_warnings': <String>[],
  };
}

AiCoachingRepository _coachingRepository({
  Future<http.StreamedResponse> Function(http.Request request)? handler,
}) {
  return AiCoachingRepository(
    apiClient: ApiClient(
      baseUrl: 'https://api.example.com/api/v1',
      httpClient: _FakeClient(
        handler ??
            (http.Request request) async =>
                _jsonResponse(_coachingResponse(), 200),
      ),
    ),
  );
}

Future<AppController> _readyController() async {
  final AppController controller = AppController(
    repository: _ScoreRepository(scoreReady: true),
  );
  await controller.bootstrap();
  return controller;
}

Future<AppController> _notReadyController() async {
  final AppController controller = AppController(
    repository: _ScoreRepository(scoreReady: false),
  );
  await controller.bootstrap();
  return controller;
}

Future<void> _pump(
  WidgetTester tester, {
  required AppController controller,
  required AiCoachingRepository coaching,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      home: ScoreScreen(controller: controller, coachingRepository: coaching),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('ready score renders ring, grade chip and lemon bot CTA', (
    WidgetTester tester,
  ) async {
    final AppController controller = await _readyController();
    await _pump(
      tester,
      controller: controller,
      coaching: _coachingRepository(),
    );

    expect(find.text('오늘의 분석'), findsOneWidget);
    expect(find.text('오늘의 종합 분석'), findsOneWidget);
    expect(find.text('78'), findsOneWidget);
    expect(find.text('좋아요'), findsOneWidget);
    expect(find.text('오늘 활동량이 좋아요.'), findsOneWidget);
    expect(find.text('레몬봇에게 물어보기'), findsOneWidget);
    // 잠금 추이 placeholder.
    expect(find.text('기록이 쌓이면 추이를 보여드려요'), findsOneWidget);
  });

  testWidgets('not_ready score shows record guidance and 촬영하기 CTA', (
    WidgetTester tester,
  ) async {
    final AppController controller = await _notReadyController();
    await _pump(
      tester,
      controller: controller,
      coaching: _coachingRepository(),
    );

    expect(find.text('기록을 추가하면 점수를 보여드려요.'), findsOneWidget);
    expect(find.text('촬영하기'), findsOneWidget);
    expect(find.text('좋아요'), findsNothing);
  });

  testWidgets('renders the daily-coaching checklist items', (
    WidgetTester tester,
  ) async {
    final AppController controller = await _readyController();
    await _pump(
      tester,
      controller: controller,
      coaching: _coachingRepository(),
    );

    expect(find.text('오늘 챙기면 좋은 1가지'), findsOneWidget);
    expect(find.text('저녁에 단백질 반찬 추가하기'), findsOneWidget);
  });

  testWidgets('checklist failure shows a retry affordance', (
    WidgetTester tester,
  ) async {
    final AppController controller = await _readyController();
    await _pump(
      tester,
      controller: controller,
      coaching: _coachingRepository(
        handler: (http.Request request) async =>
            _jsonResponse(<String, dynamic>{'detail': 'boom'}, 500),
      ),
    );

    expect(find.text('실천 리스트를 불러오지 못했어요'), findsOneWidget);
    expect(find.text('다시 시도'), findsOneWidget);
    // 화면 전체는 점수 카드를 유지한다.
    expect(find.text('오늘의 종합 분석'), findsOneWidget);
    expect(find.text('78'), findsOneWidget);
  });
}

class _ScoreRepository implements LemonAidRepository {
  _ScoreRepository({required this.scoreReady});

  final bool scoreReady;

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
      asOf: DateTime.utc(2026, 6, 1),
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
      healthScore: scoreReady
          ? const DashboardHealthScore(
              status: HealthScoreStatus.ready,
              score: 78,
              labelText: '좋아요',
              message: '오늘 활동량이 좋아요.',
            )
          : const DashboardHealthScore(status: HealthScoreStatus.notReady),
    );
  }

  @override
  Future<HomeMealsResult> fetchMeals({
    DateTime? from,
    DateTime? to,
    int limit = 50,
    int offset = 0,
  }) async {
    return HomeMealsResult.empty;
  }

  @override
  Future<HomeSupplementsResult> fetchSupplements({
    int limit = 50,
    int offset = 0,
  }) async {
    return HomeSupplementsResult.empty;
  }

  @override
  Future<SupplementImpactPreviewResponse>
  fetchLatestSupplementRecommendation() {
    throw UnimplementedError();
  }

  ConsentStatus _consent(String consentType) {
    return ConsentStatus(
      consentType: consentType,
      policyVersion: 'test',
      title: consentType,
      required: true,
      granted: true,
      occurredAt: DateTime.utc(2026, 6, 1),
      revokedAt: null,
    );
  }

  @override
  Future<SupplementAnalysisPreview> analyzeSupplementImage(
    String imagePath, {
    String ocrProvider = 'configured',
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
  Future<MealImageAnalysisPreview> analyzeMealImage(
    String imagePath, {
    String mealType = 'unknown',
  }) {
    throw UnimplementedError();
  }

  @override
  Future<MealRecordResponse> confirmMealImagePreview(
    String mealId,
    MealConfirmationRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<SupplementAnalysisSession> createSupplementAnalysisSession() {
    throw UnimplementedError();
  }

  @override
  Future<SupplementMultiImageAnalysisPreview> finalizeSupplementAnalysisSession(
    String analysisGroupId,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<ConsentAction> grantConsent(String consentType) {
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
  Future<ComprehensiveDietAnalysis> analyzeComprehensive({
    required List<Map<String, Object?>> ingredients,
    Map<String, dynamic>? userProfile,
    String persona = 'B',
  }) async {
    return ComprehensiveDietAnalysis.empty;
  }

  @override
  void close() {}

  @override
  Future<HomeMedicationsResult> fetchMedications() async {
    return HomeMedicationsResult.empty;
  }

  @override
  Future<HomeMedication> createMedication(MedicationCreateRequest request) {
    throw UnimplementedError();
  }

  @override
  Future<HomeMedication> deactivateMedication(String medicationId) {
    throw UnimplementedError();
  }

  @override
  Future<HomeMedication> reactivateMedication(String medicationId) {
    throw UnimplementedError();
  }
}
