import 'dart:convert';

import '../../core/api/api_client.dart';
import '../../core/api/api_error.dart';
import '../consent/consent_models.dart';
import '../dashboard/dashboard_models.dart';
import '../dashboard/home_models.dart';
import '../nutrition/kdri_models.dart';
import '../records/food_models.dart';
import 'comprehensive_analysis_models.dart';
import 'supplement_models.dart';

/// Canonical UUID format used by backend path identifiers (e.g. meal id).
final RegExp _kUuidPattern = RegExp(
  r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
);

/// User-confirmed payload for creating a saved medication.
///
/// The backend schema uses `extra="forbid"` (no dosage/OCR fields allowed), so
/// this request mirrors exactly the accepted fields. Class and condition codes
/// are validated against the mirrored whitelists before sending to fail fast
/// with a clear error instead of a raw 422.
class MedicationCreateRequest {
  /// Creates a medication-create request.
  ///
  /// Args:
  ///   displayName: Medication name (1..160 chars after trim, required).
  ///   medicationClass: Optional class code from [kMedicationClassLabels].
  ///   conditionTags: Up to 8 condition codes from [kConditionTagLabels].
  ///   isActive: Whether the medication starts active.
  const MedicationCreateRequest({
    required this.displayName,
    this.medicationClass,
    this.conditionTags = const <String>[],
    this.isActive = true,
  });

  /// Medication display name (required, 1..160 chars).
  final String displayName;

  /// Optional medication class code.
  final String? medicationClass;

  /// Condition tag codes (max 8).
  final List<String> conditionTags;

  /// Whether the medication starts active.
  final bool isActive;

  /// Serializes to the backend create body (forbids extra fields).
  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'display_name': displayName.trim(),
      if (medicationClass != null) 'medication_class': medicationClass,
      'condition_tags': conditionTags,
      'is_active': isActive,
    };
  }
}

/// Repository contract used by the mobile app controller.
abstract class LemonAidRepository {
  /// Fetches current-user consent state.
  Future<ConsentState> fetchConsents();

  /// Grants a consent bucket.
  Future<ConsentAction> grantConsent(String consentType);

  /// Fetches the dashboard summary.
  Future<DashboardSummary> fetchDashboardSummary({int days = 30});

  /// Fetches meal records, optionally bounded by an eaten-at window.
  Future<HomeMealsResult> fetchMeals({
    DateTime? from,
    DateTime? to,
    int limit = 50,
    int offset = 0,
  }) {
    throw UnimplementedError();
  }

  /// Fetches current-user registered supplements.
  Future<HomeSupplementsResult> fetchSupplements({
    int limit = 50,
    int offset = 0,
  }) {
    throw UnimplementedError();
  }

  /// Searches the public food catalog for the direct-input screen.
  Future<FoodCatalogList> searchFoods({
    String? q,
    String? cuisineCode,
    int limit = 50,
    int offset = 0,
  }) {
    throw UnimplementedError();
  }

  /// Fetches the food cuisine catalog (filter chips).
  Future<FoodCuisineList> fetchCuisines() {
    throw UnimplementedError();
  }

  /// Fetches the curated supplement category catalog (분류 드롭다운 옵션).
  Future<List<SupplementCategory>> fetchSupplementCategories() {
    throw UnimplementedError();
  }

  /// Soft-deletes a registered supplement (DELETE /supplements/{id} → 204).
  Future<void> deleteSupplement(String supplementId) {
    throw UnimplementedError();
  }

  /// Deletes a saved analysis result (DELETE /analysis-results/{id} → 204).
  Future<void> deleteAnalysisResult(String resultId) {
    throw UnimplementedError();
  }

  /// Fetches current-user saved medications (active and inactive).
  ///
  /// The backend list route takes no query parameters and returns every saved
  /// row (active first); the home card filters to active client-side.
  Future<HomeMedicationsResult> fetchMedications() {
    throw UnimplementedError();
  }

  /// Saves a user-confirmed medication name.
  Future<HomeMedication> createMedication(MedicationCreateRequest request) {
    throw UnimplementedError();
  }

  /// Deactivates a saved medication row.
  Future<HomeMedication> deactivateMedication(String medicationId) {
    throw UnimplementedError();
  }

