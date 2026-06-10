import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/app_controller.dart';
import 'package:lemon_aid_mobile/features/consent/consent_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/dashboard_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/home_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';
import 'package:lemon_aid_mobile/screens/dashboard_screen.dart';

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
    // 영양제가 없으면 상호작용 카드는 미등록 안내 상태.
    expect(find.text('등록된 영양제가 없어요'), findsOneWidget);
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
    currentSupplementContributions:
        const <SupplementContributionAggregate>[],
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
  });

  final DashboardHealthScore healthScore;
  final HomeSupplementsResult supplements;
  final SupplementImpactPreviewResponse impact;

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
  Future<SupplementImpactPreviewResponse>
  fetchLatestSupplementRecommendation() async {
    return impact;
  }

  @override
  void close() {}

  @override
  dynamic noSuchMethod(Invocation invocation) {
    throw UnimplementedError('Unexpected call: ${invocation.memberName}');
  }
}
