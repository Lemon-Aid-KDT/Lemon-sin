// screens/analysis_result_screen.dart — 17 Pro UIUX analysis result surface.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../app_controller.dart';
import '../core/api/api_error.dart';
import '../features/supplements/supplement_models.dart';
import '../utils/design_tokens_v2.dart';
import '../utils/mascot_poses.dart';

/// Source-style analysis result screen backed by the real Lemon-Aid endpoints.
class AnalysisResultScreen extends StatefulWidget {
  /// Creates the analysis result screen.
  ///
  /// Args:
  ///   mode: `supplement` or `meal`.
  ///   controller: Optional real app controller for OCR/YOLO/Ollama data.
  const AnalysisResultScreen({
    super.key,
    this.mode = 'supplement',
    this.controller,
  });

  /// Analysis mode selected by the camera UI.
  final String mode;

  /// Current backend-connected app state.
  final AppController? controller;

  @override
  State<AnalysisResultScreen> createState() => _AnalysisResultScreenState();
}

class _AnalysisResultScreenState extends State<AnalysisResultScreen> {
  final TextEditingController _productNameController = TextEditingController();
  final TextEditingController _manufacturerController = TextEditingController();
  final TextEditingController _ingredientNameController =
      TextEditingController();
  final TextEditingController _ingredientAmountController =
      TextEditingController();
  final TextEditingController _ingredientUnitController =
      TextEditingController();
  final TextEditingController _frequencyController = TextEditingController();
  final TextEditingController _intakeMethodTextController =
      TextEditingController();
  final TextEditingController _precautionsController = TextEditingController();
  final TextEditingController _timeOfDayController = TextEditingController();
  final TextEditingController _mealNameController = TextEditingController();
  final TextEditingController _mealPortionAmountController =
      TextEditingController();
  final TextEditingController _mealPortionUnitController =
      TextEditingController();
  final TextEditingController _mealKcalController = TextEditingController();
  final TextEditingController _mealCarbController = TextEditingController();
  final TextEditingController _mealProteinController = TextEditingController();
  final TextEditingController _mealFatController = TextEditingController();
  final TextEditingController _mealSodiumController = TextEditingController();
  String? _seededAnalysisId;
  String? _seededMealAnalysisId;
  int _selectedSupplementPreviewIndex = 0;
  List<_IngredientReviewDraft> _ingredientDrafts =
      const <_IngredientReviewDraft>[];
  bool _seedingCorrectionFields = false;

  bool get _isMeal => widget.mode == 'meal';

  @override
  void initState() {
    super.initState();
    for (final TextEditingController controller in _primaryActionControllers) {
      controller.addListener(_handlePrimaryActionFieldChanged);
    }
  }

  @override
  void dispose() {
    for (final TextEditingController controller in _primaryActionControllers) {
      controller.removeListener(_handlePrimaryActionFieldChanged);
    }
    _productNameController.dispose();
    _manufacturerController.dispose();
    _ingredientNameController.dispose();
    _ingredientAmountController.dispose();
    _ingredientUnitController.dispose();
    _frequencyController.dispose();
    _intakeMethodTextController.dispose();
    _precautionsController.dispose();
    _timeOfDayController.dispose();
    _mealNameController.dispose();
    _mealPortionAmountController.dispose();
    _mealPortionUnitController.dispose();
    _mealKcalController.dispose();
    _mealCarbController.dispose();
    _mealProteinController.dispose();
    _mealFatController.dispose();
    _mealSodiumController.dispose();
    super.dispose();
  }

  List<TextEditingController> get _primaryActionControllers =>
      <TextEditingController>[
        _productNameController,
        _manufacturerController,
        _ingredientNameController,
        _ingredientAmountController,
        _ingredientUnitController,
        _frequencyController,
        _intakeMethodTextController,
        _precautionsController,
        _timeOfDayController,
        _mealNameController,
        _mealPortionAmountController,
        _mealPortionUnitController,
        _mealKcalController,
        _mealCarbController,
        _mealProteinController,
        _mealFatController,
        _mealSodiumController,
      ];