  /// Reactivates a saved medication row (undo of deactivate).
  Future<HomeMedication> reactivateMedication(String medicationId) {
    throw UnimplementedError();
  }

  /// Uploads a selected supplement label image for preview analysis.
  Future<SupplementAnalysisPreview> analyzeSupplementImage(
    String imagePath, {
    String ocrProvider = 'configured',
  });

  /// Uploads a selected meal image for review-only food analysis.
  Future<MealImageAnalysisPreview> analyzeMealImage(
    String imagePath, {
    String mealType = 'unknown',
  });

  /// Persists a user-confirmed meal image preview.
  Future<MealRecordResponse> confirmMealImagePreview(
    String mealId,
    MealConfirmationRequest request,
  );

  /// Requests a comprehensive diet analysis (C-hybrid result surface).
  ///
  /// Args:
  ///   ingredients: Nutrient rows derived from a meal's nutrition totals.
  ///   userProfile: Optional profile for personalization; null omits the card.
  ///   persona: Backend persona variant (defaults to `B`).
  Future<ComprehensiveDietAnalysis> analyzeComprehensive({
    required List<Map<String, Object?>> ingredients,
    Map<String, dynamic>? userProfile,
    String persona = 'B',
  }) {
    throw UnimplementedError();
  }

  /// Looks up KDRIs reference values for a profile (public route, no consent).
  ///
  /// Args:
  ///   age: Profile age (1..120).
  ///   sex: Profile sex (`male` or `female`).
  ///   pregnancyStatus: `none`, `pregnant`, or `lactating` (defaults `none`).
  Future<KdriLookupResult> lookupKdris({
    required int age,
    required String sex,
    String pregnancyStatus = 'none',
  }) {
    throw UnimplementedError();
  }

  /// Creates a backend multi-image supplement analysis session.
  Future<SupplementAnalysisSession> createSupplementAnalysisSession();

  /// Uploads one image into an existing multi-image analysis session.
  Future<SupplementMultiImageAnalysisPreview>
  uploadSupplementAnalysisSessionImage(
    String analysisGroupId,
    SupplementImageUpload image, {
    String ocrProvider = 'configured',
    String? clientRequestId,
  });

  /// Uploads several supplement label images as one analysis batch.
  Future<SupplementMultiImageAnalysisPreview> analyzeSupplementImages(
    List<SupplementImageUpload> images, {
    String ocrProvider = 'configured',
  }) {
    throw UnimplementedError();
  }

  /// Uploads a one-product batch as a SINGLE request to the fusion route so the
  /// backend OCRs every image, fuses the text, and parses once into one result.
  ///
  /// Defaults to the per-image session flow ([analyzeSupplementImages]) so impls
  /// that do not need one-shot fusion keep working unchanged.
  Future<SupplementMultiImageAnalysisPreview> analyzeSupplementImagesOneShot(
    List<SupplementImageUpload> images, {
    String ocrProvider = 'configured',
  }) {
    return analyzeSupplementImages(images, ocrProvider: ocrProvider);
  }

  /// Rebuilds the backend-merged preview for an existing multi-image batch.
  Future<SupplementMultiImageAnalysisPreview> finalizeSupplementAnalysisSession(
    String analysisGroupId,
  );

  /// Parses user-reviewed OCR text for an existing preview.
  Future<SupplementAnalysisPreview> parseOcrText({
    required String analysisId,
    required SupplementOCRTextParseRequest request,
  });

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

