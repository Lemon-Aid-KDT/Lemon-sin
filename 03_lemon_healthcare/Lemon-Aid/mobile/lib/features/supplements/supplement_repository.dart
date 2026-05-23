import '../../core/api/api_client.dart';
import '../consent/consent_models.dart';
import '../dashboard/dashboard_models.dart';
import 'supplement_models.dart';

/// Repository contract used by the mobile app controller.
abstract class LemonAidRepository {
  /// Fetches current-user consent state.
  Future<ConsentState> fetchConsents();

  /// Grants a consent bucket.
  Future<ConsentAction> grantConsent(String consentType);

  /// Fetches the dashboard summary.
  Future<DashboardSummary> fetchDashboardSummary({int days = 30});

  /// Uploads a selected supplement label image for preview analysis.
  Future<SupplementAnalysisPreview> analyzeSupplementImage(String imagePath);

  /// Persists a user-confirmed supplement.
  Future<UserSupplementResponse> registerSupplement(
    UserSupplementCreate request,
  );

  /// Calculates current supplement impact against nutrition analysis.
  Future<SupplementImpactPreviewResponse> previewSupplementImpact(
    SupplementImpactPreviewRequest request,
  );

  /// Fetches the latest deterministic supplement recommendation view.
  Future<SupplementImpactPreviewResponse> fetchLatestSupplementRecommendation();

  /// Builds a safe explanation for a deterministic supplement preview.
  Future<SupplementRecommendationExplainResponse>
  explainSupplementRecommendation(
    SupplementImpactPreviewResponse preview, {
    bool useLocalLlm = false,
  });

  /// Releases repository resources.
  void close();
}

/// Backend-backed repository for the current Nutrition API contract.
class BackendLemonAidRepository implements LemonAidRepository {
  /// Creates a backend repository.
  ///
  /// Args:
  ///   apiClient: Minimal API client for `/api/v1`.
  const BackendLemonAidRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  final ApiClient _apiClient;

  @override
  Future<ConsentState> fetchConsents() async {
    final Map<String, dynamic> json = await _apiClient.getJson(
      '/me/privacy/consents',
    );
    return ConsentState.fromJson(json);
  }

  @override
  Future<ConsentAction> grantConsent(String consentType) async {
    final Map<String, dynamic> json = await _apiClient.postJson(
      '/me/privacy/consents/$consentType',
      expectedStatusCodes: const <int>{201},
    );
    return ConsentAction.fromJson(json);
  }

  @override
  Future<DashboardSummary> fetchDashboardSummary({int days = 30}) async {
    final Map<String, dynamic> json = await _apiClient.getJson(
      '/dashboard/summary',
      queryParameters: <String, String>{'days': days.toString()},
    );
    return DashboardSummary.fromJson(json);
  }

  @override
  Future<SupplementAnalysisPreview> analyzeSupplementImage(
    String imagePath,
  ) async {
    final String clientRequestId =
        'mobile-${DateTime.now().microsecondsSinceEpoch}';
    final Map<String, dynamic> json = await _apiClient.postMultipart(
      '/supplements/analyze',
      fileField: 'image',
      filePath: imagePath,
      fields: <String, String>{
        'client_request_id': clientRequestId,
        'ocr_provider': 'paddleocr',
      },
    );
    return SupplementAnalysisPreview.fromJson(json);
  }

  @override
  Future<UserSupplementResponse> registerSupplement(
    UserSupplementCreate request,
  ) async {
    final Map<String, dynamic> json = await _apiClient.postJson(
      '/supplements',
      body: request.toJson(),
      expectedStatusCodes: const <int>{201},
    );
    return UserSupplementResponse.fromJson(json);
  }

  @override
  Future<SupplementImpactPreviewResponse> previewSupplementImpact(
    SupplementImpactPreviewRequest request,
  ) async {
    final Map<String, dynamic> json = await _apiClient.postJson(
      '/nutrition/supplement-impact/preview',
      body: request.toJson(),
      expectedStatusCodes: const <int>{200},
    );
    return SupplementImpactPreviewResponse.fromJson(json);
  }

  @override
  Future<SupplementImpactPreviewResponse>
  fetchLatestSupplementRecommendation() async {
    final Map<String, dynamic> json = await _apiClient.getJson(
      '/supplements/recommendations/latest',
    );
    return SupplementImpactPreviewResponse.fromJson(json);
  }

  @override
  Future<SupplementRecommendationExplainResponse>
  explainSupplementRecommendation(
    SupplementImpactPreviewResponse preview, {
    bool useLocalLlm = false,
  }) async {
    final Map<String, dynamic> json = await _apiClient.postJson(
      '/supplements/recommendations/explain',
      body: <String, dynamic>{
        'preview': preview.toJson(),
        'locale': 'ko-KR',
        'use_local_llm': useLocalLlm,
      },
      expectedStatusCodes: const <int>{200},
    );
    return SupplementRecommendationExplainResponse.fromJson(json);
  }

  @override
  void close() {
    _apiClient.close();
  }
}
