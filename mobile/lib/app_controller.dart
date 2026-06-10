import 'dart:async';

import 'package:flutter/foundation.dart';

import 'core/api/api_error.dart';
import 'features/consent/consent_models.dart';
import 'features/dashboard/dashboard_models.dart';
import 'features/dashboard/home_models.dart';
import 'features/supplements/comprehensive_analysis_models.dart';
import 'features/supplements/supplement_models.dart';
import 'features/supplements/supplement_repository.dart';

/// Lifecycle state for an image analysis job started from the camera flow.
enum AnalysisJobPhase {
  /// No image analysis is currently tracked.
  idle,

  /// The backend analysis is still running.
  running,

  /// The backend analysis completed and a result is available.
  completed,

  /// The backend analysis failed.
  failed,
}

/// User-facing state for long-running image analysis.
class AnalysisJobSnapshot {
  /// Creates a tracked analysis job snapshot.
  ///
  /// Args:
  ///   phase: Current analysis lifecycle phase.
  ///   mode: `supplement` or `meal`.
  ///   message: User-facing status text.
  ///   resultRoute: Route that can show the finished analysis result.
  ///   startedAt: Local start timestamp.
  ///   completedAt: Local completion timestamp.
  ///   notificationRead: Whether the completion notification was dismissed.
  const AnalysisJobSnapshot({
    required this.phase,
    this.mode,
    this.message,
    this.resultRoute,
    this.startedAt,
    this.completedAt,
    this.notificationRead = true,
  });

  /// Current analysis lifecycle phase.
  final AnalysisJobPhase phase;

  /// Analysis mode, such as `supplement` or `meal`.
  final String? mode;

  /// User-facing status text.
  final String? message;

  /// Route that can display the analysis result.
  final String? resultRoute;

  /// Local timestamp when the job started.
  final DateTime? startedAt;

  /// Local timestamp when the job completed.
  final DateTime? completedAt;

  /// Whether completion notification has already been consumed.
  final bool notificationRead;

  /// Empty state.
  const AnalysisJobSnapshot.idle()
    : this(phase: AnalysisJobPhase.idle, message: null);

  /// Creates a running job state.
  factory AnalysisJobSnapshot.running({required String mode}) {
    return AnalysisJobSnapshot(
      phase: AnalysisJobPhase.running,
      mode: mode,
      message: '분석을 하고 있어요.',
      resultRoute: '/shell/home/analysis-result?mode=$mode',
      startedAt: DateTime.now(),
      notificationRead: true,
    );
  }

  /// Whether this job is actively running.
  bool get isRunning => phase == AnalysisJobPhase.running;

  /// Whether this job completed and should show a result notification.
  bool get hasUnreadCompletion {
    return phase == AnalysisJobPhase.completed && !notificationRead;
  }

  /// Returns a copy marked as completed.
  AnalysisJobSnapshot completed({required String message}) {
    return AnalysisJobSnapshot(
      phase: AnalysisJobPhase.completed,
      mode: mode,
      message: message,
      resultRoute: resultRoute,
      startedAt: startedAt,
      completedAt: DateTime.now(),
      notificationRead: false,
    );
  }

  /// Returns a copy marked as failed.
  AnalysisJobSnapshot failed({required String message}) {
    return AnalysisJobSnapshot(
      phase: AnalysisJobPhase.failed,
      mode: mode,
      message: message,
      resultRoute: resultRoute,
      startedAt: startedAt,
      completedAt: DateTime.now(),
      notificationRead: true,
    );
  }

  /// Returns a copy with completion notification consumed.
  AnalysisJobSnapshot markNotificationRead() {
    return AnalysisJobSnapshot(
      phase: phase,
      mode: mode,
      message: message,
      resultRoute: resultRoute,
      startedAt: startedAt,
      completedAt: completedAt,
      notificationRead: true,
    );
  }
}

/// User-safe supplement context queued for the chat tab.
class ChatExplanationDraft {
  /// Creates a one-shot chat explanation draft.
  ///
  /// Args:
  ///   id: Monotonic local identifier used to consume the draft once.
  ///   title: Short supplement title shown in chat.
  ///   userPrompt: User-side prompt inserted into the chat transcript.
  ///   assistantMessage: LemonBot-side explanation inserted after the prompt.
  ///   createdAt: Local creation timestamp for traceability.
  const ChatExplanationDraft({
    required this.id,
    required this.title,
    required this.userPrompt,
    required this.assistantMessage,
    required this.createdAt,
  });

  /// Monotonic local identifier used to consume the draft once.
  final int id;

  /// Short supplement title shown in chat.
  final String title;

  /// User-side prompt inserted into the chat transcript.
  final String userPrompt;

  /// LemonBot-side explanation inserted after the prompt.
  final String assistantMessage;

  /// Local creation timestamp for traceability.
  final DateTime createdAt;
}

class _SupplementAnalysisAttempt {
  const _SupplementAnalysisAttempt({
    required this.provider,
    this.preview,
    this.multiPreview,
    this.error,
  });

  final String provider;
  final SupplementAnalysisPreview? preview;
  final SupplementMultiImageAnalysisPreview? multiPreview;
  final Object? error;

  bool get succeeded => preview != null;
}

class _SupplementAnalysisSelection {
  const _SupplementAnalysisSelection({
    required this.provider,
    required this.preview,
    this.multiPreview,
  });

  final String provider;
  final SupplementAnalysisPreview preview;
  final SupplementMultiImageAnalysisPreview? multiPreview;
}

/// Coordinates the minimal mobile demo flow.
class AppController extends ChangeNotifier {
  /// Creates an app controller.
  ///
  /// Args:
  ///   repository: Backend or fake repository implementation.
  AppController({required LemonAidRepository repository})
    : _repository = repository;

  static const String ocrConsent = 'ocr_image_processing';
  static const String healthConsent = 'sensitive_health_analysis';

  final LemonAidRepository _repository;

