import 'package:flutter/foundation.dart';

import 'core/api/api_error.dart';
import 'features/consent/consent_models.dart';
import 'features/dashboard/dashboard_models.dart';
import 'features/supplements/supplement_models.dart';
import 'features/supplements/supplement_repository.dart';

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
  UserSupplementResponse? _lastRegisteredSupplement;
  SupplementImpactPreviewResponse? _supplementImpactPreview;
  SupplementRecommendationExplainResponse? _supplementExplanation;
  String? _lastRequestedOcrProvider;

  /// Whether a network operation is in progress.
  bool get busy => _busy;

  /// Last API error, if any.
  ApiError? get apiError => _apiError;

  /// Last user-safe notice.
  String? get notice => _notice;

  /// Current consent state.
  ConsentState? get consentState => _consentState;

  /// Current dashboard summary.
  DashboardSummary? get dashboardSummary => _dashboardSummary;

  /// Current supplement analysis preview.
  SupplementAnalysisPreview? get analysisPreview => _analysisPreview;

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
      _lastRequestedOcrProvider = ocrProvider;
      _analysisPreview = await _repository.analyzeSupplementImage(
        imagePath,
        ocrProvider: ocrProvider,
      );
      _lastRegisteredSupplement = null;
      _supplementImpactPreview = null;
      _supplementExplanation = null;
      _notice = 'Supplement preview is ready for review.';
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

  /// Registers a user-confirmed supplement and refreshes dashboard summary.
  Future<void> registerSupplement(UserSupplementCreate request) async {
    await _run(() async {
      _lastRegisteredSupplement = await _repository.registerSupplement(request);
      _analysisPreview = null;
      _dashboardSummary = await _repository.fetchDashboardSummary();
      _notice = 'Supplement registered and dashboard refreshed.';
    });
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

  /// Clears the current preview without sending data to the backend.
  void clearSupplementFlow() {
    _analysisPreview = null;
    _lastRegisteredSupplement = null;
    _supplementImpactPreview = null;
    _supplementExplanation = null;
    _lastRequestedOcrProvider = null;
    _apiError = null;
    _notice = null;
    notifyListeners();
  }

  /// Clears transient error and notice messages.
  void clearMessages() {
    _apiError = null;
    _notice = null;
    notifyListeners();
  }

  Future<void> _run(Future<void> Function() task) async {
    _busy = true;
    _apiError = null;
    _notice = null;
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

  @override
  void dispose() {
    _repository.close();
    super.dispose();
  }
}
