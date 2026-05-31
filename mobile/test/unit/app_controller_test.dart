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

  test('explainSupplementAnalysis uses current preview id', () async {
    final _AutoInsightRepository repository = _AutoInsightRepository();
    final AppController controller = AppController(repository: repository);

    await controller.analyzeImage('/tmp/supplement-label.png');
    await controller.explainSupplementAnalysis(useLocalLlm: true);

    expect(repository.analysisExplainCalls, 1);
    expect(
      repository.lastAnalysisExplainId,
      '00000000-0000-0000-0000-000000000001',
    );
    expect(repository.lastAnalysisExplainUsedLocalLlm, isTrue);
    expect(controller.supplementExplanation?.llmUsed, isTrue);
    expect(controller.notice, 'Analysis explanation is ready.');
  });

  test('analyzeMealImage stores food detection preview', () async {
    final _AutoInsightRepository repository = _AutoInsightRepository();
    final AppController controller = AppController(repository: repository);

    await controller.analyzeMealImage('/tmp/meal.png', mealType: 'lunch');

    expect(repository.lastMealImagePath, '/tmp/meal.png');
    expect(repository.lastMealType, 'lunch');
    expect(
      controller.mealAnalysisPreview?.foodCandidates.single.displayName,
      '비빔밥',
    );
    expect(controller.analysisPreview, isNull);
    expect(controller.notice, 'Meal image preview is ready for review.');
  });

  test('startSupplementImageAnalysis completes in background', () async {
    final _AutoInsightRepository repository = _AutoInsightRepository(
      analysisDelay: const Duration(milliseconds: 20),
    );
    final AppController controller = AppController(repository: repository);

    await controller.startSupplementImageAnalysis('/tmp/supplement-label.png');

    expect(controller.analysisJob.isRunning, isTrue);
    expect(controller.analysisPreview, isNull);

    await Future<void>.delayed(const Duration(milliseconds: 40));

    expect(controller.analysisJob.phase, AnalysisJobPhase.completed);
    expect(controller.hasUnreadAnalysisCompletion, isTrue);
    expect(
      controller.completedAnalysisRoute,
      '/shell/home/analysis-result?mode=supplement',
    );
    expect(controller.notice, '분석이 완료 되었어요.');
    expect(controller.analysisPreview?.analysisId, isNotEmpty);
    expect(
      repository.ocrProviders,
      containsAll(<String>[
        'configured',
        'paddleocr',
        'clova',
        'google_vision',
      ]),
    );

    controller.markAnalysisCompletionRead();

    expect(controller.hasUnreadAnalysisCompletion, isFalse);
  });

  test('confirmMealImagePreview stores user-confirmed meal', () async {
    final _AutoInsightRepository repository = _AutoInsightRepository();
    final AppController controller = AppController(repository: repository);

    await controller.analyzeMealImage('/tmp/meal.png', mealType: 'lunch');
    await controller.confirmMealImagePreview(
      const MealConfirmationRequest(
        analysisId: '00000000-0000-0000-0000-000000000101',
        mealType: 'lunch',
        foodItems: <MealFoodItemInput>[
          MealFoodItemInput(
            displayName: '비빔밥',
            kcal: 520,
            confidence: 0.88,
            source: 'vision',
          ),
        ],
      ),
    );

    expect(repository.confirmMealCalls, 1);
    expect(
      repository.lastConfirmedMealId,
      '00000000-0000-0000-0000-000000000201',
    );
    expect(
      repository.lastMealConfirmationRequest?.foodItems.single.displayName,
      '비빔밥',
    );
    expect(controller.mealAnalysisPreview, isNull);
    expect(controller.lastRegisteredMeal?.foodItems.single.displayName, '비빔밥');
    expect(controller.notice, 'Meal record saved and dashboard refreshed.');
  });

  test('registerSupplement blocks when health consent is missing', () async {
    final _AutoInsightRepository repository = _AutoInsightRepository()
      ..consents = <String, bool>{
        AppController.ocrConsent: true,
        AppController.healthConsent: false,
      };
    final AppController controller = AppController(repository: repository);
    await controller.bootstrap();

    await controller.registerSupplement(_registrationRequest());

    expect(controller.consentRequired, isTrue);
    expect(controller.apiError?.statusCode, 403);
    expect(repository.registerCalls, 0);
    expect(controller.lastRegisteredSupplement, isNull);
  });

  test('registerSupplement proceeds after health consent is present', () async {
    final _AutoInsightRepository repository = _AutoInsightRepository()
      ..consents = <String, bool>{
        AppController.ocrConsent: true,
        AppController.healthConsent: true,
      };
    final AppController controller = AppController(repository: repository);
    await controller.bootstrap();

    await controller.registerSupplement(_registrationRequest());

    expect(controller.consentRequired, isFalse);
    expect(repository.registerCalls, 1);
    expect(controller.lastRegisteredSupplement?.displayName, 'Vitamin D');
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
  _AutoInsightRepository({
    this.failExplanation = false,
    this.analysisDelay = Duration.zero,
  });

  final bool failExplanation;
  final Duration analysisDelay;
  Map<String, bool> consents = const <String, bool>{};
  int registerCalls = 0;
  int impactCalls = 0;
  int explainCalls = 0;
  int analysisExplainCalls = 0;
  int finalizeCalls = 0;
  int confirmMealCalls = 0;
  bool? lastExplainUsedLocalLlm;
  bool? lastAnalysisExplainUsedLocalLlm;
  String? lastAnalysisExplainId;
  String? lastFinalizeGroupId;
  String? lastMealImagePath;
  String? lastMealType;
  String? lastConfirmedMealId;
  MealConfirmationRequest? lastMealConfirmationRequest;
  final List<String> ocrProviders = <String>[];

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
  }) async {
    if (analysisDelay > Duration.zero) {
      await Future<void>.delayed(analysisDelay);
    }
    ocrProviders.add(ocrProvider);
    return SupplementAnalysisPreview.fromJson(
      _multiPreviewJson['merged_preview']! as Map<String, Object?>,
    );
  }

  @override
  Future<MealImageAnalysisPreview> analyzeMealImage(
    String imagePath, {
    String mealType = 'unknown',
  }) async {
    lastMealImagePath = imagePath;
    lastMealType = mealType;
    return MealImageAnalysisPreview.fromJson(_mealPreviewJson);
  }

  @override
  Future<MealRecordResponse> confirmMealImagePreview(
    String mealId,
    MealConfirmationRequest request,
  ) async {
    confirmMealCalls += 1;
    lastConfirmedMealId = mealId;
    lastMealConfirmationRequest = request;
    return MealRecordResponse.fromJson(_mealRecordJson);
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
  Future<ConsentState> fetchConsents() async {
    return ConsentState(
      consents: <ConsentStatus>[
        for (final MapEntry<String, bool> entry in consents.entries)
          ConsentStatus(
            consentType: entry.key,
            policyVersion: 'v1',
            title: entry.key,
            required: true,
            granted: entry.value,
            occurredAt: null,
            revokedAt: null,
          ),
      ],
    );
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

  @override
  Future<SupplementRecommendationExplainResponse> explainSupplementAnalysis(
    String analysisId, {
    bool useLocalLlm = false,
  }) async {
    analysisExplainCalls += 1;
    lastAnalysisExplainId = analysisId;
    lastAnalysisExplainUsedLocalLlm = useLocalLlm;
    return const SupplementRecommendationExplainResponse(
      safeUserMessage: 'Analysis explanation ready.',
      explanationBullets: <String>['Review extracted label fields.'],
      clinicalDisclaimer: 'Reference information only.',
      blockedTermsDetected: <String>[],
      llmUsed: true,
      warnings: <String>[],
    );
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

final Map<String, Object?> _mealPreviewJson = <String, Object?>{
  'analysis_id': '00000000-0000-0000-0000-000000000101',
  'meal_id': '00000000-0000-0000-0000-000000000201',
  'status': 'requires_confirmation',
  'meal_type': 'lunch',
  'eaten_at': '2026-05-28T03:00:00Z',
  'food_candidates': <Object?>[
    <String, Object?>{
      'display_name': '비빔밥',
      'portion_amount': null,
      'portion_unit': null,
      'kcal': null,
      'carb_g': null,
      'protein_g': null,
      'fat_g': null,
      'sodium_mg': null,
      'confidence': 0.88,
      'source': 'vision',
    },
  ],
  'nutrition_estimate_summary': <String, Object?>{
    'status': 'detected_review_required',
    'items': <Object?>[],
    'totals': <String, Object?>{},
    'detector_used': true,
  },
  'warning_codes': <String>['food_detection_review_required'],
  'pipeline_metadata': <String, Object?>{
    'intake_completed': true,
    'detector_model': 'food_yolo_local:best.pt',
    'classifier_model': null,
    'detector_used': true,
    'classifier_used': false,
    'raw_image_stored': false,
    'raw_provider_payload_stored': false,
    'requires_manual_entry': false,
  },
  'algorithm_version': 'food-image-preview-v1.0.0',
  'created_at': '2026-05-28T03:00:01Z',
};

final Map<String, Object?> _mealRecordJson = <String, Object?>{
  'id': '00000000-0000-0000-0000-000000000201',
  'status': 'confirmed',
  'meal_type': 'lunch',
  'eaten_at': '2026-05-28T03:00:00Z',
  'food_items': <Object?>[
    <String, Object?>{
      'id': '00000000-0000-0000-0000-000000000301',
      'display_name': '비빔밥',
      'portion_amount': null,
      'portion_unit': null,
      'kcal': 520,
      'carb_g': null,
      'protein_g': null,
      'fat_g': null,
      'sodium_mg': null,
      'confidence': 0.88,
      'source': 'vision',
    },
  ],
  'nutrition_summary': <String, Object?>{
    'status': 'user_confirmed',
    'items_count': 1,
    'totals': <String, Object?>{'kcal': 520},
  },
  'confirmed_at': '2026-05-28T03:05:00Z',
  'created_at': '2026-05-28T03:00:01Z',
};
