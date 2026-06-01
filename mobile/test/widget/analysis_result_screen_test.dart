import 'dart:async';

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
    expect(
      find.byKey(const ValueKey<String>('pipeline-led-ocr-success')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('pipeline-led-vision-success')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('pipeline-led-llm-success')),
      findsOneWidget,
    );
    expect(find.text('영양제명'), findsOneWidget);
    expect(find.text('상세 성분 및 함량'), findsOneWidget);
    expect(find.byType(Table), findsOneWidget);
    expect(find.text('성분명'), findsOneWidget);
    expect(find.text('함량'), findsOneWidget);
    expect(find.text('Vitamin D'), findsOneWidget);
    expect(find.text('25 mcg'), findsOneWidget);
    expect(
      tester
          .widgetList<Text>(find.text('Vitamin D'))
          .any(
            (Text widget) =>
                widget.style?.fontWeight == FontWeight.w900 &&
                widget.style?.fontSize == 16,
          ),
      isTrue,
    );
    expect(find.text('섭취 방법'), findsOneWidget);

    await tester.tap(
      find.byKey(const ValueKey<String>('supplement-candidate-summary')),
    );
    await tester.pumpAndSettle();

    expect(find.text('OCR 텍스트 전체'), findsOneWidget);
    expect(find.text('구역'), findsOneWidget);
    expect(find.text('Vitamin D 25 mcg'), findsOneWidget);
    await tester.tap(find.text('닫기'));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.text('섭취 시 주의사항'), 220);
    expect(find.text('섭취 시 주의사항'), findsOneWidget);
    expect(find.textContaining('하루 1회 1캡슐'), findsOneWidget);
    expect(find.textContaining('전문가와 상담'), findsOneWidget);
    expect(find.text('OCR'), findsNothing);
    expect(find.text('YOLO ROI'), findsNothing);
    expect(find.text('Ollama'), findsNothing);
    expect(find.text('주의사항이 보이게 한 장 더 촬영해주세요'), findsNothing);
    expect(find.text('Analysis progress'), findsNothing);
    expect(find.textContaining('OCR Auto'), findsNothing);
  });

  testWidgets('renders analyzing page while background analysis runs', (
    WidgetTester tester,
  ) async {
    final _PendingReviewRepository repository = _PendingReviewRepository();
    final AppController controller = AppController(repository: repository);
    addTearDown(() {
      repository.complete();
      controller.dispose();
    });

    await controller.startSupplementImageAnalysis('/tmp/supplement-label.jpg');

    await tester.pumpWidget(
      MaterialApp(home: AnalysisResultScreen(controller: controller)),
    );
    await tester.pump();

    expect(find.text('분석을 하고 있어요.'), findsOneWidget);
    expect(find.text('메인으로 이동'), findsOneWidget);
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
      expect(find.text('제품명이 보이게 한 장 더 촬영해주세요'), findsOneWidget);
      expect(find.text('성분표가 보이게 한 장 더 촬영해주세요'), findsOneWidget);
      expect(find.text('성분명과 함량을 확인할 수 없어요.'), findsOneWidget);

      await tester.tap(find.byTooltip('영양제명 수정'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField).at(0), '수정 비타민 D');
      await tester.enterText(find.byType(TextField).at(1), 'Lemon Lab');
      await tester.tap(find.text('저장'));
      await tester.pumpAndSettle();

      await tester.tap(find.byTooltip('상세 성분 및 함량 수정'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField).at(0), 'Vitamin D3');
      await tester.enterText(find.byType(TextField).at(1), '25');
      await tester.enterText(find.byType(TextField).at(2), 'mcg');
      await tester.tap(find.text('저장'));
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(find.byTooltip('섭취 시 주의사항 수정'), 220);
      await tester.drag(find.byType(ListView), const Offset(0, -260));
      await tester.pumpAndSettle();
      expect(find.text('해당 이미지에는 해당하는 내용이 없습니다'), findsWidgets);
      await tester.tap(find.byTooltip('섭취 시 주의사항 수정'));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byType(TextField).first,
        '임신 중이면 전문가와 상담하세요.',
      );
      await tester.tap(find.text('저장'));
      await tester.pumpAndSettle();

      expect(find.text('확인 후 저장'), findsOneWidget);
      await tester.tap(find.text('확인 후 저장'));
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
      expect(repository.registeredRequest?.evidenceRefs, <String>[
        'span-empty',
      ]);
      expect(repository.registeredRequest?.precautionSnapshot, <String>[
        '임신 중이면 전문가와 상담하세요.',
      ]);
      expect(repository.explainUsedLocalLlm, isTrue);
      expect(controller.lastRegisteredSupplement?.displayName, '수정 비타민 D');
      expect(controller.pendingChatExplanationDraft, isNotNull);
      expect(
        controller.pendingChatExplanationDraft?.assistantMessage,
        contains('성분과 함유량'),
      );
      expect(
        controller.pendingChatExplanationDraft?.assistantMessage,
        contains('Vitamin D3: 25 mcg'),
      );
    },
  );

  testWidgets('normalizes OCR provider source for supplement registration', (
    WidgetTester tester,
  ) async {
    final _ReviewRepository sourceRepository = _ReviewRepository();
    final _ReviewRepository repository = _ReviewRepository(
      preview: sourceRepository._preview(
        ingredientSource: 'clova_ocr',
        includeSecondIngredient: true,
      ),
    );
    final AppController controller = AppController(repository: repository);
    await controller.analyzeImage(
      '/tmp/supplement-label.jpg',
      ocrProvider: 'clova',
    );

    await tester.pumpWidget(
      MaterialApp(home: AnalysisResultScreen(controller: controller)),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('확인 후 저장'));
    await tester.pumpAndSettle();

    expect(
      repository.registeredRequest?.ingredients.first.source,
      'user_confirmed',
    );
    expect(repository.registeredRequest?.ingredients, hasLength(1));
    expect(
      repository.registeredRequest?.ingredients.single.displayName,
      'Vitamin D',
    );
    expect(repository.registeredRequest?.evidenceRefs, <String>[
      'span-1',
      'span-2',
      'span-3',
    ]);
  });

  testWidgets('lets reviewers choose name-only ingredient candidates', (
    WidgetTester tester,
  ) async {
    final _ReviewRepository sourceRepository = _ReviewRepository();
    final _ReviewRepository repository = _ReviewRepository(
      preview: sourceRepository._preview(includeSecondIngredient: true),
    );
    final AppController controller = AppController(repository: repository);
    await controller.analyzeImage('/tmp/supplement-label.jpg');

    await tester.pumpWidget(
      MaterialApp(home: AnalysisResultScreen(controller: controller)),
    );
    await tester.pumpAndSettle();

    expect(find.text('저장 후보 1개 · 검토 후보 2개'), findsOneWidget);
    expect(find.text('Vitamin D'), findsOneWidget);
    expect(find.text('25 mcg'), findsOneWidget);
    expect(find.text('Sunflower oil'), findsOneWidget);
    expect(
      find.byKey(const ValueKey<String>('ingredient-row-checkbox-0')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('ingredient-row-checkbox-1')),
      findsOneWidget,
    );
    expect(
      tester
          .widget<Checkbox>(
            find.byKey(const ValueKey<String>('ingredient-row-checkbox-0')),
          )
          .value,
      isTrue,
    );
    expect(
      tester
          .widget<Checkbox>(
            find.byKey(const ValueKey<String>('ingredient-row-checkbox-1')),
          )
          .value,
      isFalse,
    );

    await tester.tap(
      find.byKey(const ValueKey<String>('ingredient-row-checkbox-0')),
    );
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const ValueKey<String>('ingredient-row-checkbox-1')),
    );
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<Checkbox>(
            find.byKey(const ValueKey<String>('ingredient-row-checkbox-0')),
          )
          .value,
      isFalse,
    );
    expect(
      tester
          .widget<Checkbox>(
            find.byKey(const ValueKey<String>('ingredient-row-checkbox-1')),
          )
          .value,
      isTrue,
    );
    await tester.tap(find.byTooltip('상세 성분 및 함량 수정'));
    await tester.pumpAndSettle();

    expect(find.text('선택 성분 수정'), findsOneWidget);
    await tester.enterText(
      find.byType(TextField).at(0),
      'Sunflower oil extract',
    );
    await tester.tap(find.widgetWithText(FilledButton, '저장'));
    await tester.pumpAndSettle();

    expect(find.text('Sunflower oil extract'), findsOneWidget);
    expect(find.text('함량 확인 필요'), findsOneWidget);

    await tester.tap(find.text('확인 후 저장'));
    await tester.pumpAndSettle();

    expect(repository.registeredRequest?.ingredients, hasLength(1));
    expect(
      repository.registeredRequest?.ingredients.single.displayName,
      'Sunflower oil extract',
    );
    expect(repository.registeredRequest?.ingredients.single.amount, isNull);
    expect(repository.registeredRequest?.ingredients.single.unit, isNull);
  });

  testWidgets('switches between multi-image supplement result tabs', (
    WidgetTester tester,
  ) async {
    final _ReviewRepository repository = _ReviewRepository();
    final AppController controller = AppController(repository: repository);
    await controller.analyzeImages(const <SupplementImageUpload>[
      SupplementImageUpload(path: '/tmp/supplement-a.jpg'),
      SupplementImageUpload(path: '/tmp/supplement-b.jpg'),
    ]);

    await tester.pumpWidget(
      MaterialApp(home: AnalysisResultScreen(controller: controller)),
    );
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey<String>('supplement-preview-tab-0')),
      findsOneWidget,
    );
    expect(
      find.byKey(const ValueKey<String>('supplement-preview-tab-1')),
      findsOneWidget,
    );
    expect(find.text('비타민 D'), findsWidgets);
    expect(find.text('오메가-3'), findsOneWidget);
    expect(find.text('Omega-3'), findsNothing);

    await tester.tap(
      find.byKey(const ValueKey<String>('supplement-preview-tab-1')),
    );
    await tester.pumpAndSettle();

    expect(find.text('Omega-3'), findsOneWidget);
    expect(find.text('1000 mg'), findsOneWidget);
  });

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
  _ReviewRepository({
    SupplementAnalysisPreview? preview,
    SupplementMultiImageAnalysisPreview? multiPreview,
  }) : _previewOverride = preview,
       _multiPreviewOverride = multiPreview;

  final SupplementAnalysisPreview? _previewOverride;
  final SupplementMultiImageAnalysisPreview? _multiPreviewOverride;
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
    return Future<SupplementMultiImageAnalysisPreview>.value(
      _multiPreviewOverride ?? _multiPreview(),
    );
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
        precautionSnapshot: request.precautionSnapshot,
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

  SupplementAnalysisPreview _preview({
    String analysisId = 'analysis-1',
    String productName = '비타민 D',
    String manufacturer = 'Lemon Lab',
    String ingredientName = 'Vitamin D',
    double? ingredientAmount = 25,
    String? ingredientUnit = 'mcg',
    String ingredientSource = 'ocr_llm_preview',
    bool includeSecondIngredient = false,
  }) {
    final List<SupplementIngredientCandidate> ingredients =
        <SupplementIngredientCandidate>[
          SupplementIngredientCandidate(
            displayName: ingredientName,
            nutrientCode: ingredientName.toLowerCase().replaceAll(' ', '_'),
            amount: ingredientAmount,
            unit: ingredientUnit,
            confidence: 0.92,
            source: ingredientSource,
          ),
        ];
    if (includeSecondIngredient) {
      ingredients.add(
        SupplementIngredientCandidate(
          displayName: 'Sunflower oil',
          nutrientCode: null,
          amount: null,
          unit: null,
          confidence: 0.81,
          source: ingredientSource,
        ),
      );
    }
    final String ingredientText =
        '$ingredientName ${ingredientAmount?.toStringAsFixed(0) ?? ''} ${ingredientUnit ?? ''}'
            .trim();
    return SupplementAnalysisPreview(
      analysisId: analysisId,
      status: 'requires_confirmation',
      parsedProduct: SupplementParsedProduct(
        productName: productName,
        manufacturer: manufacturer,
        servingSize: 'capsule',
        dailyServings: 1,
      ),
      ingredientCandidates: ingredients,
      layoutAvailable: true,
      layoutFallbackReason: null,
      labelSections: <SupplementPreviewLabelSection>[
        SupplementPreviewLabelSection(
          sectionId: 'section-1',
          sectionType: 'supplement_facts',
          headingText: 'Supplement Facts',
          textBundle: ingredientText,
          confidence: 0.91,
          requiresReview: false,
          evidenceRefs: const <String>['span-1'],
        ),
        const SupplementPreviewLabelSection(
          sectionId: 'section-2',
          sectionType: 'intake_method',
          headingText: 'Directions',
          textBundle: '하루 1회 1캡슐',
          confidence: 0.9,
          requiresReview: false,
          evidenceRefs: <String>['span-2'],
        ),
        const SupplementPreviewLabelSection(
          sectionId: 'section-3',
          sectionType: 'precautions',
          headingText: 'Warning',
          textBundle: '임신 중이면 전문가와 상담하세요.',
          confidence: 0.88,
          requiresReview: false,
          evidenceRefs: <String>['span-3'],
        ),
      ],
      intakeMethod: const SupplementPreviewIntakeMethod(
        text: '하루 1회 1캡슐',
        structured: SupplementPreviewStructuredIntakeMethod(
          frequency: 'daily',
          timeOfDay: <String>['morning'],
          timesPerDay: 1,
          amountPerTime: 1,
          amountUnit: 'capsule',
          withFood: 'unknown',
        ),
        confidence: 0.9,
        requiresReview: false,
        evidenceRefs: <String>['span-2'],
      ),
      precautions: const <SupplementPreviewPrecaution>[
        SupplementPreviewPrecaution(
          text: '임신 중이면 전문가와 상담하세요.',
          category: 'pregnancy',
          severity: 'review',
          confidence: 0.88,
          requiresReview: false,
          evidenceRefs: <String>['span-3'],
        ),
      ],
      functionalClaims: const <SupplementPreviewFunctionalClaim>[],
      evidenceSpans: <SupplementPreviewEvidenceSpan>[
        SupplementPreviewEvidenceSpan(
          spanId: 'span-1',
          sourceType: 'ocr',
          sectionType: 'supplement_facts',
          textExcerpt: ingredientText,
          pageIndex: null,
          cellRef: null,
          confidence: 0.91,
        ),
        const SupplementPreviewEvidenceSpan(
          spanId: 'span-2',
          sourceType: 'ocr',
          sectionType: 'intake_method',
          textExcerpt: '하루 1회 1캡슐',
          pageIndex: null,
          cellRef: null,
          confidence: 0.9,
        ),
        const SupplementPreviewEvidenceSpan(
          spanId: 'span-3',
          sourceType: 'ocr',
          sectionType: 'precautions',
          textExcerpt: '임신 중이면 전문가와 상담하세요.',
          pageIndex: null,
          cellRef: null,
          confidence: 0.88,
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
        ocrStatus: 'success',
        visionStatus: 'success',
        llmStatus: 'success',
        ocrProvider: 'paddleocr_local',
        ocrTextPresent: true,
        ocrConfidenceBucket: 'high',
        roiCount: 1,
        sectionCount: 3,
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

  SupplementMultiImageAnalysisPreview _multiPreview() {
    final List<SupplementAnalysisPreview> previews =
        <SupplementAnalysisPreview>[
          _preview(),
          _preview(
            analysisId: 'analysis-2',
            productName: '오메가-3',
            manufacturer: 'Ocean Lab',
            ingredientName: 'Omega-3',
            ingredientAmount: 1000,
            ingredientUnit: 'mg',
          ),
        ];
    return SupplementMultiImageAnalysisPreview(
      analysisGroupId: 'multi-analysis-1',
      imageCount: previews.length,
      previews: previews,
      mergedPreview: null,
      missingRequiredSections: const <String>[],
      actionRequired: 'none',
      pipelineMetadata: previews.first.pipelineMetadata,
      expiresAt: previews.first.expiresAt,
    );
  }
}

class _PendingReviewRepository extends _ReviewRepository {
  final Completer<SupplementAnalysisPreview> _completer =
      Completer<SupplementAnalysisPreview>();

  @override
  Future<SupplementAnalysisPreview> analyzeSupplementImage(
    String imagePath, {
    String ocrProvider = 'configured',
  }) {
    return _completer.future;
  }

  void complete() {
    if (!_completer.isCompleted) {
      _completer.complete(_preview());
    }
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
    missingRequiredSections: const <String>[
      'product_name',
      'supplement_facts',
      'intake_method',
      'precautions',
    ],
    imageRole: 'unknown',
    multiImageGroupId: null,
    sourceType: 'uploaded_image',
    identityConflict: null,
    pipelineMetadata: const SupplementImagePipelineMetadata(
      intakeCompleted: true,
      imageCount: 1,
      imageRole: 'unknown',
      visionRoiUsed: false,
      ocrStatus: 'success',
      visionStatus: 'skipped',
      llmStatus: 'warning',
      ocrProvider: 'paddleocr_local',
      ocrTextPresent: true,
      ocrConfidenceBucket: 'low',
      roiCount: 0,
      sectionCount: 0,
      llmParserUsed: true,
      parserContractVersion: 'test-parser-v3',
      missingRequiredSections: <String>[
        'product_name',
        'supplement_facts',
        'intake_method',
        'precautions',
      ],
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