  bool _busy = false;
  ApiError? _apiError;
  String? _notice;
  ConsentState? _consentState;
  DashboardSummary? _dashboardSummary;
  DashboardHealthScore _healthScore = const DashboardHealthScore(
    status: HealthScoreStatus.notReady,
  );
  HomeMealsResult _recentMeals = HomeMealsResult.empty;
  HomeSupplementsResult _homeSupplements = HomeSupplementsResult.empty;
  bool _homeDataLoading = false;
  bool _homeMealsFailed = false;
  bool _homeSupplementsFailed = false;
  bool _homeImpactFailed = false;
  SupplementAnalysisPreview? _analysisPreview;
  SupplementMultiImageAnalysisPreview? _multiImageAnalysisPreview;
  MealImageAnalysisPreview? _mealAnalysisPreview;
  ComprehensiveDietAnalysis? _comprehensiveDietAnalysis;
  MealRecordResponse? _lastRegisteredMeal;
  UserSupplementResponse? _lastRegisteredSupplement;
  UserSupplementCreate? _lastRegisteredSupplementRequest;
  SupplementImpactPreviewResponse? _supplementImpactPreview;
  SupplementRecommendationExplainResponse? _supplementExplanation;
  ChatExplanationDraft? _pendingChatExplanationDraft;
  String? _lastRequestedOcrProvider;
  AnalysisJobSnapshot _analysisJob = const AnalysisJobSnapshot.idle();
  int _analysisJobSerial = 0;
  int _chatDraftSerial = 0;
  bool _consentRequired = false;

  static const List<String> _automaticOcrProviders = <String>[
    'configured',
    'paddleocr',
    'clova',
    'google_vision',
  ];

  /// Whether a network operation is in progress.
  bool get busy => _busy;

  /// Last API error, if any.
  ApiError? get apiError => _apiError;

  /// Last user-safe notice.
  String? get notice => _notice;

  /// Whether the last action was blocked because a required consent is missing.
  ///
  /// When true, the UI should route the user to the consent screen and let them
  /// grant the missing bucket (e.g. sensitive health analysis) before retrying.
  bool get consentRequired => _consentRequired;

  /// Current consent state.
  ConsentState? get consentState => _consentState;

  /// Current dashboard summary.
  DashboardSummary? get dashboardSummary => _dashboardSummary;

  /// Latest parsed daily health score block (not_ready when unavailable).
  DashboardHealthScore get healthScore => _healthScore;

  /// Recently loaded meals (last 7 days window for the home tab).
  HomeMealsResult get recentMeals => _recentMeals;

  /// Current-user registered supplements for the home tab.
  HomeSupplementsResult get homeSupplements => _homeSupplements;

  /// Whether the home blocks (meals/supplements/impact) are loading.
  bool get homeDataLoading => _homeDataLoading;

  /// Whether the meals block failed to load on the last attempt.
  bool get homeMealsFailed => _homeMealsFailed;

  /// Whether the supplements block failed to load on the last attempt.
  bool get homeSupplementsFailed => _homeSupplementsFailed;

  /// Whether the supplement interaction block failed to load on the last attempt.
  bool get homeImpactFailed => _homeImpactFailed;

  /// Meals eaten on [day] (client-side filter over the loaded window).
  List<HomeMeal> mealsForDay(DateTime day) {
    return _recentMeals.results.where((HomeMeal meal) {
      final DateTime? eatenAt = meal.eatenAt;
      if (eatenAt == null) return false;
      final DateTime local = eatenAt.toLocal();
      return local.year == day.year &&
          local.month == day.month &&
          local.day == day.day;
    }).toList(growable: false);
  }

  /// Whether any meal record exists for [day].
  bool hasMealRecord(DateTime day) => mealsForDay(day).isNotEmpty;

  /// Current supplement analysis preview.
  SupplementAnalysisPreview? get analysisPreview => _analysisPreview;

  /// Current multi-image supplement analysis preview, if the batch endpoint was used.
  SupplementMultiImageAnalysisPreview? get multiImageAnalysisPreview =>
      _multiImageAnalysisPreview;

  /// Current meal image analysis preview.
  MealImageAnalysisPreview? get mealAnalysisPreview => _mealAnalysisPreview;

  /// Latest comprehensive diet analysis (C-hybrid result surface), if loaded.
  ///
  /// Null when not requested or when the request failed; the result screen
  /// hides the score/insight area in that case and keeps showing base info.
  ComprehensiveDietAnalysis? get comprehensiveDietAnalysis =>
      _comprehensiveDietAnalysis;

  /// Most recently confirmed meal record.
  MealRecordResponse? get lastRegisteredMeal => _lastRegisteredMeal;

  /// Most recently registered supplement.
  UserSupplementResponse? get lastRegisteredSupplement =>
      _lastRegisteredSupplement;

  /// User-confirmed request that produced the most recently registered supplement.
  UserSupplementCreate? get lastRegisteredSupplementRequest =>
      _lastRegisteredSupplementRequest;

  /// Latest deterministic supplement impact preview.
  SupplementImpactPreviewResponse? get supplementImpactPreview =>
      _supplementImpactPreview;

  /// Latest safe supplement explanation.
  SupplementRecommendationExplainResponse? get supplementExplanation =>
      _supplementExplanation;

  /// One-shot supplement explanation draft waiting for the chat tab.
  ChatExplanationDraft? get pendingChatExplanationDraft =>
      _pendingChatExplanationDraft;

  /// Most recent mobile-selected OCR provider for smoke-test diagnostics.
  String? get lastRequestedOcrProvider => _lastRequestedOcrProvider;

  /// Current long-running image analysis job, if any.
  AnalysisJobSnapshot get analysisJob => _analysisJob;

  /// Whether a completed analysis result has not been opened yet.
  bool get hasUnreadAnalysisCompletion => _analysisJob.hasUnreadCompletion;

  /// Result route for the latest completed analysis, if available.
  String? get completedAnalysisRoute {
    return _analysisJob.hasUnreadCompletion ? _analysisJob.resultRoute : null;
  }

  /// Whether the two P2 demo consents are granted.
  bool get hasMinimumConsents {
    final ConsentState? state = _consentState;
    return state != null &&
        state.isGranted(ocrConsent) &&
        state.isGranted(healthConsent);
  }

  /// Loads consent state and dashboard summary when possible.
  Future<void> bootstrap() async {
    await _run(() async {
      _consentState = await _repository.fetchConsents();
      if (hasMinimumConsents) {
        _dashboardSummary = await _repository.fetchDashboardSummary();
        _healthScore = _dashboardSummary!.healthScore;
        await _loadHomeData();
      }
    });
  }

  /// Grants the P2 minimum consents and refreshes the dashboard.
  Future<void> grantMinimumConsents() async {
    await _run(() async {
      await _repository.grantConsent(ocrConsent);
      await _repository.grantConsent(healthConsent);
      _consentState = await _repository.fetchConsents();
      _dashboardSummary = await _repository.fetchDashboardSummary();
      _notice = 'Required demo consents are active.';
    });
  }

  /// Refreshes the dashboard summary and home data blocks.
  Future<void> refreshDashboard() async {
    await _run(() async {
      _dashboardSummary = await _repository.fetchDashboardSummary();
      _healthScore = _dashboardSummary!.healthScore;
      await _loadHomeData();
      _notice = 'Dashboard refreshed.';
    });
  }

