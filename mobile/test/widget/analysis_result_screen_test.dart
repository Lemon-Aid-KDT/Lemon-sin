import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/app_controller.dart';
import 'package:lemon_aid_mobile/app_providers.dart';
import 'package:lemon_aid_mobile/features/consent/consent_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/dashboard_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/home_models.dart';
import 'package:lemon_aid_mobile/features/supplements/comprehensive_analysis_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
import 'package:lemon_aid_mobile/features/records/food_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';
import 'package:lemon_aid_mobile/screens/analysis_result_screen.dart';
import 'package:lemon_aid_mobile/shared/widgets/low_confidence_banner.dart';

void main() {
  testWidgets('renders source-style analysis result with real pipeline data', (
    WidgetTester tester,
  ) async {
    final _ReviewRepository repository = _ReviewRepository();
    final AppController controller = AppController(
      repository: _ReviewRepository(
        preview: repository._preview(
          ingredientName: '비타민 D',
          originalIngredientName: 'Vitamin D',
        ),
      ),
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
    expect(find.text('비타민 D'), findsOneWidget);
    expect(find.text('원문: Vitamin D'), findsOneWidget);
    expect(find.text('25 mcg'), findsOneWidget);
    expect(
      tester
          .widgetList<Text>(find.text('비타민 D'))
          .any(
            (Text widget) =>
                widget.style?.fontWeight == FontWeight.w900 &&
                widget.style?.fontSize == 16,
          ),
      isTrue,
    );
    await tester.tap(
      find.byKey(const ValueKey<String>('supplement-candidate-summary')),
    );
    await tester.pumpAndSettle();

    expect(find.text('OCR 텍스트 전체'), findsOneWidget);
    expect(find.text('구역'), findsOneWidget);
    expect(find.text('비타민 D 25 mcg'), findsOneWidget);
    await tester.tap(find.text('닫기'));
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(find.text('섭취 방법'), 120);
    expect(find.text('섭취 방법'), findsOneWidget);
    expect(find.textContaining('하루 1회 1캡슐'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('섭취 시 주의사항'), 220);
    expect(find.text('섭취 시 주의사항'), findsOneWidget);
    expect(find.textContaining('전문가와 상담'), findsOneWidget);
    expect(find.text('OCR'), findsNothing);
    expect(find.text('YOLO ROI'), findsNothing);
    expect(find.text('Ollama'), findsNothing);
    expect(find.text('주의사항이 보이게 한 장 더 촬영해주세요'), findsNothing);
    expect(find.text('Analysis progress'), findsNothing);
    expect(find.textContaining('OCR Auto'), findsNothing);
  });

  testWidgets('preserves OCR original ingredient name after single edit', (
    WidgetTester tester,
  ) async {
    final _ReviewRepository sourceRepository = _ReviewRepository();
    final _ReviewRepository repository = _ReviewRepository(
      preview: sourceRepository._preview(
        ingredientName: '글루코사민 염산염',
        originalIngredientName: 'Glucosamine Hydrochloride',
        ingredientAmount: 1500,
        ingredientUnit: 'mg',
      ),
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

    expect(find.text('글루코사민 염산염'), findsOneWidget);
    expect(find.text('원문: Glucosamine Hydrochloride'), findsOneWidget);

    await tester.tap(find.byTooltip('상세 성분 및 함량 수정'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).at(0), '글루코사민 HCl');
    await tester.tap(find.text('저장'));
    await tester.pumpAndSettle();

    expect(find.text('글루코사민 HCl'), findsOneWidget);
    expect(find.text('원문: Glucosamine Hydrochloride'), findsOneWidget);

    await tester.tap(find.text('확인 후 저장'));
    await tester.pumpAndSettle();

    expect(
      repository.registeredRequest?.ingredients.single.displayName,
      '글루코사민 HCl',
    );
    expect(
      repository.registeredRequest?.ingredients.single.originalName,
      'Glucosamine Hydrochloride',
    );
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
      expect(
        controller.pendingChatExplanationDraft?.assistantMessage,
        contains('출처'),
      );
      expect(
        controller.pendingChatExplanationDraft?.assistantMessage,
        contains('vitamin-d.md'),
      );
    },
  );

  testWidgets('normalizes OCR provider source for supplement registration', (
    WidgetTester tester,
  ) async {
    final _ReviewRepository sourceRepository = _ReviewRepository();
    final _ReviewRepository repository = _ReviewRepository(
      preview: sourceRepository._preview(
        ingredientName: '비타민 D',
        originalIngredientName: 'Vitamin D',
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
      '비타민 D',
    );
    expect(
      repository.registeredRequest?.ingredients.single.originalName,
      'Vitamin D',
    );
    expect(
      controller.pendingChatExplanationDraft?.assistantMessage,
      contains('비타민 D(Vitamin D): 25 mcg'),
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
    expect(find.text('선택 1/2'), findsOneWidget);
    expect(find.text('전체 선택'), findsOneWidget);
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
      find.byKey(const ValueKey<String>('ingredient-select-all-button')),
    );
    await tester.pumpAndSettle();
    expect(find.text('선택 2/2'), findsOneWidget);
    expect(find.text('전체 해제'), findsOneWidget);
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
      isTrue,
    );

    await tester.tap(
      find.byKey(const ValueKey<String>('ingredient-select-all-button')),
    );
    await tester.pumpAndSettle();
    expect(find.text('선택 0/2'), findsOneWidget);
    expect(find.text('전체 선택'), findsOneWidget);
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
      isFalse,
    );

    await tester.tap(
      find.byKey(const ValueKey<String>('ingredient-select-all-button')),
    );
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const ValueKey<String>('ingredient-row-checkbox-0')),
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

  testWidgets(
    'groups front and facts photos into supplement-level result tabs',
    (WidgetTester tester) async {
      final SupplementMultiImageAnalysisPreview multiPreview =
          _threeSupplementMultiPreview();
      final _ReviewRepository repository = _ReviewRepository(
        multiPreview: multiPreview,
      );
      final AppController controller = AppController(repository: repository);
      await controller.analyzeImages(const <SupplementImageUpload>[
        SupplementImageUpload(path: '/tmp/lemon-multi-front.jpg'),
        SupplementImageUpload(path: '/tmp/lemon-multi-facts.jpg'),
        SupplementImageUpload(path: '/tmp/omega-plus.jpg'),
        SupplementImageUpload(path: '/tmp/magnesium-calm.jpg'),
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
      expect(
        find.byKey(const ValueKey<String>('supplement-preview-tab-2')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey<String>('supplement-preview-tab-3')),
        findsNothing,
      );
      expect(find.text('Merged batch'), findsNothing);
      expect(find.text('Lemon Multi'), findsWidgets);
      expect(find.text('Vitamin C'), findsOneWidget);
      expect(find.text('500 mg'), findsOneWidget);

      await tester.tap(
        find.byKey(const ValueKey<String>('supplement-preview-tab-1')),
      );
      await tester.pumpAndSettle();

      expect(find.text('Omega Plus'), findsWidgets);
      expect(find.text('Omega-3'), findsOneWidget);
      expect(find.text('1000 mg'), findsOneWidget);
      expect(find.text('Vitamin C'), findsNothing);

      await tester.tap(
        find.byKey(const ValueKey<String>('supplement-preview-tab-2')),
      );
      await tester.pumpAndSettle();

      expect(find.text('Magnesium Calm'), findsWidgets);
      expect(find.text('Magnesium'), findsOneWidget);
      expect(find.text('200 mg'), findsOneWidget);
      expect(find.text('Omega-3'), findsNothing);
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

  testWidgets(
    'meal manual-entry fallback merges database_match items into confirm',
    (WidgetTester tester) async {
      final _ReviewRepository repository = _ReviewRepository(
        mealPreviewJson: _manualEntryMealPreviewJson,
        foodCatalog: const <FoodCatalogItem>[
          FoodCatalogItem(
            id: 'cat-1',
            cuisineCode: 'korean',
            courseCode: 'rice',
            canonicalNameKo: '김치볶음밥',
            source: 'seed',
          ),
        ],
      );
      final AppController controller = AppController(repository: repository);
      await controller.analyzeMealImage('/tmp/meal.png', mealType: 'lunch');

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            lemonAidRepositoryProvider.overrideWithValue(repository),
          ],
          child: MaterialApp(
            home: AnalysisResultScreen(mode: 'meal', controller: controller),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // 저장 버튼 라벨(하단 고정)은 즉시 보인다.
      expect(find.text('음식 직접 입력'), findsOneWidget);

      // 후보 0건 + 수동입력 → 직접 입력 폴백 카드. 하단으로 스크롤해 노출.
      await _scrollResultDetails(tester);
      expect(find.text('음식을 직접 검색해 담기'), findsOneWidget);

      // 폴백 카드의 '직접 입력으로 찾기' → 음식 검색 화면 진입.
      await tester.tap(find.text('직접 입력으로 찾기'));
      await tester.pumpAndSettle();
      expect(find.text('직접 입력'), findsOneWidget);

      // 검색 결과를 ⊕ 로 담고 '기록에 추가하기' 로 합류.
      await tester.tap(find.byIcon(Icons.add_rounded).first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('기록에 추가하기'));
      await tester.pumpAndSettle();

      // 분석 결과 화면으로 복귀 + 저장 버튼이 활성 라벨로 바뀜.
      expect(find.text('확인 후 식단 저장'), findsOneWidget);
      await tester.tap(find.text('확인 후 식단 저장'));
      await tester.pumpAndSettle();

      // confirm payload 에 database_match 항목이 합류됐는지.
      final MealFoodItemInput merged =
          repository.confirmedMealRequest!.foodItems.single;
      expect(merged.displayName, '김치볶음밥');
      expect(merged.foodCatalogItemId, 'cat-1');
      expect(merged.source, 'database_match');
    },
  );

  testWidgets(
    'renders figma C-hybrid diet result with score and prioritized caution',
    (WidgetTester tester) async {
      final _ComprehensiveMealRepository repository =
          _ComprehensiveMealRepository(comprehensive: _comprehensiveAnalysis());
      final AppController controller = AppController(repository: repository);
      await controller.analyzeMealImage('/tmp/meal.png', mealType: 'lunch');

      await tester.pumpWidget(
        MaterialApp(
          home: AnalysisResultScreen(mode: 'meal', controller: controller),
        ),
      );
      await tester.pumpAndSettle();

      // Score ring header + grade chip (no raw % exposure).
      expect(
        find.byKey(const ValueKey<String>('diet-score-header')),
        findsOneWidget,
      );
      expect(find.text('균형이 잘 잡혔어요'), findsOneWidget);
      expect(find.text('신뢰도 높음'), findsOneWidget);

      // Cautionary component card is the top-priority insight card.
      expect(
        find.byKey(const ValueKey<String>('cautionary-component-card')),
        findsOneWidget,
      );
      expect(find.text('카페인'), findsOneWidget);
      expect(find.text('출처 · caffeine.md'), findsOneWidget);

      // Nutrient grid renders below the priority caution card.
      expect(find.text('단백질'), findsOneWidget);

      // The caution card sits above the nutrient grid (priority placement).
      final double cautionTop = tester
          .getTopLeft(
            find.byKey(const ValueKey<String>('cautionary-component-card')),
          )
          .dy;
      final double proteinTop = tester.getTopLeft(find.text('단백질')).dy;
      expect(cautionTop, lessThan(proteinTop));

      // The save CTA lives in the persistent bottom bar (always visible).
      expect(find.text('확인 후 식단 저장'), findsOneWidget);

      // The comprehensive request carried the meal nutrient totals.
      expect(repository.comprehensiveIngredients, isNotNull);
      expect(
        repository.comprehensiveIngredients!
            .map((Map<String, Object?> row) => row['nutrient_code'])
            .toList(),
        containsAll(<String>['carbohydrate_g', 'protein_g', 'fat_g']),
      );

      // Purpose card renders after scrolling it into view.
      await tester.scrollUntilVisible(
        find.byKey(const ValueKey<String>('purpose-target-card')),
        160,
      );
      expect(find.text('당뇨'), findsOneWidget);

      // Base meal cards remain intact below the C-hybrid cards.
      await tester.scrollUntilVisible(find.text('음식 후보'), 160);
      expect(find.text('음식 후보'), findsOneWidget);
    },
  );

  testWidgets('shows low-confidence banner when diet score confidence is low', (
    WidgetTester tester,
  ) async {
    final _ComprehensiveMealRepository repository =
        _ComprehensiveMealRepository(
          comprehensive: _comprehensiveAnalysis(scoreConfidence: 0.4),
        );
    final AppController controller = AppController(repository: repository);
    await controller.analyzeMealImage('/tmp/meal.png', mealType: 'lunch');

    await tester.pumpWidget(
      MaterialApp(
        home: AnalysisResultScreen(mode: 'meal', controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('신뢰도 직접 확인 필요'), findsWidgets);
    expect(find.byType(LowConfidenceBanner), findsOneWidget);
  });

  testWidgets('keeps base meal layout when comprehensive analysis is empty', (
    WidgetTester tester,
  ) async {
    final _ComprehensiveMealRepository repository =
        _ComprehensiveMealRepository();
    final AppController controller = AppController(repository: repository);
    await controller.analyzeMealImage('/tmp/meal.png', mealType: 'lunch');

    await tester.pumpWidget(
      MaterialApp(
        home: AnalysisResultScreen(mode: 'meal', controller: controller),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey<String>('diet-score-header')),
      findsNothing,
    );
    expect(
      find.byKey(const ValueKey<String>('cautionary-component-card')),
      findsNothing,
    );
    expect(find.text('음식 후보'), findsOneWidget);
    expect(find.text('확인 후 식단 저장'), findsOneWidget);
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
    ComprehensiveDietAnalysis? comprehensive,
    Map<String, Object?>? mealPreviewJson,
    this.foodCatalog = const <FoodCatalogItem>[],
  }) : _previewOverride = preview,
       _multiPreviewOverride = multiPreview,
       _comprehensiveOverride = comprehensive,
       _mealPreviewJsonOverride = mealPreviewJson;

  final SupplementAnalysisPreview? _previewOverride;
  final SupplementMultiImageAnalysisPreview? _multiPreviewOverride;
  final ComprehensiveDietAnalysis? _comprehensiveOverride;
  final Map<String, Object?>? _mealPreviewJsonOverride;

  /// Catalog rows returned by the direct-input food search fallback.
  List<FoodCatalogItem> foodCatalog;
  UserSupplementCreate? registeredRequest;
  String? confirmedMealId;
  MealConfirmationRequest? confirmedMealRequest;
  List<Map<String, Object?>>? comprehensiveIngredients;
  bool explainUsedLocalLlm = false;

  @override
  Future<ComprehensiveDietAnalysis> analyzeComprehensive({
    required List<Map<String, Object?>> ingredients,
    Map<String, dynamic>? userProfile,
    String persona = 'B',
  }) async {
    comprehensiveIngredients = ingredients;
    return _comprehensiveOverride ?? ComprehensiveDietAnalysis.empty;
  }

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
    return MealImageAnalysisPreview.fromJson(
      _mealPreviewJsonOverride ?? _mealPreviewJson,
    );
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
  Future<FoodCatalogList> searchFoods({
    String? q,
    String? cuisineCode,
    int limit = 50,
    int offset = 0,
  }) async {
    return FoodCatalogList(results: foodCatalog, limit: limit, offset: offset);
  }

  @override
  Future<FoodCuisineList> fetchCuisines() async => FoodCuisineList.empty;

  @override
  Future<void> deleteSupplement(String supplementId) async {
    throw UnimplementedError();
  }

  @override
  Future<void> deleteAnalysisResult(String resultId) async {
    throw UnimplementedError();
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

  @override
  Future<ConsentState> fetchConsents() {
    throw UnimplementedError();
  }

  @override
  Future<DashboardSummary> fetchDashboardSummary({int days = 30}) {
    return Future<DashboardSummary>.value(_dashboardSummary());
  }

  @override
  Future<HomeMealsResult> fetchMeals({
    DateTime? from,
    DateTime? to,
    int limit = 50,
    int offset = 0,
  }) {
    return Future<HomeMealsResult>.value(HomeMealsResult.empty);
  }

  @override
  Future<HomeSupplementsResult> fetchSupplements({
    int limit = 50,
    int offset = 0,
  }) {
    return Future<HomeSupplementsResult>.value(HomeSupplementsResult.empty);
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
        sourceCitations: <SupplementExplanationSourceCitation>[
          SupplementExplanationSourceCitation(
            title: '비타민 D',
            sourcePath: 'vitamin-d.md',
            heading: '확인 필요',
            excerpt: '비타민 D는 개인 상태와 함께 확인합니다.',
            score: 9,
          ),
        ],
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
        sourceCitations: <SupplementExplanationSourceCitation>[
          SupplementExplanationSourceCitation(
            title: '성분표 확인',
            sourcePath: 'supplement-label.md',
            heading: '라벨',
            excerpt: '성분표는 저장 전 확인합니다.',
            score: 5,
          ),
        ],
        warnings: <String>[],
      ),
    );
  }

  SupplementAnalysisPreview _preview({
    String analysisId = 'analysis-1',
    String? productName = '비타민 D',
    String? manufacturer = 'Lemon Lab',
    String ingredientName = 'Vitamin D',
    String? originalIngredientName,
    double? ingredientAmount = 25,
    String? ingredientUnit = 'mcg',
    String ingredientSource = 'ocr_llm_preview',
    bool includeSecondIngredient = false,
    bool includeIngredientCandidates = true,
    bool includeSupplementFactsSection = true,
    bool includeIntakeSection = true,
    bool includePrecautionsSection = true,
    String imageRole = 'supplement_facts',
    List<String> missingRequiredSections = const <String>[],
  }) {
    final List<SupplementIngredientCandidate> ingredients =
        includeIngredientCandidates
        ? <SupplementIngredientCandidate>[
            SupplementIngredientCandidate(
              displayName: ingredientName,
              originalName: originalIngredientName,
              nutrientCode: ingredientName.toLowerCase().replaceAll(' ', '_'),
              amount: ingredientAmount,
              unit: ingredientUnit,
              confidence: 0.92,
              source: ingredientSource,
            ),
          ]
        : <SupplementIngredientCandidate>[];
    if (includeIngredientCandidates && includeSecondIngredient) {
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
    final List<SupplementPreviewLabelSection> labelSections =
        <SupplementPreviewLabelSection>[
          if (includeSupplementFactsSection)
            SupplementPreviewLabelSection(
              sectionId: 'section-1',
              sectionType: 'supplement_facts',
              headingText: 'Supplement Facts',
              textBundle: ingredientText,
              confidence: 0.91,
              requiresReview: false,
              evidenceRefs: const <String>['span-1'],
            ),
          if (includeIntakeSection)
            const SupplementPreviewLabelSection(
              sectionId: 'section-2',
              sectionType: 'intake_method',
              headingText: 'Directions',
              textBundle: '하루 1회 1캡슐',
              confidence: 0.9,
              requiresReview: false,
              evidenceRefs: <String>['span-2'],
            ),
          if (includePrecautionsSection)
            const SupplementPreviewLabelSection(
              sectionId: 'section-3',
              sectionType: 'precautions',
              headingText: 'Warning',
              textBundle: '임신 중이면 전문가와 상담하세요.',
              confidence: 0.88,
              requiresReview: false,
              evidenceRefs: <String>['span-3'],
            ),
        ];
    final List<SupplementPreviewEvidenceSpan> evidenceSpans =
        <SupplementPreviewEvidenceSpan>[
          if (includeSupplementFactsSection)
            SupplementPreviewEvidenceSpan(
              spanId: 'span-1',
              sourceType: 'ocr',
              sectionType: 'supplement_facts',
              textExcerpt: ingredientText,
              pageIndex: null,
              cellRef: null,
              confidence: 0.91,
            ),
          if (includeIntakeSection)
            const SupplementPreviewEvidenceSpan(
              spanId: 'span-2',
              sourceType: 'ocr',
              sectionType: 'intake_method',
              textExcerpt: '하루 1회 1캡슐',
              pageIndex: null,
              cellRef: null,
              confidence: 0.9,
            ),
          if (includePrecautionsSection)
            const SupplementPreviewEvidenceSpan(
              spanId: 'span-3',
              sourceType: 'ocr',
              sectionType: 'precautions',
              textExcerpt: '임신 중이면 전문가와 상담하세요.',
              pageIndex: null,
              cellRef: null,
              confidence: 0.88,
            ),
        ];
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
      labelSections: labelSections,
      intakeMethod: includeIntakeSection
          ? const SupplementPreviewIntakeMethod(
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
            )
          : SupplementPreviewIntakeMethod.empty,
      precautions: includePrecautionsSection
          ? const <SupplementPreviewPrecaution>[
              SupplementPreviewPrecaution(
                text: '임신 중이면 전문가와 상담하세요.',
                category: 'pregnancy',
                severity: 'review',
                confidence: 0.88,
                requiresReview: false,
                evidenceRefs: <String>['span-3'],
              ),
            ]
          : const <SupplementPreviewPrecaution>[],
      functionalClaims: const <SupplementPreviewFunctionalClaim>[],
      evidenceSpans: evidenceSpans,
      imageQualityReport: null,
      analysisScope: 'supplement_label',
      actionRequired: 'none',
      detectedProductRegions: const <SupplementDetectedProductRegion>[],
      selectedRegionId: null,
      missingRequiredSections: missingRequiredSections,
      imageRole: imageRole,
      multiImageGroupId: null,
      sourceType: 'uploaded_image',
      identityConflict: null,
      pipelineMetadata: SupplementImagePipelineMetadata(
        intakeCompleted: true,
        imageCount: 1,
        imageRole: imageRole,
        visionRoiUsed: true,
        ocrStatus: 'success',
        visionStatus: 'success',
        llmStatus: 'success',
        ocrProvider: 'paddleocr_local',
        ocrTextPresent: true,
        ocrConfidenceBucket: 'high',
        roiCount: 1,
        sectionCount: labelSections.length,
        llmParserUsed: true,
        parserContractVersion: 'test-parser-v3',
        missingRequiredSections: missingRequiredSections,
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

/// Meal-flow repository whose meal preview carries nutrition totals so the
/// comprehensive diet analysis call fires with real nutrient rows.
class _ComprehensiveMealRepository extends _ReviewRepository {
  _ComprehensiveMealRepository({super.comprehensive});

  @override
  Future<MealImageAnalysisPreview> analyzeMealImage(
    String imagePath, {
    String mealType = 'unknown',
  }) async {
    return MealImageAnalysisPreview.fromJson(_mealPreviewWithTotalsJson);
  }
}

ComprehensiveDietAnalysis _comprehensiveAnalysis({
  double scoreConfidence = 0.9,
}) {
  return ComprehensiveDietAnalysis.fromJson(<String, dynamic>{
    'diet_score': 78,
    'diet_score_label': '균형이 잘 잡혔어요',
    'diet_score_message': '나트륨만 조금 줄이면 좋아요.',
    'diet_score_confidence': scoreConfidence,
    'deficient_nutrients': <Object?>[
      <String, dynamic>{
        'nutrient_code': 'protein_g',
        'nutrient_name': '단백질',
        'deficit_ratio': 0.5,
        'unit': 'g',
        'confidence': 0.7,
        'message': '단백질이 더 필요해요.',
      },
    ],
    'excessive_nutrients': <Object?>[
      <String, dynamic>{
        'nutrient_code': 'sodium_mg',
        'nutrient_name': '나트륨',
        'excess_ratio': 1.1,
        'unit': 'mg',
        'confidence': 0.4,
        'message': '나트륨을 조금 줄여보세요.',
      },
    ],
    'cautionary_components': <Object?>[
      <String, dynamic>{
        'component': '카페인',
        'reason': '늦은 시간 섭취',
        'severity': 'high',
        'message': '저녁 섭취는 피하는 게 좋아요.',
        'source_citation': 'caffeine.md',
      },
    ],
    'purpose_targets': <Object?>[
      <String, dynamic>{
        'condition': '당뇨',
        'relevance_score': 0.8,
        'evidence_level': 'moderate',
        'message': 'GI 지수를 함께 확인해보세요.',
      },
    ],
    'chronic_disease_indications': <String>[],
    'warnings': <String>[],
  });
}

final Map<String, Object?> _mealPreviewWithTotalsJson = <String, Object?>{
  ..._mealPreviewJson,
  'nutrition_estimate_summary': <String, Object?>{
    'status': 'detected_review_required',
    'items': <Object?>[],
    'totals': <String, Object?>{
      'carb_g': 78,
      'protein_g': 18,
      'fat_g': 12,
      'sodium_mg': 820,
    },
    'detector_used': true,
  },
};

SupplementMultiImageAnalysisPreview _threeSupplementMultiPreview() {
  final _ReviewRepository source = _ReviewRepository();
  final List<SupplementAnalysisPreview> previews = <SupplementAnalysisPreview>[
    source._preview(
      analysisId: 'analysis-a-front',
      productName: 'Lemon Multi',
      manufacturer: 'Lemon Lab',
      includeIngredientCandidates: false,
      includeSupplementFactsSection: false,
      includeIntakeSection: false,
      includePrecautionsSection: false,
      imageRole: 'front_label',
      missingRequiredSections: const <String>[
        'supplement_facts',
        'intake_method',
        'precautions',
      ],
    ),
    source._preview(
      analysisId: 'analysis-a-facts',
      productName: null,
      manufacturer: null,
      ingredientName: 'Vitamin C',
      ingredientAmount: 500,
      ingredientUnit: 'mg',
      includeIntakeSection: false,
      includePrecautionsSection: false,
      missingRequiredSections: const <String>[
        'product_name',
        'intake_method',
        'precautions',
      ],
    ),
    source._preview(
      analysisId: 'analysis-b',
      productName: 'Omega Plus',
      manufacturer: 'Ocean Lab',
      ingredientName: 'Omega-3',
      ingredientAmount: 1000,
      ingredientUnit: 'mg',
      missingRequiredSections: const <String>[],
    ),
    source._preview(
      analysisId: 'analysis-c',
      productName: 'Magnesium Calm',
      manufacturer: 'Mineral Lab',
      ingredientName: 'Magnesium',
      ingredientAmount: 200,
      ingredientUnit: 'mg',
      missingRequiredSections: const <String>[],
    ),
  ];
  return SupplementMultiImageAnalysisPreview(
    analysisGroupId: 'multi-analysis-three-products',
    imageCount: previews.length,
    previews: previews,
    mergedPreview: source._preview(
      analysisId: 'analysis-global',
      productName: 'Merged batch',
      manufacturer: 'Global Lab',
      ingredientName: 'Global Ingredient',
      ingredientAmount: 1,
      ingredientUnit: 'mg',
    ),
    missingRequiredSections: const <String>[],
    actionRequired: 'none',
    pipelineMetadata: previews.first.pipelineMetadata,
    expiresAt: previews.first.expiresAt,
  );
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

// 후보 0건 + requires_manual_entry: 카메라 분석 폴백(직접 입력) 진입 케이스.
final Map<String, Object?> _manualEntryMealPreviewJson = <String, Object?>{
  'analysis_id': '00000000-0000-0000-0000-000000000101',
  'meal_id': '00000000-0000-0000-0000-000000000201',
  'status': 'requires_confirmation',
  'meal_type': 'lunch',
  'eaten_at': '2026-05-28T03:00:00Z',
  'food_candidates': <Object?>[],
  'nutrition_estimate_summary': <String, Object?>{
    'status': 'manual_entry_required',
    'items': <Object?>[],
    'totals': <String, Object?>{},
    'detector_used': false,
  },
  'warning_codes': <String>['food_detection_manual_entry_required'],
  'pipeline_metadata': <String, Object?>{
    'intake_completed': true,
    'detector_model': null,
    'classifier_model': null,
    'detector_used': false,
    'classifier_used': false,
    'raw_image_stored': false,
    'raw_provider_payload_stored': false,
    'requires_manual_entry': true,
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