  void _handlePrimaryActionFieldChanged() {
    if (!mounted || _seedingCorrectionFields) return;
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final AppController? controller = widget.controller;
    final List<_SupplementReviewGroup> supplementGroups =
        _supplementReviewGroups(controller);
    final int activeSupplementPreviewIndex = _activeSupplementPreviewIndex(
      supplementGroups.length,
    );
    final SupplementAnalysisPreview? preview = supplementGroups.isEmpty
        ? null
        : supplementGroups[activeSupplementPreviewIndex].preview;
    final MealImageAnalysisPreview? mealPreview =
        controller?.mealAnalysisPreview;
    if (preview != null) {
      _seedCorrectionFields(preview);
    }
    if (mealPreview != null) {
      _seedMealCorrectionFields(mealPreview);
    }
    final UserSupplementResponse? registered =
        controller?.lastRegisteredSupplement;
    final MealRecordResponse? registeredMeal = controller?.lastRegisteredMeal;
    final ApiError? error = controller?.apiError;
    final AnalysisJobSnapshot? analysisJob = controller?.analysisJob;
    if (analysisJob?.isRunning == true && analysisJob?.mode == widget.mode) {
      return _AnalysisInProgressScreen(isMeal: _isMeal);
    }
    return Scaffold(
      backgroundColor: AppColor.section,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: <Widget>[
            _ResultTopBar(isMeal: _isMeal),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(
                  AppSpace.page,
                  AppSpace.lg,
                  AppSpace.page,
                  AppSpace.xl + 88,
                ),
                children: <Widget>[
                  if (error != null) ...<Widget>[
                    _StatusBanner(error: error),
                    const SizedBox(height: AppSpace.md),
                  ],
                  if (!_isMeal && supplementGroups.length > 1) ...<Widget>[
                    _SupplementPreviewTabs(
                      groups: supplementGroups,
                      selectedIndex: activeSupplementPreviewIndex,
                      onSelected: (int index) {
                        setState(() {
                          _selectedSupplementPreviewIndex = index;
                          _seededAnalysisId = null;
                        });
                      },
                    ),
                    const SizedBox(height: AppSpace.md),
                  ],
                  _SummaryCard(
                    isMeal: _isMeal,
                    preview: preview,
                    mealPreview: mealPreview,
                    registered: registered,
                    registeredMeal: registeredMeal,
                    busy: controller?.busy == true,
                    onTap: !_isMeal && preview != null
                        ? () => _showOcrTextTable(context, preview)
                        : null,
                  ),
                  const SizedBox(height: AppSpace.md),
                  if (_isMeal)
                    ..._mealCards(mealPreview, registeredMeal)
                  else
                    ..._supplementCards(preview),
                  if (!_isMeal && preview != null) ...<Widget>[
                    const SizedBox(height: AppSpace.md),
                    _AnalysisExplanationCard(
                      explanation: controller?.supplementExplanation,
                      busy: controller?.busy == true,
                      onExplain: controller == null
                          ? null
                          : () => _handleAnalysisExplanation(controller),
                    ),
                    if (controller?.supplementImpactPreview !=
                        null) ...<Widget>[
                      const SizedBox(height: AppSpace.md),
                      _ImpactPreviewCard(
                        preview: controller!.supplementImpactPreview!,
                        explanation: controller.supplementExplanation,
                      ),
                    ],
                  ],
                  const SizedBox(height: AppSpace.lg),
                  const _MedicalNote(),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.page,
            AppSpace.sm,
            AppSpace.page,
            AppSpace.md,
          ),
          child: _SaveButton(
            label: _primaryLabel(preview, registered, registeredMeal),
            busy: controller?.busy == true,
            onTap: () => _handlePrimaryAction(context),
          ),
        ),
      ),
    );
  }

  List<Widget> _mealCards(
    MealImageAnalysisPreview? preview,
    MealRecordResponse? registeredMeal,
  ) {
    final FoodImagePipelineMetadata? pipeline = preview?.pipelineMetadata;
    final List<MealFoodCandidate> candidates =
        preview?.foodCandidates ?? const <MealFoodCandidate>[];
    final bool hasCandidates = candidates.isNotEmpty;
    final String firstCandidate = hasCandidates
        ? candidates.first.displayName
        : '후보 없음';
    final String candidateValue = candidates.length > 1
        ? '$firstCandidate 외 ${candidates.length - 1}개'
        : firstCandidate;
    final String detectorModel = pipeline?.detectorModel ?? 'not configured';
    final String warningText = preview == null || preview.warningCodes.isEmpty
        ? 'warning 없음'
        : preview.warningCodes.join(', ');
    return <Widget>[
      _ResultCard(
        color: Color(0xFF22B07D),
        icon: Icons.eco_rounded,
        label: '음식 후보',
        value: candidateValue,
        desc: hasCandidates
            ? 'YOLO 후보는 등록 전 사용자 확인이 필요해요'
            : '사진은 업로드됐지만 음식 후보는 직접 입력이 필요해요',
      ),
      const SizedBox(height: AppSpace.sm),
      _ResultCard(
        color: Color(0xFFFF9500),
        icon: Icons.center_focus_strong_rounded,
        label: 'Food YOLO',
        value: pipeline?.detectorUsed == true ? 'on' : 'review',
        desc: '모델 $detectorModel · 원본 이미지와 payload는 저장하지 않아요',
      ),
      const SizedBox(height: AppSpace.sm),
      _ResultCard(
        color: Color(0xFFFF6B6B),
        icon: Icons.shield_outlined,
        label: '수동 확인',
        value: pipeline?.requiresManualEntry == false ? '후보 확인' : '직접 입력',
        desc: warningText,
      ),
      const SizedBox(height: AppSpace.sm),
      _ResultCard(
        color: AppColor.brand,
        icon: Icons.workspace_premium_rounded,
        label: '분석 상태',
        value: registeredMeal?.status ?? preview?.status ?? '분석 전',
        desc: registeredMeal == null
            ? preview?.algorithmVersion ?? '식단 사진을 먼저 분석해주세요'
            : '${registeredMeal.foodItems.length}개 음식이 식단 기록으로 저장됐어요',
        big: true,
      ),
      if (preview != null && registeredMeal == null) ...<Widget>[
        const SizedBox(height: AppSpace.md),
        _MealReviewCorrectionCard(
          mealNameController: _mealNameController,
          portionAmountController: _mealPortionAmountController,
          portionUnitController: _mealPortionUnitController,
          kcalController: _mealKcalController,
          carbController: _mealCarbController,
          proteinController: _mealProteinController,
          fatController: _mealFatController,
          sodiumController: _mealSodiumController,
          requiresManualEntry: pipeline?.requiresManualEntry == true,
        ),
      ],
    ];
  }

  List<Widget> _supplementCards(SupplementAnalysisPreview? preview) {
    final SupplementImagePipelineMetadata? pipeline = preview?.pipelineMetadata;
    final List<String> missingSections = _missingRequiredSections(preview);
    return <Widget>[
      if (pipeline != null) ...<Widget>[
        _PipelineLedStrip(metadata: pipeline),
        const SizedBox(height: AppSpace.sm),
      ],
      _SupplementInfoCard(
        icon: Icons.medication_rounded,
        title: '영양제명',
        body: _productInfoBody(preview),
        missingMessage: missingSections.contains('product_name')
            ? '제품명이 보이게 한 장 더 촬영해주세요'
            : null,
        onEdit: preview == null ? null : () => _editProductInfo(context),
      ),
      const SizedBox(height: AppSpace.sm),
      _SupplementInfoCard(
        icon: Icons.fact_check_rounded,
        title: '상세 성분 및 함량',
        bodyWidget: _ingredientInfoTable(preview),
        missingMessage: missingSections.contains('supplement_facts')
            ? '성분표가 보이게 한 장 더 촬영해주세요'
            : null,
        onEdit: preview == null ? null : () => _editIngredientInfo(context),
      ),
      const SizedBox(height: AppSpace.sm),
      _SupplementInfoCard(
        icon: Icons.schedule_rounded,
        title: '섭취 방법',
        body: _intakeInfoBody(preview),
        missingMessage: missingSections.contains('intake_method')
            ? '사진을 더 찍어서 보강해주세요.'
            : null,
        onEdit: preview == null ? null : () => _editIntakeInfo(context),
      ),
      const SizedBox(height: AppSpace.sm),
      _SupplementInfoCard(
        icon: Icons.shield_rounded,
        title: '섭취 시 주의사항',
        body: _precautionInfoBody(preview),
        missingMessage: missingSections.contains('precautions')
            ? '사진을 더 찍어서 보강해주세요.'
            : null,
        onEdit: preview == null ? null : () => _editPrecautionsInfo(context),
      ),
    ];
  }

  List<_SupplementReviewGroup> _supplementReviewGroups(
    AppController? controller,
  ) {
    final List<SupplementAnalysisPreview> multiPreviews =
        controller?.multiImageAnalysisPreview?.previews ??
        const <SupplementAnalysisPreview>[];
    if (multiPreviews.length > 1) {
      return _groupSupplementPreviews(multiPreviews);
    }
    final SupplementAnalysisPreview? singlePreview =
        controller?.analysisPreview;
    if (singlePreview == null) return const <_SupplementReviewGroup>[];
    return <_SupplementReviewGroup>[
      _SupplementReviewGroup(
        label: _supplementPreviewLabel(singlePreview, 0),
        preview: singlePreview,
        sourcePreviews: <SupplementAnalysisPreview>[singlePreview],
      ),
    ];
  }

  List<_SupplementReviewGroup> _groupSupplementPreviews(
    List<SupplementAnalysisPreview> previews,
  ) {
    final List<_MutableSupplementReviewGroup> groups =
        <_MutableSupplementReviewGroup>[];
    for (final SupplementAnalysisPreview preview in previews) {
      final String? identityKey = _supplementIdentityKey(preview);
      if (identityKey != null) {
        final _MutableSupplementReviewGroup? existing = groups
            .cast<_MutableSupplementReviewGroup?>()
            .firstWhere(
              (_MutableSupplementReviewGroup? group) =>
                  group?.identityKey == identityKey,
              orElse: () => null,
            );
        if (existing != null) {
          existing.previews.add(preview);
          continue;
        }
        groups.add(
          _MutableSupplementReviewGroup(
            identityKey: identityKey,
            previews: <SupplementAnalysisPreview>[preview],
          ),
        );
        continue;
      }

      final _MutableSupplementReviewGroup? previous = groups.isEmpty
          ? null
          : groups.last;
      if (previous != null &&
          _canAttachIdentitylessPreview(previous, preview)) {
        previous.previews.add(preview);
        continue;
      }
      groups.add(
        _MutableSupplementReviewGroup(
          identityKey: null,
          previews: <SupplementAnalysisPreview>[preview],
        ),
      );
    }

    return <_SupplementReviewGroup>[
      for (int index = 0; index < groups.length; index++)
        _buildSupplementReviewGroup(groups[index].previews, index),
    ];
  }

  _SupplementReviewGroup _buildSupplementReviewGroup(
    List<SupplementAnalysisPreview> previews,
    int index,
  ) {
    final SupplementAnalysisPreview preview = _mergeSupplementGroupPreview(
      previews,
    );
    return _SupplementReviewGroup(
      label: _supplementPreviewLabel(preview, index),
      preview: preview,
      sourcePreviews: previews,
    );
  }

  bool _canAttachIdentitylessPreview(
    _MutableSupplementReviewGroup previous,
    SupplementAnalysisPreview preview,
  ) {
    if (!_hasSupplementFactsEvidence(preview)) return false;
    final bool previousHasProductIdentity = previous.previews.any(
      (SupplementAnalysisPreview item) => _supplementIdentityKey(item) != null,
    );
    if (!previousHasProductIdentity) return false;
    return !previous.previews.any(_hasSupplementFactsEvidence);
  }

  SupplementAnalysisPreview _mergeSupplementGroupPreview(
    List<SupplementAnalysisPreview> previews,
  ) {
    if (previews.length == 1) return previews.first;
    final SupplementAnalysisPreview base = _representativePreview(previews);
    final SupplementParsedProduct parsedProduct = _mergedParsedProduct(
      previews,
      base,
    );
    final List<SupplementIngredientCandidate> ingredients = _mergedIngredients(
      previews,
    );
    final List<SupplementPreviewLabelSection> labelSections =
        _mergedLabelSections(previews);
    final List<SupplementPreviewPrecaution> precautions = _mergedPrecautions(
      previews,
    );
    final List<SupplementPreviewFunctionalClaim> functionalClaims =
        _mergedFunctionalClaims(previews);
    final List<SupplementPreviewEvidenceSpan> evidenceSpans =
        _mergedEvidenceSpans(previews);
    final SupplementPreviewIntakeMethod intakeMethod = _mergedIntakeMethod(
      previews,
      base,
    );
    final List<String> missingRequiredSections = _calculatedMissingSections(
      parsedProduct: parsedProduct,
      ingredients: ingredients,
      labelSections: labelSections,
      intakeMethod: intakeMethod,
      precautions: precautions,
    );
    return SupplementAnalysisPreview(
      analysisId: base.analysisId,
      status: base.status,
      parsedProduct: parsedProduct,
      ingredientCandidates: ingredients,
      layoutAvailable: previews.any(
        (SupplementAnalysisPreview preview) => preview.layoutAvailable,
      ),
      layoutFallbackReason: base.layoutFallbackReason,
      labelSections: labelSections,
      intakeMethod: intakeMethod,
      precautions: precautions,
      functionalClaims: functionalClaims,
      evidenceSpans: evidenceSpans,
      imageQualityReport: base.imageQualityReport,
      analysisScope: base.analysisScope,
      actionRequired: _mergedActionRequired(previews),
      detectedProductRegions: base.detectedProductRegions,
      selectedRegionId: base.selectedRegionId,
      missingRequiredSections: missingRequiredSections,
      imageRole: 'mixed',
      multiImageGroupId: base.multiImageGroupId,
      sourceType: base.sourceType,
      identityConflict: base.identityConflict,
      pipelineMetadata: _mergedPipelineMetadata(
        previews,
        missingRequiredSections,
        labelSections.length,
      ),
      lowConfidenceFields: _mergedStrings(
        previews.map(
          (SupplementAnalysisPreview preview) => preview.lowConfidenceFields,
        ),
      ),
      warnings: _mergedStrings(
        previews.map((SupplementAnalysisPreview preview) => preview.warnings),
      ),
      algorithmVersion: base.algorithmVersion,
      sourceManifestVersion: base.sourceManifestVersion,
      expiresAt: base.expiresAt,
    );
  }

  SupplementAnalysisPreview _representativePreview(
    List<SupplementAnalysisPreview> previews,
  ) {
    SupplementAnalysisPreview best = previews.first;
    int bestScore = _previewMergeScore(best);
    for (final SupplementAnalysisPreview preview in previews.skip(1)) {
      final int score = _previewMergeScore(preview);
      if (score > bestScore) {
        best = preview;
        bestScore = score;
      }
    }
    return best;
  }

  int _previewMergeScore(SupplementAnalysisPreview preview) {
    return preview.ingredientCandidates.length * 6 +
        preview.labelSections.length * 4 +
        preview.evidenceSpans.length +
        (_nonEmpty(preview.parsedProduct.productName) == null ? 0 : 5) +
        (_nonEmpty(preview.parsedProduct.manufacturer) == null ? 0 : 2) +
        (_nonEmpty(preview.intakeMethod.text) == null ? 0 : 3) +
        preview.precautions.length * 3;
  }

  SupplementParsedProduct _mergedParsedProduct(
    List<SupplementAnalysisPreview> previews,
    SupplementAnalysisPreview base,
  ) {
    return SupplementParsedProduct(
      productName:
          _firstNonEmpty(
            previews.map(
              (SupplementAnalysisPreview preview) =>
                  preview.parsedProduct.productName,
            ),
          ) ??
          base.parsedProduct.productName,
      manufacturer:
          _firstNonEmpty(
            previews.map(
              (SupplementAnalysisPreview preview) =>
                  preview.parsedProduct.manufacturer,
            ),
          ) ??
          base.parsedProduct.manufacturer,
      servingSize:
          _firstNonEmpty(
            previews.map(
              (SupplementAnalysisPreview preview) =>
                  preview.parsedProduct.servingSize,
            ),
          ) ??
          base.parsedProduct.servingSize,
      dailyServings:
          _firstDailyServings(previews) ?? base.parsedProduct.dailyServings,
    );
  }

  List<SupplementIngredientCandidate> _mergedIngredients(
    List<SupplementAnalysisPreview> previews,
  ) {
    final Set<String> seen = <String>{};
    final List<SupplementIngredientCandidate> merged =
        <SupplementIngredientCandidate>[];
    for (final SupplementAnalysisPreview preview in previews) {
      for (final SupplementIngredientCandidate ingredient
          in preview.ingredientCandidates) {
        final String key = _ingredientKey(ingredient);
        if (seen.add(key)) merged.add(ingredient);
      }
    }
    return merged;
  }

  List<SupplementPreviewLabelSection> _mergedLabelSections(
    List<SupplementAnalysisPreview> previews,
  ) {
    final Set<String> seen = <String>{};
    final List<SupplementPreviewLabelSection> merged =
        <SupplementPreviewLabelSection>[];
    for (final SupplementAnalysisPreview preview in previews) {
      for (final SupplementPreviewLabelSection section
          in preview.labelSections) {
        final String key = <String>[
          section.sectionType,
          section.headingText ?? '',
          section.textBundle ?? '',
        ].map(_normalizeKeyPart).join('|');
        if (seen.add(key)) merged.add(section);
      }
    }
    return merged;
  }

  List<SupplementPreviewPrecaution> _mergedPrecautions(
    List<SupplementAnalysisPreview> previews,
  ) {
    final Set<String> seen = <String>{};
    final List<SupplementPreviewPrecaution> merged =
        <SupplementPreviewPrecaution>[];
    for (final SupplementAnalysisPreview preview in previews) {
      for (final SupplementPreviewPrecaution precaution
          in preview.precautions) {
        final String key = _normalizeKeyPart(precaution.text);
        if (seen.add(key)) merged.add(precaution);
      }
    }
    return merged;
  }

  List<SupplementPreviewFunctionalClaim> _mergedFunctionalClaims(
    List<SupplementAnalysisPreview> previews,
  ) {
    final Set<String> seen = <String>{};
    final List<SupplementPreviewFunctionalClaim> merged =
        <SupplementPreviewFunctionalClaim>[];
    for (final SupplementAnalysisPreview preview in previews) {
      for (final SupplementPreviewFunctionalClaim claim
          in preview.functionalClaims) {
        final String key = _normalizeKeyPart(claim.text);
        if (seen.add(key)) merged.add(claim);
      }
    }
    return merged;
  }

  List<SupplementPreviewEvidenceSpan> _mergedEvidenceSpans(
    List<SupplementAnalysisPreview> previews,
  ) {
    final Set<String> seen = <String>{};
    final List<SupplementPreviewEvidenceSpan> merged =
        <SupplementPreviewEvidenceSpan>[];
    for (final SupplementAnalysisPreview preview in previews) {
      for (final SupplementPreviewEvidenceSpan span in preview.evidenceSpans) {
        final String key = span.spanId.isEmpty
            ? _normalizeKeyPart('${span.sectionType}|${span.textExcerpt}')
            : span.spanId;
        if (seen.add(key)) merged.add(span);
      }
    }
    return merged;
  }

  SupplementPreviewIntakeMethod _mergedIntakeMethod(
    List<SupplementAnalysisPreview> previews,
    SupplementAnalysisPreview base,
  ) {
    for (final SupplementAnalysisPreview preview in previews) {
      if (_nonEmpty(preview.intakeMethod.text) != null) {
        return preview.intakeMethod;
      }
    }
    return base.intakeMethod;
  }

  SupplementImagePipelineMetadata _mergedPipelineMetadata(
    List<SupplementAnalysisPreview> previews,
    List<String> missingRequiredSections,
    int sectionCount,
  ) {
    final SupplementImagePipelineMetadata base = _representativePreview(
      previews,
    ).pipelineMetadata;
    return SupplementImagePipelineMetadata(
      intakeCompleted: previews.every(
        (SupplementAnalysisPreview preview) =>
            preview.pipelineMetadata.intakeCompleted,
      ),
      imageCount: previews.length,
      imageRole: 'mixed',
      visionRoiUsed: previews.any(
        (SupplementAnalysisPreview preview) =>
            preview.pipelineMetadata.visionRoiUsed,
      ),
      ocrStatus: _mergedStageStatus(
        previews.map(
          (SupplementAnalysisPreview preview) =>
              preview.pipelineMetadata.ocrStatus,
        ),
      ),
      visionStatus: _mergedStageStatus(
        previews.map(
          (SupplementAnalysisPreview preview) =>
              preview.pipelineMetadata.visionStatus,
        ),
      ),
      llmStatus: _mergedStageStatus(
        previews.map(
          (SupplementAnalysisPreview preview) =>
              preview.pipelineMetadata.llmStatus,
        ),
      ),
      ocrProvider:
          _firstNonEmpty(
            previews.map(
              (SupplementAnalysisPreview preview) =>
                  preview.pipelineMetadata.ocrProvider,
            ),
          ) ??
          base.ocrProvider,
      ocrTextPresent: previews.any(
        (SupplementAnalysisPreview preview) =>
            preview.pipelineMetadata.ocrTextPresent,
      ),
      ocrConfidenceBucket: _mergedConfidenceBucket(
        previews.map(
          (SupplementAnalysisPreview preview) =>
              preview.pipelineMetadata.ocrConfidenceBucket,
        ),
      ),
      roiCount: previews.fold<int>(
        0,
        (int total, SupplementAnalysisPreview preview) =>
            total + preview.pipelineMetadata.roiCount,
      ),
      sectionCount: sectionCount,
      llmParserUsed: previews.any(
        (SupplementAnalysisPreview preview) =>
            preview.pipelineMetadata.llmParserUsed,
      ),
      parserContractVersion:
          _firstNonEmpty(
            previews.map(
              (SupplementAnalysisPreview preview) =>
                  preview.pipelineMetadata.parserContractVersion,
            ),
          ) ??
          base.parserContractVersion,
      missingRequiredSections: missingRequiredSections,
      rawImageStored: previews.any(
        (SupplementAnalysisPreview preview) =>
            preview.pipelineMetadata.rawImageStored,
      ),
      rawOcrTextStored: previews.any(
        (SupplementAnalysisPreview preview) =>
            preview.pipelineMetadata.rawOcrTextStored,
      ),
    );
  }

  List<String> _calculatedMissingSections({
    required SupplementParsedProduct parsedProduct,
    required List<SupplementIngredientCandidate> ingredients,
    required List<SupplementPreviewLabelSection> labelSections,
    required SupplementPreviewIntakeMethod intakeMethod,
    required List<SupplementPreviewPrecaution> precautions,
  }) {
    final Set<String> sectionTypes = labelSections
        .map((SupplementPreviewLabelSection section) => section.sectionType)
        .toSet();
    return <String>[
      if (_nonEmpty(parsedProduct.productName) == null) 'product_name',
      if (ingredients.isEmpty && !sectionTypes.contains('supplement_facts'))
        'supplement_facts',
      if (_nonEmpty(intakeMethod.text) == null &&
          !sectionTypes.contains('intake_method'))
        'intake_method',
      if (precautions.isEmpty && !sectionTypes.contains('precautions'))
        'precautions',
    ];
  }

  String _mergedActionRequired(List<SupplementAnalysisPreview> previews) {
    if (previews.any(
      (SupplementAnalysisPreview preview) =>
          preview.actionRequired == 'blocked',
    )) {
      return 'blocked';
    }
    if (previews.any(
      (SupplementAnalysisPreview preview) =>
          preview.actionRequired == 'additional_label_image_required',
    )) {
      return 'additional_label_image_required';
    }
    if (previews.any(
      (SupplementAnalysisPreview preview) =>
          preview.actionRequired == 'review_required',
    )) {
      return 'review_required';
    }
    return previews.first.actionRequired;
  }

  bool _hasSupplementFactsEvidence(SupplementAnalysisPreview preview) {
    if (preview.ingredientCandidates.isNotEmpty) return true;
    return preview.labelSections.any(
      (SupplementPreviewLabelSection section) =>
          section.sectionType == 'supplement_facts',
    );
  }

  String? _supplementIdentityKey(SupplementAnalysisPreview preview) {
    final String? productName = _nonEmpty(preview.parsedProduct.productName);
    final String? manufacturer = _nonEmpty(preview.parsedProduct.manufacturer);
    if (productName == null && manufacturer == null) return null;
    return <String>[
      ?manufacturer,
      ?productName,
    ].map(_normalizeKeyPart).join('|');
  }

  String _supplementPreviewLabel(SupplementAnalysisPreview preview, int index) {
    final String? productName =
        _nonEmpty(preview.parsedProduct.productName) ??
        _nonEmpty(
          preview.ingredientCandidates.isEmpty
              ? null
              : preview.ingredientCandidates.first.displayName,
        );
    return productName ?? '영양제 ${index + 1}';
  }

  String _ingredientKey(SupplementIngredientCandidate ingredient) {
    return <String>[
      ingredient.displayName,
      ingredient.amount?.toString() ?? '',
      ingredient.unit ?? '',
    ].map(_normalizeKeyPart).join('|');
  }

  String _mergedStageStatus(Iterable<String> statuses) {
    final Set<String> values = statuses.toSet();
    if (values.contains('success')) return 'success';
    if (values.contains('warning')) return 'warning';
    if (values.contains('failed')) return 'failed';
    return 'skipped';
  }

  String _mergedConfidenceBucket(Iterable<String> buckets) {
    final Set<String> values = buckets.toSet();
    if (values.contains('high')) return 'high';
    if (values.contains('medium')) return 'medium';
    if (values.contains('low')) return 'low';
    if (values.contains('unknown')) return 'unknown';
    return 'none';
  }

  List<String> _mergedStrings(Iterable<List<String>> values) {
    final Set<String> seen = <String>{};
    final List<String> merged = <String>[];
    for (final List<String> list in values) {
      for (final String value in list) {
        if (seen.add(value)) merged.add(value);
      }
    }
    return merged;
  }

  String? _firstNonEmpty(Iterable<String?> values) {
    for (final String? value in values) {
      final String? normalized = _nonEmpty(value);
      if (normalized != null) return normalized;
    }
    return null;
  }

  double? _firstDailyServings(List<SupplementAnalysisPreview> previews) {
    for (final SupplementAnalysisPreview preview in previews) {
      final double? dailyServings = preview.parsedProduct.dailyServings;
      if (dailyServings != null) return dailyServings;
    }
    return null;
  }

  String _normalizeKeyPart(String value) {
    return value.trim().toLowerCase().replaceAll(RegExp(r'\s+'), ' ');
  }

  int _activeSupplementPreviewIndex(int itemCount) {
    if (itemCount == 0) return 0;
    if (_selectedSupplementPreviewIndex < 0) return 0;
    if (_selectedSupplementPreviewIndex >= itemCount) {
      return itemCount - 1;
    }
    return _selectedSupplementPreviewIndex;
  }

  List<String> _missingRequiredSections(SupplementAnalysisPreview? preview) {
    final List<String> pipelineMissing =
        preview?.pipelineMetadata.missingRequiredSections ?? const <String>[];
    if (pipelineMissing.isNotEmpty) return pipelineMissing;
    return preview?.missingRequiredSections ?? const <String>[];
  }

  String _productInfoBody(SupplementAnalysisPreview? preview) {
    final String? productName =
        _nonEmpty(_productNameController.text) ??
        preview?.parsedProduct.productName;
    final String? manufacturer =
        _nonEmpty(_manufacturerController.text) ??
        preview?.parsedProduct.manufacturer;
    if (productName == null && manufacturer == null) {
      return '제품명을 확인할 수 없어요.';
    }
    if (manufacturer == null) return productName!;
    if (productName == null) return manufacturer;
    return '$productName\n$manufacturer';
  }

  Widget _ingredientInfoTable(SupplementAnalysisPreview? preview) {
    final List<_IngredientAmountRowData> rows = _ingredientAmountRows(preview);
    if (rows.isEmpty) {
      return const Text(
        '성분명과 함량을 확인할 수 없어요.',
        style: TextStyle(
          color: AppColor.ink,
          fontSize: 15,
          height: 1.45,
          fontWeight: FontWeight.w800,
          letterSpacing: 0,
        ),
      );
    }
    return _IngredientAmountTable(
      rows: rows,
      onSelectionChanged: _setIngredientDraftSelected,
      onAllSelectionChanged: _setAllIngredientDraftsSelected,
    );
  }

  List<_IngredientAmountRowData> _ingredientAmountRows(
    SupplementAnalysisPreview? preview,
  ) {
    if (_ingredientDrafts.isNotEmpty) {
      return <_IngredientAmountRowData>[
        for (int index = 0; index < _ingredientDrafts.length; index++)
          _ingredientAmountRowFromDraft(_ingredientDrafts[index], index),
      ];
    }
    final List<SupplementIngredientCandidate> candidates =
        preview?.ingredientCandidates.take(5).toList(growable: false) ??
        const <SupplementIngredientCandidate>[];
    return candidates
        .map(_ingredientAmountRowFromCandidate)
        .toList(growable: false);
  }

  String _intakeInfoBody(SupplementAnalysisPreview? preview) {
    if (_missingRequiredSections(preview).contains('intake_method')) {
      return '해당 이미지에는 해당하는 내용이 없습니다';
    }
    final String? directText = _nonEmpty(_intakeMethodTextController.text);
    if (directText != null) return directText;
    final String? previewText = _nonEmpty(preview?.intakeMethod.text);
    if (previewText != null) return previewText;
    final List<String> parts = <String>[
      if (_nonEmpty(_frequencyController.text) != null)
        _nonEmpty(_frequencyController.text)!,
      if (_splitCsv(_timeOfDayController.text).isNotEmpty)
        _splitCsv(_timeOfDayController.text).join(', '),
    ];
    final String structured = parts
        .where((String value) => value.trim().isNotEmpty)
        .join(' · ');
    return structured.isEmpty ? '섭취 방법을 확인할 수 없어요.' : structured;
  }

  String _precautionInfoBody(SupplementAnalysisPreview? preview) {
    if (_missingRequiredSections(preview).contains('precautions')) {
      return '해당 이미지에는 해당하는 내용이 없습니다';
    }
    final List<String> confirmed = _confirmedPrecautions();
    if (confirmed.isNotEmpty) return confirmed.join('\n');
    final List<String> precautions =
        preview?.precautions
            .map((SupplementPreviewPrecaution item) => item.text)
            .toList() ??
        const <String>[];
    if (precautions.isEmpty) {
      return '주의사항을 확인할 수 없어요.';
    }
    return precautions.join('\n');
  }

  _IngredientAmountRowData _ingredientAmountRowFromCandidate(
    SupplementIngredientCandidate candidate,
  ) {
    return _IngredientAmountRowData(
      name: candidate.displayName,
      originalName: _visibleOriginalName(
        candidate.displayName,
        candidate.originalName,
      ),
      amount: _ingredientAmountText(candidate.amount, candidate.unit),
    );
  }

  _IngredientAmountRowData _ingredientAmountRowFromDraft(
    _IngredientReviewDraft draft,
    int index,
  ) {
    return _IngredientAmountRowData(
      draftIndex: index,
      selected: draft.selected,
      name: draft.displayName.isEmpty ? '성분명 확인 필요' : draft.displayName,
      originalName: _visibleOriginalName(draft.displayName, draft.originalName),
      amount: _ingredientAmountText(
        _parseOptionalDouble(draft.amountText),
        draft.unit,
      ),
    );
  }

  static String? _visibleOriginalName(String displayName, String? originalName) {
    final String display = displayName.trim();
    final String? original = _nonEmpty(originalName);
    if (original == null) return null;
    if (display.isNotEmpty && original.toLowerCase() == display.toLowerCase()) {
      return null;
    }
    return original;
  }

  String _ingredientAmountText(double? amount, String? unit) {
    if (amount == null) return '함량 확인 필요';
    final String amountText = _formatEditableAmount(amount);
    final String? normalizedUnit = _nonEmpty(unit);
    if (normalizedUnit == null) return amountText;
    return '$amountText $normalizedUnit';
  }

  Future<void> _editProductInfo(BuildContext context) async {
    await _showEditDialog(
      context,
      title: '영양제명 수정',
      fields: <Widget>[
        _ReviewTextField(
          controller: _productNameController,
          label: '제품명',
          hintText: '예: 비타민 D',
        ),
        const SizedBox(height: AppSpace.sm),
        _ReviewTextField(
          controller: _manufacturerController,
          label: '제조사',
          hintText: '라벨에 있으면 입력',
        ),
      ],
    );
  }

  Future<void> _editIngredientInfo(BuildContext context) async {
    if (_ingredientDrafts.length <= 1) {
      final bool? confirmed = await _showEditDialog(
        context,
        title: '성분 및 함량 수정',
        fields: <Widget>[
          _ReviewTextField(
            controller: _ingredientNameController,
            label: '대표 성분',
            hintText: '예: Vitamin D',
          ),
          if (_ingredientDrafts.isNotEmpty &&
              _visibleOriginalName(
                    _ingredientDrafts.first.displayName,
                    _ingredientDrafts.first.originalName,
                  ) !=
                  null) ...<Widget>[
            const SizedBox(height: AppSpace.xs),
            _OriginalIngredientNameText(
              originalName: _ingredientDrafts.first.originalName!,
            ),
          ],
          const SizedBox(height: AppSpace.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _ReviewTextField(
                  controller: _ingredientAmountController,
                  label: '함량',
                  hintText: '25',
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: _ReviewTextField(
                  controller: _ingredientUnitController,
                  label: '단위',
                  hintText: 'mg, mcg, IU',
                ),
              ),
            ],
          ),
        ],
      );
      if (confirmed == true && mounted) {
        setState(_syncSingleIngredientDraftFromFields);
      }
      return;
    }

    final List<int> selectedIndexes = <int>[
      for (int index = 0; index < _ingredientDrafts.length; index++)
        if (_ingredientDrafts[index].selected) index,
    ];
    if (selectedIndexes.length == 1) {
      await _editSingleIngredientDraft(context, selectedIndexes.single);
      return;
    }

    List<_IngredientReviewDraft> drafts = _ingredientDrafts
        .map((_IngredientReviewDraft draft) => draft)
        .toList();
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext dialogContext) {
        return StatefulBuilder(
          builder: (BuildContext context, StateSetter setDialogState) {
            return AlertDialog(
              title: const Text('성분 선택 및 수정'),
              content: SizedBox(
                width: double.maxFinite,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      const Text(
                        '체크된 성분만 저장돼요. 기타 원료처럼 함량이 없는 후보는 기본으로 제외했어요.',
                        style: TextStyle(
                          color: AppColor.inkSecondary,
                          fontSize: 13,
                          height: 1.35,
                          letterSpacing: 0,
                        ),
                      ),
                      const SizedBox(height: AppSpace.sm),
                      _IngredientBulkSelectionBar(
                        selectedCount: drafts
                            .where(
                              (_IngredientReviewDraft draft) => draft.selected,
                            )
                            .length,
                        selectableCount: drafts.length,
                        onPressed: drafts.isEmpty
                            ? null
                            : () {
                                final bool shouldSelectAll = !drafts.every(
                                  (_IngredientReviewDraft draft) =>
                                      draft.selected,
                                );
                                setDialogState(() {
                                  drafts = <_IngredientReviewDraft>[
                                    for (final _IngredientReviewDraft draft
                                        in drafts)
                                      draft.copyWith(selected: shouldSelectAll),
                                  ];
                                });
                              },
                      ),
                      const SizedBox(height: AppSpace.sm),
                      for (int index = 0; index < drafts.length; index++) ...[
                        _IngredientReviewTile(
                          draft: drafts[index],
                          onChanged: (_IngredientReviewDraft next) {
                            setDialogState(() {
                              drafts = <_IngredientReviewDraft>[
                                for (int i = 0; i < drafts.length; i++)
                                  i == index ? next : drafts[i],
                              ];
                            });
                          },
                        ),
                        if (index < drafts.length - 1)
                          const SizedBox(height: AppSpace.sm),
                      ],
                    ],
                  ),
                ),
              ),
              actions: <Widget>[
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(false),
                  child: const Text('취소'),
                ),
                FilledButton(
                  onPressed: () => Navigator.of(dialogContext).pop(true),
                  child: const Text('저장'),
                ),
              ],
            );
          },
        );
      },
    );
    if (confirmed == true && mounted) {
      setState(() {
        _ingredientDrafts = drafts;
        _syncPrimaryIngredientControllers();
      });
    }
  }

  Future<void> _editSingleIngredientDraft(
    BuildContext context,
    int draftIndex,
  ) async {
    final _IngredientReviewDraft draft = _ingredientDrafts[draftIndex];
    final TextEditingController nameController = TextEditingController(
      text: draft.displayName,
    );
    final TextEditingController amountController = TextEditingController(
      text: draft.amountText,
    );
    final TextEditingController unitController = TextEditingController(
      text: draft.unit,
    );
    try {
      final bool? confirmed = await _showEditDialog(
        context,
        title: '선택 성분 수정',
        fields: <Widget>[
          _ReviewTextField(
            controller: nameController,
            label: '대표 성분',
            hintText: '예: Vitamin D',
          ),
          if (_visibleOriginalName(draft.displayName, draft.originalName) !=
              null) ...<Widget>[
            const SizedBox(height: AppSpace.xs),
            _OriginalIngredientNameText(originalName: draft.originalName!),
          ],
          const SizedBox(height: AppSpace.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _ReviewTextField(
                  controller: amountController,
                  label: '함량',
                  hintText: '25',
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: _ReviewTextField(
                  controller: unitController,
                  label: '단위',
                  hintText: 'mg, mcg, IU',
                ),
              ),
            ],
          ),
        ],
      );
      if (confirmed == true && mounted) {
        setState(() {
          _ingredientDrafts = <_IngredientReviewDraft>[
            for (int index = 0; index < _ingredientDrafts.length; index++)
              index == draftIndex
                  ? _ingredientDrafts[index].copyWith(
                      displayName: nameController.text,
                      amountText: amountController.text,
                      unit: unitController.text,
                      selected: true,
                    )
                  : _ingredientDrafts[index],
          ];
          _syncPrimaryIngredientControllers();
        });
      }
    } finally {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        nameController.dispose();
        amountController.dispose();
        unitController.dispose();
      });
    }
  }

  Future<void> _editIntakeInfo(BuildContext context) async {
    await _showEditDialog(
      context,
      title: '섭취 방법 수정',
      fields: <Widget>[
        _ReviewTextField(
          controller: _intakeMethodTextController,
          label: '라벨 문장',
          hintText: '예: 하루 1회 1정',
        ),
        const SizedBox(height: AppSpace.sm),
        Row(
          children: <Widget>[
            Expanded(
              child: _ReviewTextField(
                controller: _frequencyController,
                label: '주기',
                hintText: 'daily',
              ),
            ),
            const SizedBox(width: AppSpace.sm),
            Expanded(
              child: _ReviewTextField(
                controller: _timeOfDayController,
                label: '복용 시간',
                hintText: 'morning, evening',
              ),
            ),
          ],
        ),
      ],
    );
  }

  Future<void> _editPrecautionsInfo(BuildContext context) async {
    await _showEditDialog(
      context,
      title: '주의사항 수정',
      fields: <Widget>[
        _ReviewTextField(
          controller: _precautionsController,
          label: '주의사항',
          hintText: '한 줄에 한 문장씩 입력',
          maxLines: 5,
        ),
      ],
    );
  }

  Future<bool?> _showEditDialog(
    BuildContext context, {
    required String title,
    required List<Widget> fields,
  }) async {
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext dialogContext) {
        return AlertDialog(
          title: Text(title),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: fields),
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('취소'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('저장'),
            ),
          ],
        );
      },
    );
    if (confirmed == true && mounted) {
      setState(() {});
    }
    return confirmed;
  }

  void _seedCorrectionFields(SupplementAnalysisPreview preview) {
    if (_seededAnalysisId == preview.analysisId) return;
    _seedingCorrectionFields = true;
    try {
      _seededAnalysisId = preview.analysisId;
      _productNameController.text = preview.parsedProduct.productName ?? '';
      _manufacturerController.text = preview.parsedProduct.manufacturer ?? '';
      SupplementIngredientCandidate? firstCandidate;
      for (final SupplementIngredientCandidate candidate
          in preview.ingredientCandidates) {
        if (candidate.amount != null && _nonEmpty(candidate.unit) != null) {
          firstCandidate = candidate;
          break;
        }
      }
      _ingredientNameController.text = firstCandidate?.displayName ?? '';
      _ingredientAmountController.text = firstCandidate?.amount == null
          ? ''
          : _formatEditableAmount(firstCandidate!.amount!);
      _ingredientUnitController.text = firstCandidate?.unit ?? '';
      _ingredientDrafts = _seedIngredientDrafts(preview.ingredientCandidates);
      _frequencyController.text =
          preview.intakeMethod.structured.frequency == 'unknown'
          ? ''
          : preview.intakeMethod.structured.frequency;
      _intakeMethodTextController.text = preview.intakeMethod.text ?? '';
      _precautionsController.text = preview.precautions
          .map((SupplementPreviewPrecaution precaution) => precaution.text)
          .join('\n');
      _timeOfDayController.text = preview.intakeMethod.structured.timeOfDay
          .join(', ');
    } finally {
      _seedingCorrectionFields = false;
    }
  }

  void _seedMealCorrectionFields(MealImageAnalysisPreview preview) {
    if (_seededMealAnalysisId == preview.analysisId) return;
    _seedingCorrectionFields = true;
    try {
      _seededMealAnalysisId = preview.analysisId;
      final MealFoodCandidate? firstCandidate = preview.foodCandidates.isEmpty
          ? null
          : preview.foodCandidates.first;
      _mealNameController.text = firstCandidate?.displayName ?? '';
      _mealPortionAmountController.text = _formatOptionalAmount(
        firstCandidate?.portionAmount,
      );
      _mealPortionUnitController.text = firstCandidate?.portionUnit ?? '';
      _mealKcalController.text = _formatOptionalAmount(firstCandidate?.kcal);
      _mealCarbController.text = _formatOptionalAmount(firstCandidate?.carbG);
      _mealProteinController.text = _formatOptionalAmount(
        firstCandidate?.proteinG,
      );
      _mealFatController.text = _formatOptionalAmount(firstCandidate?.fatG);
      _mealSodiumController.text = _formatOptionalAmount(
        firstCandidate?.sodiumMg,
      );
    } finally {
      _seedingCorrectionFields = false;
    }
  }

  String _primaryLabel(
    SupplementAnalysisPreview? preview,
    UserSupplementResponse? registered,
    MealRecordResponse? registeredMeal,
  ) {
    if (_isMeal) {
      if (registeredMeal != null) return '홈으로 돌아가기';
      if (widget.controller?.mealAnalysisPreview == null) return '다시 촬영하기';
      return _nonEmpty(_mealNameController.text) == null
          ? '음식 직접 입력'
          : '확인 후 식단 저장';
    }
    if (registered != null) return '챗으로 설명 보내기';
    if (preview == null) return '다시 촬영하기';
    if (!_hasReviewIngredient(preview)) return '성분 직접 입력';
    return '확인 후 저장';
  }

  Future<void> _handlePrimaryAction(BuildContext context) async {
    HapticFeedback.mediumImpact();
    if (widget.controller == null) {
      context.go('/shell/home');
      return;
    }
    final AppController appController = widget.controller!;
    if (_isMeal) {
      final MealImageAnalysisPreview? mealPreview =
          appController.mealAnalysisPreview;
      if (appController.lastRegisteredMeal != null) {
        context.go('/shell/home');
        return;
      }
      if (mealPreview == null) {
        appController.clearSupplementFlow();
        if (context.mounted) {
          context.go('/shell/camera');
        }
        return;
      }
      if (_nonEmpty(_mealNameController.text) == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('음식명을 입력한 뒤 식단 기록으로 저장해주세요.')),
        );
        return;
      }
      await appController.confirmMealImagePreview(
        _mealConfirmationRequest(mealPreview),
      );
      return;
    }
    if (appController.lastRegisteredSupplement != null) {
      final bool queued = appController.queueSupplementExplanationForChat();
      if (queued && context.mounted) {
        context.go('/shell/chat');
      }
      return;
    }
    final List<_SupplementReviewGroup> reviewGroups = _supplementReviewGroups(
      appController,
    );
    final SupplementAnalysisPreview? preview = reviewGroups.isEmpty
        ? null
        : reviewGroups[_activeSupplementPreviewIndex(reviewGroups.length)]
              .preview;
    if (preview == null) {
      appController.clearSupplementFlow();
      if (context.mounted) {
        context.go('/shell/camera');
      }
      return;
    }
    if (!_hasReviewIngredient(preview)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('성분명을 입력하거나 라벨 사진을 다시 추가해주세요.')),
      );
      return;
    }
    await appController.registerSupplement(
      _registrationRequest(preview),
      refreshImpact: true,
      explainWithLocalLlm: true,
    );
    if (!context.mounted || appController.lastRegisteredSupplement == null) {
      return;
    }
    final bool queued = appController.queueSupplementExplanationForChat();
    if (queued) {
      GoRouter.maybeOf(context)?.go('/shell/chat');
    }
  }

  Future<void> _showOcrTextTable(
    BuildContext context,
    SupplementAnalysisPreview preview,
  ) async {
    final List<_OcrTextRowData> rows = _ocrTextRows(preview);
    await showDialog<void>(
      context: context,
      builder: (BuildContext dialogContext) {
        return AlertDialog(
          title: const Text('OCR 텍스트 전체'),
          content: SizedBox(
            key: const ValueKey<String>('ocr-text-table'),
            width: double.maxFinite,
            child: SingleChildScrollView(
              child: rows.isEmpty
                  ? const Text(
                      '표시할 OCR 텍스트가 없습니다.',
                      style: TextStyle(
                        color: AppColor.inkSecondary,
                        fontSize: 14,
                        height: 1.45,
                        letterSpacing: 0,
                      ),
                    )
                  : _OcrTextTable(rows: rows),
            ),
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('닫기'),
            ),
          ],
        );
      },
    );
  }

  List<_OcrTextRowData> _ocrTextRows(SupplementAnalysisPreview preview) {
    final List<_OcrTextRowData> rows = <_OcrTextRowData>[];
    for (final SupplementPreviewEvidenceSpan span in preview.evidenceSpans) {
      final String? text = _nonEmpty(span.textExcerpt);
      if (text == null) continue;
      rows.add(
        _OcrTextRowData(
          section: _sectionLabel(span.sectionType),
          source: span.sourceType.toUpperCase(),
          text: text,
          confidence: _confidenceLabel(span.confidence),
        ),
      );
    }
    if (rows.isNotEmpty) return rows;
    for (final SupplementPreviewLabelSection section in preview.labelSections) {
      final String? text = _nonEmpty(section.textBundle);
      if (text == null) continue;
      rows.add(
        _OcrTextRowData(
          section: _sectionLabel(section.sectionType),
          source: 'SECTION',
          text: text,
          confidence: _confidenceLabel(section.confidence),
        ),
      );
    }
    return rows;
  }

  void _setIngredientDraftSelected(int index, bool selected) {
    if (index < 0 || index >= _ingredientDrafts.length) return;
    setState(() {
      _ingredientDrafts = <_IngredientReviewDraft>[
        for (int i = 0; i < _ingredientDrafts.length; i++)
          i == index
              ? _ingredientDrafts[i].copyWith(selected: selected)
              : _ingredientDrafts[i],
      ];
      _syncPrimaryIngredientControllers();
    });
  }

  void _setAllIngredientDraftsSelected(bool selected) {
    if (_ingredientDrafts.isEmpty) return;
    setState(() {
      _ingredientDrafts = <_IngredientReviewDraft>[
        for (final _IngredientReviewDraft draft in _ingredientDrafts)
          draft.copyWith(selected: selected),
      ];
      _syncPrimaryIngredientControllers();
    });
  }

  static String _sectionLabel(String sectionType) {
    return switch (sectionType) {
      'supplement_facts' || 'ingredients' || 'ingredient_candidates' => '성분표',
      'intake_method' => '섭취 방법',
      'precautions' => '주의사항',
      'product_name' => '제품명',
      _ => sectionType,
    };
  }

  static String _confidenceLabel(double? confidence) {
    if (confidence == null) return '-';
    return '${(confidence * 100).round()}%';
  }

  MealConfirmationRequest _mealConfirmationRequest(
    MealImageAnalysisPreview preview,
  ) {
    final MealFoodCandidate? firstCandidate = preview.foodCandidates.isEmpty
        ? null
        : preview.foodCandidates.first;
    return MealConfirmationRequest(
      analysisId: preview.analysisId,
      mealType: preview.mealType,
      eatenAt: preview.eatenAt,
      foodItems: <MealFoodItemInput>[
        MealFoodItemInput(
          displayName: _nonEmpty(_mealNameController.text) ?? '식단',
          portionAmount: _parseOptionalDouble(
            _mealPortionAmountController.text,
          ),
          portionUnit: _nonEmpty(_mealPortionUnitController.text),
          kcal: _parseOptionalDouble(_mealKcalController.text),
          carbG: _parseOptionalDouble(_mealCarbController.text),
          proteinG: _parseOptionalDouble(_mealProteinController.text),
          fatG: _parseOptionalDouble(_mealFatController.text),
          sodiumMg: _parseOptionalDouble(_mealSodiumController.text),
          confidence: firstCandidate?.confidence,
          source: firstCandidate?.source ?? 'manual',
        ),
      ],
    );
  }

  UserSupplementCreate _registrationRequest(SupplementAnalysisPreview preview) {
    final List<UserSupplementIngredientInput> ingredients =
        _selectedIngredientInputs();
    final String fallbackName = ingredients.isEmpty
        ? '영양제'
        : ingredients.first.displayName;
    return UserSupplementCreate(
      analysisId: preview.analysisId,
      displayName: _nonEmpty(_productNameController.text) ?? fallbackName,
      manufacturer: _nonEmpty(_manufacturerController.text),
      ingredients: ingredients,
      serving: SupplementServing(
        amount: preview.intakeMethod.structured.amountPerTime,
        unit:
            _nonEmpty(preview.parsedProduct.servingSize) ??
            _nonEmpty(preview.intakeMethod.structured.amountUnit),
        dailyServings:
            preview.parsedProduct.dailyServings ??
            preview.intakeMethod.structured.timesPerDay ??
            1,
      ),
      intakeSchedule: SupplementIntakeSchedule(
        frequency: _nonEmpty(_frequencyController.text) ?? 'daily',
        timeOfDay: _splitCsv(_timeOfDayController.text),
      ),
      precautionSnapshot: _confirmedPrecautions(),
      evidenceRefs: _registrationEvidenceRefs(preview),
    );
  }

  List<String> _registrationEvidenceRefs(SupplementAnalysisPreview preview) {
    final Set<String> seen = <String>{};
    final List<String> refs = <String>[];
    for (final SupplementPreviewEvidenceSpan span in preview.evidenceSpans) {
      final String ref = span.spanId.trim();
      if (ref.isEmpty || !seen.add(ref)) {
        continue;
      }
      refs.add(ref);
      if (refs.length >= 80) {
        break;
      }
    }
    return refs;
  }

  String _registrationIngredientSource(String source) {
    final String normalized = source.trim();
    if (normalized == 'user_confirmed' || normalized == 'ocr_llm_preview') {
      return normalized;
    }
    return 'ocr_llm_preview';
  }

  List<String> _confirmedPrecautions() {
    final Set<String> seen = <String>{};
    final List<String> values = <String>[];
    for (final String line in _precautionsController.text.split('\n')) {
      final String normalized = line.trim();
      if (normalized.isEmpty || !seen.add(normalized)) {
        continue;
      }
      values.add(normalized);
      if (values.length >= 40) {
        break;
      }
    }
    return values;
  }

  bool _hasReviewIngredient(SupplementAnalysisPreview preview) {
    return _selectedIngredientInputs().isNotEmpty ||
        _correctedIngredient() != null;
  }

  Future<void> _handleAnalysisExplanation(AppController controller) async {
    HapticFeedback.selectionClick();
    await controller.explainSupplementAnalysis(useLocalLlm: true);
  }

  UserSupplementIngredientInput? _correctedIngredient() {
    final String? name = _nonEmpty(_ingredientNameController.text);
    if (name == null) return null;
    return UserSupplementIngredientInput(
      displayName: name,
      originalName: _primaryIngredientOriginalName(name),
      nutrientCode: null,
      amount: _parseOptionalDouble(_ingredientAmountController.text),
      unit: _nonEmpty(_ingredientUnitController.text),
      confidence: 1,
      source: 'user_confirmed',
    );
  }

  List<UserSupplementIngredientInput> _selectedIngredientInputs() {
    final List<UserSupplementIngredientInput> selected = _ingredientDrafts
        .where(
          (_IngredientReviewDraft draft) => draft.selected && draft.isValid,
        )
        .map(
          (_IngredientReviewDraft draft) => draft.toInput(
            source: _registrationIngredientSource(draft.source),
          ),
        )
        .toList(growable: false);
    if (selected.isNotEmpty) return selected;
    final UserSupplementIngredientInput? corrected = _correctedIngredient();
    if (corrected == null) return const <UserSupplementIngredientInput>[];
    return <UserSupplementIngredientInput>[corrected];
  }

  String? _primaryIngredientOriginalName(String displayName) {
    final String displayKey = displayName.trim().toLowerCase();
    for (final _IngredientReviewDraft draft in _ingredientDrafts) {
      if (draft.displayName.trim().toLowerCase() == displayKey) {
        return _nonEmpty(draft.originalName);
      }
    }
    for (final _IngredientReviewDraft draft in _ingredientDrafts) {
      final String? originalName = _nonEmpty(draft.originalName);
      if (originalName != null) return originalName;
    }
    return null;
  }

  void _syncSingleIngredientDraftFromFields() {
    final UserSupplementIngredientInput? corrected = _correctedIngredient();
    if (corrected == null) {
      _ingredientDrafts = const <_IngredientReviewDraft>[];
      return;
    }
    _ingredientDrafts = <_IngredientReviewDraft>[
      _IngredientReviewDraft.fromInput(corrected),
    ];
  }

  void _syncPrimaryIngredientControllers() {
    _IngredientReviewDraft? firstSelected;
    for (final _IngredientReviewDraft draft in _ingredientDrafts) {
      if (draft.selected && draft.isValid) {
        firstSelected = draft;
        break;
      }
    }
    _ingredientNameController.text = firstSelected?.displayName ?? '';
    _ingredientAmountController.text = firstSelected?.amountText ?? '';
    _ingredientUnitController.text = firstSelected?.unit ?? '';
  }

  List<_IngredientReviewDraft> _seedIngredientDrafts(
    List<SupplementIngredientCandidate> candidates,
  ) {
    return candidates
        .map(_IngredientReviewDraft.fromCandidate)
        .toList(growable: false);
  }

  static String _formatEditableAmount(double value) {
    return value == value.roundToDouble()
        ? value.toStringAsFixed(0)
        : value.toString();
  }

  static String _formatOptionalAmount(double? value) {
    if (value == null) return '';
    return _formatEditableAmount(value);
  }

  static double? _parseOptionalDouble(String value) {
    final String trimmed = value.trim();
    if (trimmed.isEmpty) return null;
    return double.tryParse(trimmed);
  }

  static List<String> _splitCsv(String value) {
    return value
        .split(',')
        .map((String part) => part.trim())
        .where((String part) => part.isNotEmpty)
        .toList(growable: false);
  }

  static String? _nonEmpty(String? value) {
    final String? trimmed = value?.trim();
    if (trimmed == null || trimmed.isEmpty) return null;
    return trimmed;
  }
}