  /// Loads today's meals, supplements, and the interaction impact preview.
  ///
  /// Each block is independent: a single block failing does not fail the whole
  /// home load. Per-block failure flags drive empty/error states in the UI.
  Future<void> _loadHomeData() async {
    _homeDataLoading = true;
    _homeMealsFailed = false;
    _homeSupplementsFailed = false;
    _homeImpactFailed = false;
    notifyListeners();

    final DateTime now = DateTime.now();
    final DateTime weekStart = DateTime(
      now.year,
      now.month,
      now.day,
    ).subtract(const Duration(days: 6));

    await Future.wait<void>(<Future<void>>[
      _loadMealsBlock(weekStart),
      _loadSupplementsBlock(),
      _loadImpactBlock(),
    ]);

    _homeDataLoading = false;
    notifyListeners();
  }

  Future<void> _loadMealsBlock(DateTime from) async {
    try {
      _recentMeals = await _repository.fetchMeals(from: from, limit: 100);
    } catch (_) {
      _homeMealsFailed = true;
    }
  }

  Future<void> _loadSupplementsBlock() async {
    try {
      _homeSupplements = await _repository.fetchSupplements(limit: 100);
    } catch (_) {
      _homeSupplementsFailed = true;
    }
  }

  Future<void> _loadImpactBlock() async {
    try {
      _supplementImpactPreview = await _repository
          .fetchLatestSupplementRecommendation();
    } catch (_) {
      _homeImpactFailed = true;
    }
  }

  /// Uploads a supplement label image and stores the preview.
  Future<void> analyzeImage(
    String imagePath, {
    String ocrProvider = 'configured',
  }) async {
    await _run(() async {
      final _SupplementAnalysisSelection selection =
          await _analyzeSupplementImageAutomatically(imagePath);
      _lastRequestedOcrProvider = selection.provider;
      _analysisPreview = selection.preview;
      _multiImageAnalysisPreview = null;
      _mealAnalysisPreview = null;
      _lastRegisteredSupplement = null;
      _lastRegisteredSupplementRequest = null;
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
      _comprehensiveDietAnalysis = null;
      _pendingChatExplanationDraft = null;
      _notice = 'Supplement preview is ready for review.';
    });
  }

  /// Uploads a multi-image supplement label batch and stores its review preview.
  Future<void> analyzeImages(
    List<SupplementImageUpload> images, {
    String ocrProvider = 'configured',
  }) async {
    await _run(() async {
      final _SupplementAnalysisSelection selection =
          await _analyzeSupplementImagesAutomatically(images);
      _lastRequestedOcrProvider = selection.provider;
      _multiImageAnalysisPreview = selection.multiPreview;
      _analysisPreview = selection.preview;
      _mealAnalysisPreview = null;
      _lastRegisteredSupplement = null;
      _lastRegisteredSupplementRequest = null;
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
      _comprehensiveDietAnalysis = null;
      _pendingChatExplanationDraft = null;
      _notice = 'Supplement image batch is ready for review.';
    });
  }

  /// Starts supplement image analysis and lets the UI navigate away immediately.
  Future<void> startSupplementImageAnalysis(String imagePath) async {
    if (_analysisJob.isRunning) {
      _apiError = const ApiError(
        statusCode: 0,
        message: '이미 분석이 진행 중입니다. 완료 후 다시 시도해주세요.',
      );
      notifyListeners();
      return;
    }
    final int serial = _beginAnalysisJob('supplement');
    unawaited(_finishSupplementImageAnalysis(serial, imagePath));
  }

  /// Starts multi-image supplement analysis without blocking navigation.
  Future<void> startSupplementImageBatchAnalysis(
    List<SupplementImageUpload> images,
  ) async {
    if (_analysisJob.isRunning) {
      _apiError = const ApiError(
        statusCode: 0,
        message: '이미 분석이 진행 중입니다. 완료 후 다시 시도해주세요.',
      );
      notifyListeners();
      return;
    }
    final int serial = _beginAnalysisJob('supplement');
    unawaited(_finishSupplementImageBatchAnalysis(serial, images));
  }

  /// Starts meal image analysis without blocking navigation.
  Future<void> startMealImageAnalysis(String imagePath) async {
    if (_analysisJob.isRunning) {
      _apiError = const ApiError(
        statusCode: 0,
        message: '이미 분석이 진행 중입니다. 완료 후 다시 시도해주세요.',
      );
      notifyListeners();
      return;
    }
    final int serial = _beginAnalysisJob('meal');
    unawaited(_finishMealImageAnalysis(serial, imagePath));
  }

  /// Marks the current completion notification as read.
  void markAnalysisCompletionRead() {
    if (!_analysisJob.hasUnreadCompletion) return;
    _analysisJob = _analysisJob.markNotificationRead();
    notifyListeners();
  }

  /// Rebuilds the merged preview for the current multi-image analysis session.
  Future<void> finalizeAnalysisSession(String analysisGroupId) async {
    await _run(() async {
      _multiImageAnalysisPreview = await _repository
          .finalizeSupplementAnalysisSession(analysisGroupId);
      _analysisPreview = _multiImageAnalysisPreview?.primaryPreview;
      _mealAnalysisPreview = null;
      _lastRegisteredSupplement = null;
      _lastRegisteredSupplementRequest = null;
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
      _comprehensiveDietAnalysis = null;
      _pendingChatExplanationDraft = null;
      _notice = 'Supplement image batch was finalized for review.';
    });
  }

  /// Uploads a meal image and stores its review-only food detection preview.
  Future<void> analyzeMealImage(
    String imagePath, {
    String mealType = 'unknown',
  }) async {
    await _run(() async {
      _mealAnalysisPreview = await _repository.analyzeMealImage(
        imagePath,
        mealType: mealType,
      );
      _analysisPreview = null;
      _multiImageAnalysisPreview = null;
      _lastRegisteredSupplement = null;
      _lastRegisteredSupplementRequest = null;
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
      _comprehensiveDietAnalysis = null;
      _pendingChatExplanationDraft = null;
      _notice = 'Meal image preview is ready for review.';
    });
    await _refreshComprehensiveDietAnalysis();
  }

