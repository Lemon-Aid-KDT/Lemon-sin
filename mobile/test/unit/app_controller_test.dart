import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/app_controller.dart';
import 'package:lemon_aid_mobile/core/api/api_error.dart';
import 'package:lemon_aid_mobile/features/consent/consent_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/dashboard_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';

void main() {
  test(
    'registration can automatically refresh impact and local explanation',
    () async {
      final _AutoInsightRepository repository = _AutoInsightRepository();
      final AppController controller = AppController(repository: repository);

      await controller.registerSupplement(
        _registrationRequest(),
        refreshImpact: true,
        explainWithLocalLlm: true,
      );

      expect(repository.registerCalls, 1);
      expect(repository.impactCalls, 1);
      expect(repository.explainCalls, 1);
      expect(repository.lastExplainUsedLocalLlm, isTrue);
      expect(controller.lastRegisteredSupplement?.displayName, 'Vitamin D');
      expect(controller.analysisPreview, isNull);
      expect(controller.multiImageAnalysisPreview, isNull);
      expect(
        controller.supplementImpactPreview?.safeUserMessage,
        'Impact ready.',
      );
      expect(controller.supplementExplanation?.llmUsed, isTrue);
      expect(controller.apiError, isNull);
    },
  );

  test(
    'registration keeps saved supplement when post-registration explanation fails',
    () async {
      final _AutoInsightRepository repository = _AutoInsightRepository(
        failExplanation: true,
      );
      final AppController controller = AppController(repository: repository);

      await controller.registerSupplement(
        _registrationRequest(),
        refreshImpact: true,
        explainWithLocalLlm: true,
      );

      expect(controller.lastRegisteredSupplement?.displayName, 'Vitamin D');
      expect(
        controller.supplementImpactPreview?.safeUserMessage,
        'Impact ready.',
      );
      expect(controller.supplementExplanation, isNull);
      expect(controller.apiError?.message, 'explanation unavailable');
      expect(controller.notice, contains('explanation needs retry'));
    },
  );

  test('finalizeAnalysisSession stores merged preview for review', () async {
    final _AutoInsightRepository repository = _AutoInsightRepository();
    final AppController controller = AppController(repository: repository);

    await controller.finalizeAnalysisSession('multi-test');

    expect(repository.finalizeCalls, 1);
    expect(repository.lastFinalizeGroupId, 'multi-test');
    expect(controller.multiImageAnalysisPreview?.analysisGroupId, 'multi-test');
    expect(
      controller.analysisPreview?.analysisId,
      '00000000-0000-0000-0000-000000000001',
    );
    expect(
      controller.notice,
      'Supplement image batch was finalized for review.',
    );
    expect(controller.apiError, isNull);
  });
}

UserSupplementCreate _registrationRequest() {
  return const UserSupplementCreate(
    analysisId: 'analysis-1',
    displayName: 'Vitamin D',
    manufacturer: 'Lemon Lab',
    ingredients: <UserSupplementIngredientInput>[
      UserSupplementIngredientInput(
        displayName: 'Vitamin D',
        nutrientCode: 'vitamin_d',
        amount: 25,
        unit: 'mcg',
        confidence: 0.92,
        source: 'ocr_llm_preview',
      ),
    ],
    serving: SupplementServing(amount: 1, unit: 'capsule', dailyServings: 1),
    intakeSchedule: SupplementIntakeSchedule(
      frequency: 'daily',
      timeOfDay: <String>['morning'],
    ),
  );
}

class _AutoInsightRepository implements LemonAidRepository {
  _AutoInsightRepository({this.failExplanation = false});

  final bool failExplanation;
  int registerCalls = 0;
  int impactCalls = 0;
  int explainCalls = 0;
  int finalizeCalls = 0;
  bool? lastExplainUsedLocalLlm;
  String? lastFinalizeGroupId;

  @override
  Future<UserSupplementResponse> registerSupplement(
    UserSupplementCreate request,
  ) async {
    registerCalls += 1;
    return UserSupplementResponse(
      id: 'supplement-1',
      displayName: request.displayName,
      manufacturer: request.manufacturer,
    );
  }

