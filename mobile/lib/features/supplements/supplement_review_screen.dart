import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../app_controller.dart';
import '../../core/api/api_error.dart';
import '../../utils/design_tokens_v2.dart';
import 'supplement_models.dart';

/// Source-UI styled supplement analysis review flow backed by real OCR data.
class SupplementReviewScreen extends StatefulWidget {
  /// Creates the review screen.
  ///
  /// Args:
  ///   controller: App state controller with the current analysis preview.
  ///   onClose: Callback for leaving the review flow.
  const SupplementReviewScreen({
    required this.controller,
    this.onClose,
    super.key,
  });

  /// App controller with OCR preview, registration, and explanation actions.
  final AppController controller;

  /// Called when the user closes the review flow.
  final VoidCallback? onClose;

  @override
  State<SupplementReviewScreen> createState() => _SupplementReviewScreenState();
}

class _SupplementReviewScreenState extends State<SupplementReviewScreen> {
  static const double _lowConfidenceThreshold = 0.75;

  final TextEditingController _displayNameController = TextEditingController();
  final TextEditingController _manufacturerController = TextEditingController();
  final TextEditingController _servingAmountController =
      TextEditingController();
  final TextEditingController _servingUnitController = TextEditingController();
  final TextEditingController _dailyServingsController = TextEditingController(
    text: '1',
  );
  final TextEditingController _frequencyController = TextEditingController(
    text: 'daily',
  );
  final TextEditingController _timeOfDayController = TextEditingController();
  final List<_IngredientDraft> _ingredientDrafts = <_IngredientDraft>[];
  String? _seededAnalysisId;

  @override
  void initState() {
    super.initState();
    _seedFromPreview(widget.controller.analysisPreview);
  }

  @override
  void didUpdateWidget(covariant SupplementReviewScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    _seedFromPreview(widget.controller.analysisPreview);
  }