  /// Best-effort comprehensive diet analysis for the current meal preview.
  ///
  /// Converts the meal nutrition totals into nutrient rows and asks the backend
  /// for the C-hybrid result. Failures are swallowed so the result screen keeps
  /// working with the base meal preview when the endpoint is unavailable.
  Future<void> _refreshComprehensiveDietAnalysis() async {
    final MealImageAnalysisPreview? preview = _mealAnalysisPreview;
    if (preview == null) return;
    final List<Map<String, Object?>> ingredients =
        _comprehensiveIngredientsFromMeal(preview);
    if (ingredients.isEmpty) return;
    try {
      final ComprehensiveDietAnalysis analysis = await _repository
          .analyzeComprehensive(ingredients: ingredients);
      _comprehensiveDietAnalysis = analysis;
      notifyListeners();
    } on ApiError {
      // Score area stays hidden; base meal info still renders.
    } on FormatException {
      // Score area stays hidden; base meal info still renders.
    } on UnimplementedError {
      // Repository without the endpoint (e.g. tests) keeps the base layout.
    }
  }

  /// Maps a meal preview's nutrition totals to comprehensive nutrient rows.
  List<Map<String, Object?>> _comprehensiveIngredientsFromMeal(
    MealImageAnalysisPreview preview,
  ) {
    final Object? totals = preview.nutritionEstimateSummary['totals'];
    final Map<String, Object?> totalsMap = totals is Map<String, Object?>
        ? totals
        : totals is Map<Object?, Object?>
        ? Map<String, Object?>.from(totals)
        : const <String, Object?>{};
    const List<List<String>> nutrientFields = <List<String>>[
      <String>['carb_g', 'carbohydrate_g', '탄수화물', 'g'],
      <String>['protein_g', 'protein_g', '단백질', 'g'],
      <String>['fat_g', 'fat_g', '지방', 'g'],
      <String>['sodium_mg', 'sodium_mg', '나트륨', 'mg'],
    ];
    final List<Map<String, Object?>> rows = <Map<String, Object?>>[];
    for (final List<String> field in nutrientFields) {
      final Object? raw = totalsMap[field[0]];
      final double? amount = raw is num ? raw.toDouble() : null;
      if (amount == null) continue;
      rows.add(
        ComprehensiveIngredientInput(
          displayName: field[2],
          nutrientCode: field[1],
          amount: amount,
          unit: field[3],
        ).toJson(),
      );
    }
    return rows;
  }

  /// Confirms the current meal image preview after user review.
  Future<void> confirmMealImagePreview(MealConfirmationRequest request) async {
    final MealImageAnalysisPreview? preview = _mealAnalysisPreview;
    if (preview == null) {
      _apiError = const ApiError(
        statusCode: 0,
        message: 'Analyze a meal image before confirming it.',
      );
      notifyListeners();
      return;
    }

    await _run(() async {
      _lastRegisteredMeal = await _repository.confirmMealImagePreview(
        preview.mealId,
        request,
      );
      _mealAnalysisPreview = null;
      _analysisPreview = null;
      _multiImageAnalysisPreview = null;
      _lastRegisteredSupplement = null;
      _lastRegisteredSupplementRequest = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
      _comprehensiveDietAnalysis = null;
      _pendingChatExplanationDraft = null;
      _dashboardSummary = await _repository.fetchDashboardSummary();
      _notice = 'Meal record saved and dashboard refreshed.';
    });
  }

  /// Parses user-reviewed OCR text for the current preview.
  Future<void> parseOcrText(String ocrText) async {
    final SupplementAnalysisPreview? preview = _analysisPreview;
    if (preview == null) {
      _apiError = const ApiError(
        statusCode: 0,
        message: 'Upload an image before submitting OCR text.',
      );
      notifyListeners();
      return;
    }

    await _run(() async {
      _analysisPreview = await _repository.parseOcrText(
        analysisId: preview.analysisId,
        request: SupplementOCRTextParseRequest(ocrText: ocrText),
      );
      _notice = 'OCR text was parsed. Confirm fields before registration.';
    });
  }

  /// Registers a user-confirmed supplement and optionally refreshes insights.
  Future<void> registerSupplement(
    UserSupplementCreate request, {
    bool refreshImpact = false,
    bool explainWithLocalLlm = false,
  }) async {
    _consentRequired = false;
    // Confirming a supplement persists sensitive health data, so the backend
    // requires SENSITIVE_HEALTH_ANALYSIS consent (analyze only needs OCR
    // consent). When consent state is already loaded and health consent is
    // known-missing, surface an actionable message instead of a silent 403.
    // When state is not loaded yet, proceed and let the 403 mapping below
    // route to consent re-entry.
    final ConsentState? consent = _consentState;
    if (consent != null && !consent.isGranted(healthConsent)) {
      _apiError = const ApiError(
        statusCode: 403,
        message: '영양제 저장에는 민감 건강정보 분석 동의가 필요해요. 동의 화면에서 동의한 뒤 다시 저장해주세요.',
      );
      _consentRequired = true;
      _notice = null;
      notifyListeners();
      return;
    }
    await _run(() async {
      _lastRegisteredSupplement = await _repository.registerSupplement(request);
      _lastRegisteredSupplementRequest = request;
      _analysisPreview = null;
      _multiImageAnalysisPreview = null;
      _mealAnalysisPreview = null;
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
      _comprehensiveDietAnalysis = null;
      _pendingChatExplanationDraft = null;
      _dashboardSummary = await _repository.fetchDashboardSummary();
      _notice = 'Supplement registered and dashboard refreshed.';
      if (refreshImpact || explainWithLocalLlm) {
        await _refreshPostRegistrationInsights(
          explainWithLocalLlm: explainWithLocalLlm,
        );
      }
    });
    // Defensive mapping when local consent state was stale: a 403 from the
    // confirm endpoint is consent-driven, so route the user to consent re-entry.
    if (_apiError?.statusCode == 403) {
      _consentRequired = true;
      notifyListeners();
    }
  }

  /// Calculates current supplement impact after registration or refresh.
  Future<void> previewSupplementImpact({
    SupplementImpactPreviewRequest request =
        const SupplementImpactPreviewRequest(),
  }) async {
    await _run(() async {
      _supplementImpactPreview = await _repository.previewSupplementImpact(
        request,
      );
      _supplementExplanation = null;
      _notice = 'Supplement impact check is ready.';
    });
  }

  /// Fetches the latest deterministic supplement recommendation view.
  Future<void> refreshSupplementRecommendation() async {
    await _run(() async {
      _supplementImpactPreview = await _repository
          .fetchLatestSupplementRecommendation();
      _supplementExplanation = null;
      _notice = 'Supplement check refreshed.';
    });
  }

