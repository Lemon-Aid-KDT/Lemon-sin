import 'package:flutter_test/flutter_test.dart';
import 'package:lemon_aid_mobile/app_controller.dart';
import 'package:lemon_aid_mobile/features/consent/consent_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/dashboard_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';

void main() {
  test('redacts unexpected exception messages before UI state', () async {
    final AppController controller = AppController(
      repository: _ThrowingRepository(
        Exception('raw_ocr_text=Vitamin D Authorization Bearer token'),
      ),
    );

    await controller.bootstrap();

    expect(controller.apiError?.message, 'Unexpected error occurred.');
    expect(controller.apiError.toString(), isNot(contains('raw_ocr_text')));
    expect(controller.apiError.toString(), isNot(contains('Bearer')));
  });

  test('redacts format exception messages before UI state', () async {
    final AppController controller = AppController(
      repository: _ThrowingRepository(
        const FormatException('provider_payload raw_ocr_text'),
      ),
    );

    await controller.bootstrap();

    expect(controller.apiError?.message, 'Invalid response from server.');
    expect(controller.apiError.toString(), isNot(contains('provider_payload')));
    expect(controller.apiError.toString(), isNot(contains('raw_ocr_text')));
  });
}

class _ThrowingRepository implements LemonAidRepository {
  const _ThrowingRepository(this.error);

  final Object error;

  Never _throw() {
    throw error;
  }

  @override
  Future<ConsentState> fetchConsents() async => _throw();

  @override
  Future<ConsentAction> grantConsent(String consentType) async => _throw();

  @override
  Future<DashboardSummary> fetchDashboardSummary({int days = 30}) async =>
      _throw();

  @override
  Future<SupplementAnalysisPreview> analyzeSupplementImage(
    String imagePath,
  ) async => _throw();

  @override
  Future<UserSupplementResponse> registerSupplement(
    UserSupplementCreate request,
  ) async => _throw();

  @override
  Future<SupplementImpactPreviewResponse> previewSupplementImpact(
    SupplementImpactPreviewRequest request,
  ) async => _throw();

  @override
  Future<SupplementImpactPreviewResponse>
  fetchLatestSupplementRecommendation() async => _throw();

  @override
  Future<SupplementRecommendationExplainResponse>
  explainSupplementRecommendation(
    SupplementImpactPreviewResponse preview, {
    bool useLocalLlm = false,
  }) async => _throw();

  @override
  void close() {}
}