  /// Builds a safe explanation for an unregistered analysis preview.
  Future<SupplementRecommendationExplainResponse> explainSupplementAnalysis(
    String analysisId, {
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
  Future<HomeMealsResult> fetchMeals({
    DateTime? from,
    DateTime? to,
    int limit = 50,
    int offset = 0,
  }) async {
    final Map<String, String> query = <String, String>{
      'limit': limit.toString(),
      'offset': offset.toString(),
    };
    if (from != null) {
      query['from_eaten_at'] = from.toUtc().toIso8601String();
    }
    if (to != null) {
      query['to_eaten_at'] = to.toUtc().toIso8601String();
    }
    final Map<String, dynamic> json = await _apiClient.getJson(
      '/meals',
      queryParameters: query,
    );
    return HomeMealsResult.fromJson(json);
  }

  @override
  Future<HomeSupplementsResult> fetchSupplements({
    int limit = 50,
    int offset = 0,
  }) async {
    final Map<String, dynamic> json = await _apiClient.getJson(
      '/supplements',
      queryParameters: <String, String>{
        'limit': limit.toString(),
        'offset': offset.toString(),
      },
    );
    return HomeSupplementsResult.fromJson(json);
  }

  @override
  Future<FoodCatalogList> searchFoods({
    String? q,
    String? cuisineCode,
    int limit = 50,
    int offset = 0,
  }) async {
    final Map<String, String> query = <String, String>{
      'limit': limit.toString(),
      'offset': offset.toString(),
    };
    final String? normalizedQuery = q?.trim();
    if (normalizedQuery != null && normalizedQuery.isNotEmpty) {
      query['q'] = normalizedQuery;
    }
    final String? normalizedCuisine = cuisineCode?.trim();
    if (normalizedCuisine != null && normalizedCuisine.isNotEmpty) {
      query['cuisine_code'] = normalizedCuisine;
    }
    final Map<String, dynamic> json = await _apiClient.getJson(
      '/meals/foods',
      queryParameters: query,
    );
    return FoodCatalogList.fromJson(json);
  }

  @override
  Future<FoodCuisineList> fetchCuisines() async {
    final Map<String, dynamic> json = await _apiClient.getJson(
      '/meals/cuisines',
    );
    return FoodCuisineList.fromJson(json);
  }

  @override
  Future<List<SupplementCategory>> fetchSupplementCategories() async {
    final Map<String, dynamic> json = await _apiClient.getJson(
      '/supplements/categories?limit=100',
    );
    return SupplementCategory.listFromJson(json);
  }

  @override
  Future<void> deleteSupplement(String supplementId) async {
    final String normalized = supplementId.trim();
    if (normalized.isEmpty) {
      throw ArgumentError.value(
        supplementId,
        'supplementId',
        'Supplement id is required',
      );
    }
    await _apiClient.delete('/supplements/${Uri.encodeComponent(normalized)}');
  }

  @override
  Future<void> deleteAnalysisResult(String resultId) async {
    final String normalized = resultId.trim();
    if (normalized.isEmpty) {
      throw ArgumentError.value(
        resultId,
        'resultId',
        'Analysis result id is required',
      );
    }
    await _apiClient.delete(
      '/analysis-results/${Uri.encodeComponent(normalized)}',
    );
  }

  @override
  Future<HomeMedicationsResult> fetchMedications() async {
    final Map<String, dynamic> json = await _withHealthConsentRetry(
      () => _apiClient.getJson('/me/medications'),
    );
    return HomeMedicationsResult.fromJson(json);
  }

  @override
  Future<HomeMedication> createMedication(
    MedicationCreateRequest request,
  ) async {
    final String normalizedName = request.displayName.trim();
    if (normalizedName.isEmpty) {
      throw ArgumentError.value(
        request.displayName,
        'displayName',
        'Medication name is required',
      );
    }
    final String? medicationClass = request.medicationClass;
    if (medicationClass != null &&
        !kMedicationClassLabels.containsKey(medicationClass)) {
      throw ArgumentError.value(
        medicationClass,
        'medicationClass',
        'Unsupported medication class',
      );
    }
    for (final String tag in request.conditionTags) {
      if (!kConditionTagLabels.containsKey(tag)) {
        throw ArgumentError.value(tag, 'conditionTags', 'Unsupported tag');
      }
    }
    final Map<String, dynamic> json = await _withHealthConsentRetry(
      () => _apiClient.postJson(
        '/me/medications',
        body: request.toJson(),
        expectedStatusCodes: const <int>{201},
      ),
    );
    return HomeMedication.fromJson(json);
  }

  @override
  Future<HomeMedication> deactivateMedication(String medicationId) async {
    final String encodedId = _encodeMedicationId(medicationId);
    final Map<String, dynamic> json = await _withHealthConsentRetry(
      () => _apiClient.postJson(
        '/me/medications/$encodedId/deactivate',
        expectedStatusCodes: const <int>{200},
      ),
    );
    return HomeMedication.fromJson(json);
  }

  @override
  Future<HomeMedication> reactivateMedication(String medicationId) async {
    final String encodedId = _encodeMedicationId(medicationId);
    final Map<String, dynamic> json = await _withHealthConsentRetry(
      () => _apiClient.postJson(
        '/me/medications/$encodedId',
        body: <String, dynamic>{'is_active': true},
        expectedStatusCodes: const <int>{200},
      ),
    );
    return HomeMedication.fromJson(json);
  }

  /// Runs [request] and, on a `403 consent_required`, grants the sensitive
  /// health analysis consent once and retries exactly once
  /// (pattern: `features/chat/chat_repository.dart`).
  Future<Map<String, dynamic>> _withHealthConsentRetry(
    Future<Map<String, dynamic>> Function() request,
  ) async {
    try {
      return await request();
    } on ApiError catch (error) {
      if (error.statusCode != 403 || error.code != 'consent_required') {
        rethrow;
      }
      await grantConsent('sensitive_health_analysis');
      return request();
    }
  }

  String _encodeMedicationId(String medicationId) {
    final String normalized = medicationId.trim();
    if (normalized.isEmpty) {
      throw ArgumentError.value(
        medicationId,
        'medicationId',
        'Medication id is required',
      );
    }
    return Uri.encodeComponent(normalized);
  }

  @override
  Future<SupplementAnalysisPreview> analyzeSupplementImage(
    String imagePath, {
    String ocrProvider = 'configured',
  }) async {
    final String selectedOcrProvider = _normalizeOcrProvider(ocrProvider);
    final String clientRequestId =
        'mobile-${DateTime.now().microsecondsSinceEpoch}';
    final Map<String, dynamic> json = await _apiClient.postMultipart(
      '/supplements/analyze',
      fileField: 'image',
      filePath: imagePath,
      fields: <String, String>{
        'client_request_id': clientRequestId,
        'ocr_provider': selectedOcrProvider,
      },
    );
    return SupplementAnalysisPreview.fromJson(json);
  }

  @override
  Future<MealImageAnalysisPreview> analyzeMealImage(
    String imagePath, {
    String mealType = 'unknown',
  }) async {
    final String selectedMealType = _normalizeMealType(mealType);
    final String clientRequestId =
        'mobile-meal-${DateTime.now().microsecondsSinceEpoch}';
    final Map<String, dynamic> json = await _apiClient.postMultipart(
      '/meals/analyze-image',
      fileField: 'image',
      filePath: imagePath,
      fields: <String, String>{
        'client_request_id': clientRequestId,
        'meal_type': selectedMealType,
      },
    );
    return MealImageAnalysisPreview.fromJson(json);
  }

  @override
  Future<MealRecordResponse> confirmMealImagePreview(
    String mealId,
    MealConfirmationRequest request,
  ) async {
    final String normalizedMealId = mealId.trim();
    if (normalizedMealId.isEmpty) {
      throw ArgumentError.value(mealId, 'mealId', 'Meal id is required');
    }
    // Backend declares meal_id as a UUID path param; validate client-side so a
    // malformed preview id fails fast with a clear error instead of a raw 422.
    if (!_kUuidPattern.hasMatch(normalizedMealId)) {
      throw ArgumentError.value(mealId, 'mealId', 'Meal id must be a UUID');
    }
    final String encodedMealId = Uri.encodeComponent(normalizedMealId);
    final Map<String, dynamic> json = await _apiClient.postJson(
      '/meals/$encodedMealId/confirm',
      body: request.toJson(),
      expectedStatusCodes: const <int>{200},
    );
    return MealRecordResponse.fromJson(json);
  }

  @override
  Future<ComprehensiveDietAnalysis> analyzeComprehensive({
    required List<Map<String, Object?>> ingredients,
    Map<String, dynamic>? userProfile,
    String persona = 'B',
  }) async {
    final Map<String, dynamic> json = await _apiClient.postJson(
      '/supplements/analyze/comprehensive',
      body: <String, dynamic>{
        'ingredients': ingredients,
        'user_profile': ?userProfile,
        'persona': persona,
      },
      expectedStatusCodes: const <int>{200},
    );
    return ComprehensiveDietAnalysis.fromJson(json);
  }

  @override
  Future<KdriLookupResult> lookupKdris({
    required int age,
    required String sex,
    String pregnancyStatus = 'none',
  }) async {
    if (age < 1 || age > 120) {
      throw ArgumentError.value(age, 'age', 'Age must be between 1 and 120');
    }
    final String normalizedSex = _normalizeSex(sex);
    final String normalizedPregnancyStatus = _normalizePregnancyStatus(
      pregnancyStatus,
    );
    final Map<String, dynamic> json = await _apiClient.getJson(
      '/nutrition/kdris',
      queryParameters: <String, String>{
        'age': age.toString(),
        'sex': normalizedSex,
        'pregnancy_status': normalizedPregnancyStatus,
      },
    );
    return KdriLookupResult.fromJson(json);
  }

  @override
  Future<SupplementMultiImageAnalysisPreview> analyzeSupplementImages(
    List<SupplementImageUpload> images, {
    String ocrProvider = 'configured',
  }) async {
    if (images.isEmpty) {
      throw ArgumentError.value(
        images,
        'images',
        'At least one image is required',
      );
    }
    for (final SupplementImageUpload image in images) {
      _normalizeImageRole(image.role);
    }
    final SupplementAnalysisSession session =
        await createSupplementAnalysisSession();
    for (int index = 0; index < images.length; index += 1) {
      await uploadSupplementAnalysisSessionImage(
        session.analysisGroupId,
        images[index],
        ocrProvider: ocrProvider,
        clientRequestId:
            'mobile-${DateTime.now().microsecondsSinceEpoch}-$index',
      );
    }
    return finalizeSupplementAnalysisSession(session.analysisGroupId);
  }

  @override
  Future<SupplementMultiImageAnalysisPreview> analyzeSupplementImagesOneShot(
    List<SupplementImageUpload> images, {
    String ocrProvider = 'configured',
  }) async {
    if (images.isEmpty) {
      throw ArgumentError.value(
        images,
        'images',
        'At least one image is required',
      );
    }
    final String selectedOcrProvider = _normalizeOcrProvider(ocrProvider);
    final List<String> roles = <String>[
      for (final SupplementImageUpload image in images)
        _normalizeImageRole(image.role),
    ];
    final Map<String, dynamic> json = await _apiClient.postMultipartFiles(
      '/supplements/analyze-multi',
      fileField: 'images',
      filePaths: <String>[
        for (final SupplementImageUpload image in images) image.path,
      ],
      fields: <String, String>{
        'ocr_provider': selectedOcrProvider,
        'merge_strategy': 'single_product',
        'image_roles_json': jsonEncode(roles),
      },
      expectedStatusCodes: const <int>{202},
    );
    return SupplementMultiImageAnalysisPreview.fromJson(json);
  }

  @override
  Future<SupplementAnalysisSession> createSupplementAnalysisSession() async {
    final Map<String, dynamic> json = await _apiClient.postJson(
      '/supplements/analysis-sessions',
      expectedStatusCodes: const <int>{201},
    );
    return SupplementAnalysisSession.fromJson(json);
  }

  @override
  Future<SupplementMultiImageAnalysisPreview>
  uploadSupplementAnalysisSessionImage(
    String analysisGroupId,
    SupplementImageUpload image, {
    String ocrProvider = 'configured',
    String? clientRequestId,
  }) async {
    final String normalizedGroupId = _normalizeAnalysisGroupId(analysisGroupId);
    final String selectedOcrProvider = _normalizeOcrProvider(ocrProvider);
    final String encodedGroupId = Uri.encodeComponent(normalizedGroupId);
    final String selectedRole = _normalizeImageRole(image.role);
    final Map<String, String> fields = <String, String>{
      'ocr_provider': selectedOcrProvider,
      'image_role': selectedRole,
    };
    final String? normalizedClientRequestId = clientRequestId?.trim();
    if (normalizedClientRequestId != null &&
        normalizedClientRequestId.isNotEmpty) {
      fields['client_request_id'] = normalizedClientRequestId;
    }
    final Map<String, dynamic> json = await _apiClient.postMultipart(
      '/supplements/analysis-sessions/$encodedGroupId/images',
      fileField: 'image',
      filePath: image.path,
      fields: fields,
      expectedStatusCodes: const <int>{202},
    );
    return SupplementMultiImageAnalysisPreview.fromJson(json);
  }

  @override
  Future<SupplementMultiImageAnalysisPreview> finalizeSupplementAnalysisSession(
    String analysisGroupId,
  ) async {
    final String normalizedGroupId = _normalizeAnalysisGroupId(analysisGroupId);
    final String encodedGroupId = Uri.encodeComponent(normalizedGroupId);
    final Map<String, dynamic> json = await _apiClient.postJson(
      '/supplements/analysis-sessions/$encodedGroupId/finalize',
      expectedStatusCodes: const <int>{200},
    );
    return SupplementMultiImageAnalysisPreview.fromJson(json);
  }

  @override
  Future<SupplementAnalysisPreview> parseOcrText({
    required String analysisId,
    required SupplementOCRTextParseRequest request,
  }) async {
    final Map<String, dynamic> json = await _apiClient.postJson(
      '/supplements/analyses/$analysisId/ocr-text',
      body: request.toJson(),
      expectedStatusCodes: const <int>{200},
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
    if (request.selectedSupplementIds.isNotEmpty ||
        !request.includeAllActiveSupplements) {
      throw UnsupportedError(
        'Selected supplement impact preview is not available in the current '
        'backend contract.',
      );
    }
    return fetchLatestSupplementRecommendation();
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
  Future<SupplementRecommendationExplainResponse> explainSupplementAnalysis(
    String analysisId, {
    bool useLocalLlm = false,
  }) async {
    final String normalizedAnalysisId = analysisId.trim();
    if (normalizedAnalysisId.isEmpty) {
      throw ArgumentError.value(
        analysisId,
        'analysisId',
        'Analysis id is required',
      );
    }
    final String encodedAnalysisId = Uri.encodeComponent(normalizedAnalysisId);
    final Map<String, dynamic> json = await _apiClient.postJson(
      '/supplements/analyses/$encodedAnalysisId/explain',
      body: <String, dynamic>{'locale': 'ko-KR', 'use_local_llm': useLocalLlm},
      expectedStatusCodes: const <int>{200},
    );
    return SupplementRecommendationExplainResponse.fromJson(json);
  }

  @override
  void close() {
    _apiClient.close();
  }

  static String _normalizeOcrProvider(String value) {
    final String normalized = value.trim();
    const Set<String> allowedProviders = <String>{
      'configured',
      'paddleocr',
      'google_vision',
      'clova',
    };
    if (!allowedProviders.contains(normalized)) {
      throw ArgumentError.value(
        value,
        'ocrProvider',
        'Unsupported OCR provider',
      );
    }
    return normalized;
  }

  static String _normalizeImageRole(String value) {
    final String normalized = value.trim().isEmpty ? 'unknown' : value.trim();
    const Set<String> allowedRoles = <String>{
      'unknown',
      'front_label',
      'supplement_facts',
      'intake_method',
      'ingredients',
      'precautions',
      'barcode',
      'mixed',
    };
    if (!allowedRoles.contains(normalized)) {
      throw ArgumentError.value(value, 'imageRole', 'Unsupported image role');
    }
    return normalized;
  }

  static String _normalizeSex(String value) {
    final String normalized = value.trim().toLowerCase();
    const Set<String> allowedSexes = <String>{'male', 'female'};
    if (!allowedSexes.contains(normalized)) {
      throw ArgumentError.value(value, 'sex', 'Unsupported sex');
    }
    return normalized;
  }

  static String _normalizePregnancyStatus(String value) {
    final String normalized = value.trim().isEmpty
        ? 'none'
        : value.trim().toLowerCase();
    const Set<String> allowedStatuses = <String>{
      'none',
      'pregnant',
      'lactating',
    };
    if (!allowedStatuses.contains(normalized)) {
      throw ArgumentError.value(
        value,
        'pregnancyStatus',
        'Unsupported pregnancy status',
      );
    }
    return normalized;
  }

  static String _normalizeMealType(String value) {
    final String normalized = value.trim().isEmpty ? 'unknown' : value.trim();
    const Set<String> allowedMealTypes = <String>{
      'breakfast',
      'lunch',
      'dinner',
      'snack',
      'unknown',
    };
    if (!allowedMealTypes.contains(normalized)) {
      throw ArgumentError.value(value, 'mealType', 'Unsupported meal type');
    }
    return normalized;
  }

  static String _normalizeAnalysisGroupId(String value) {
    final String normalized = value.trim();
    if (normalized.isEmpty) {
      throw ArgumentError.value(
        value,
        'analysisGroupId',
        'Analysis group id is required',
      );
    }
    return normalized;
  }
}