  /// Builds a safe deterministic explanation for the current impact preview.
  Future<void> explainSupplementRecommendation({
    bool useLocalLlm = false,
  }) async {
    final SupplementImpactPreviewResponse? preview = _supplementImpactPreview;
    if (preview == null) {
      _apiError = const ApiError(
        statusCode: 0,
        message:
            'Run a supplement impact check before requesting an explanation.',
      );
      notifyListeners();
      return;
    }

    await _run(() async {
      _supplementExplanation = await _repository
          .explainSupplementRecommendation(preview, useLocalLlm: useLocalLlm);
      _notice = 'Supplement check explanation is ready.';
    });
  }

  /// Builds a safe explanation for the current analysis preview before saving.
  Future<void> explainSupplementAnalysis({bool useLocalLlm = false}) async {
    final SupplementAnalysisPreview? preview = _analysisPreview;
    if (preview == null) {
      _apiError = const ApiError(
        statusCode: 0,
        message: 'Analyze an image before requesting an explanation.',
      );
      notifyListeners();
      return;
    }

    await _run(() async {
      _supplementExplanation = await _repository.explainSupplementAnalysis(
        preview.analysisId,
        useLocalLlm: useLocalLlm,
      );
      _notice = 'Analysis explanation is ready.';
    });
  }

  /// Queues the latest supplement context so the chat tab can explain it.
  ///
  /// Returns true when a draft was created. The draft intentionally contains
  /// only user-confirmed fields and safe summaries, not raw OCR text or
  /// provider payloads.
  bool queueSupplementExplanationForChat() {
    final ChatExplanationDraft? draft = _buildSupplementChatDraft();
    if (draft == null) {
      _apiError = const ApiError(
        statusCode: 0,
        message: '저장된 영양제 정보가 없어 챗으로 설명을 보낼 수 없어요.',
      );
      _notice = null;
      notifyListeners();
      return false;
    }
    _pendingChatExplanationDraft = draft;
    _apiError = null;
    _notice = '챗으로 영양제 정보를 보냈어요.';
    notifyListeners();
    return true;
  }

  /// Clears a chat explanation draft after the chat screen consumed it.
  void markChatExplanationDraftDelivered(int id) {
    if (_pendingChatExplanationDraft?.id != id) return;
    _pendingChatExplanationDraft = null;
    notifyListeners();
  }

  /// Clears the current preview without sending data to the backend.
  void clearSupplementFlow() {
    _analysisPreview = null;
    _multiImageAnalysisPreview = null;
    _mealAnalysisPreview = null;
    _lastRegisteredMeal = null;
    _lastRegisteredSupplement = null;
    _lastRegisteredSupplementRequest = null;
    _supplementImpactPreview = null;
    _supplementExplanation = null;
    _pendingChatExplanationDraft = null;
    _lastRequestedOcrProvider = null;
    if (!_analysisJob.isRunning) {
      _analysisJob = const AnalysisJobSnapshot.idle();
    }
    _apiError = null;
    _notice = null;
    _consentRequired = false;
    notifyListeners();
  }

  /// Clears transient error and notice messages.
  void clearMessages() {
    _apiError = null;
    _notice = null;
    _consentRequired = false;
    notifyListeners();
  }