  @override
  Future<DashboardSummary> fetchDashboardSummary({int days = 30}) async {
    return DashboardSummary(
      asOf: DateTime.utc(2026, 5, 28),
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
        registeredCount: 1,
        requiresReviewCount: 0,
      ),
      disclaimers: const <String>[],
      algorithmVersion: 'test',
    );
  }

  @override
  Future<SupplementImpactPreviewResponse> previewSupplementImpact(
    SupplementImpactPreviewRequest request,
  ) async {
    impactCalls += 1;
    return _impactPreview();
  }

  @override
  Future<SupplementRecommendationExplainResponse>
  explainSupplementRecommendation(
    SupplementImpactPreviewResponse preview, {
    bool useLocalLlm = false,
  }) async {
    explainCalls += 1;
    lastExplainUsedLocalLlm = useLocalLlm;
    if (failExplanation) {
      throw const ApiError(statusCode: 503, message: 'explanation unavailable');
    }
    return const SupplementRecommendationExplainResponse(
      safeUserMessage: 'Local explanation ready.',
      explanationBullets: <String>['Review duplicate supplement sources.'],
      clinicalDisclaimer: 'Reference information only.',
      blockedTermsDetected: <String>[],
      llmUsed: true,
      warnings: <String>[],
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
  Future<SupplementMultiImageAnalysisPreview> analyzeSupplementImages(
    List<SupplementImageUpload> images, {
    String ocrProvider = 'configured',
  }) {
    throw UnimplementedError();
  }

  @override
  Future<SupplementMultiImageAnalysisPreview> finalizeSupplementAnalysisSession(
    String analysisGroupId,
  ) async {
    finalizeCalls += 1;
    lastFinalizeGroupId = analysisGroupId;
    return SupplementMultiImageAnalysisPreview.fromJson(_multiPreviewJson);
  }

  @override
  void close() {}

  @override
  Future<ConsentState> fetchConsents() {
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
  Future<SupplementImpactPreviewResponse>
  fetchLatestSupplementRecommendation() {
    throw UnimplementedError();
  }
}

SupplementImpactPreviewResponse _impactPreview() {
  return const SupplementImpactPreviewResponse(
    calculationVersion: 'supplement-impact-v1.0.0',
    referenceVersion: '2025',
    sourceManifestVersion: null,
    dataStatus: 'partial',
    currentSupplementContributions: <SupplementContributionAggregate>[],
    deficiencySupportCandidates: <SupplementNutritionInsight>[],
    excessOrDuplicateRisks: <SupplementNutritionInsight>[],
    missingProfileFields: <String>[],
    safeUserMessage: 'Impact ready.',
    clinicalDisclaimer: 'Reference information only.',
    warnings: <String>[],
    requiresUserConfirmation: true,
  );
}

final Map<String, Object?> _multiPreviewJson = <String, Object?>{
  'analysis_group_id': 'multi-test',
  'image_count': 2,
  'previews': <Object?>[
    <String, Object?>{
      'analysis_id': '00000000-0000-0000-0000-000000000001',
      'status': 'requires_confirmation',
      'parsed_product': <String, Object?>{'product_name': 'Vitamin D'},
      'ingredient_candidates': <Object?>[],
      'algorithm_version': 'test',
      'source_manifest_version': null,
      'expires_at': '2026-05-28T00:00:00Z',
    },
  ],
  'merged_preview': <String, Object?>{
    'analysis_id': '00000000-0000-0000-0000-000000000001',
    'status': 'requires_confirmation',
    'parsed_product': <String, Object?>{'product_name': 'Vitamin D'},
    'ingredient_candidates': <Object?>[],
    'image_role': 'mixed',
    'multi_image_group_id': 'multi-test',
    'algorithm_version': 'test',
    'source_manifest_version': null,
    'expires_at': '2026-05-28T00:00:00Z',
  },
  'missing_required_sections': <String>[],
  'action_required': 'review_required',
  'pipeline_metadata': <String, Object?>{
    'intake_completed': true,
    'image_count': 2,
    'image_role': 'mixed',
    'raw_image_stored': false,
    'raw_ocr_text_stored': false,
  },
  'expires_at': '2026-05-28T00:00:00Z',
};
