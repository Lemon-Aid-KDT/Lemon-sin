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
    expect(find.text('OCR'), findsOneWidget);
    expect(find.text('paddleocr_local'), findsOneWidget);
    expect(find.text('YOLO ROI'), findsOneWidget);
    expect(find.text('on'), findsOneWidget);
    expect(find.text('Ollama'), findsOneWidget);
    expect(find.text('parser on'), findsOneWidget);
    expect(find.text('Analysis progress'), findsNothing);
    expect(find.textContaining('OCR Auto'), findsNothing);
  });
}

class _ReviewRepository implements LemonAidRepository {
  @override
  Future<SupplementAnalysisPreview> analyzeSupplementImage(
    String imagePath, {
    String ocrProvider = 'configured',
  }) async {
    return _preview();
  }

  @override
  void close() {}

  @override
  Future<ConsentState> fetchConsents() {
    throw UnimplementedError();
  }

  @override
  Future<DashboardSummary> fetchDashboardSummary({int days = 30}) {
    throw UnimplementedError();
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
    throw UnimplementedError();
  }

  @override
  Future<SupplementImpactPreviewResponse> previewSupplementImpact(
    SupplementImpactPreviewRequest request,
  ) {
    throw UnimplementedError();
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
    throw UnimplementedError();
  }

  SupplementAnalysisPreview _preview() {
    return SupplementAnalysisPreview(
      analysisId: 'analysis-1',
      status: 'requires_confirmation',
      parsedProduct: const SupplementParsedProduct(
        productName: '비타민 D',
        manufacturer: 'Lemon Lab',
        servingSize: 'capsule',
        dailyServings: 1,
      ),
      ingredientCandidates: const <SupplementIngredientCandidate>[
        SupplementIngredientCandidate(
          displayName: 'Vitamin D',
          nutrientCode: 'vitamin_d',
          amount: 25,
          unit: 'mcg',
          confidence: 0.92,
          source: 'ocr_llm_preview',
        ),
      ],
      layoutAvailable: true,
      layoutFallbackReason: null,
      labelSections: const <SupplementPreviewLabelSection>[
        SupplementPreviewLabelSection(
          sectionId: 'section-1',
          sectionType: 'supplement_facts',
          headingText: 'Supplement Facts',
          textBundle: 'Vitamin D 25 mcg',
          confidence: 0.91,
          requiresReview: false,
          evidenceRefs: <String>['span-1'],
        ),
      ],
      intakeMethod: SupplementPreviewIntakeMethod.empty,
      precautions: const <SupplementPreviewPrecaution>[],
      functionalClaims: const <SupplementPreviewFunctionalClaim>[],
      evidenceSpans: const <SupplementPreviewEvidenceSpan>[
        SupplementPreviewEvidenceSpan(
          spanId: 'span-1',
          sourceType: 'ocr',
          sectionType: 'supplement_facts',
          textExcerpt: 'Vitamin D 25 mcg',
          pageIndex: null,
          cellRef: null,
          confidence: 0.91,
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
        visionRoiUsed: true,
        ocrProvider: 'paddleocr_local',
        llmParserUsed: true,
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
}