  Future<void> _run(Future<void> Function() task) async {
    _busy = true;
    _apiError = null;
    _notice = null;
    _consentRequired = false;
    notifyListeners();
    try {
      await task();
    } on ApiError catch (error) {
      _apiError = error;
    } on FormatException catch (error) {
      _apiError = ApiError(statusCode: 0, message: error.message);
    } catch (error) {
      _apiError = ApiError(statusCode: 0, message: error.toString());
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  int _beginAnalysisJob(String mode) {
    _analysisJobSerial += 1;
    _analysisPreview = null;
    _multiImageAnalysisPreview = null;
    _mealAnalysisPreview = null;
    _lastRegisteredSupplement = null;
    _lastRegisteredSupplementRequest = null;
    _lastRegisteredMeal = null;
    _supplementImpactPreview = null;
    _supplementExplanation = null;
    _pendingChatExplanationDraft = null;
    _analysisJob = AnalysisJobSnapshot.running(mode: mode);
    _apiError = null;
    _notice = '분석을 하고 있어요.';
    notifyListeners();
    return _analysisJobSerial;
  }

  bool _isCurrentAnalysisJob(int serial) {
    return serial == _analysisJobSerial && _analysisJob.isRunning;
  }

  Future<void> _finishSupplementImageAnalysis(
    int serial,
    String imagePath,
  ) async {
    try {
      final _SupplementAnalysisSelection selection =
          await _analyzeSupplementImageAutomatically(imagePath);
      if (!_isCurrentAnalysisJob(serial)) return;
      _lastRequestedOcrProvider = selection.provider;
      _analysisPreview = selection.preview;
      _multiImageAnalysisPreview = null;
      _mealAnalysisPreview = null;
      _lastRegisteredSupplement = null;
      _lastRegisteredSupplementRequest = null;
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
      _comprehensiveDietAnalysis = null;
      _pendingChatExplanationDraft = null;
      _apiError = null;
      _notice = '분석이 완료 되었어요.';
      _analysisJob = _analysisJob.completed(message: _notice!);
    } catch (error) {
      if (!_isCurrentAnalysisJob(serial)) return;
      _apiError = _apiErrorFromObject(error);
      _notice = '분석을 완료하지 못했어요.';
      _analysisJob = _analysisJob.failed(message: _notice!);
    } finally {
      notifyListeners();
    }
  }

  Future<void> _finishSupplementImageBatchAnalysis(
    int serial,
    List<SupplementImageUpload> images,
  ) async {
    try {
      final _SupplementAnalysisSelection selection =
          await _analyzeSupplementImagesAutomatically(images);
      if (!_isCurrentAnalysisJob(serial)) return;
      _lastRequestedOcrProvider = selection.provider;
      _multiImageAnalysisPreview = selection.multiPreview;
      _analysisPreview = selection.preview;
      _mealAnalysisPreview = null;
      _lastRegisteredSupplement = null;
      _lastRegisteredSupplementRequest = null;
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
      _comprehensiveDietAnalysis = null;
      _pendingChatExplanationDraft = null;
      _apiError = null;
      _notice = '분석이 완료 되었어요.';
      _analysisJob = _analysisJob.completed(message: _notice!);
    } catch (error) {
      if (!_isCurrentAnalysisJob(serial)) return;
      _apiError = _apiErrorFromObject(error);
      _notice = '분석을 완료하지 못했어요.';
      _analysisJob = _analysisJob.failed(message: _notice!);
    } finally {
      notifyListeners();
    }
  }

  Future<void> _finishMealImageAnalysis(int serial, String imagePath) async {
    try {
      _mealAnalysisPreview = await _repository.analyzeMealImage(imagePath);
      if (!_isCurrentAnalysisJob(serial)) return;
      _analysisPreview = null;
      _multiImageAnalysisPreview = null;
      _lastRegisteredSupplement = null;
      _lastRegisteredSupplementRequest = null;
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
      _comprehensiveDietAnalysis = null;
      _pendingChatExplanationDraft = null;
      _apiError = null;
      _notice = '분석이 완료 되었어요.';
      _analysisJob = _analysisJob.completed(message: _notice!);
    } catch (error) {
      if (!_isCurrentAnalysisJob(serial)) return;
      _apiError = _apiErrorFromObject(error);
      _notice = '분석을 완료하지 못했어요.';
      _analysisJob = _analysisJob.failed(message: _notice!);
    } finally {
      notifyListeners();
    }
  }

  Future<_SupplementAnalysisSelection> _analyzeSupplementImageAutomatically(
    String imagePath,
  ) async {
    final List<_SupplementAnalysisAttempt> attempts = await Future.wait(
      _automaticOcrProviders.map((String provider) async {
        try {
          final SupplementAnalysisPreview preview = await _repository
              .analyzeSupplementImage(imagePath, ocrProvider: provider);
          return _SupplementAnalysisAttempt(
            provider: provider,
            preview: preview,
          );
        } catch (error) {
          return _SupplementAnalysisAttempt(provider: provider, error: error);
        }
      }),
    );
    final _SupplementAnalysisAttempt attempt = _selectBestSupplementAttempt(
      attempts,
    );
    return _SupplementAnalysisSelection(
      provider: attempt.provider,
      preview: attempt.preview!,
    );
  }

  Future<_SupplementAnalysisSelection> _analyzeSupplementImagesAutomatically(
    List<SupplementImageUpload> images,
  ) async {
    final List<_SupplementAnalysisAttempt> attempts = await Future.wait(
      _automaticOcrProviders.map((String provider) async {
        try {
          final SupplementMultiImageAnalysisPreview multiPreview =
              await _repository.analyzeSupplementImages(
                images,
                ocrProvider: provider,
              );
          final SupplementAnalysisPreview? preview =
              multiPreview.primaryPreview;
          if (preview == null) {
            throw const FormatException(
              'Supplement analysis returned no preview.',
            );
          }
          return _SupplementAnalysisAttempt(
            provider: provider,
            preview: preview,
            multiPreview: multiPreview,
          );
        } catch (error) {
          return _SupplementAnalysisAttempt(provider: provider, error: error);
        }
      }),
    );
    final _SupplementAnalysisAttempt attempt = _selectBestSupplementAttempt(
      attempts,
    );
    return _SupplementAnalysisSelection(
      provider: attempt.provider,
      preview: attempt.preview!,
      multiPreview: attempt.multiPreview,
    );
  }

  _SupplementAnalysisAttempt _selectBestSupplementAttempt(
    List<_SupplementAnalysisAttempt> attempts,
  ) {
    final List<_SupplementAnalysisAttempt> successful = attempts
        .where((_SupplementAnalysisAttempt attempt) => attempt.succeeded)
        .toList(growable: false);
    if (successful.isEmpty) {
      final Object? firstError = attempts
          .map((_SupplementAnalysisAttempt attempt) => attempt.error)
          .whereType<Object>()
          .firstOrNull;
      if (firstError != null) throw firstError;
      throw const FormatException('Supplement analysis returned no results.');
    }
    successful.sort((
      _SupplementAnalysisAttempt left,
      _SupplementAnalysisAttempt right,
    ) {
      final int scoreCompare = _scoreSupplementPreview(
        right.preview!,
      ).compareTo(_scoreSupplementPreview(left.preview!));
      if (scoreCompare != 0) return scoreCompare;
      return _providerPriority(
        left.provider,
      ).compareTo(_providerPriority(right.provider));
    });
    return successful.first;
  }

  int _providerPriority(String provider) {
    final int index = _automaticOcrProviders.indexOf(provider);
    return index < 0 ? _automaticOcrProviders.length : index;
  }

  int _scoreSupplementPreview(SupplementAnalysisPreview preview) {
    final SupplementImagePipelineMetadata pipeline = preview.pipelineMetadata;
    final Set<String> missingSections = <String>{
      ...preview.missingRequiredSections,
      ...pipeline.missingRequiredSections,
    };
    int score = 0;
    score += preview.ingredientCandidates.length * 1000;
    score += preview.labelSections.length * 120;
    score += preview.evidenceSpans.length * 30;
    score += pipeline.sectionCount * 80;
    score += pipeline.roiCount * 30;
    if (pipeline.ocrTextPresent) score += 150;
    if (pipeline.visionRoiUsed) score += 90;
    if (pipeline.llmParserUsed) score += 80;
    if (preview.parsedProduct.productName?.trim().isNotEmpty == true) {
      score += 120;
    }
    score += switch (pipeline.ocrConfidenceBucket) {
      'high' => 90,
      'medium' => 45,
      'low' => -30,
      _ => 0,
    };
    if (missingSections.contains('supplement_facts')) score -= 650;
    if (missingSections.contains('ingredients')) score -= 650;
    if (preview.actionRequired == 'additional_label_image_required') {
      score -= 450;
    } else if (preview.actionRequired == 'blocked') {
      score -= 900;
    } else if (preview.actionRequired == 'none') {
      score += 120;
    }
    final Set<String> retakeReasons =
        preview.imageQualityReport?.retakeReasons.toSet() ?? <String>{};
    if (retakeReasons.contains('cover_only')) score -= 500;
    if (retakeReasons.contains('partial_table')) score -= 350;
    return score;
  }

  ChatExplanationDraft? _buildSupplementChatDraft() {
    final UserSupplementResponse? registered = _lastRegisteredSupplement;
    final UserSupplementCreate? request = _lastRegisteredSupplementRequest;
    final SupplementAnalysisPreview? analysis = _analysisPreview;
    if (registered == null && request == null && analysis == null) {
      return null;
    }

    final String title = _firstNonEmpty(<String?>[
      registered?.displayName,
      request?.displayName,
      analysis?.parsedProduct.productName,
      '영양제',
    ])!;
    final List<String> contextLines = _supplementChatContextLines(
      request: request,
      analysis: analysis,
    );
    final String prompt =
        '$title 성분과 함유량을 다시 정리하고, 내 건강 정보 기준으로 섭취 주의점을 쉽게 설명해줘.';
    final List<String> answer = <String>[
      '전달받은 $title 정보를 기준으로 정리할게요.',
      '',
      '성분과 함유량',
      ..._supplementChatIngredientLines(request: request, analysis: analysis),
      '',
      '내 정보 기준 확인',
      ..._supplementChatImpactLines(),
      '',
      '주의사항',
      ..._supplementChatPrecautionLines(request: request, analysis: analysis),
      '',
      if (_supplementExplanation != null) ...<String>[
        _supplementExplanation!.safeUserMessage,
        for (final String bullet in _supplementExplanation!.explanationBullets)
          '· $bullet',
        ..._supplementChatSourceLines(_supplementExplanation!),
      ],
      for (final String line in contextLines) '· $line',
      '의료적 진단·처방이 아닌 건강관리 참고 정보예요. 복용 중인 약이나 질환이 있으면 의사·약사와 확인해주세요.',
    ];

    _chatDraftSerial += 1;
    return ChatExplanationDraft(
      id: _chatDraftSerial,
      title: title,
      userPrompt: prompt,
      assistantMessage: answer.join('\n'),
      createdAt: DateTime.now(),
    );
  }

  List<String> _supplementChatSourceLines(
    SupplementRecommendationExplainResponse explanation,
  ) {
    if (explanation.sourceCitations.isEmpty) {
      return const <String>[];
    }
    return <String>[
      '',
      '출처',
      for (final SupplementExplanationSourceCitation citation
          in explanation.sourceCitations.take(4))
        '· ${citation.title} (${citation.sourcePath})',
    ];
  }

  List<String> _supplementChatContextLines({
    required UserSupplementCreate? request,
    required SupplementAnalysisPreview? analysis,
  }) {
    final List<String> lines = <String>[];
    if (request != null) {
      if (request.manufacturer?.trim().isNotEmpty == true) {
        lines.add('제조사: ${request.manufacturer!.trim()}');
      }
      if (request.ingredients.isEmpty) {
        lines.add('성분: 등록된 성분 후보가 부족해 라벨 재촬영 또는 직접 입력이 필요해요.');
      } else {
        lines.add(
          '성분: ${request.ingredients.map(_formatConfirmedIngredient).join(', ')}',
        );
      }
      lines.add('섭취량: ${_formatServing(request.serving)}');
      final SupplementIntakeSchedule? schedule = request.intakeSchedule;
      if (schedule != null) {
        lines.add('섭취 방법: ${_formatIntakeSchedule(schedule)}');
      }
      if (request.precautionSnapshot.isEmpty) {
        lines.add('주의사항: 라벨에서 확인된 주의 문구가 부족해요.');
      } else {
        lines.add('주의사항: ${request.precautionSnapshot.take(3).join(' / ')}');
      }
      return lines;
    }

    if (analysis != null) {
      final String? productName = analysis.parsedProduct.productName;
      if (productName?.trim().isNotEmpty == true) {
        lines.add('제품명 후보: ${productName!.trim()}');
      }
      if (analysis.ingredientCandidates.isEmpty) {
        lines.add('성분: OCR 성분 후보가 비어 있어 더 선명한 성분표 사진이 필요해요.');
      } else {
        lines.add(
          '성분 후보: ${analysis.ingredientCandidates.map(_formatPreviewIngredient).join(', ')}',
        );
      }
      if (analysis.precautions.isEmpty) {
        lines.add('주의사항: 주의사항 영역이 비어 있어 추가 촬영이 필요해요.');
      } else {
        lines.add(
          '주의사항 후보: ${analysis.precautions.map((SupplementPreviewPrecaution item) => item.text).take(3).join(' / ')}',
        );
      }
    }
    return lines;
  }

  List<String> _supplementChatIngredientLines({
    required UserSupplementCreate? request,
    required SupplementAnalysisPreview? analysis,
  }) {
    final List<String> lines = <String>[];
    if (request != null) {
      for (final UserSupplementIngredientInput ingredient
          in request.ingredients.take(8)) {
        lines.add('· ${_formatConfirmedIngredientForChat(ingredient)}');
      }
      if (lines.isEmpty) {
        lines.add('· 저장된 성분이 부족해 라벨 재촬영 또는 직접 입력이 필요해요.');
      }
      return lines;
    }
    if (analysis != null) {
      for (final SupplementIngredientCandidate ingredient
          in analysis.ingredientCandidates.take(8)) {
        lines.add('· ${_formatPreviewIngredientForChat(ingredient)}');
      }
    }
    if (lines.isEmpty) {
      lines.add('· 성분 후보가 비어 있어 더 선명한 성분표 사진이 필요해요.');
    }
    return lines;
  }

  List<String> _supplementChatImpactLines() {
    final SupplementImpactPreviewResponse? preview = _supplementImpactPreview;
    if (preview == null) {
      return <String>[
        '· 건강 정보 DB와 연결한 영향도 계산은 아직 완료되지 않았어요.',
        '· 우선 라벨에서 사용자가 확인한 성분 기준으로 참고 설명만 제공합니다.',
      ];
    }
    final List<String> lines = <String>['· ${preview.safeUserMessage}'];
    if (preview.excessOrDuplicateRisks.isNotEmpty) {
      lines.add(
        '· 중복·상한 확인 필요: ${preview.excessOrDuplicateRisks.map(_formatInsightForChat).take(3).join(' / ')}',
      );
    } else {
      lines.add('· 현재 계산 결과에서 중복·상한 위험 신호는 표시되지 않았어요.');
    }
    if (preview.deficiencySupportCandidates.isNotEmpty) {
      lines.add(
        '· 부족 보완 후보: ${preview.deficiencySupportCandidates.map(_formatInsightForChat).take(3).join(' / ')}',
      );
    }
    if (preview.missingProfileFields.isNotEmpty) {
      lines.add(
        '· 개인화 보강 필요: ${preview.missingProfileFields.take(3).join(', ')}',
      );
    }
    return lines;
  }

  List<String> _supplementChatPrecautionLines({
    required UserSupplementCreate? request,
    required SupplementAnalysisPreview? analysis,
  }) {
    final List<String> precautions =
        request?.precautionSnapshot.isNotEmpty == true
        ? request!.precautionSnapshot
        : analysis?.precautions
                  .map((SupplementPreviewPrecaution item) => item.text)
                  .toList(growable: false) ??
              const <String>[];
    if (precautions.isEmpty) {
      return <String>['· 라벨에서 확인된 주의 문구가 부족해요. 주의사항 영역을 한 장 더 촬영해주세요.'];
    }
    return <String>[
      for (final String precaution in precautions.take(4))
        '· ${precaution.trim()}',
    ];
  }

  String _formatConfirmedIngredient(UserSupplementIngredientInput ingredient) {
    final List<String> parts = <String>[
      _formatBilingualConfirmedIngredientName(ingredient),
    ];
    if (ingredient.amount != null) {
      parts.add(_formatAmount(ingredient.amount!));
    }
    if (ingredient.unit?.trim().isNotEmpty == true) {
      parts.add(ingredient.unit!.trim());
    }
    return parts.join(' ');
  }

  String _formatConfirmedIngredientForChat(
    UserSupplementIngredientInput ingredient,
  ) {
    final String name = _formatBilingualConfirmedIngredientName(ingredient);
    final List<String> amountParts = <String>[];
    if (ingredient.amount != null) {
      amountParts.add(_formatAmount(ingredient.amount!));
    }
    if (ingredient.unit?.trim().isNotEmpty == true) {
      amountParts.add(ingredient.unit!.trim());
    }
    if (amountParts.isEmpty) return '$name: 함량 확인 필요';
    return '$name: ${amountParts.join(' ')}';
  }

  String _formatPreviewIngredientForChat(
    SupplementIngredientCandidate ingredient,
  ) {
    final String name = _formatBilingualIngredientName(ingredient);
    final List<String> amountParts = <String>[];
    if (ingredient.amount != null) {
      amountParts.add(_formatAmount(ingredient.amount!));
    }
    if (ingredient.unit?.trim().isNotEmpty == true) {
      amountParts.add(ingredient.unit!.trim());
    }
    if (amountParts.isEmpty) return '$name: 함량 확인 필요';
    return '$name: ${amountParts.join(' ')}';
  }

  String _formatInsightForChat(SupplementNutritionInsight insight) {
    final String name = insight.nutrientName?.trim().isNotEmpty == true
        ? insight.nutrientName!.trim()
        : insight.nutrientCode.trim();
    final List<String> amountParts = <String>[];
    if (insight.estimatedTotalAmount != null) {
      amountParts.add(_formatAmount(insight.estimatedTotalAmount!));
    } else if (insight.supplementDailyAmount != null) {
      amountParts.add(_formatAmount(insight.supplementDailyAmount!));
    }
    if (insight.referenceUnit?.trim().isNotEmpty == true) {
      amountParts.add(insight.referenceUnit!.trim());
    }
    final String amountText = amountParts.isEmpty
        ? ''
        : ' ${amountParts.join(' ')}';
    return '$name$amountText';
  }

  String _formatPreviewIngredient(SupplementIngredientCandidate ingredient) {
    final List<String> parts = <String>[
      _formatBilingualIngredientName(ingredient),
    ];
    if (ingredient.amount != null) {
      parts.add(_formatAmount(ingredient.amount!));
    }
    if (ingredient.unit?.trim().isNotEmpty == true) {
      parts.add(ingredient.unit!.trim());
    }
    return parts.join(' ');
  }

  String _formatBilingualIngredientName(
    SupplementIngredientCandidate ingredient,
  ) {
    final String displayName = ingredient.displayName.trim();
    final String? originalName = _firstNonEmpty(<String?>[
      ingredient.originalName,
    ]);
    if (originalName == null ||
        originalName.toLowerCase() == displayName.toLowerCase()) {
      return displayName;
    }
    return '$displayName($originalName)';
  }

  String _formatBilingualConfirmedIngredientName(
    UserSupplementIngredientInput ingredient,
  ) {
    final String displayName = ingredient.displayName.trim();
    final String? originalName = _firstNonEmpty(<String?>[
      ingredient.originalName,
    ]);
    if (originalName == null ||
        originalName.toLowerCase() == displayName.toLowerCase()) {
      return displayName;
    }
    return '$displayName($originalName)';
  }

  String _formatServing(SupplementServing serving) {
    final List<String> parts = <String>[];
    if (serving.amount != null) {
      parts.add(_formatAmount(serving.amount!));
    }
    if (serving.unit?.trim().isNotEmpty == true) {
      parts.add(serving.unit!.trim());
    }
    parts.add('하루 ${_formatAmount(serving.dailyServings)}회');
    return parts.join(' ');
  }

  String _formatIntakeSchedule(SupplementIntakeSchedule schedule) {
    final List<String> parts = <String>[schedule.frequency.trim()];
    if (schedule.timeOfDay.isNotEmpty) {
      parts.add(schedule.timeOfDay.join(', '));
    }
    if (schedule.withFood?.trim().isNotEmpty == true) {
      parts.add(schedule.withFood!.trim());
    }
    return parts.where((String value) => value.isNotEmpty).join(' · ');
  }

  String _formatAmount(double value) {
    if (value == value.roundToDouble()) {
      return value.toStringAsFixed(0);
    }
    return value.toStringAsFixed(2).replaceFirst(RegExp(r'0+$'), '');
  }

  String? _firstNonEmpty(Iterable<String?> values) {
    for (final String? value in values) {
      final String? normalized = value?.trim();
      if (normalized != null && normalized.isNotEmpty) {
        return normalized;
      }
    }
    return null;
  }

  ApiError _apiErrorFromObject(Object error) {
    if (error is ApiError) return error;
    if (error is FormatException) {
      return ApiError(statusCode: 0, message: error.message);
    }
    return ApiError(statusCode: 0, message: error.toString());
  }

  Future<void> _refreshPostRegistrationInsights({
    required bool explainWithLocalLlm,
  }) async {
    try {
      _supplementImpactPreview = await _repository.previewSupplementImpact(
        const SupplementImpactPreviewRequest(),
      );
      _notice = 'Supplement registered and impact check is ready.';
    } on ApiError catch (error) {
      _apiError = error;
      _notice = 'Supplement registered, but impact check needs retry.';
      return;
    } on FormatException catch (error) {
      _apiError = ApiError(statusCode: 0, message: error.message);
      _notice = 'Supplement registered, but impact check needs retry.';
      return;
    }

    if (!explainWithLocalLlm || _supplementImpactPreview == null) {
      return;
    }
    try {
      _supplementExplanation = await _repository
          .explainSupplementRecommendation(
            _supplementImpactPreview!,
            useLocalLlm: true,
          );
      _notice = 'Supplement registered and local explanation is ready.';
    } on ApiError catch (error) {
      _apiError = error;
      _notice =
          'Supplement registered and impact check is ready; explanation needs retry.';
    } on FormatException catch (error) {
      _apiError = ApiError(statusCode: 0, message: error.message);
      _notice =
          'Supplement registered and impact check is ready; explanation needs retry.';
    }
  }

  @override
  void dispose() {
    _repository.close();
    super.dispose();
  }
}
