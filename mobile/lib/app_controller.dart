import 'dart:async';

import 'package:flutter/foundation.dart';

import 'core/api/api_error.dart';
import 'features/consent/consent_models.dart';
import 'features/dashboard/dashboard_models.dart';
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
  SupplementAnalysisPreview? _analysisPreview;
  SupplementMultiImageAnalysisPreview? _multiImageAnalysisPreview;
  MealImageAnalysisPreview? _mealAnalysisPreview;
  MealRecordResponse? _lastRegisteredMeal;
  UserSupplementResponse? _lastRegisteredSupplement;
  SupplementImpactPreviewResponse? _supplementImpactPreview;
  SupplementRecommendationExplainResponse? _supplementExplanation;
  String? _lastRequestedOcrProvider;
  AnalysisJobSnapshot _analysisJob = const AnalysisJobSnapshot.idle();
  int _analysisJobSerial = 0;
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

  /// Current supplement analysis preview.
  SupplementAnalysisPreview? get analysisPreview => _analysisPreview;

  /// Current multi-image supplement analysis preview, if the batch endpoint was used.
  SupplementMultiImageAnalysisPreview? get multiImageAnalysisPreview =>
      _multiImageAnalysisPreview;

  /// Current meal image analysis preview.
  MealImageAnalysisPreview? get mealAnalysisPreview => _mealAnalysisPreview;

  /// Most recently confirmed meal record.
  MealRecordResponse? get lastRegisteredMeal => _lastRegisteredMeal;

  /// Most recently registered supplement.
  UserSupplementResponse? get lastRegisteredSupplement =>
      _lastRegisteredSupplement;

  /// Latest deterministic supplement impact preview.
  SupplementImpactPreviewResponse? get supplementImpactPreview =>
      _supplementImpactPreview;

  /// Latest safe supplement explanation.
  SupplementRecommendationExplainResponse? get supplementExplanation =>
      _supplementExplanation;

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

  /// Refreshes the dashboard summary.
  Future<void> refreshDashboard() async {
    await _run(() async {
      _dashboardSummary = await _repository.fetchDashboardSummary();
      _notice = 'Dashboard refreshed.';
    });
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
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
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
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
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
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
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
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
      _notice = 'Meal image preview is ready for review.';
    });
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
      _supplementImpactPreview = null;
      _supplementExplanation = null;
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
      _analysisPreview = null;
      _multiImageAnalysisPreview = null;
      _mealAnalysisPreview = null;
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
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

  /// Clears the current preview without sending data to the backend.
  void clearSupplementFlow() {
    _analysisPreview = null;
    _multiImageAnalysisPreview = null;
    _mealAnalysisPreview = null;
    _lastRegisteredMeal = null;
    _lastRegisteredSupplement = null;
    _supplementImpactPreview = null;
    _supplementExplanation = null;
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
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
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
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
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
      _lastRegisteredMeal = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
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