  @override
  void dispose() {
    _displayNameController.dispose();
    _manufacturerController.dispose();
    _servingAmountController.dispose();
    _servingUnitController.dispose();
    _dailyServingsController.dispose();
    _frequencyController.dispose();
    _timeOfDayController.dispose();
    for (final _IngredientDraft draft in _ingredientDrafts) {
      draft.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final SupplementAnalysisPreview? preview =
        widget.controller.analysisPreview;
    final UserSupplementResponse? registered =
        widget.controller.lastRegisteredSupplement;
    return Scaffold(
      backgroundColor: AppColor.section,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: <Widget>[
            _TopBar(onClose: _close),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(
                  AppSpace.page,
                  AppSpace.lg,
                  AppSpace.page,
                  AppSpace.xl + 92,
                ),
                children: <Widget>[
                  if (widget.controller.apiError != null) ...<Widget>[
                    _InlineErrorCard(
                      error: widget.controller.apiError!,
                      onDismissed: widget.controller.clearMessages,
                    ),
                    const SizedBox(height: AppSpace.md),
                  ],
                  if (registered != null) ...<Widget>[
                    _RegisteredSummaryCard(registered: registered),
                    const SizedBox(height: AppSpace.md),
                    _ImpactCard(
                      preview: widget.controller.supplementImpactPreview,
                      explanation: widget.controller.supplementExplanation,
                      busy: widget.controller.busy,
                      onRefresh: widget.controller.previewSupplementImpact,
                      onExplainWithOllama: () => widget.controller
                          .explainSupplementRecommendation(useLocalLlm: true),
                    ),
                  ] else if (preview != null) ...<Widget>[
                    _SummaryCard(preview: preview),
                    const SizedBox(height: AppSpace.md),
                    _PipelineCard(
                      preview: preview,
                      requestedOcrProvider:
                          widget.controller.lastRequestedOcrProvider,
                    ),
                    const SizedBox(height: AppSpace.md),
                    if (_reviewMessage(preview) != null) ...<Widget>[
                      _ReviewNoticeCard(message: _reviewMessage(preview)!),
                      const SizedBox(height: AppSpace.md),
                    ],
                    _ProductFormCard(
                      displayNameController: _displayNameController,
                      manufacturerController: _manufacturerController,
                      servingAmountController: _servingAmountController,
                      servingUnitController: _servingUnitController,
                      dailyServingsController: _dailyServingsController,
                      frequencyController: _frequencyController,
                      timeOfDayController: _timeOfDayController,
                    ),
                    const SizedBox(height: AppSpace.md),
                    _IngredientFormCard(
                      drafts: _ingredientDrafts,
                      onAdd: _addManualIngredient,
                      onRemove: _removeIngredient,
                      onSelectionChanged: _setIngredientSelected,
                    ),
                    if (preview.labelSections.isNotEmpty ||
                        preview.evidenceSpans.isNotEmpty) ...<Widget>[
                      const SizedBox(height: AppSpace.md),
                      _EvidenceCard(preview: preview),
                    ],
                    if (preview.warnings.isNotEmpty) ...<Widget>[
                      const SizedBox(height: AppSpace.md),
                      _WarningsCard(warnings: preview.warnings),
                    ],
                  ] else ...<Widget>[_EmptyReviewCard(onRetake: _retake)],
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
          child: registered == null
              ? Row(
                  children: <Widget>[
                    Expanded(
                      child: _SecondaryButton(
                        label: '다시 촬영',
                        icon: Icons.camera_alt_rounded,
                        onTap: widget.controller.busy ? null : _retake,
                      ),
                    ),
                    const SizedBox(width: AppSpace.sm),
                    Expanded(
                      flex: 2,
                      child: _PrimaryButton(
                        label: widget.controller.busy ? '저장 중' : '확인 후 저장',
                        onTap: widget.controller.busy ? null : _register,
                      ),
                    ),
                  ],
                )
              : _PrimaryButton(
                  label: '홈으로 돌아가기',
                  onTap: widget.controller.busy ? null : _close,
                ),
        ),
      ),
    );
  }

  void _seedFromPreview(SupplementAnalysisPreview? preview) {
    if (preview == null || _seededAnalysisId == preview.analysisId) {
      return;
    }
    _seededAnalysisId = preview.analysisId;
    _displayNameController.text = preview.parsedProduct.productName ?? '';
    _manufacturerController.text = preview.parsedProduct.manufacturer ?? '';
    _servingUnitController.text = preview.parsedProduct.servingSize ?? '';
    _servingAmountController.clear();
    final double? dailyServings =
        preview.parsedProduct.dailyServings ??
        preview.intakeMethod.structured.timesPerDay;
    _dailyServingsController.text = dailyServings?.toString() ?? '1';
    if (preview.intakeMethod.structured.frequency != 'unknown') {
      _frequencyController.text = preview.intakeMethod.structured.frequency;
    }
    _timeOfDayController.text = preview.intakeMethod.structured.timeOfDay.join(
      ', ',
    );

    for (final _IngredientDraft draft in _ingredientDrafts) {
      draft.dispose();
    }
    _ingredientDrafts
      ..clear()
      ..addAll(
        preview.ingredientCandidates.isEmpty
            ? <_IngredientDraft>[_IngredientDraft.manual()]
            : <_IngredientDraft>[
                for (final MapEntry<int, SupplementIngredientCandidate> entry
                    in preview.ingredientCandidates
                        .take(8)
                        .toList(growable: false)
                        .asMap()
                        .entries)
                  _IngredientDraft.fromCandidate(
                    entry.value,
                    requiresReview: _candidateRequiresReview(
                      preview,
                      entry.key,
                    ),
                  ),
              ],
      );
  }

  bool _candidateRequiresReview(SupplementAnalysisPreview preview, int index) {
    final SupplementIngredientCandidate candidate =
        preview.ingredientCandidates[index];
    if (candidate.confidence < _lowConfidenceThreshold) {
      return true;
    }
    return preview.lowConfidenceFields.any((String field) {
      return field == 'ingredients' ||
          field == 'ingredient_candidates' ||
          field == 'ingredients.$index' ||
          field == 'ingredient_candidates.$index' ||
          field.startsWith('ingredients.$index.') ||
          field.startsWith('ingredient_candidates.$index.');
    });
  }

  String? _reviewMessage(SupplementAnalysisPreview preview) {
    final String? provider = preview.pipelineMetadata.ocrProvider;
    if (preview.ingredientCandidates.isEmpty) {
      if (provider != null && provider != 'intake-only') {
        return '$provider OCR은 실행됐지만 성분 후보가 비어 있어요. 라벨을 확인한 뒤 성분을 직접 입력해주세요.';
      }
      return '사진 업로드는 완료됐지만 성분 후보가 비어 있어요. 더 선명한 라벨을 선택하거나 성분을 직접 입력해주세요.';
    }
    if (preview.lowConfidenceFields.isNotEmpty ||
        preview.ingredientCandidates.any(
          (SupplementIngredientCandidate candidate) =>
              candidate.confidence < _lowConfidenceThreshold,
        )) {
      return '확신도가 낮은 항목이 있어요. 라벨을 직접 보고 값이 맞는지 확인해주세요.';
    }
    if (preview.promptsImageRiskConfirmation) {
      return preview.imageActionLabel;
    }
    return null;
  }

  void _addManualIngredient() {
    setState(() {
      _ingredientDrafts.add(_IngredientDraft.manual());
    });
  }

  void _removeIngredient(_IngredientDraft draft) {
    setState(() {
      _ingredientDrafts.remove(draft);
      draft.dispose();
    });
  }

  void _setIngredientSelected(_IngredientDraft draft, bool selected) {
    setState(() {
      draft.selected = selected;
    });
  }

  Future<void> _register() async {
    final SupplementAnalysisPreview? preview =
        widget.controller.analysisPreview;
    if (preview == null) {
      _showSnackBar('분석 결과가 없어요. 다시 촬영해주세요.');
      return;
    }
    final String displayName = _displayNameController.text.trim();
    if (displayName.isEmpty) {
      _showSnackBar('영양제 이름을 입력해주세요.');
      return;
    }
    if (preview.blocksRegistrationForImageRisk) {
      _showSnackBar('사진 검토가 필요한 상태예요. 다른 라벨 사진으로 다시 시도해주세요.');
      return;
    }
    if (preview.promptsImageRiskConfirmation) {
      final bool confirmed = await _confirmDialog(
        title: '사진 확인 필요',
        message: '라벨을 직접 확인한 뒤 저장할까요?',
      );
      if (!confirmed) return;
    }
    final List<_IngredientDraft> selectedDrafts = _ingredientDrafts
        .where((_IngredientDraft draft) => draft.selected)
        .toList(growable: false);
    if (selectedDrafts.any((_IngredientDraft draft) => draft.requiresReview)) {
      final bool confirmed = await _confirmDialog(
        title: '확인 필요 항목 포함',
        message: '낮은 확신도의 성분이 포함되어 있어요. 라벨을 확인한 뒤 저장할까요?',
      );
      if (!confirmed) return;
    }
    final List<UserSupplementIngredientInput> ingredients = selectedDrafts
        .map(_ingredientFromDraft)
        .whereType<UserSupplementIngredientInput>()
        .toList(growable: false);
    if (ingredients.isEmpty) {
      _showSnackBar('저장하려면 성분을 하나 이상 입력해주세요.');
      return;
    }

    HapticFeedback.mediumImpact();
    await widget.controller.registerSupplement(
      UserSupplementCreate(
        analysisId: preview.analysisId,
        displayName: displayName,
        manufacturer: _emptyToNull(_manufacturerController.text),
        ingredients: ingredients,
        serving: SupplementServing(
          amount: _parseOptionalDouble(_servingAmountController.text),
          unit: _emptyToNull(_servingUnitController.text),
          dailyServings:
              _parseOptionalDouble(_dailyServingsController.text) ?? 1,
        ),
        intakeSchedule: SupplementIntakeSchedule(
          frequency: _frequencyController.text.trim().isEmpty
              ? 'daily'
              : _frequencyController.text.trim(),
          timeOfDay: _splitCsv(_timeOfDayController.text),
        ),
      ),
    );
    if (widget.controller.lastRegisteredSupplement != null) {
      await widget.controller.previewSupplementImpact();
    }
  }

  UserSupplementIngredientInput? _ingredientFromDraft(_IngredientDraft draft) {
    final String displayName = draft.displayNameController.text.trim();
    if (!draft.selected || displayName.isEmpty) {
      return null;
    }
    return UserSupplementIngredientInput(
      displayName: displayName,
      nutrientCode: _emptyToNull(draft.nutrientCodeController.text),
      amount: _parseOptionalDouble(draft.amountController.text),
      unit: _emptyToNull(draft.unitController.text),
      confidence: draft.confidence,
      source: draft.source,
    );
  }

  Future<bool> _confirmDialog({
    required String title,
    required String message,
  }) async {
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text(title),
          content: Text(message),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('취소'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('확인'),
            ),
          ],
        );
      },
    );
    return confirmed == true;
  }

  void _retake() {
    widget.controller.clearSupplementFlow();
  }

  void _close() {
    widget.controller.clearSupplementFlow();
    widget.onClose?.call();
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }
}