class _SupplementReviewGroup {
  const _SupplementReviewGroup({
    required this.label,
    required this.preview,
    required this.sourcePreviews,
  });

  final String label;
  final SupplementAnalysisPreview preview;
  final List<SupplementAnalysisPreview> sourcePreviews;
}

class _MutableSupplementReviewGroup {
  _MutableSupplementReviewGroup({
    required this.identityKey,
    required this.previews,
  });

  final String? identityKey;
  final List<SupplementAnalysisPreview> previews;
}

class _IngredientReviewDraft {
  const _IngredientReviewDraft({
    required this.displayName,
    required this.originalName,
    required this.amountText,
    required this.unit,
    required this.selected,
    required this.nutrientCode,
    required this.confidence,
    required this.source,
    required this.dailyValuePercent,
  });

  factory _IngredientReviewDraft.fromCandidate(
    SupplementIngredientCandidate candidate,
  ) {
    final String amountText = candidate.amount == null
        ? ''
        : _AnalysisResultScreenState._formatEditableAmount(candidate.amount!);
    final bool hasAmountAndUnit =
        candidate.amount != null &&
        _AnalysisResultScreenState._nonEmpty(candidate.unit) != null;
    return _IngredientReviewDraft(
      displayName: candidate.displayName,
      originalName: candidate.originalName,
      amountText: amountText,
      unit: candidate.unit ?? '',
      selected: hasAmountAndUnit,
      nutrientCode: candidate.nutrientCode,
      confidence: candidate.confidence,
      source: candidate.source,
      dailyValuePercent: candidate.dailyValuePercent,
    );
  }

