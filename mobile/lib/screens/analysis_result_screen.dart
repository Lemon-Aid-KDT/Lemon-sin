// screens/analysis_result_screen.dart — 17 Pro UIUX analysis result surface.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../app_controller.dart';
import '../core/api/api_error.dart';
import '../features/supplements/supplement_models.dart';
import '../utils/design_tokens_v2.dart';

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
  final TextEditingController _frequencyController = TextEditingController(
    text: 'daily',
  );
  final TextEditingController _timeOfDayController = TextEditingController();
  String? _seededAnalysisId;

  bool get _isMeal => widget.mode == 'meal';

  @override
  void dispose() {
    _productNameController.dispose();
    _manufacturerController.dispose();
    _ingredientNameController.dispose();
    _ingredientAmountController.dispose();
    _ingredientUnitController.dispose();
    _frequencyController.dispose();
    _timeOfDayController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final AppController? controller = widget.controller;
    final SupplementAnalysisPreview? preview = controller?.analysisPreview;
    if (preview != null) {
      _seedCorrectionFields(preview);
    }
    final UserSupplementResponse? registered =
        controller?.lastRegisteredSupplement;
    final ApiError? error = controller?.apiError;
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
                  _SummaryCard(
                    isMeal: _isMeal,
                    preview: preview,
                    registered: registered,
                    busy: controller?.busy == true,
                  ),
                  const SizedBox(height: AppSpace.md),
                  if (_isMeal)
                    ..._mealCards()
                  else
                    ..._supplementCards(preview, registered),
                  if (!_isMeal) ...<Widget>[
                    const SizedBox(height: AppSpace.md),
                    _IngredientPreviewCard(preview: preview),
                    if (preview != null) ...<Widget>[
                      const SizedBox(height: AppSpace.md),
                      _ReviewCorrectionCard(
                        productNameController: _productNameController,
                        manufacturerController: _manufacturerController,
                        ingredientNameController: _ingredientNameController,
                        ingredientAmountController: _ingredientAmountController,
                        ingredientUnitController: _ingredientUnitController,
                        frequencyController: _frequencyController,
                        timeOfDayController: _timeOfDayController,
                        missingSections: preview.missingRequiredSections,
                        evidenceSpans: preview.evidenceSpans,
                      ),
                    ],
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
            label: _primaryLabel(preview, registered),
            busy: controller?.busy == true,
            onTap: () => _handlePrimaryAction(context),
          ),
        ),
      ),
    );
  }

  List<Widget> _mealCards() {
    return <Widget>[
      const _ResultCard(
        color: Color(0xFF22B07D),
        icon: Icons.eco_rounded,
        label: '부족 영양소',
        value: '비타민 D · 마그네슘',
        desc: '식단 endpoint 연결 전까지 UI 기준 화면으로 유지해요',
      ),
      const SizedBox(height: AppSpace.sm),
      const _ResultCard(
        color: Color(0xFFFF9500),
        icon: Icons.warning_amber_rounded,
        label: '과다 섭취',
        value: '나트륨 · 당류',
        desc: '식단 분석 endpoint가 확정되면 실제 수치로 교체합니다',
      ),
      const SizedBox(height: AppSpace.sm),
      const _ResultCard(
        color: Color(0xFFFF6B6B),
        icon: Icons.shield_outlined,
        label: '주의 성분',
        value: '검토 대기',
        desc: '만성질환·복약 교차 점검은 backend 결과만 표시합니다',
      ),
      const SizedBox(height: AppSpace.sm),
      const _ResultCard(
        color: AppColor.brand,
        icon: Icons.workspace_premium_rounded,
        label: '오늘 식단 점수',
        value: '78점',
        desc: '현재 화면은 UIUX branch 기준의 식단 점수 데모입니다',
        big: true,
      ),
    ];
  }

  List<Widget> _supplementCards(
    SupplementAnalysisPreview? preview,
    UserSupplementResponse? registered,
  ) {
    final SupplementImagePipelineMetadata? pipeline = preview?.pipelineMetadata;
    final String provider = _ocrProviderLabel(pipeline?.ocrProvider);
    final String requested = _ocrProviderLabel(
      widget.controller?.lastRequestedOcrProvider,
    );
    final int candidateCount = preview?.ingredientCandidates.length ?? 0;
    final int sectionCount =
        pipeline?.sectionCount ?? preview?.labelSections.length ?? 0;
    final bool hasTextSignal =
        pipeline?.ocrTextPresent == true ||
        candidateCount > 0 ||
        sectionCount > 0 ||
        (preview?.evidenceSpans.isNotEmpty ?? false);
    final int roiCount =
        pipeline?.roiCount ??
        preview?.imageQualityReport?.detectedRois.length ??
        preview?.detectedProductRegions.length ??
        0;
    final List<String> missingSections =
        pipeline?.missingRequiredSections ??
        preview?.missingRequiredSections ??
        const <String>[];
    final String confidenceBucket = pipeline?.ocrConfidenceBucket ?? 'none';
    final bool parserUsed = pipeline?.llmParserUsed == true;
    final String parserValue = parserUsed
        ? (candidateCount > 0 || sectionCount > 0
              ? 'parser on'
              : 'parser empty')
        : 'parser review';
    return <Widget>[
      _ResultCard(
        color: const Color(0xFF22B07D),
        icon: Icons.document_scanner_rounded,
        label: 'OCR',
        value: hasTextSignal ? provider : 'no text · $provider',
        desc:
            '요청 $requested · 신뢰도 $confidenceBucket · 성분 $candidateCount개 · 섹션 $sectionCount개',
      ),
      const SizedBox(height: AppSpace.sm),
      _ResultCard(
        color: const Color(0xFFFF9500),
        icon: Icons.center_focus_strong_rounded,
        label: 'YOLO ROI',
        value: pipeline?.visionRoiUsed == true ? 'on ($roiCount)' : 'off',
        desc: roiCount > 0
            ? '검출 ROI $roiCount개를 backend가 안전 메타데이터로 반환했어요'
            : 'ROI가 없거나 backend vision 설정이 꺼져 있어요',
      ),
      const SizedBox(height: AppSpace.sm),
      _ResultCard(
        color: const Color(0xFF4D7BFF),
        icon: Icons.auto_awesome_rounded,
        label: 'Ollama',
        value: parserValue,
        desc: missingSections.isEmpty
            ? '멀티모달 보조와 로컬 LLM 설명은 backend runtime 설정으로 제어해요'
            : '추가 확인 필요: ${missingSections.join(', ')}',
      ),
      const SizedBox(height: AppSpace.sm),
      _ResultCard(
        color: const Color(0xFFFF6B6B),
        icon: Icons.fact_check_rounded,
        label: '확인 상태',
        value: registered != null ? '저장 완료' : preview?.status ?? '분석 전',
        desc:
            registered?.displayName ??
            preview?.actionRequired ??
            '카메라에서 영양제 사진을 분석해주세요',
        big: true,
      ),
    ];
  }

  void _seedCorrectionFields(SupplementAnalysisPreview preview) {
    if (_seededAnalysisId == preview.analysisId) return;
    _seededAnalysisId = preview.analysisId;
    _productNameController.text = preview.parsedProduct.productName ?? '';
    _manufacturerController.text = preview.parsedProduct.manufacturer ?? '';
    final SupplementIngredientCandidate? firstCandidate =
        preview.ingredientCandidates.isEmpty
        ? null
        : preview.ingredientCandidates.first;
    _ingredientNameController.text = firstCandidate?.displayName ?? '';
    _ingredientAmountController.text = firstCandidate?.amount == null
        ? ''
        : _formatEditableAmount(firstCandidate!.amount!);
    _ingredientUnitController.text = firstCandidate?.unit ?? '';
    _frequencyController.text =
        preview.intakeMethod.structured.frequency == 'unknown'
        ? 'daily'
        : preview.intakeMethod.structured.frequency;
    _timeOfDayController.text = preview.intakeMethod.structured.timeOfDay.join(
      ', ',
    );
  }

  String _primaryLabel(
    SupplementAnalysisPreview? preview,
    UserSupplementResponse? registered,
  ) {
    if (_isMeal) return '홈으로 돌아가기';
    if (registered != null) return '로컬 LLM 설명 보기';
    if (preview == null) return '다시 촬영하기';
    if (!_hasReviewIngredient(preview)) return '성분 직접 입력';
    return '확인 후 저장';
  }

  Future<void> _handlePrimaryAction(BuildContext context) async {
    HapticFeedback.mediumImpact();
    if (_isMeal || widget.controller == null) {
      context.go('/shell/home');
      return;
    }
    final AppController appController = widget.controller!;
    if (appController.lastRegisteredSupplement != null) {
      await appController.explainSupplementRecommendation(useLocalLlm: true);
      return;
    }
    final SupplementAnalysisPreview? preview = appController.analysisPreview;
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
  }

  UserSupplementCreate _registrationRequest(SupplementAnalysisPreview preview) {
    final UserSupplementIngredientInput? correctedIngredient =
        _correctedIngredient();
    final List<UserSupplementIngredientInput> previewIngredients = preview
        .ingredientCandidates
        .take(8)
        .map(
          (SupplementIngredientCandidate candidate) =>
              UserSupplementIngredientInput(
                displayName: candidate.displayName,
                nutrientCode: candidate.nutrientCode,
                amount: candidate.amount,
                unit: candidate.unit,
                confidence: candidate.confidence,
                source: candidate.source,
              ),
        )
        .toList(growable: false);
    final List<UserSupplementIngredientInput> ingredients =
        correctedIngredient == null
        ? previewIngredients
        : <UserSupplementIngredientInput>[
            correctedIngredient,
            for (final UserSupplementIngredientInput ingredient
                in previewIngredients.skip(1))
              ingredient,
          ];
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
    );
  }

  bool _hasReviewIngredient(SupplementAnalysisPreview preview) {
    return _nonEmpty(_ingredientNameController.text) != null ||
        preview.ingredientCandidates.isNotEmpty;
  }

  UserSupplementIngredientInput? _correctedIngredient() {
    final String? name = _nonEmpty(_ingredientNameController.text);
    if (name == null) return null;
    return UserSupplementIngredientInput(
      displayName: name,
      nutrientCode: null,
      amount: _parseOptionalDouble(_ingredientAmountController.text),
      unit: _nonEmpty(_ingredientUnitController.text),
      confidence: 1,
      source: 'user_confirmed',
    );
  }

  static String _formatEditableAmount(double value) {
    return value == value.roundToDouble()
        ? value.toStringAsFixed(0)
        : value.toString();
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

  String _ocrProviderLabel(String? provider) {
    final String value = provider?.trim() ?? '';
    if (value.isEmpty || value == 'configured') return 'Auto';
    if (value == 'paddleocr') return 'Paddle';
    if (value == 'google_vision') return 'Google Vision';
    if (value == 'clova') return 'CLOVA';
    return value;
  }

  static String? _nonEmpty(String? value) {
    final String? trimmed = value?.trim();
    if (trimmed == null || trimmed.isEmpty) return null;
    return trimmed;
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
    required this.registered,
    required this.busy,
  });

  final bool isMeal;
  final SupplementAnalysisPreview? preview;
  final UserSupplementResponse? registered;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    return Container(
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
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
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
  }

  String _headline() {
    if (isMeal) return '오늘 식사는 균형이 잘 잡혔어요';
    if (registered != null) return '${registered!.displayName} 저장이 끝났어요';
    final int count = preview?.ingredientCandidates.length ?? 0;
    if (count > 0) return '성분 후보 $count개를 찾았어요';
    if (preview != null) return '성분 후보가 비어 있어 다시 확인이 필요해요';
    return '카메라로 영양제 라벨을 촬영해주세요';
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

class _IngredientPreviewCard extends StatelessWidget {
  const _IngredientPreviewCard({required this.preview});

  final SupplementAnalysisPreview? preview;

  @override
  Widget build(BuildContext context) {
    final List<SupplementIngredientCandidate> candidates =
        preview?.ingredientCandidates.take(5).toList(growable: false) ??
        const <SupplementIngredientCandidate>[];
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
            '성분 후보',
            style: TextStyle(
              color: AppColor.ink,
              fontSize: 18,
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: AppSpace.md),
          if (candidates.isEmpty)
            const Text(
              '사진은 업로드됐지만 성분 후보가 비어 있어요. 더 선명한 라벨 사진으로 다시 테스트해주세요.',
              style: TextStyle(
                color: AppColor.inkSecondary,
                fontSize: 14,
                height: 1.45,
                letterSpacing: 0,
              ),
            )
          else
            for (final SupplementIngredientCandidate candidate in candidates)
              Padding(
                padding: const EdgeInsets.only(bottom: AppSpace.sm),
                child: Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        candidate.displayName,
                        style: const TextStyle(
                          color: AppColor.ink,
                          fontSize: 15,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0,
                        ),
                      ),
                    ),
                    Text(
                      _amountText(candidate),
                      style: const TextStyle(
                        color: AppColor.inkSecondary,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
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

  String _amountText(SupplementIngredientCandidate candidate) {
    final double? amount = candidate.amount;
    final String? unit = candidate.unit;
    if (amount == null) return '검토';
    final String amountText = amount == amount.roundToDouble()
        ? amount.toStringAsFixed(0)
        : amount.toStringAsFixed(2);
    return unit == null || unit.isEmpty ? amountText : '$amountText $unit';
  }
}

class _ReviewCorrectionCard extends StatelessWidget {
  const _ReviewCorrectionCard({
    required this.productNameController,
    required this.manufacturerController,
    required this.ingredientNameController,
    required this.ingredientAmountController,
    required this.ingredientUnitController,
    required this.frequencyController,
    required this.timeOfDayController,
    required this.missingSections,
    required this.evidenceSpans,
  });

  final TextEditingController productNameController;
  final TextEditingController manufacturerController;
  final TextEditingController ingredientNameController;
  final TextEditingController ingredientAmountController;
  final TextEditingController ingredientUnitController;
  final TextEditingController frequencyController;
  final TextEditingController timeOfDayController;
  final List<String> missingSections;
  final List<SupplementPreviewEvidenceSpan> evidenceSpans;

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
            '확인 후 수정',
            style: TextStyle(
              color: AppColor.ink,
              fontSize: 18,
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: AppSpace.xs),
          Text(
            missingSections.isEmpty
                ? '라벨과 대조해 저장할 값을 확인하세요.'
                : '추가 확인 필요: ${missingSections.map(_roleLabel).join(', ')}',
            style: const TextStyle(
              color: AppColor.inkSecondary,
              fontSize: 13,
              height: 1.4,
              fontWeight: FontWeight.w700,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: AppSpace.md),
          _ReviewTextField(
            controller: productNameController,
            label: '제품명',
            hintText: '예: 비타민 D',
          ),
          const SizedBox(height: AppSpace.sm),
          _ReviewTextField(
            controller: manufacturerController,
            label: '제조사',
            hintText: '라벨에 있으면 입력',
          ),
          const SizedBox(height: AppSpace.sm),
          _ReviewTextField(
            controller: ingredientNameController,
            label: '대표 성분',
            hintText: '예: Vitamin D',
          ),
          const SizedBox(height: AppSpace.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _ReviewTextField(
                  controller: ingredientAmountController,
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
                  controller: ingredientUnitController,
                  label: '단위',
                  hintText: 'mg, mcg, IU',
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _ReviewTextField(
                  controller: frequencyController,
                  label: '주기',
                  hintText: 'daily',
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: _ReviewTextField(
                  controller: timeOfDayController,
                  label: '복용 시간',
                  hintText: 'morning, evening',
                ),
              ),
            ],
          ),
          if (evidenceSpans.isNotEmpty) ...<Widget>[
            const SizedBox(height: AppSpace.md),
            const Text(
              '근거 일부',
              style: TextStyle(
                color: AppColor.ink,
                fontSize: 13,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
            const SizedBox(height: AppSpace.xs),
            for (final SupplementPreviewEvidenceSpan span in evidenceSpans.take(
              2,
            ))
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  '${_roleLabel(span.sectionType)} · ${span.textExcerpt}',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColor.inkSecondary,
                    fontSize: 12,
                    height: 1.35,
                    letterSpacing: 0,
                  ),
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
  });

  final TextEditingController controller;
  final String label;
  final String hintText;
  final TextInputType? keyboardType;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
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

String _roleLabel(String value) {
  return switch (value) {
    'front_label' => '앞면',
    'supplement_facts' => '성분표',
    'ingredients' => '원료',
    'intake_method' => '섭취법',
    'precautions' => '주의',
    'functional_info' || 'functional_claims' => '기능성',
    'barcode' => '바코드',
    'mixed' => '묶음',
    _ => value.isEmpty ? '기타' : value,
  };
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
          ],
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
