import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/app_controller.dart';
import 'package:lemon_aid_mobile/features/consent/consent_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/dashboard_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';
import 'package:lemon_aid_mobile/screens/analysis_result_screen.dart';

void main() {
  testWidgets('renders source-style analysis result with real pipeline data', (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _ReviewRepository(),
    );
    await controller.analyzeImage(
      '/tmp/supplement-label.jpg',
      ocrProvider: 'paddleocr',
    );

    await tester.pumpWidget(
      MaterialApp(home: AnalysisResultScreen(controller: controller)),
    );
    await tester.pumpAndSettle();

    expect(find.text('영양제 분석'), findsOneWidget);
    expect(find.text('성분 후보 1개를 찾았어요'), findsOneWidget);
    expect(find.text('OCR'), findsOneWidget);
    expect(find.text('paddleocr_local'), findsOneWidget);
    expect(find.text('YOLO ROI'), findsOneWidget);
    expect(find.text('on (1)'), findsOneWidget);
    expect(find.text('Ollama'), findsOneWidget);
    expect(find.text('parser on'), findsOneWidget);
    await _scrollResultDetails(tester);
    expect(find.text('확인 후 수정'), findsOneWidget);
    expect(find.text('Analysis progress'), findsNothing);
    expect(find.textContaining('OCR Auto'), findsNothing);
  });

  testWidgets(
    'registers user-corrected ingredient when OCR candidates are empty',
    (WidgetTester tester) async {
      final _ReviewRepository repository = _ReviewRepository(
        preview: _emptyCandidatePreview(),
      );
      final AppController controller = AppController(repository: repository);
      await controller.analyzeImage(
        '/tmp/supplement-label.jpg',
        ocrProvider: 'paddleocr',
      );

      await tester.pumpWidget(
        MaterialApp(home: AnalysisResultScreen(controller: controller)),
      );
      await tester.pumpAndSettle();

      expect(find.text('성분 직접 입력'), findsOneWidget);
      await _scrollResultDetails(tester);
      expect(find.text('확인 후 수정'), findsOneWidget);
      await tester.enterText(find.byType(TextField).at(0), '수정 비타민 D');
      await tester.enterText(find.byType(TextField).at(1), 'Lemon Lab');
      await tester.enterText(find.byType(TextField).at(2), 'Vitamin D3');
      await tester.enterText(find.byType(TextField).at(3), '25');
      await tester.enterText(find.byType(TextField).at(4), 'mcg');

      await tester.tap(find.text('성분 직접 입력'));
      await tester.pumpAndSettle();

      expect(repository.registeredRequest?.displayName, '수정 비타민 D');
      expect(repository.registeredRequest?.manufacturer, 'Lemon Lab');
      expect(
        repository.registeredRequest?.ingredients.single.displayName,
        'Vitamin D3',
      );
      expect(repository.registeredRequest?.ingredients.single.amount, 25);
      expect(repository.registeredRequest?.ingredients.single.unit, 'mcg');
      expect(
        repository.registeredRequest?.ingredients.single.source,
        'user_confirmed',
      );
      expect(repository.explainUsedLocalLlm, isTrue);
      expect(controller.lastRegisteredSupplement?.displayName, '수정 비타민 D');
    },
  );

  testWidgets('renders meal analysis with food YOLO endpoint data', (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _ReviewRepository(),
    );
    await controller.analyzeMealImage('/tmp/meal.png', mealType: 'lunch');

    await tester.pumpWidget(
      MaterialApp(
        home: AnalysisResultScreen(mode: 'meal', controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('식단 분석'), findsOneWidget);
    expect(find.text('음식 후보 1개를 찾았어요'), findsOneWidget);
    expect(find.text('음식 후보'), findsOneWidget);
    expect(find.text('비빔밥'), findsOneWidget);
    expect(find.text('Food YOLO'), findsOneWidget);
    expect(find.text('on'), findsOneWidget);
    expect(find.textContaining('food_yolo_local:best.pt'), findsOneWidget);
    expect(find.textContaining('endpoint 연결 전'), findsNothing);
  });

  testWidgets('confirms meal analysis into user-reviewed meal record', (
    WidgetTester tester,
  ) async {
    final _ReviewRepository repository = _ReviewRepository();
    final AppController controller = AppController(repository: repository);
    await controller.analyzeMealImage('/tmp/meal.png', mealType: 'lunch');

    await tester.pumpWidget(
      MaterialApp(
        home: AnalysisResultScreen(mode: 'meal', controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    await _scrollResultDetails(tester);
    expect(find.text('식단 확인'), findsOneWidget);
    await tester.enterText(find.byType(TextField).first, '수정 비빔밥');
    await tester.tap(find.text('확인 후 식단 저장'));
    await tester.pumpAndSettle();

    expect(repository.confirmedMealId, '00000000-0000-0000-0000-000000000201');
    expect(
      repository.confirmedMealRequest?.foodItems.single.displayName,
      '수정 비빔밥',
    );
    expect(
      controller.lastRegisteredMeal?.foodItems.single.displayName,
      '수정 비빔밥',
    );
  });
}

Future<void> _scrollResultDetails(WidgetTester tester) async {
  await tester.drag(find.byType(ListView), const Offset(0, -700));
  await tester.pumpAndSettle();
}

class _ReviewRepository implements LemonAidRepository {
  _ReviewRepository({SupplementAnalysisPreview? preview})
    : _previewOverride = preview;

  final SupplementAnalysisPreview? _previewOverride;
  UserSupplementCreate? registeredRequest;
  String? confirmedMealId;
  MealConfirmationRequest? confirmedMealRequest;
  bool explainUsedLocalLlm = false;

  @override
  Future<SupplementAnalysisPreview> analyzeSupplementImage(
    String imagePath, {
    String ocrProvider = 'configured',
  }) async {
    return _previewOverride ?? _preview();
  }

  @override
  Future<MealImageAnalysisPreview> analyzeMealImage(
    String imagePath, {
    String mealType = 'unknown',
  }) async {
    return MealImageAnalysisPreview.fromJson(_mealPreviewJson);
  }

  @override
  Future<MealRecordResponse> confirmMealImagePreview(
    String mealId,
    MealConfirmationRequest request,
  ) {
    confirmedMealId = mealId;
    confirmedMealRequest = request;
    return Future<MealRecordResponse>.value(
      _mealRecordFromRequest(mealId, request),
    );
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
  Future<ConsentState> fetchConsents() {
    throw UnimplementedError();
  }

  @override
  Future<DashboardSummary> fetchDashboardSummary({int days = 30}) {
    return Future<DashboardSummary>.value(_dashboardSummary());
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
    registeredRequest = request;
    return Future<UserSupplementResponse>.value(
      UserSupplementResponse(
        id: 'supplement-1',
        displayName: request.displayName,
        manufacturer: request.manufacturer,
      ),
    );
  }

  @override
  Future<SupplementImpactPreviewResponse> previewSupplementImpact(
    SupplementImpactPreviewRequest request,
  ) {
    return Future<SupplementImpactPreviewResponse>.value(_impactPreview());
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
    explainUsedLocalLlm = useLocalLlm;
    return Future<SupplementRecommendationExplainResponse>.value(
      const SupplementRecommendationExplainResponse(
        safeUserMessage: 'Local explanation ready.',
        explanationBullets: <String>['라벨 확인 값을 기준으로 설명합니다.'],
        clinicalDisclaimer: 'Reference information only.',
        blockedTermsDetected: <String>[],
        llmUsed: true,
        warnings: <String>[],
      ),
    );
  }

  @override
  Future<SupplementRecommendationExplainResponse> explainSupplementAnalysis(
    String analysisId, {
    bool useLocalLlm = false,
  }) {
    return Future<SupplementRecommendationExplainResponse>.value(
      const SupplementRecommendationExplainResponse(
        safeUserMessage: 'Analysis explanation ready.',
        explanationBullets: <String>['성분 후보를 등록 전에 확인합니다.'],
        clinicalDisclaimer: 'Reference information only.',
        blockedTermsDetected: <String>[],
        llmUsed: true,
        warnings: <String>[],
      ),
    );
  }

  SupplementAnalysisPreview _preview() {
    return SupplementAnalysisPreview(
      analysisId: 'analysis-1',
      status: 'requires_confirmation',
      parsedProduct: const SupplementParsedProduct(
        productName: '비타민 D',
        manufacturer: 'Lemon Lab',
        servingSize: 'capsule',
        dailyServings: 1,
      ),
      ingredientCandidates: const <SupplementIngredientCandidate>[
        SupplementIngredientCandidate(
          displayName: 'Vitamin D',
          nutrientCode: 'vitamin_d',
          amount: 25,
          unit: 'mcg',
          confidence: 0.92,
          source: 'ocr_llm_preview',
        ),
      ],
      layoutAvailable: true,
      layoutFallbackReason: null,
      labelSections: const <SupplementPreviewLabelSection>[
        SupplementPreviewLabelSection(
          sectionId: 'section-1',
          sectionType: 'supplement_facts',
          headingText: 'Supplement Facts',
          textBundle: 'Vitamin D 25 mcg',
          confidence: 0.91,
          requiresReview: false,
          evidenceRefs: <String>['span-1'],
        ),
      ],
      intakeMethod: SupplementPreviewIntakeMethod.empty,
      precautions: const <SupplementPreviewPrecaution>[],
      functionalClaims: const <SupplementPreviewFunctionalClaim>[],
      evidenceSpans: const <SupplementPreviewEvidenceSpan>[
        SupplementPreviewEvidenceSpan(
          spanId: 'span-1',
          sourceType: 'ocr',
          sectionType: 'supplement_facts',
          textExcerpt: 'Vitamin D 25 mcg',
          pageIndex: null,
          cellRef: null,
          confidence: 0.91,
        ),
      ],
      imageQualityReport: null,
      analysisScope: 'supplement_label',
      actionRequired: 'none',
      detectedProductRegions: const <SupplementDetectedProductRegion>[],
      selectedRegionId: null,
      missingRequiredSections: const <String>[],
      imageRole: 'supplement_facts',
      multiImageGroupId: null,
      sourceType: 'uploaded_image',
      identityConflict: null,
      pipelineMetadata: const SupplementImagePipelineMetadata(
        intakeCompleted: true,
        imageCount: 1,
        imageRole: 'supplement_facts',
        visionRoiUsed: true,
        ocrProvider: 'paddleocr_local',
        ocrTextPresent: true,
        ocrConfidenceBucket: 'high',
        roiCount: 1,
        sectionCount: 1,
        llmParserUsed: true,
        parserContractVersion: 'test-parser-v3',
        missingRequiredSections: <String>[],
        rawImageStored: false,
        rawOcrTextStored: false,
      ),
      lowConfidenceFields: const <String>[],
      warnings: const <String>[],
      algorithmVersion: 'test',
      sourceManifestVersion: null,
      expiresAt: DateTime.utc(2026, 5, 26),
    );
  }
}

SupplementAnalysisPreview _emptyCandidatePreview() {
  return SupplementAnalysisPreview(
    analysisId: 'analysis-empty',
    status: 'requires_confirmation',
    parsedProduct: const SupplementParsedProduct(
      productName: null,
      manufacturer: null,
      servingSize: null,
      dailyServings: null,
    ),
    ingredientCandidates: const <SupplementIngredientCandidate>[],
    layoutAvailable: true,
    layoutFallbackReason: null,
    labelSections: const <SupplementPreviewLabelSection>[],
    intakeMethod: SupplementPreviewIntakeMethod.empty,
    precautions: const <SupplementPreviewPrecaution>[],
    functionalClaims: const <SupplementPreviewFunctionalClaim>[],
    evidenceSpans: const <SupplementPreviewEvidenceSpan>[
      SupplementPreviewEvidenceSpan(
        spanId: 'span-empty',
        sourceType: 'ocr',
        sectionType: 'supplement_facts',
        textExcerpt: '라벨 일부만 확인됨',
        pageIndex: null,
        cellRef: null,
        confidence: 0.42,
      ),
    ],
    imageQualityReport: null,
    analysisScope: 'supplement_label',
    actionRequired: 'review_required',
    detectedProductRegions: const <SupplementDetectedProductRegion>[],
    selectedRegionId: null,
    missingRequiredSections: const <String>['supplement_facts'],
    imageRole: 'unknown',
    multiImageGroupId: null,
    sourceType: 'uploaded_image',
    identityConflict: null,
    pipelineMetadata: const SupplementImagePipelineMetadata(
      intakeCompleted: true,
      imageCount: 1,
      imageRole: 'unknown',
      visionRoiUsed: false,
      ocrProvider: 'paddleocr_local',
      ocrTextPresent: true,
      ocrConfidenceBucket: 'low',
      roiCount: 0,
      sectionCount: 0,
      llmParserUsed: true,
      parserContractVersion: 'test-parser-v3',
      missingRequiredSections: <String>['supplement_facts'],
      rawImageStored: false,
      rawOcrTextStored: false,
    ),
    lowConfidenceFields: const <String>['ingredient_candidates'],
    warnings: const <String>['Automatic parsing needs review.'],
    algorithmVersion: 'test',
    sourceManifestVersion: null,
    expiresAt: DateTime.utc(2026, 5, 26),
  );
}

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

MealRecordResponse _mealRecordFromRequest(
  String mealId,
  MealConfirmationRequest request,
) {
  final MealFoodItemInput item = request.foodItems.first;
  return MealRecordResponse(
    id: mealId,
    status: 'confirmed',
    mealType: request.mealType ?? 'unknown',
    eatenAt: request.eatenAt ?? DateTime.utc(2026, 5, 28, 3),
    foodItems: <MealFoodItemResponse>[
      MealFoodItemResponse(
        id: '00000000-0000-0000-0000-000000000301',
        displayName: item.displayName,
        portionAmount: item.portionAmount,
        portionUnit: item.portionUnit,
        kcal: item.kcal,
        carbG: item.carbG,
        proteinG: item.proteinG,
        fatG: item.fatG,
        sodiumMg: item.sodiumMg,
        confidence: item.confidence,
        source: item.source,
      ),
    ],
    nutritionSummary: const <String, Object?>{'status': 'user_confirmed'},
    confirmedAt: DateTime.utc(2026, 5, 28, 3, 5),
    createdAt: DateTime.utc(2026, 5, 28, 3),
  );
}

DashboardSummary _dashboardSummary() {
  return DashboardSummary(
    asOf: DateTime.utc(2026, 5, 28),
    nutrition: const DashboardNutritionSummary(
      dataStatus: 'partial',
      lowCount: 0,
      highCount: 0,
      datasetVersion: 'test',
    ),
    activity: const DashboardActivitySummary(
      dataStatus: 'partial',
      latestSteps: null,
      latestActivityScore: null,
    ),
    weight: const DashboardWeightSummary(
      dataStatus: 'partial',
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