  factory _IngredientReviewDraft.fromInput(
    UserSupplementIngredientInput input,
  ) {
    return _IngredientReviewDraft(
      displayName: input.displayName,
      originalName: input.originalName,
      amountText: input.amount == null
          ? ''
          : _AnalysisResultScreenState._formatEditableAmount(input.amount!),
      unit: input.unit ?? '',
      selected: true,
      nutrientCode: input.nutrientCode,
      confidence: input.confidence,
      source: input.source,
      dailyValuePercent: input.dailyValuePercent,
    );
  }

  final String displayName;
  final String? originalName;
  final String amountText;
  final String unit;
  final bool selected;
  final String? nutrientCode;
  final double confidence;
  final String source;
  final double? dailyValuePercent;

  bool get isValid {
    return _AnalysisResultScreenState._nonEmpty(displayName) != null;
  }

  UserSupplementIngredientInput toInput({required String source}) {
    return UserSupplementIngredientInput(
      displayName: displayName.trim(),
      originalName: _AnalysisResultScreenState._nonEmpty(originalName),
      nutrientCode: nutrientCode,
      amount: _AnalysisResultScreenState._parseOptionalDouble(amountText),
      unit: _AnalysisResultScreenState._nonEmpty(unit),
      confidence: selected ? 1 : confidence,
      source: selected ? 'user_confirmed' : source,
      dailyValuePercent: dailyValuePercent,
    );
  }

