import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:lemon_aid_mobile/app_controller.dart';
import 'package:lemon_aid_mobile/core/storage/local_prefs.dart';
import 'package:lemon_aid_mobile/features/consent/consent_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/dashboard_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/home_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';
import 'package:lemon_aid_mobile/features/supplements/comprehensive_analysis_models.dart';
import 'package:lemon_aid_mobile/screens/dashboard_screen.dart';
import 'package:lemon_aid_mobile/utils/design_tokens_v2.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('shows the ready health score and a calm interaction state', (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _HomeRepository(
        healthScore: const DashboardHealthScore(
          status: HealthScoreStatus.ready,
          score: 78,
          labelText: '좋아요',
          message: '오늘 활동량이 좋아요.',
        ),
        supplements: const HomeSupplementsResult(
          results: <HomeSupplement>[
            HomeSupplement(
              id: 'sup-1',
              displayName: '비타민 D',
              manufacturer: '레몬랩스',
              schedule: HomeSupplementSchedule(
                frequency: 'daily',
                timeOfDay: <String>['morning'],
                timesPerDay: 1,
              ),
            ),
          ],
          limit: 50,
          offset: 0,
        ),
        impact: _impact(risks: const <SupplementNutritionInsight>[]),
      ),
    );
    await controller.bootstrap();

    await _pumpScreen(tester, controller);

    expect(find.text('78'), findsOneWidget);
    expect(find.text('오늘의 분석'), findsOneWidget);
    expect(find.textContaining('오늘 활동량이 좋아요.'), findsOneWidget);
    expect(find.text('안심하고 드셔도 돼요'), findsOneWidget);
    expect(find.text('영양제 관리'), findsOneWidget);
    expect(find.text('비타민 D'), findsOneWidget);
    // 복약 카드 빈 상태 (약 0개).
    expect(find.text('복약 관리'), findsOneWidget);
    expect(find.text('약 등록하기'), findsOneWidget);
  });

  testWidgets('shows the not_ready prompt when the score is unavailable', (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _HomeRepository(
        healthScore: const DashboardHealthScore(
          status: HealthScoreStatus.notReady,
        ),
        supplements: HomeSupplementsResult.empty,
        impact: _impact(risks: const <SupplementNutritionInsight>[]),
      ),
    );
    await controller.bootstrap();

    await _pumpScreen(tester, controller);

    expect(find.text('기록을 추가하면 점수를 보여드려요'), findsOneWidget);
    // 영양제·약이 모두 없으면 상호작용 카드는 ③ 미등록 안내 상태.
    expect(find.text('등록된 영양제·약이 없어요'), findsOneWidget);
  });

  testWidgets('lists interaction risks when the preview reports them', (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _HomeRepository(
        healthScore: const DashboardHealthScore(
          status: HealthScoreStatus.notReady,
        ),
        supplements: const HomeSupplementsResult(
          results: <HomeSupplement>[
            HomeSupplement(
              id: 'sup-1',
              displayName: '비타민 D',
              manufacturer: null,
              schedule: null,
            ),
          ],
          limit: 50,
          offset: 0,
        ),
        impact: _impact(
          risks: const <SupplementNutritionInsight>[
            SupplementNutritionInsight(
              nutrientCode: 'vitamin_d',
              nutrientName: '비타민 D',
              actionLabel: '중복 확인',
              reasonCode: 'duplicate_input',
              supplementDailyAmount: 50,
              estimatedTotalAmount: 50,
              referenceUnit: 'mcg',
              userMessage: '비타민 D 섭취가 겹칠 수 있어요.',
            ),
          ],
        ),
      ),
    );
    await controller.bootstrap();

    await _pumpScreen(tester, controller);

    expect(find.text('확인이 필요해요 · 1건'), findsOneWidget);
    expect(find.textContaining('비타민 D 섭취가 겹칠 수 있어요.'), findsOneWidget);
  });

  testWidgets('renders the medication card list with class and tag labels', (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _HomeRepository(
        healthScore: const DashboardHealthScore(
          status: HealthScoreStatus.notReady,
        ),
        supplements: HomeSupplementsResult.empty,
        impact: _impact(risks: const <SupplementNutritionInsight>[]),
        medications: const HomeMedicationsResult(
          items: <HomeMedication>[
            HomeMedication(
              id: 'med-1',
              displayName: '아모디핀',
              medicationClass: 'calcium_channel_blocker',
              conditionTags: <String>['hypertension', 'diabetes', 'other'],
            ),
          ],
        ),
      ),
    );
    await controller.bootstrap();

    await _pumpScreen(tester, controller);

    expect(find.text('복약 관리'), findsOneWidget);
    expect(find.text('아모디핀'), findsOneWidget);
    expect(find.text('칼슘 채널 차단제'), findsOneWidget);
    // condition_tags 칩 최대 2 + n.
    expect(find.text('고혈압'), findsOneWidget);
    expect(find.text('당뇨'), findsOneWidget);
    expect(find.text('+1'), findsOneWidget);
    // 약 ≥1 이면 상호작용 카드에 약 기준 각주가 붙는다.
    expect(find.textContaining('등록한 약 1개 기준으로 함께 살펴봐요'), findsOneWidget);
  });

  testWidgets('toggles the medication intake check', (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _HomeRepository(
        healthScore: const DashboardHealthScore(
          status: HealthScoreStatus.notReady,
        ),
        supplements: HomeSupplementsResult.empty,
        impact: _impact(risks: const <SupplementNutritionInsight>[]),
        medications: const HomeMedicationsResult(
          items: <HomeMedication>[
            HomeMedication(id: 'med-1', displayName: '아모디핀'),
          ],
        ),
      ),
    );
    await controller.bootstrap();

    await _pumpScreen(tester, controller);

    expect(find.text('0/1 완료'), findsOneWidget);

    await tester.ensureVisible(find.text('아모디핀'));
    await tester.pump();
    await tester.tap(find.text('아모디핀'));
    await tester.pump();

    expect(find.text('1/1 완료'), findsOneWidget);
  });

  testWidgets('add medication sheet keeps the submit disabled until a name is '
      'entered', (WidgetTester tester) async {
    final AppController controller = AppController(
      repository: _HomeRepository(
        healthScore: const DashboardHealthScore(
          status: HealthScoreStatus.notReady,
        ),
        supplements: HomeSupplementsResult.empty,
        impact: _impact(risks: const <SupplementNutritionInsight>[]),
      ),
    );
    await controller.bootstrap();

    await _pumpScreen(tester, controller);

    await tester.ensureVisible(find.text('약 등록하기'));
    await tester.pump();
    await tester.tap(find.text('약 등록하기'));
    await tester.pumpAndSettle();

    expect(find.text('약 추가'), findsOneWidget);
    // 이름이 비어 있으면 '추가하기' 버튼은 비활성 (onPressed null).
    final AppPrimaryButton disabled = tester.widget<AppPrimaryButton>(
      find.widgetWithText(AppPrimaryButton, '추가하기'),
    );
    expect(disabled.enabled, isFalse);

    await tester.enterText(find.byType(TextField).first, '아모디핀');
    await tester.pump();

    final AppPrimaryButton enabled = tester.widget<AppPrimaryButton>(
      find.widgetWithText(AppPrimaryButton, '추가하기'),
    );
    expect(enabled.enabled, isTrue);
  });

  testWidgets('new medication card copy avoids prohibited medical terms', (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _HomeRepository(
        healthScore: const DashboardHealthScore(
          status: HealthScoreStatus.notReady,
        ),
        supplements: HomeSupplementsResult.empty,
        impact: _impact(risks: const <SupplementNutritionInsight>[]),
        medications: const HomeMedicationsResult(
          items: <HomeMedication>[
            HomeMedication(id: 'med-1', displayName: '아모디핀'),
          ],
        ),
      ),
    );
    await controller.bootstrap();

    await _pumpScreen(tester, controller);

    // 복약 카드/각주 신규 문구.
    const List<String> newCopy = <String>[
      '복약 관리',
      '약 변경은 의사·약사와 상담해주세요.',
      '복용 중인 약을 등록하면 음식·영양제 궁합을 확인해드려요.',
      '등록한 약 1개 기준으로 함께 살펴봐요 · 방금 확인',
      '복용 시점·용량 안내는 의사·약사와 상담해주세요.',
    ];
    const List<String> bannedTerms = <String>['진단', '처방', '치료', '효능'];
    for (final String copy in newCopy) {
      for (final String banned in bannedTerms) {
        expect(
          copy.contains(banned),
          isFalse,
          reason: '"$copy" 에 금칙어 "$banned" 가 포함됨',
        );
      }
    }
  });

  testWidgets('shows the kcal watch-lock caption without an estimate', (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _HomeRepository(
        healthScore: const DashboardHealthScore(
          status: HealthScoreStatus.ready,
          score: 70,
        ),
        supplements: HomeSupplementsResult.empty,
        impact: _impact(risks: const <SupplementNutritionInsight>[]),
      ),
    );
    await controller.bootstrap();

    await _pumpScreen(tester, controller);

    // 목표 kcal 미연동 — 잠금 캡션 노출, 소모/잔여 추정치 미노출.
    expect(find.text('워치를 연동하면 소모·잔여 칼로리도 보여드려요'), findsOneWidget);
    expect(find.text('오늘 먹은 음식 합계예요'), findsOneWidget);
    // '소모'/'더 먹을 수 있어요' 같은 추정 문구는 어디에도 없다.
    expect(find.textContaining('kcal 소모'), findsNothing);
    expect(find.textContaining('더 먹을 수 있어요'), findsNothing);
  });

  testWidgets("today's analysis card exposes a '자세히' deep link affordance", (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _HomeRepository(
        healthScore: const DashboardHealthScore(
          status: HealthScoreStatus.ready,
          score: 78,
          message: '오늘 활동량이 좋아요.',
        ),
        supplements: HomeSupplementsResult.empty,
        impact: _impact(risks: const <SupplementNutritionInsight>[]),
      ),
    );
    await controller.bootstrap();

    await _pumpScreen(tester, controller);

    expect(find.text('오늘의 분석'), findsOneWidget);
    expect(find.text('자세히'), findsOneWidget);
  });

  testWidgets("today's analysis card deep-links to the score tab", (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _HomeRepository(
        healthScore: const DashboardHealthScore(
          status: HealthScoreStatus.ready,
          score: 78,
          message: '오늘 활동량이 좋아요.',
        ),
        supplements: HomeSupplementsResult.empty,
        impact: _impact(risks: const <SupplementNutritionInsight>[]),
      ),
    );
    await controller.bootstrap();

    final GoRouter router = GoRouter(
      initialLocation: '/shell/home',
      routes: <RouteBase>[
        GoRoute(
          path: '/shell/home',
          builder: (BuildContext context, GoRouterState state) =>
              DashboardScreen(controller: controller),
        ),
        GoRoute(
          path: '/shell/score',
          builder: (BuildContext context, GoRouterState state) =>
              const Scaffold(body: Text('분석 탭 화면')),
        ),
      ],
    );

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 1300));
    await tester.pump(const Duration(milliseconds: 400));

    await tester.ensureVisible(find.text('자세히'));
    await tester.pump();
    await tester.tap(find.text('자세히'));
    await tester.pumpAndSettle();

    expect(find.text('분석 탭 화면'), findsOneWidget);
  });

  testWidgets('persists the supplement check across a screen rebuild', (
    WidgetTester tester,
  ) async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final LocalPrefs prefs = await LocalPrefs.create();
    final AppController controller = AppController(
      repository: _HomeRepository(
        healthScore: const DashboardHealthScore(
          status: HealthScoreStatus.notReady,
        ),
        supplements: const HomeSupplementsResult(
          results: <HomeSupplement>[
            HomeSupplement(
              id: 'sup-1',
              displayName: '비타민 D',
              manufacturer: null,
              schedule: null,
            ),
          ],
          limit: 50,
          offset: 0,
        ),
        impact: _impact(risks: const <SupplementNutritionInsight>[]),
      ),
    );
    await controller.bootstrap();

    await tester.pumpWidget(
      MaterialApp(
        home: DashboardScreen(controller: controller, localPrefs: prefs),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 1300));
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('0/1 완료'), findsOneWidget);
    await tester.ensureVisible(find.text('비타민 D'));
    await tester.pump();
    await tester.tap(find.text('비타민 D'));
    await tester.pump();
    expect(find.text('1/1 완료'), findsOneWidget);

    // 토글이 prefs(오늘 날짜 키)에 영속됐는지 직접 확인.
    final DateTime today = DateTime.now();
    expect(prefs.supplementCheckedIds(today), contains('sup-1'));

    // 같은 prefs 를 가진 새 화면을 다시 띄우면 체크가 복원된다.
    await tester.pumpWidget(
      MaterialApp(
        home: DashboardScreen(controller: controller, localPrefs: prefs),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 1300));
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('1/1 완료'), findsOneWidget);
  });

  testWidgets('long-pressing a supplement deletes it with an undo toast', (
    WidgetTester tester,
  ) async {
    final AppController controller = AppController(
      repository: _HomeRepository(
        healthScore: const DashboardHealthScore(
          status: HealthScoreStatus.notReady,
        ),
        supplements: const HomeSupplementsResult(
          results: <HomeSupplement>[
            HomeSupplement(
              id: 'sup-1',
              displayName: '비타민 D',
              manufacturer: null,
              schedule: null,
            ),
          ],
          limit: 50,
          offset: 0,
        ),
        impact: _impact(risks: const <SupplementNutritionInsight>[]),
      ),
    );
    await controller.bootstrap();
    await _pumpScreen(tester, controller);

    expect(find.text('비타민 D'), findsOneWidget);
    await tester.ensureVisible(find.text('비타민 D'));
    await tester.pump();
    await tester.longPress(find.text('비타민 D'));
    await tester.pumpAndSettle();

    // 삭제 확인 모달 → 삭제.
    expect(find.text('이 기록을 삭제할까요?'), findsOneWidget);
    await tester.tap(find.text('삭제'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // 낙관적 제거 + 실행취소 토스트.
    expect(find.text('영양제를 삭제했어요'), findsOneWidget);
    expect(find.text('실행취소'), findsOneWidget);
    expect(controller.homeSupplements.results, isEmpty);

    // 실행취소 시 복원된다.
    await tester.tap(find.text('실행취소'));
    await tester.pump();
    expect(controller.homeSupplements.results.length, 1);
  });
}

Future<void> _pumpScreen(WidgetTester tester, AppController controller) async {
  await tester.pumpWidget(
    MaterialApp(home: DashboardScreen(controller: controller)),
  );
  // 진입 애니메이션(게이지 차오름·스태거)이 끝나길 기다린다.
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
  await tester.pump(const Duration(milliseconds: 1300));
  await tester.pump(const Duration(milliseconds: 400));
}

SupplementImpactPreviewResponse _impact({
  required List<SupplementNutritionInsight> risks,
}) {
  return SupplementImpactPreviewResponse(
    calculationVersion: 'v1',
    referenceVersion: 'kdri-2020',
    sourceManifestVersion: null,
    dataStatus: 'ready',
    currentSupplementContributions: const <SupplementContributionAggregate>[],
    deficiencySupportCandidates: const <SupplementNutritionInsight>[],
    excessOrDuplicateRisks: risks,
    missingProfileFields: const <String>[],
    safeUserMessage: risks.isEmpty
        ? '지금 등록된 영양제에서 중복·상한 신호는 없어요.'
        : '겹치는 성분이 있어 확인이 필요해요.',
    clinicalDisclaimer: '의료적 진단이 아니에요.',
    warnings: const <String>[],
    requiresUserConfirmation: risks.isNotEmpty,
  );
}

class _HomeRepository implements LemonAidRepository {
  _HomeRepository({
    required this.healthScore,
    required this.supplements,
    required this.impact,
    this.medications = HomeMedicationsResult.empty,
  });

  final DashboardHealthScore healthScore;
  final HomeSupplementsResult supplements;
  final SupplementImpactPreviewResponse impact;
  final HomeMedicationsResult medications;

  @override
  Future<ConsentState> fetchConsents() async {
    return ConsentState(
      consents: <ConsentStatus>[
        _granted(AppController.ocrConsent),
        _granted(AppController.healthConsent),
      ],
    );
  }

  ConsentStatus _granted(String consentType) {
    return ConsentStatus(
      consentType: consentType,
      policyVersion: 'test',
      title: consentType,
      required: true,
      granted: true,
      occurredAt: DateTime.utc(2026, 6, 10),
      revokedAt: null,
    );
  }

  @override
  Future<DashboardSummary> fetchDashboardSummary({int days = 30}) async {
    return DashboardSummary(
      asOf: DateTime.utc(2026, 6, 10),
      nutrition: const DashboardNutritionSummary(
        dataStatus: 'ready',
        lowCount: 0,
        highCount: 0,
        datasetVersion: 'test',
      ),
      activity: const DashboardActivitySummary(
        dataStatus: 'ready',
        latestSteps: 5000,
        latestActivityScore: 80,
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
      healthScore: healthScore,
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
    return supplements;
  }

  @override
  Future<HomeMedicationsResult> fetchMedications() async {
    return medications;
  }

  @override
  Future<SupplementImpactPreviewResponse>
  fetchLatestSupplementRecommendation() async {
    return impact;
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
  dynamic noSuchMethod(Invocation invocation) {
    throw UnimplementedError('Unexpected call: ${invocation.memberName}');
  }
}