/// Source-UI styled consent gate for local OCR smoke tests.
class SupplementConsentGateScreen extends StatelessWidget {
  /// Creates a consent gate.
  ///
  /// Args:
  ///   controller: App controller used to grant local demo consents.
  ///   onClose: Callback for leaving the camera branch.
  const SupplementConsentGateScreen({
    required this.controller,
    this.onClose,
    super.key,
  });

  /// App controller.
  final AppController controller;

  /// Called when the user closes the gate.
  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColor.section,
      body: SafeArea(
        child: Column(
          children: <Widget>[
            _TopBar(onClose: onClose),
            Expanded(
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.all(AppSpace.page),
                  child: AppCard(
                    padding: const EdgeInsets.all(AppSpace.xl),
                    radius: AppRadius.xl,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Container(
                          width: 56,
                          height: 56,
                          decoration: const BoxDecoration(
                            color: AppColor.brandSoft,
                            shape: BoxShape.circle,
                          ),
                          alignment: Alignment.center,
                          child: const Icon(
                            Icons.verified_user_rounded,
                            color: AppColor.ink,
                            size: 28,
                          ),
                        ),
                        const SizedBox(height: AppSpace.lg),
                        Text('OCR 테스트 동의가 필요해요', style: AppText.title),
                        const SizedBox(height: AppSpace.sm),
                        Text(
                          '라벨 이미지 분석과 건강 정보 비교에 필요한 로컬 테스트 동의를 활성화합니다.',
                          style: AppText.body.copyWith(
                            color: AppColor.inkSecondary,
                          ),
                        ),
                        if (controller.apiError != null) ...<Widget>[
                          const SizedBox(height: AppSpace.md),
                          _InlineErrorCard(
                            error: controller.apiError!,
                            onDismissed: controller.clearMessages,
                          ),
                        ],
                        const SizedBox(height: AppSpace.xl),
                        _PrimaryButton(
                          label: controller.busy ? '처리 중' : '동의하고 계속',
                          onTap: controller.busy
                              ? null
                              : controller.grantMinimumConsents,
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

class _TopBar extends StatelessWidget {
  const _TopBar({this.onClose});

  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.page,
        AppSpace.sm,
        AppSpace.page,
        AppSpace.sm,
      ),
      child: Row(
        children: <Widget>[
          GestureDetector(
            onTap: onClose,
            child: const SizedBox(
              width: 44,
              height: 44,
              child: Icon(Icons.close_rounded, color: AppColor.ink, size: 26),
            ),
          ),
          const Spacer(),
          Text(
            '영양제 분석',
            style: AppText.subtitle.copyWith(fontWeight: FontWeight.w800),
          ),
          const Spacer(),
          const SizedBox(width: 44, height: 44),
        ],
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.preview});

  final SupplementAnalysisPreview preview;

  @override
  Widget build(BuildContext context) {
    final bool hasIngredients = preview.ingredientCandidates.isNotEmpty;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFFFFE27A), AppColor.brand],
        ),
        borderRadius: BorderRadius.circular(AppRadius.xl),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: AppColor.brand.withValues(alpha: 0.30),
            blurRadius: 18,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 58,
            height: 58,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.42),
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Icon(
              hasIngredients
                  ? Icons.check_rounded
                  : Icons.priority_high_rounded,
              color: AppColor.ink,
              size: 30,
            ),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  hasIngredients ? '분석이 끝났어요' : '확인이 필요해요',
                  style: AppText.caption.copyWith(
                    color: AppColor.ink.withValues(alpha: 0.68),
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  hasIngredients
                      ? '성분 후보 ${preview.ingredientCandidates.length}개를 찾았어요'
                      : '성분 후보를 직접 확인해주세요',
                  style: AppText.subtitle.copyWith(
                    fontWeight: FontWeight.w900,
                    height: 1.25,
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

class _PipelineCard extends StatelessWidget {
  const _PipelineCard({
    required this.preview,
    required this.requestedOcrProvider,
  });

  final SupplementAnalysisPreview preview;
  final String? requestedOcrProvider;

  @override
  Widget build(BuildContext context) {
    final SupplementImagePipelineMetadata pipeline = preview.pipelineMetadata;
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.cardInside),
      radius: AppRadius.xl,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('분석 상태', style: AppText.subtitle),
          const SizedBox(height: AppSpace.md),
          Wrap(
            spacing: AppSpace.sm,
            runSpacing: AppSpace.sm,
            children: <Widget>[
              _StatusPill(
                icon: Icons.document_scanner_rounded,
                label: 'OCR',
                value: _ocrStatusLabel(pipeline.ocrProvider),
                color: AppColor.brand,
              ),
              _StatusPill(
                icon: Icons.crop_free_rounded,
                label: 'YOLO ROI',
                value: pipeline.visionRoiUsed ? 'on' : 'off',
                color: pipeline.visionRoiUsed
                    ? AppColor.success
                    : AppColor.inkDisabled,
              ),
              _StatusPill(
                icon: Icons.psychology_rounded,
                label: 'Parser',
                value: pipeline.llmParserUsed ? 'done' : 'review',
                color: pipeline.llmParserUsed
                    ? AppColor.success
                    : AppColor.warning,
              ),
              _StatusPill(
                icon: Icons.lock_rounded,
                label: 'Retention',
                value: pipeline.rawImageStored || pipeline.rawOcrTextStored
                    ? 'stored'
                    : 'clean',
                color: pipeline.rawImageStored || pipeline.rawOcrTextStored
                    ? AppColor.warning
                    : AppColor.success,
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _ocrStatusLabel(String? producedProvider) {
    if (producedProvider != null && producedProvider != 'intake-only') {
      return producedProvider;
    }
    final String? requested = requestedOcrProvider;
    if (requested != null && requested.isNotEmpty) {
      return 'no text · $requested';
    }
    return producedProvider ?? 'not run';
  }
}

class _ProductFormCard extends StatelessWidget {
  const _ProductFormCard({
    required this.displayNameController,
    required this.manufacturerController,
    required this.servingAmountController,
    required this.servingUnitController,
    required this.dailyServingsController,
    required this.frequencyController,
    required this.timeOfDayController,
  });

  final TextEditingController displayNameController;
  final TextEditingController manufacturerController;
  final TextEditingController servingAmountController;
  final TextEditingController servingUnitController;
  final TextEditingController dailyServingsController;
  final TextEditingController frequencyController;
  final TextEditingController timeOfDayController;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.cardInside),
      radius: AppRadius.xl,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('제품 정보', style: AppText.subtitle),
          const SizedBox(height: AppSpace.md),
          _ReviewField(
            controller: displayNameController,
            label: '영양제 이름',
            icon: Icons.medication_rounded,
          ),
          const SizedBox(height: AppSpace.sm),
          _ReviewField(
            controller: manufacturerController,
            label: '제조사',
            icon: Icons.apartment_rounded,
          ),
          const SizedBox(height: AppSpace.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _ReviewField(
                  controller: servingAmountController,
                  label: '1회 섭취량',
                  icon: Icons.pin_rounded,
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: _ReviewField(
                  controller: servingUnitController,
                  label: '단위',
                  icon: Icons.straighten_rounded,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _ReviewField(
                  controller: dailyServingsController,
                  label: '하루 횟수',
                  icon: Icons.repeat_rounded,
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: _ReviewField(
                  controller: frequencyController,
                  label: '빈도',
                  icon: Icons.event_repeat_rounded,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.sm),
          _ReviewField(
            controller: timeOfDayController,
            label: '섭취 시간',
            icon: Icons.schedule_rounded,
          ),
        ],
      ),
    );
  }
}

class _IngredientFormCard extends StatelessWidget {
  const _IngredientFormCard({
    required this.drafts,
    required this.onAdd,
    required this.onRemove,
    required this.onSelectionChanged,
  });

  final List<_IngredientDraft> drafts;
  final VoidCallback onAdd;
  final ValueChanged<_IngredientDraft> onRemove;
  final void Function(_IngredientDraft draft, bool selected) onSelectionChanged;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.cardInside),
      radius: AppRadius.xl,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Text('성분 확인', style: AppText.subtitle),
              const Spacer(),
              TextButton.icon(
                onPressed: onAdd,
                icon: const Icon(Icons.add_rounded, size: 18),
                label: const Text('추가'),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.sm),
          for (final _IngredientDraft draft in drafts) ...<Widget>[
            _IngredientTile(
              draft: draft,
              removable: drafts.length > 1,
              onRemove: () => onRemove(draft),
              onSelectionChanged: (bool selected) =>
                  onSelectionChanged(draft, selected),
            ),
            if (draft != drafts.last) const SizedBox(height: AppSpace.sm),
          ],
        ],
      ),
    );
  }
}

class _IngredientTile extends StatelessWidget {
  const _IngredientTile({
    required this.draft,
    required this.removable,
    required this.onRemove,
    required this.onSelectionChanged,
  });

  final _IngredientDraft draft;
  final bool removable;
  final VoidCallback onRemove;
  final ValueChanged<bool> onSelectionChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpace.md),
      decoration: BoxDecoration(
        color: AppColor.sunken,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(
          color: draft.requiresReview ? AppColor.warningSoft : AppColor.border,
        ),
      ),
      child: Column(
        children: <Widget>[
          Row(
            children: <Widget>[
              Checkbox(
                value: draft.selected,
                activeColor: AppColor.brand,
                checkColor: AppColor.ink,
                onChanged: (bool? value) => onSelectionChanged(value ?? false),
              ),
              Expanded(
                child: _ReviewField(
                  controller: draft.displayNameController,
                  label: '성분명',
                  compact: true,
                ),
              ),
              if (removable)
                IconButton(
                  tooltip: '성분 삭제',
                  onPressed: onRemove,
                  icon: const Icon(Icons.close_rounded),
                ),
            ],
          ),
          const SizedBox(height: AppSpace.sm),
          Row(
            children: <Widget>[
              Expanded(
                child: _ReviewField(
                  controller: draft.amountController,
                  label: '함량',
                  compact: true,
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: _ReviewField(
                  controller: draft.unitController,
                  label: '단위',
                  compact: true,
                ),
              ),
            ],
          ),
          if (draft.requiresReview) ...<Widget>[
            const SizedBox(height: AppSpace.sm),
            Row(
              children: <Widget>[
                const Icon(
                  Icons.warning_amber_rounded,
                  color: AppColor.warning,
                  size: 16,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    '라벨 확인 필요 · confidence ${(draft.confidence * 100).round()}%',
                    style: AppText.micro.copyWith(color: AppColor.review),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _EvidenceCard extends StatelessWidget {
  const _EvidenceCard({required this.preview});

  final SupplementAnalysisPreview preview;

  @override
  Widget build(BuildContext context) {
    final List<SupplementPreviewLabelSection> sections = preview.labelSections
        .take(3)
        .toList(growable: false);
    final List<SupplementPreviewEvidenceSpan> spans = preview.evidenceSpans
        .take(3)
        .toList(growable: false);
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.cardInside),
      radius: AppRadius.xl,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('라벨 근거', style: AppText.subtitle),
          const SizedBox(height: AppSpace.sm),
          for (final SupplementPreviewLabelSection section in sections)
            _EvidenceLine(
              title: section.headingText ?? section.sectionType,
              body: section.textBundle ?? '섹션 내용 확인 필요',
            ),
          for (final SupplementPreviewEvidenceSpan span in spans)
            _EvidenceLine(title: span.sectionType, body: span.textExcerpt),
        ],
      ),
    );
  }
}

class _ImpactCard extends StatelessWidget {
  const _ImpactCard({
    required this.preview,
    required this.explanation,
    required this.busy,
    required this.onRefresh,
    required this.onExplainWithOllama,
  });

  final SupplementImpactPreviewResponse? preview;
  final SupplementRecommendationExplainResponse? explanation;
  final bool busy;
  final VoidCallback onRefresh;
  final VoidCallback onExplainWithOllama;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.cardInside),
      radius: AppRadius.xl,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('추천 설명', style: AppText.subtitle),
          const SizedBox(height: AppSpace.sm),
          Text(
            preview?.safeUserMessage ?? '저장된 영양제를 기준으로 영향도를 확인할 수 있어요.',
            style: AppText.body.copyWith(color: AppColor.inkSecondary),
          ),
          if (explanation != null) ...<Widget>[
            const SizedBox(height: AppSpace.md),
            Text(explanation!.safeUserMessage, style: AppText.body),
            const SizedBox(height: AppSpace.sm),
            for (final String bullet in explanation!.explanationBullets)
              _BulletText(text: bullet),
            const SizedBox(height: AppSpace.sm),
            _StatusPill(
              icon: Icons.memory_rounded,
              label: 'Ollama',
              value: explanation!.llmUsed ? 'used' : 'fallback',
              color: explanation!.llmUsed ? AppColor.success : AppColor.warning,
            ),
          ],
          const SizedBox(height: AppSpace.md),
          Row(
            children: <Widget>[
              Expanded(
                child: _SecondaryButton(
                  label: '영향도 새로고침',
                  icon: Icons.refresh_rounded,
                  onTap: busy ? null : onRefresh,
                ),
              ),
              const SizedBox(width: AppSpace.sm),
              Expanded(
                child: _PrimaryButton(
                  label: busy ? '요청 중' : 'Ollama 설명',
                  onTap: busy || preview == null ? null : onExplainWithOllama,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RegisteredSummaryCard extends StatelessWidget {
  const _RegisteredSummaryCard({required this.registered});

  final UserSupplementResponse registered;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.brand,
        borderRadius: BorderRadius.circular(AppRadius.xl),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.45),
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: const Icon(
              Icons.check_circle_rounded,
              color: AppColor.ink,
              size: 30,
            ),
          ),
          const SizedBox(width: AppSpace.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  '저장됐어요',
                  style: AppText.caption.copyWith(
                    color: AppColor.ink.withValues(alpha: 0.70),
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  registered.displayName,
                  style: AppText.subtitle.copyWith(fontWeight: FontWeight.w900),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InlineErrorCard extends StatelessWidget {
  const _InlineErrorCard({required this.error, required this.onDismissed});

  final ApiError error;
  final VoidCallback onDismissed;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpace.md),
      decoration: BoxDecoration(
        color: AppColor.dangerSoft,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppColor.danger.withValues(alpha: 0.26)),
      ),
      child: Row(
        children: <Widget>[
          const Icon(Icons.error_outline_rounded, color: AppColor.danger),
          const SizedBox(width: AppSpace.sm),
          Expanded(
            child: Text(
              error.message,
              style: AppText.body.copyWith(
                color: AppColor.ink,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          IconButton(
            tooltip: '오류 닫기',
            onPressed: onDismissed,
            icon: const Icon(Icons.close_rounded),
          ),
        ],
      ),
    );
  }
}

class _ReviewNoticeCard extends StatelessWidget {
  const _ReviewNoticeCard({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpace.cardInside),
      decoration: BoxDecoration(
        color: AppColor.warningSoft,
        borderRadius: BorderRadius.circular(AppRadius.xl),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Icon(Icons.info_outline_rounded, color: AppColor.review),
          const SizedBox(width: AppSpace.sm),
          Expanded(
            child: Text(
              message,
              style: AppText.body.copyWith(
                color: AppColor.ink,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _WarningsCard extends StatelessWidget {
  const _WarningsCard({required this.warnings});

  final List<String> warnings;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.cardInside),
      radius: AppRadius.xl,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('확인 메시지', style: AppText.subtitle),
          const SizedBox(height: AppSpace.sm),
          for (final String warning in warnings.take(4))
            _BulletText(text: warning),
        ],
      ),
    );
  }
}

class _EmptyReviewCard extends StatelessWidget {
  const _EmptyReviewCard({required this.onRetake});

  final VoidCallback onRetake;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(AppSpace.xl),
      radius: AppRadius.xl,
      child: Column(
        children: <Widget>[
          const Icon(
            Icons.camera_alt_outlined,
            color: AppColor.brand,
            size: 48,
          ),
          const SizedBox(height: AppSpace.md),
          Text('분석 결과가 없어요', style: AppText.subtitle),
          const SizedBox(height: AppSpace.sm),
          Text(
            '카메라나 갤러리에서 영양제 라벨을 선택해주세요.',
            textAlign: TextAlign.center,
            style: AppText.body.copyWith(color: AppColor.inkSecondary),
          ),
        ],
      ),
    );
  }
}

class _ReviewField extends StatelessWidget {
  const _ReviewField({
    required this.controller,
    required this.label,
    this.icon,
    this.compact = false,
    this.keyboardType,
  });

  final TextEditingController controller;
  final String label;
  final IconData? icon;
  final bool compact;
  final TextInputType? keyboardType;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      style: AppText.body.copyWith(fontWeight: FontWeight.w700),
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: icon == null ? null : Icon(icon, size: 19),
        filled: true,
        fillColor: AppColor.sunken,
        isDense: compact,
        contentPadding: EdgeInsets.symmetric(
          horizontal: compact ? 12 : 14,
          vertical: compact ? 10 : 14,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, color: color, size: 16),
          const SizedBox(width: 6),
          Text(
            '$label: $value',
            style: AppText.micro.copyWith(
              color: AppColor.ink,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _EvidenceLine extends StatelessWidget {
  const _EvidenceLine({required this.title, required this.body});

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpace.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            title,
            style: AppText.caption.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 2),
          Text(body, style: AppText.caption),
        ],
      ),
    );
  }
}

class _BulletText extends StatelessWidget {
  const _BulletText({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: SizedBox(
              width: 5,
              height: 5,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: AppColor.brand,
                  shape: BoxShape.circle,
                ),
              ),
            ),
          ),
          const SizedBox(width: AppSpace.sm),
          Expanded(child: Text(text, style: AppText.caption)),
        ],
      ),
    );
  }
}

class _PrimaryButton extends StatelessWidget {
  const _PrimaryButton({required this.label, required this.onTap});

  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 56,
      child: FilledButton(
        onPressed: onTap,
        style: FilledButton.styleFrom(
          backgroundColor: AppColor.brand,
          foregroundColor: AppColor.ink,
          disabledBackgroundColor: AppColor.inkDisabled,
          disabledForegroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.full),
          ),
        ),
        child: Text(
          label,
          style: AppText.body.copyWith(
            fontWeight: FontWeight.w900,
            color: onTap == null ? Colors.white : AppColor.ink,
          ),
        ),
      ),
    );
  }
}