  _IngredientReviewDraft copyWith({
    String? displayName,
    String? amountText,
    String? unit,
    bool? selected,
  }) {
    return _IngredientReviewDraft(
      displayName: displayName ?? this.displayName,
      originalName: originalName,
      amountText: amountText ?? this.amountText,
      unit: unit ?? this.unit,
      selected: selected ?? this.selected,
      nutrientCode: nutrientCode,
      confidence: confidence,
      source: source,
      dailyValuePercent: dailyValuePercent,
    );
  }
}

class _OriginalIngredientNameText extends StatelessWidget {
  const _OriginalIngredientNameText({required this.originalName});

  final String originalName;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Text(
        '원문: $originalName',
        style: const TextStyle(
          color: AppColor.inkSecondary,
          fontSize: 12,
          height: 1.35,
          fontWeight: FontWeight.w700,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _IngredientReviewTile extends StatelessWidget {
  const _IngredientReviewTile({required this.draft, required this.onChanged});

  final _IngredientReviewDraft draft;
  final ValueChanged<_IngredientReviewDraft> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpace.sm),
      decoration: BoxDecoration(
        color: AppColor.section,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(
          color: draft.selected ? AppColor.brand : const Color(0xFFE4E7E2),
        ),
      ),
      child: Column(
        children: <Widget>[
          CheckboxListTile(
            value: draft.selected,
            contentPadding: EdgeInsets.zero,
            controlAffinity: ListTileControlAffinity.leading,
            title: Text(
              draft.displayName.isEmpty ? '성분명 없음' : draft.displayName,
              style: const TextStyle(
                color: AppColor.ink,
                fontSize: 14,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                if (_AnalysisResultScreenState._visibleOriginalName(
                      draft.displayName,
                      draft.originalName,
                    ) !=
                    null)
                  Text(
                    '원문: ${draft.originalName}',
                    style: const TextStyle(
                      color: AppColor.inkSecondary,
                      fontSize: 12,
                      height: 1.3,
                      letterSpacing: 0,
                    ),
                  ),
                Text(
                  draft.amountText.isEmpty && draft.unit.isEmpty
                      ? '함량이 없어 기본 제외됨'
                      : '${draft.amountText} ${draft.unit}'.trim(),
                  style: const TextStyle(
                    color: AppColor.inkSecondary,
                    fontSize: 12,
                    height: 1.3,
                    letterSpacing: 0,
                  ),
                ),
              ],
            ),
            onChanged: (bool? value) {
              onChanged(draft.copyWith(selected: value ?? false));
            },
          ),
          TextFormField(
            initialValue: draft.displayName,
            decoration: const InputDecoration(
              labelText: '성분명',
              isDense: true,
              filled: true,
            ),
            onChanged: (String value) {
              onChanged(draft.copyWith(displayName: value));
            },
          ),
          const SizedBox(height: AppSpace.xs),
          Row(
            children: <Widget>[
              Expanded(
                child: TextFormField(
                  initialValue: draft.amountText,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  decoration: const InputDecoration(
                    labelText: '함량',
                    isDense: true,
                    filled: true,
                  ),
                  onChanged: (String value) {
                    onChanged(draft.copyWith(amountText: value));
                  },
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: TextFormField(
                  initialValue: draft.unit,
                  decoration: const InputDecoration(
                    labelText: '단위',
                    isDense: true,
                    filled: true,
                  ),
                  onChanged: (String value) {
                    onChanged(draft.copyWith(unit: value));
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _IngredientAmountRowData {
  const _IngredientAmountRowData({
    required this.name,
    required this.amount,
    this.originalName,
    this.draftIndex,
    this.selected = false,
  });

  final String name;
  final String amount;
  final String? originalName;
  final int? draftIndex;
  final bool selected;
}

class _IngredientAmountTable extends StatelessWidget {
  const _IngredientAmountTable({
    required this.rows,
    required this.onSelectionChanged,
    required this.onAllSelectionChanged,
  });

  final List<_IngredientAmountRowData> rows;
  final void Function(int index, bool selected) onSelectionChanged;
  final ValueChanged<bool> onAllSelectionChanged;

  @override
  Widget build(BuildContext context) {
    final List<_IngredientAmountRowData> selectableRows = rows
        .where((_IngredientAmountRowData row) => row.draftIndex != null)
        .toList(growable: false);
    final int selectedCount = selectableRows
        .where((_IngredientAmountRowData row) => row.selected)
        .length;
    final int selectableCount = selectableRows.length;
    final bool allSelected =
        selectableCount > 0 && selectedCount == selectableCount;
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: const Color(0xFFE7EAF0)),
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            _IngredientBulkSelectionBar(
              selectedCount: selectedCount,
              selectableCount: selectableCount,
              onPressed: selectableCount == 0
                  ? null
                  : () => onAllSelectionChanged(!allSelected),
            ),
            const Divider(height: 1, thickness: 1, color: Color(0xFFE7EAF0)),
            Table(
              defaultVerticalAlignment: TableCellVerticalAlignment.middle,
              columnWidths: const <int, TableColumnWidth>{
                0: FixedColumnWidth(42),
                1: FlexColumnWidth(1.35),
                2: FlexColumnWidth(1),
              },
              border: const TableBorder(
                horizontalInside: BorderSide(color: Color(0xFFE7EAF0)),
              ),
              children: <TableRow>[
                const TableRow(
                  decoration: BoxDecoration(color: Color(0xFFFFF7D6)),
                  children: <Widget>[
                    _IngredientAmountCell(text: '선택', isHeader: true),
                    _IngredientAmountCell(text: '성분명', isHeader: true),
                    _IngredientAmountCell(text: '함량', isHeader: true),
                  ],
                ),
                for (final MapEntry<int, _IngredientAmountRowData> entry
                    in rows.asMap().entries)
                  TableRow(
                    children: <Widget>[
                      _IngredientSelectionCell(
                        row: entry.value,
                        rowIndex: entry.key,
                        onSelectionChanged: onSelectionChanged,
                      ),
                      _IngredientAmountCell(
                        text: entry.value.name,
                        secondaryText: entry.value.originalName == null
                            ? null
                            : '원문: ${entry.value.originalName}',
                      ),
                      _IngredientAmountCell(text: entry.value.amount),
                    ],
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _IngredientBulkSelectionBar extends StatelessWidget {
  const _IngredientBulkSelectionBar({
    required this.selectedCount,
    required this.selectableCount,
    required this.onPressed,
  });

  final int selectedCount;
  final int selectableCount;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final bool allSelected =
        selectableCount > 0 && selectedCount == selectableCount;
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.sm,
        AppSpace.xs,
        AppSpace.xs,
        AppSpace.xs,
      ),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              '선택 $selectedCount/$selectableCount',
              style: const TextStyle(
                color: AppColor.inkSecondary,
                fontSize: 12,
                fontWeight: FontWeight.w800,
                height: 1.25,
                letterSpacing: 0,
              ),
            ),
          ),
          TextButton.icon(
            key: const ValueKey<String>('ingredient-select-all-button'),
            onPressed: onPressed,
            style: TextButton.styleFrom(
              foregroundColor: AppColor.ink,
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpace.xs,
                vertical: 2,
              ),
              minimumSize: const Size(0, 32),
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            icon: Icon(
              allSelected ? Icons.remove_done_rounded : Icons.done_all_rounded,
              size: 17,
            ),
            label: Text(
              allSelected ? '전체 해제' : '전체 선택',
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _IngredientSelectionCell extends StatelessWidget {
  const _IngredientSelectionCell({
    required this.row,
    required this.rowIndex,
    required this.onSelectionChanged,
  });

  final _IngredientAmountRowData row;
  final int rowIndex;
  final void Function(int index, bool selected) onSelectionChanged;

  @override
  Widget build(BuildContext context) {
    final int? draftIndex = row.draftIndex;
    return Center(
      child: Checkbox(
        key: ValueKey<String>('ingredient-row-checkbox-$rowIndex'),
        value: row.selected,
        visualDensity: VisualDensity.compact,
        onChanged: draftIndex == null
            ? null
            : (bool? selected) {
                onSelectionChanged(draftIndex, selected ?? false);
              },
      ),
    );
  }
}

class _OcrTextRowData {
  const _OcrTextRowData({
    required this.section,
    required this.source,
    required this.text,
    required this.confidence,
  });

  final String section;
  final String source;
  final String text;
  final String confidence;
}

class _OcrTextTable extends StatelessWidget {
  const _OcrTextTable({required this.rows});

  final List<_OcrTextRowData> rows;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Colors.white,
          border: Border.all(color: const Color(0xFFE7EAF0)),
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        child: Table(
          defaultVerticalAlignment: TableCellVerticalAlignment.middle,
          columnWidths: const <int, TableColumnWidth>{
            0: FixedColumnWidth(76),
            1: FixedColumnWidth(70),
            2: FlexColumnWidth(1),
            3: FixedColumnWidth(58),
          },
          border: const TableBorder(
            horizontalInside: BorderSide(color: Color(0xFFE7EAF0)),
          ),
          children: <TableRow>[
            const TableRow(
              decoration: BoxDecoration(color: Color(0xFFFFF7D6)),
              children: <Widget>[
                _IngredientAmountCell(text: '구역', isHeader: true),
                _IngredientAmountCell(text: '출처', isHeader: true),
                _IngredientAmountCell(text: '텍스트', isHeader: true),
                _IngredientAmountCell(text: '신뢰도', isHeader: true),
              ],
            ),
            for (final _OcrTextRowData row in rows)
              TableRow(
                children: <Widget>[
                  _IngredientAmountCell(text: row.section),
                  _IngredientAmountCell(text: row.source),
                  _IngredientAmountCell(text: row.text),
                  _IngredientAmountCell(text: row.confidence),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _IngredientAmountCell extends StatelessWidget {
  const _IngredientAmountCell({
    required this.text,
    this.secondaryText,
    this.isHeader = false,
  });

  final String text;
  final String? secondaryText;
  final bool isHeader;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.sm,
        vertical: AppSpace.xs,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            text,
            softWrap: true,
            style: TextStyle(
              color: isHeader ? AppColor.inkSecondary : AppColor.ink,
              fontSize: isHeader ? 12 : 16,
              height: 1.35,
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          if (secondaryText != null && secondaryText!.isNotEmpty)
            Text(
              secondaryText!,
              softWrap: true,
              style: const TextStyle(
                color: AppColor.inkSecondary,
                fontSize: 11,
                height: 1.3,
                fontWeight: FontWeight.w700,
                letterSpacing: 0,
              ),
            ),
        ],
      ),
    );
  }
}

class _AnalysisInProgressScreen extends StatelessWidget {
  const _AnalysisInProgressScreen({required this.isMeal});

  final bool isMeal;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.section,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: <Widget>[
            _ResultTopBar(isMeal: isMeal),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpace.page,
                  AppSpace.xl,
                  AppSpace.page,
                  AppSpace.xl,
                ),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 420),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Container(
                          width: 172,
                          height: 172,
                          padding: const EdgeInsets.all(AppSpace.md),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(AppRadius.xl),
                            boxShadow: AppShadow.elev1,
                          ),
                          child: Image.asset(
                            MascotFor.analyzing.asset,
                            fit: BoxFit.contain,
                          ),
                        ),
                        const SizedBox(height: AppSpace.lg),
                        const Text(
                          '분석을 하고 있어요.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: AppColor.ink,
                            fontSize: 24,
                            fontWeight: FontWeight.w900,
                            height: 1.18,
                            letterSpacing: 0,
                          ),
                        ),
                        const SizedBox(height: AppSpace.sm),
                        Text(
                          isMeal
                              ? '식단 후보를 확인하는 동안 다른 탭을 사용해도 괜찮아요.'
                              : 'OCR, YOLO, LLM 후보를 함께 확인하는 동안 다른 탭을 사용해도 괜찮아요.',
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            color: AppColor.inkSecondary,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            height: 1.45,
                            letterSpacing: 0,
                          ),
                        ),
                        const SizedBox(height: AppSpace.lg),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            onPressed: () => context.go('/shell/home'),
                            icon: const Icon(Icons.home_rounded),
                            label: const Text('메인으로 이동'),
                            style: FilledButton.styleFrom(
                              backgroundColor: AppColor.brand,
                              foregroundColor: AppColor.ink,
                              textStyle: const TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 0,
                              ),
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(
                                  AppRadius.full,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ResultTopBar extends StatelessWidget {
  const _ResultTopBar({required this.isMeal});

  final bool isMeal;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColor.section,
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page,
        AppSpace.sm,
        AppSpace.page,
        AppSpace.sm,
      ),
      child: Row(
        children: <Widget>[
          GestureDetector(
            onTap: () =>
                context.canPop() ? context.pop() : context.go('/shell/home'),
            child: const SizedBox(
              width: 40,
              height: 40,
              child: Icon(Icons.close_rounded, color: AppColor.ink, size: 24),
            ),
          ),
          const Spacer(),
          Text(
            isMeal ? '식단 분석' : '영양제 분석',
            style: const TextStyle(
              color: AppColor.ink,
              fontSize: 16,
              fontWeight: FontWeight.w800,
              letterSpacing: 0,
            ),
          ),
          const Spacer(),
          const SizedBox(width: 40, height: 40),
        ],
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.isMeal,
    required this.preview,
    required this.mealPreview,
    required this.registered,
    required this.registeredMeal,
    required this.busy,
    required this.onTap,
  });

  final bool isMeal;
  final SupplementAnalysisPreview? preview;
  final MealImageAnalysisPreview? mealPreview;
  final UserSupplementResponse? registered;
  final MealRecordResponse? registeredMeal;
  final bool busy;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final Widget card = Container(
      key: const ValueKey<String>('supplement-candidate-summary'),
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(
        AppSpace.cardInside,
        AppSpace.lg,
        AppSpace.cardInside,
        AppSpace.lg,
      ),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFFFFE07A), AppColor.brand],
        ),
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: AppColor.brand.withValues(alpha: 0.32),
            blurRadius: 18,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.42),
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Icon(
              isMeal ? Icons.restaurant_rounded : Icons.medication_rounded,
              color: AppColor.ink,
              size: 28,
            ),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  busy ? '분석 중이에요' : '분석이 끝났어요',
                  style: TextStyle(
                    color: AppColor.ink.withValues(alpha: 0.65),
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _headline(),
                  style: const TextStyle(
                    color: AppColor.ink,
                    fontSize: 19,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
    if (onTap == null) return card;
    return GestureDetector(onTap: onTap, child: card);
  }

  String _headline() {
    if (isMeal) {
      if (registeredMeal != null) {
        return '${registeredMeal!.foodItems.length}개 음식이 저장됐어요';
      }
      final MealImageAnalysisPreview? preview = mealPreview;
      if (preview == null) return '식단 사진을 분석해주세요';
      final int count = preview.foodCandidates.length;
      if (count > 0) return '음식 후보 $count개를 찾았어요';
      if (preview.pipelineMetadata.requiresManualEntry) {
        return '음식 후보를 직접 확인해주세요';
      }
      return '식단 분석이 끝났어요';
    }
    if (registered != null) return '${registered!.displayName} 저장이 끝났어요';
    final List<SupplementIngredientCandidate> candidates =
        preview?.ingredientCandidates ??
        const <SupplementIngredientCandidate>[];
    final int selectedByDefault = candidates
        .where(
          (SupplementIngredientCandidate candidate) =>
              candidate.amount != null &&
              candidate.unit?.trim().isNotEmpty == true,
        )
        .length;
    if (selectedByDefault > 0 && selectedByDefault < candidates.length) {
      return '저장 후보 $selectedByDefault개 · 검토 후보 ${candidates.length}개';
    }
    if (selectedByDefault > 0) return '성분 후보 $selectedByDefault개를 찾았어요';
    final int count = candidates.length;
    if (count > 0) return '검토가 필요한 성분 후보 $count개';
    if (preview != null) return '성분 후보가 비어 있어 다시 확인이 필요해요';
    return '카메라로 영양제 라벨을 촬영해주세요';
  }
}

class _SupplementPreviewTabs extends StatelessWidget {
  const _SupplementPreviewTabs({
    required this.groups,
    required this.selectedIndex,
    required this.onSelected,
  });

  final List<_SupplementReviewGroup> groups;
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: <Widget>[
          for (int index = 0; index < groups.length; index++) ...<Widget>[
            ChoiceChip(
              key: ValueKey<String>('supplement-preview-tab-$index'),
              selected: selectedIndex == index,
              label: Text(groups[index].label),
              selectedColor: AppColor.brand,
              labelStyle: TextStyle(
                color: selectedIndex == index
                    ? AppColor.ink
                    : AppColor.inkSecondary,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
              onSelected: (_) => onSelected(index),
            ),
            if (index < groups.length - 1) const SizedBox(width: AppSpace.xs),
          ],
        ],
      ),
    );
  }
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({
    required this.color,
    required this.icon,
    required this.label,
    required this.value,
    required this.desc,
    this.big = false,
  });

  final Color color;
  final IconData icon;
  final String label;
  final String value;
  final String desc;
  final bool big;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadow.elev1,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, color: color, size: 24),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  label,
                  style: TextStyle(
                    color: AppColor.inkSecondary,
                    fontSize: big ? 15 : 13,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(height: 5),
                Text(
                  value,
                  style: TextStyle(
                    color: AppColor.ink,
                    fontSize: big ? 24 : 18,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0,
                    height: 1.2,
                  ),
                ),
                const SizedBox(height: 7),
                Text(
                  desc,
                  style: const TextStyle(
                    color: AppColor.inkSecondary,
                    fontSize: 13,
                    height: 1.38,
                    letterSpacing: 0,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _MealReviewCorrectionCard extends StatelessWidget {
  const _MealReviewCorrectionCard({
    required this.mealNameController,
    required this.portionAmountController,
    required this.portionUnitController,
    required this.kcalController,
    required this.carbController,
    required this.proteinController,
    required this.fatController,
    required this.sodiumController,
    required this.requiresManualEntry,
  });

  final TextEditingController mealNameController;
  final TextEditingController portionAmountController;
  final TextEditingController portionUnitController;
  final TextEditingController kcalController;
  final TextEditingController carbController;
  final TextEditingController proteinController;
  final TextEditingController fatController;
  final TextEditingController sodiumController;
  final bool requiresManualEntry;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadow.elev1,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Expanded(
                child: Text(
                  '식단 확인',
                  style: TextStyle(
                    color: AppColor.ink,
                    fontSize: 18,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0,
                  ),
                ),
              ),
              if (requiresManualEntry)
                const Icon(
                  Icons.edit_note_rounded,
                  color: AppColor.warning,
                  size: 22,
                ),
            ],
          ),
          const SizedBox(height: AppSpace.md),
          _ReviewTextField(
            controller: mealNameController,
            label: '음식명',
            hintText: '예: 비빔밥',
          ),
          const SizedBox(height: AppSpace.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _ReviewTextField(
                  controller: portionAmountController,
                  label: '분량',
                  hintText: '1',
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: _ReviewTextField(
                  controller: portionUnitController,
                  label: '단위',
                  hintText: 'bowl',
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _ReviewTextField(
                  controller: kcalController,
                  label: 'kcal',
                  hintText: '520',
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: _ReviewTextField(
                  controller: sodiumController,
                  label: '나트륨 mg',
                  hintText: '820',
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _ReviewTextField(
                  controller: carbController,
                  label: '탄수화물 g',
                  hintText: '78',
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: _ReviewTextField(
                  controller: proteinController,
                  label: '단백질 g',
                  hintText: '18',
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: _ReviewTextField(
                  controller: fatController,
                  label: '지방 g',
                  hintText: '12',
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PipelineLedStrip extends StatelessWidget {
  const _PipelineLedStrip({required this.metadata});

  final SupplementImagePipelineMetadata metadata;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: <Widget>[
        _PipelineLed(status: metadata.ocrStatus, stage: 'ocr'),
        const SizedBox(width: AppSpace.xs),
        _PipelineLed(status: metadata.visionStatus, stage: 'vision'),
        const SizedBox(width: AppSpace.xs),
        _PipelineLed(status: metadata.llmStatus, stage: 'llm'),
      ],
    );
  }
}

class _PipelineLed extends StatelessWidget {
  const _PipelineLed({required this.status, required this.stage});

  final String status;
  final String stage;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: '$stage $status',
      child: Container(
        key: ValueKey<String>('pipeline-led-$stage-$status'),
        width: 10,
        height: 10,
        decoration: BoxDecoration(
          color: _statusColor(status),
          shape: BoxShape.circle,
        ),
      ),
    );
  }

  Color _statusColor(String status) {
    return switch (status) {
      'success' => const Color(0xFF22B07D),
      'warning' => const Color(0xFFFFC107),
      'failed' => const Color(0xFFFF6B6B),
      _ => const Color(0xFFC7CDD6),
    };
  }
}

class _SupplementInfoCard extends StatelessWidget {
  const _SupplementInfoCard({
    required this.icon,
    required this.title,
    this.body,
    this.bodyWidget,
    required this.missingMessage,
    required this.onEdit,
  }) : assert(body != null || bodyWidget != null);

  final IconData icon;
  final String title;
  final String? body;
  final Widget? bodyWidget;
  final String? missingMessage;
  final VoidCallback? onEdit;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadow.elev1,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: AppColor.brand.withValues(alpha: 0.13),
                  borderRadius: BorderRadius.circular(13),
                ),
                child: Icon(icon, color: AppColor.brand, size: 22),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    color: AppColor.ink,
                    fontSize: 17,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0,
                  ),
                ),
              ),
              IconButton(
                tooltip: '$title 수정',
                onPressed: onEdit,
                icon: const Icon(Icons.edit_rounded),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.sm),
          bodyWidget ??
              Text(
                body!,
                style: const TextStyle(
                  color: AppColor.ink,
                  fontSize: 17,
                  height: 1.45,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0,
                ),
              ),
          if (missingMessage != null) ...<Widget>[
            const SizedBox(height: AppSpace.sm),
            Text(
              missingMessage!,
              style: const TextStyle(
                color: Color(0xFFD87900),
                fontSize: 13,
                height: 1.4,
                fontWeight: FontWeight.w800,
                letterSpacing: 0,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ReviewTextField extends StatelessWidget {
  const _ReviewTextField({
    required this.controller,
    required this.label,
    required this.hintText,
    this.keyboardType,
    this.maxLines = 1,
  });

  final TextEditingController controller;
  final String label;
  final String hintText;
  final TextInputType? keyboardType;
  final int maxLines;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      maxLines: maxLines,
      style: const TextStyle(
        color: AppColor.ink,
        fontSize: 14,
        fontWeight: FontWeight.w800,
        letterSpacing: 0,
      ),
      decoration: InputDecoration(
        labelText: label,
        hintText: hintText,
        isDense: true,
        filled: true,
        fillColor: const Color(0xFFF6F7F5),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: Color(0xFFE3E6E0)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: Color(0xFFE3E6E0)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: const BorderSide(color: AppColor.brand, width: 1.5),
        ),
      ),
    );
  }
}

class _ImpactPreviewCard extends StatelessWidget {
  const _ImpactPreviewCard({required this.preview, required this.explanation});

  final SupplementImpactPreviewResponse preview;
  final SupplementRecommendationExplainResponse? explanation;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadow.elev1,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            '로컬 LLM 설명',
            style: TextStyle(
              color: AppColor.ink,
              fontSize: 18,
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: AppSpace.sm),
          Text(
            explanation?.safeUserMessage ?? preview.safeUserMessage,
            style: const TextStyle(
              color: AppColor.inkSecondary,
              fontSize: 14,
              height: 1.45,
              letterSpacing: 0,
            ),
          ),
          if (explanation != null) ...<Widget>[
            const SizedBox(height: AppSpace.sm),
            for (final String bullet in explanation!.explanationBullets.take(3))
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  '· $bullet',
                  style: const TextStyle(
                    color: AppColor.inkSecondary,
                    fontSize: 13,
                    height: 1.35,
                    letterSpacing: 0,
                  ),
                ),
              ),
            _ExplanationSourceList(citations: explanation!.sourceCitations),
          ],
        ],
      ),
    );
  }
}

class _AnalysisExplanationCard extends StatelessWidget {
  const _AnalysisExplanationCard({
    required this.explanation,
    required this.busy,
    required this.onExplain,
  });

  final SupplementRecommendationExplainResponse? explanation;
  final bool busy;
  final VoidCallback? onExplain;

  @override
  Widget build(BuildContext context) {
    final SupplementRecommendationExplainResponse? current = explanation;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.surface,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadow.elev1,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            '등록 전 로컬 설명',
            style: TextStyle(
              color: AppColor.ink,
              fontSize: 18,
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: AppSpace.sm),
          Text(
            current?.safeUserMessage ?? 'Ollama가 등록 전 분석 후보와 누락 섹션을 요약해요.',
            style: const TextStyle(
              color: AppColor.inkSecondary,
              fontSize: 14,
              height: 1.45,
              letterSpacing: 0,
            ),
          ),
          if (current != null) ...<Widget>[
            const SizedBox(height: AppSpace.sm),
            for (final String bullet in current.explanationBullets.take(3))
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  '· $bullet',
                  style: const TextStyle(
                    color: AppColor.inkSecondary,
                    fontSize: 13,
                    height: 1.35,
                    letterSpacing: 0,
                  ),
                ),
              ),
            _ExplanationSourceList(citations: current.sourceCitations),
          ],
          const SizedBox(height: AppSpace.md),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: busy ? null : onExplain,
              icon: const Icon(Icons.auto_awesome_rounded, size: 18),
              label: Text(busy ? '요청 중' : '분석 설명 받기'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColor.ink,
                side: const BorderSide(color: AppColor.brand),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ExplanationSourceList extends StatelessWidget {
  const _ExplanationSourceList({required this.citations});

  final List<SupplementExplanationSourceCitation> citations;

  @override
  Widget build(BuildContext context) {
    if (citations.isEmpty) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.only(top: AppSpace.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            '출처',
            style: TextStyle(
              color: AppColor.ink,
              fontSize: 13,
              fontWeight: FontWeight.w800,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: 4),
          for (final SupplementExplanationSourceCitation citation
              in citations.take(4))
            Text(
              '· ${citation.title} (${citation.sourcePath})',
              style: const TextStyle(
                color: AppColor.inkSecondary,
                fontSize: 12,
                height: 1.35,
                letterSpacing: 0,
              ),
            ),
        ],
      ),
    );
  }
}

class _StatusBanner extends StatelessWidget {
  const _StatusBanner({required this.error});

  final ApiError error;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpace.md),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF2F2),
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: const Color(0xFFFFD0D0)),
      ),
      child: Text(
        error.message,
        style: const TextStyle(
          color: Color(0xFFB42318),
          fontSize: 14,
          fontWeight: FontWeight.w700,
          height: 1.35,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _MedicalNote extends StatelessWidget {
  const _MedicalNote();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.md),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFBEB),
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: const Color(0xFFFDE68A)),
      ),
      child: const Text(
        '의료적 진단·처방이 아닌 건강관리 참고 정보예요. 라벨과 복약 정보는 저장 전 직접 확인해주세요.',
        style: TextStyle(
          color: Color(0xFF92400E),
          fontSize: 13,
          height: 1.45,
          fontWeight: FontWeight.w700,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _SaveButton extends StatelessWidget {
  const _SaveButton({
    required this.label,
    required this.busy,
    required this.onTap,
  });

  final String label;
  final bool busy;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 56,
      child: FilledButton(
        onPressed: busy ? null : onTap,
        style: FilledButton.styleFrom(
          backgroundColor: AppColor.brand,
          foregroundColor: AppColor.ink,
          disabledBackgroundColor: AppColor.inkDisabled.withValues(alpha: 0.16),
          disabledForegroundColor: AppColor.inkSecondary,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.full),
          ),
        ),
        child: Text(
          busy ? '처리 중' : label,
          style: const TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w900,
            letterSpacing: 0,
          ),
        ),
      ),
    );
  }
}