class _SecondaryButton extends StatelessWidget {
  const _SecondaryButton({
    required this.label,
    required this.icon,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 56,
      child: OutlinedButton.icon(
        onPressed: onTap,
        icon: Icon(icon, size: 18),
        label: Text(label),
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColor.ink,
          side: const BorderSide(color: AppColor.borderStrong),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.full),
          ),
        ),
      ),
    );
  }
}

class _IngredientDraft {
  _IngredientDraft({
    required String displayName,
    required String? nutrientCode,
    required double? amount,
    required String? unit,
    required this.confidence,
    required this.source,
    required this.selected,
    required this.requiresReview,
  }) : displayNameController = TextEditingController(text: displayName),
       nutrientCodeController = TextEditingController(text: nutrientCode ?? ''),
       amountController = TextEditingController(text: amount?.toString() ?? ''),
       unitController = TextEditingController(text: unit ?? '');

  factory _IngredientDraft.fromCandidate(
    SupplementIngredientCandidate candidate, {
    required bool requiresReview,
  }) {
    return _IngredientDraft(
      displayName: candidate.displayName,
      nutrientCode: candidate.nutrientCode,
      amount: candidate.amount,
      unit: candidate.unit,
      confidence: candidate.confidence,
      source: candidate.source == 'user_confirmed'
          ? 'user_confirmed'
          : 'ocr_llm_preview',
      selected: !requiresReview,
      requiresReview: requiresReview,
    );
  }

  factory _IngredientDraft.manual() {
    return _IngredientDraft(
      displayName: '',
      nutrientCode: null,
      amount: null,
      unit: null,
      confidence: 1,
      source: 'user_confirmed',
      selected: true,
      requiresReview: false,
    );
  }

  final TextEditingController displayNameController;
  final TextEditingController nutrientCodeController;
  final TextEditingController amountController;
  final TextEditingController unitController;
  final double confidence;
  final String source;
  bool selected;
  final bool requiresReview;

  void dispose() {
    displayNameController.dispose();
    nutrientCodeController.dispose();
    amountController.dispose();
    unitController.dispose();
  }
}

String? _emptyToNull(String value) {
  final String trimmed = value.trim();
  return trimmed.isEmpty ? null : trimmed;
}

double? _parseOptionalDouble(String value) {
  final String trimmed = value.trim();
  return trimmed.isEmpty ? null : double.tryParse(trimmed);
}

List<String> _splitCsv(String value) {
  return value
      .split(',')
      .map((String item) => item.trim())
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
}
