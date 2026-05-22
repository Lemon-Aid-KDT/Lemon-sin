import 'dart:io';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';

import '../../app_controller.dart';
import 'supplement_models.dart';

/// Supplement capture, OCR text review, and registration screen.
class SupplementFlowScreen extends StatefulWidget {
  /// Creates the supplement flow screen.
  const SupplementFlowScreen({
    required this.controller,
    this.onClose,
    ImagePicker? imagePicker,
    super.key,
  }) : _imagePicker = imagePicker;

  /// App flow controller.
  final AppController controller;

  /// Called when the fullscreen capture flow should return to the dashboard.
  final VoidCallback? onClose;
  final ImagePicker? _imagePicker;

  @override
  State<SupplementFlowScreen> createState() => _SupplementFlowScreenState();
}

class _SupplementFlowScreenState extends State<SupplementFlowScreen> {
  static const double _lowConfidenceThreshold = 0.75;
  static const MethodChannel _cameraPermissionChannel = MethodChannel(
    'com.lemonaid.mobile/camera_permission',
  );

  late final ImagePicker _imagePicker;
  final TextEditingController _ocrTextController = TextEditingController();
  final TextEditingController _displayNameController = TextEditingController();
  final TextEditingController _manufacturerController = TextEditingController();
  final TextEditingController _servingAmountController =
      TextEditingController();
  final TextEditingController _servingUnitController = TextEditingController();
  final TextEditingController _dailyServingsController =
      TextEditingController();
  final TextEditingController _frequencyController = TextEditingController(
    text: 'daily',
  );
  final TextEditingController _timeOfDayController = TextEditingController();
  final List<_IngredientDraft> _ingredientDrafts = <_IngredientDraft>[];
  String? _seededAnalysisId;
  _SelectedLabelImage? _selectedImage;
  _SupplementFlowStage _stage = _SupplementFlowStage.idle;

  @override
  void initState() {
    super.initState();
    _imagePicker = widget._imagePicker ?? ImagePicker();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _recoverLostImage();
    });
  }

  @override
  void dispose() {
    _ocrTextController.dispose();
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
    if (preview != null) {
      _seedFromPreview(preview);
    }

    if (!widget.controller.hasMinimumConsents) {
      return _BlackConsentRequired(onClose: widget.onClose);
    }

    if (preview == null) {
      return _BlackCaptureSurface(
        busy: widget.controller.busy,
        selectedImage: _selectedImage,
        stage: _stage,
        onCamera: () => _pickImage(ImageSource.camera),
        onGallery: () => _pickImage(ImageSource.gallery),
        onAnalyze: _analyzeSelectedImage,
        onRetake: _resetSelectedImage,
        onClose: widget.onClose,
      );
    }

    return ColoredBox(
      color: const Color(0xFFF4F6F3),
      child: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
          children: <Widget>[
            _ReviewTopBar(onClose: widget.onClose),
            const SizedBox(height: 16),
            _ProcessingTimeline(
              stage: _stage,
              preview: preview,
              busy: widget.controller.busy,
            ),
            const SizedBox(height: 16),
            _PreviewCard(preview: preview),
            const SizedBox(height: 16),
            _OcrTextCard(
              controller: _ocrTextController,
              busy: widget.controller.busy,
              onSubmit: _submitOcrText,
            ),
            const SizedBox(height: 16),
            _RegistrationCard(
              displayNameController: _displayNameController,
              manufacturerController: _manufacturerController,
              servingAmountController: _servingAmountController,
              servingUnitController: _servingUnitController,
              dailyServingsController: _dailyServingsController,
              frequencyController: _frequencyController,
              timeOfDayController: _timeOfDayController,
              ingredientDrafts: _ingredientDrafts,
              preview: preview,
              busy: widget.controller.busy,
              evidenceSpans: preview.evidenceSpans,
              onIngredientSelectionChanged: _setIngredientSelected,
              onAddIngredient: _addManualIngredient,
              onRemoveIngredient: _removeIngredient,
              onRegister: _registerSupplement,
            ),
            if (widget.controller.lastRegisteredSupplement != null) ...<Widget>[
              const SizedBox(height: 16),
              _RegisteredCard(
                response: widget.controller.lastRegisteredSupplement!,
              ),
            ],
            if (widget.controller.supplementImpactPreview != null) ...<Widget>[
              const SizedBox(height: 16),
              _SupplementImpactCard(
                preview: widget.controller.supplementImpactPreview!,
                explanation: widget.controller.supplementExplanation,
                busy: widget.controller.busy,
                onRefresh: widget.controller.refreshSupplementRecommendation,
                onExplain: () =>
                    widget.controller.explainSupplementRecommendation(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _recoverLostImage() async {
    try {
      final LostDataResponse response = await _imagePicker.retrieveLostData();
      final List<XFile>? files = response.files;
      if (!mounted || files == null || files.isEmpty) {
        return;
      }
      setState(() {
        _selectedImage = _SelectedLabelImage(
          path: files.first.path,
          source: 'android_lost_data',
          recoveredFromLostData: true,
        );
        _stage = _SupplementFlowStage.imageSelected;
      });
      await _refreshSelectedImageQuality(files.first.path);
    } catch (_) {
      // The plugin may be unavailable in widget tests; recovery is best-effort.
    }
  }

  Future<void> _pickImage(ImageSource source) async {
    if (source == ImageSource.camera &&
        (Platform.isAndroid || Platform.isIOS)) {
      final String cameraPermissionStatus = await _requestCameraPermission();
      if (!mounted) {
        return;
      }
      if (cameraPermissionStatus != _cameraPermissionGranted) {
        _showSnackBar(_cameraPermissionMessage(cameraPermissionStatus));
        return;
      }
    }

    XFile? image;
    try {
      image = await _imagePicker.pickImage(source: source);
    } catch (error) {
      if (mounted) {
        _showSnackBar(_imagePickerErrorMessage(error, source));
      }
      return;
    }
    if (image == null) return;
    final XFile selectedImage = image;
    setState(() {
      _selectedImage = _SelectedLabelImage(
        path: selectedImage.path,
        source: source == ImageSource.camera ? 'camera' : 'gallery',
        recoveredFromLostData: false,
      );
      _stage = _SupplementFlowStage.imageSelected;
      _seededAnalysisId = null;
    });
    widget.controller.clearSupplementFlow();
    await _refreshSelectedImageQuality(selectedImage.path);
  }

  void _resetSelectedImage() {
    widget.controller.clearSupplementFlow();
    setState(() {
      _selectedImage = null;
      _stage = _SupplementFlowStage.idle;
      _seededAnalysisId = null;
    });
  }

  Future<void> _refreshSelectedImageQuality(String imagePath) async {
    final _LocalCaptureQualityReport report =
        await _LocalCaptureQualityReport.analyzeFile(imagePath);
    if (!mounted) {
      return;
    }
    final _SelectedLabelImage? current = _selectedImage;
    if (current == null || current.path != imagePath) {
      return;
    }
    setState(() {
      _selectedImage = current.copyWith(captureQualityReport: report);
    });
  }

  Future<void> _analyzeSelectedImage() async {
    final _SelectedLabelImage? image = _selectedImage;
    if (image == null) {
      _showSnackBar('Select a label image before analysis.');
      return;
    }
    final _LocalCaptureQualityReport? captureQualityReport =
        image.captureQualityReport;
    if (captureQualityReport != null && captureQualityReport.requiresReview) {
      final bool proceed = await _confirmCaptureQualityBeforeAnalysis(
        captureQualityReport,
      );
      if (!mounted || !proceed) {
        return;
      }
    }
    setState(() {
      _stage = _SupplementFlowStage.uploading;
    });
    await Future<void>.delayed(Duration.zero);
    if (!mounted) {
      return;
    }
    setState(() {
      _stage = _SupplementFlowStage.ocrProcessing;
    });
    await widget.controller.analyzeImage(image.path);
    if (!mounted) {
      return;
    }
    setState(() {
      _stage = widget.controller.analysisPreview == null
          ? _SupplementFlowStage.imageSelected
          : _SupplementFlowStage.confirmationRequired;
    });
  }

  Future<bool> _confirmCaptureQualityBeforeAnalysis(
    _LocalCaptureQualityReport report,
  ) async {
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        final List<_LocalCaptureQualityIssue> issues = report.issues
            .take(3)
            .toList(growable: false);
        return AlertDialog(
          title: const Text('촬영 품질 확인'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text('OCR 전에 이미지 품질을 다시 확인해주세요.'),
              const SizedBox(height: 12),
              for (final _LocalCaptureQualityIssue issue in issues)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    '${_captureQualityIssueLabel(issue.reasonCode)}: '
                    '${_captureQualityGuidance(issue.reasonCode) ?? '이미지를 다시 확인해주세요.'}',
                  ),
                ),
            ],
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('다시 선택'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('그래도 분석'),
            ),
          ],
        );
      },
    );
    return confirmed == true;
  }

  Future<void> _submitOcrText() async {
    final String ocrText = _ocrTextController.text.trim();
    if (ocrText.isEmpty) {
      _showSnackBar('Enter OCR text before parsing.');
      return;
    }
    setState(() {
      _stage = _SupplementFlowStage.structuring;
    });
    await widget.controller.parseOcrText(ocrText);
    if (!mounted) {
      return;
    }
    setState(() {
      _stage = widget.controller.analysisPreview == null
          ? _SupplementFlowStage.imageSelected
          : _SupplementFlowStage.confirmationRequired;
    });
  }

  Future<void> _registerSupplement() async {
    final String displayName = _displayNameController.text.trim();
    if (displayName.isEmpty) {
      _showSnackBar('Display name is required.');
      return;
    }
    final SupplementAnalysisPreview? preview =
        widget.controller.analysisPreview;
    if (preview?.blocksRegistrationForImageRisk ?? false) {
      _showSnackBar('Resolve the image review action before registration.');
      return;
    }
    if (preview?.promptsImageRiskConfirmation ?? false) {
      final bool continueRegistration = await _confirmImageRiskSelection(
        preview!,
      );
      if (!continueRegistration) {
        return;
      }
    }

    final List<_IngredientDraft> selectedDrafts = _ingredientDrafts
        .where((_IngredientDraft draft) => draft.selected)
        .toList(growable: false);
    if (selectedDrafts.any((_IngredientDraft draft) => draft.requiresReview)) {
      final bool continueRegistration = await _confirmLowConfidenceSelection();
      if (!continueRegistration) {
        return;
      }
    }

    final List<UserSupplementIngredientInput> ingredients = selectedDrafts
        .map(_ingredientFromDraft)
        .whereType<UserSupplementIngredientInput>()
        .toList(growable: false);
    if (ingredients.isEmpty) {
      _showSnackBar('At least one ingredient is required.');
      return;
    }

    final UserSupplementCreate request = UserSupplementCreate(
      analysisId: preview?.analysisId,
      displayName: displayName,
      manufacturer: _emptyToNull(_manufacturerController.text),
      ingredients: ingredients,
      serving: SupplementServing(
        amount: _parseOptionalDouble(_servingAmountController.text),
        unit: _emptyToNull(_servingUnitController.text),
        dailyServings: _parseOptionalDouble(_dailyServingsController.text) ?? 1,
      ),
      intakeSchedule: SupplementIntakeSchedule(
        frequency: _frequencyController.text.trim().isEmpty
            ? 'daily'
            : _frequencyController.text.trim(),
        timeOfDay: _splitCsv(_timeOfDayController.text),
      ),
    );

    setState(() {
      _stage = _SupplementFlowStage.registering;
    });
    await widget.controller.registerSupplement(request);
    if (widget.controller.lastRegisteredSupplement == null) {
      if (!mounted) {
        return;
      }
      setState(() {
        _stage = _SupplementFlowStage.confirmationRequired;
      });
      return;
    }
    _ocrTextController.clear();
    _seededAnalysisId = null;
    if (!mounted) {
      return;
    }
    setState(() {
      _stage = _SupplementFlowStage.registered;
      _selectedImage = null;
    });
    await widget.controller.previewSupplementImpact();
    if (!mounted) {
      return;
    }
    setState(() {
      _stage = widget.controller.supplementImpactPreview == null
          ? _SupplementFlowStage.registered
          : _SupplementFlowStage.impactReady;
    });
  }

  UserSupplementIngredientInput? _ingredientFromDraft(_IngredientDraft draft) {
    if (!draft.selected) {
      return null;
    }
    final String displayName = draft.displayNameController.text.trim();
    if (displayName.isEmpty) {
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

  void _seedFromPreview(SupplementAnalysisPreview preview) {
    if (_seededAnalysisId == preview.analysisId) {
      return;
    }
    _seededAnalysisId = preview.analysisId;
    _displayNameController.text = preview.parsedProduct.productName ?? '';
    _manufacturerController.text = preview.parsedProduct.manufacturer ?? '';
    _servingUnitController.text = preview.parsedProduct.servingSize ?? '';
    final double? previewDailyServings =
        preview.parsedProduct.dailyServings ??
        preview.intakeMethod.structured.timesPerDay;
    _dailyServingsController.text = previewDailyServings?.toString() ?? '1';
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
                        .take(5)
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

  Future<bool> _confirmLowConfidenceSelection() async {
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('확인 필요 항목 포함'),
          content: const Text(
            '선택한 성분 중 확인 필요로 표시된 값이 있습니다. 라벨을 직접 확인한 뒤 저장하세요.',
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('취소'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('확인 후 저장'),
            ),
          ],
        );
      },
    );
    return confirmed == true;
  }

  Future<bool> _confirmImageRiskSelection(
    SupplementAnalysisPreview preview,
  ) async {
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Image review required'),
          content: Text(
            '${preview.imageActionLabel}. Confirm the label directly before saving.',
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Confirmed'),
            ),
          ],
        );
      },
    );
    return confirmed == true;
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<String> _requestCameraPermission() async {
    try {
      final String? status = await _cameraPermissionChannel
          .invokeMethod<String>('requestCameraPermission');
      return status ?? _cameraPermissionDenied;
    } on MissingPluginException {
      return _cameraPermissionGranted;
    } on PlatformException {
      return _cameraPermissionDenied;
    }
  }

  String _imagePickerErrorMessage(Object error, ImageSource source) {
    if (error is PlatformException) {
      switch (error.code) {
        case 'camera_access_denied':
          return _cameraPermissionDeniedMessage;
        case 'camera_access_restricted':
          return _cameraPermissionRestrictedMessage;
        case 'photo_access_denied':
          return '사진 접근 권한이 거부됐어요. 선택 가능한 사진을 허용하거나 다시 선택해주세요.';
        case 'photo_access_restricted':
          return '이 기기에서는 사진 접근이 제한돼 있어요. 다른 이미지를 선택해주세요.';
      }
    }
    return source == ImageSource.camera
        ? '시뮬레이터에서는 실제 카메라를 사용할 수 없어요. 갤러리 사진으로 테스트해주세요.'
        : '사진을 불러오지 못했어요. 다른 이미지로 다시 시도해주세요.';
  }
}

const String _cameraPermissionGranted = 'granted';
const String _cameraPermissionDenied = 'denied';
const String _cameraPermissionRestricted = 'restricted';
const String _cameraPermissionDeniedMessage =
    '카메라 권한이 거부됐어요. 설정에서 카메라 접근을 허용하거나 갤러리 사진으로 다시 시도해주세요.';
const String _cameraPermissionRestrictedMessage =
    '이 기기에서는 카메라 접근이 제한돼 있어요. 갤러리 사진으로 테스트해주세요.';

String _cameraPermissionMessage(String status) {
  return status == _cameraPermissionRestricted
      ? _cameraPermissionRestrictedMessage
      : _cameraPermissionDeniedMessage;
}

class _BlackConsentRequired extends StatelessWidget {
  const _BlackConsentRequired({required this.onClose});

  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.black,
      child: SafeArea(
        child: Column(
          children: <Widget>[
            _CaptureTopBar(title: '영양제 촬영', onClose: onClose),
            const Spacer(),
            const Icon(
              Icons.verified_user_outlined,
              color: Color(0xFFFFC400),
              size: 56,
            ),
            const SizedBox(height: 18),
            const Text(
              '동의가 필요해요',
              style: TextStyle(
                color: Colors.white,
                fontSize: 24,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 10),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 44),
              child: Text(
                'OCR 이미지 처리와 건강 분석 동의 후 영양제 라벨을 분석할 수 있어요.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Color(0xFFC8C8C8),
                  fontSize: 15,
                  height: 1.35,
                ),
              ),
            ),
            const Spacer(),
          ],
        ),
      ),
    );
  }
}

class _BlackCaptureSurface extends StatelessWidget {
  const _BlackCaptureSurface({
    required this.busy,
    required this.selectedImage,
    required this.stage,
    required this.onCamera,
    required this.onGallery,
    required this.onAnalyze,
    required this.onRetake,
    required this.onClose,
  });

  final bool busy;
  final _SelectedLabelImage? selectedImage;
  final _SupplementFlowStage stage;
  final VoidCallback onCamera;
  final VoidCallback onGallery;
  final VoidCallback onAnalyze;
  final VoidCallback onRetake;
  final VoidCallback? onClose;

  bool get _processing {
    return stage == _SupplementFlowStage.uploading ||
        stage == _SupplementFlowStage.ocrProcessing ||
        stage == _SupplementFlowStage.structuring;
  }

  @override
  Widget build(BuildContext context) {
    final _SelectedLabelImage? image = selectedImage;
    return ColoredBox(
      color: Colors.black,
      child: SafeArea(
        child: Column(
          children: <Widget>[
            _CaptureTopBar(
              title: image == null ? '영양제 촬영' : '미리보기',
              closeIcon: image == null
                  ? Icons.close_rounded
                  : Icons.arrow_back_rounded,
              onClose: image == null ? onClose : onRetake,
            ),
            const SizedBox(height: 16),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: image == null
                    ? const _SimulatorCameraFrame()
                    : SupplementLabelPreviewFrame(imagePath: image.path),
              ),
            ),
            if (_processing) ...<Widget>[
              const SizedBox(height: 14),
              const _CaptureStatusPill(
                icon: Icons.manage_search_rounded,
                label: 'OCR 분석 중이에요',
              ),
            ],
            if (image?.captureQualityReport != null) ...<Widget>[
              const SizedBox(height: 12),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: _LocalCaptureQualityPanel(
                  report: image!.captureQualityReport!,
                ),
              ),
            ],
            const SizedBox(height: 18),
            if (image == null)
              _CaptureControls(
                busy: busy,
                onCamera: onCamera,
                onGallery: onGallery,
              )
            else
              _PreviewControls(
                busy: busy,
                source: image.source,
                recoveredFromLostData: image.recoveredFromLostData,
                onRetake: onRetake,
                onAnalyze: onAnalyze,
              ),
            const SizedBox(height: 18),
          ],
        ),
      ),
    );
  }
}

class _CaptureTopBar extends StatelessWidget {
  const _CaptureTopBar({
    required this.title,
    required this.onClose,
    this.closeIcon = Icons.close_rounded,
  });

  final String title;
  final VoidCallback? onClose;
  final IconData closeIcon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      child: Row(
        children: <Widget>[
          _RoundCaptureIcon(icon: closeIcon, onTap: onClose),
          const Spacer(),
          Text(
            title,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
          const Spacer(),
          const SizedBox(width: 52, height: 52),
        ],
      ),
    );
  }
}

class _RoundCaptureIcon extends StatelessWidget {
  const _RoundCaptureIcon({required this.icon, required this.onTap});

  final IconData icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 52,
      height: 52,
      child: IconButton(
        tooltip: '닫기',
        onPressed: onTap,
        style: IconButton.styleFrom(
          backgroundColor: Colors.white.withValues(alpha: 0.10),
          foregroundColor: Colors.white,
        ),
        icon: Icon(icon, size: 26),
      ),
    );
  }
}

class _SimulatorCameraFrame extends StatelessWidget {
  const _SimulatorCameraFrame();

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: <Widget>[
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              border: Border.all(color: const Color(0xFF2B2B2B), width: 1.4),
              borderRadius: BorderRadius.circular(28),
            ),
            child: const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Icon(
                    Icons.no_photography_outlined,
                    color: Color(0xFF777777),
                    size: 56,
                  ),
                  SizedBox(height: 14),
                  Text(
                    '시뮬레이터에서는 카메라를 사용할 수 없어요',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Color(0xFFC8C8C8),
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        const _GuideCorners(),
        const Positioned(
          left: 28,
          right: 28,
          bottom: 28,
          child: _CaptureStatusPill(
            icon: Icons.photo_library_outlined,
            label: '갤러리 사진으로 OCR을 테스트해주세요',
          ),
        ),
      ],
    );
  }
}

/// OCR label preview frame that preserves the full selected image.
class SupplementLabelPreviewFrame extends StatelessWidget {
  /// Creates a preview frame for a selected label image.
  ///
  /// Args:
  ///   imagePath: Local image path returned by `ImagePicker`.
  const SupplementLabelPreviewFrame({required this.imagePath, super.key});

  /// Local selected image path.
  final String imagePath;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(28),
      child: ColoredBox(
        color: Colors.white,
        child: InteractiveViewer(
          maxScale: 4,
          child: Center(
            child: Image.file(
              File(imagePath),
              fit: BoxFit.contain,
              width: double.infinity,
              height: double.infinity,
            ),
          ),
        ),
      ),
    );
  }
}

class _GuideCorners extends StatelessWidget {
  const _GuideCorners();

  @override
  Widget build(BuildContext context) {
    const double size = 48;
    const double inset = 24;
    const Color color = Color(0xFFFFC400);
    return Stack(
      children: const <Widget>[
        Positioned(
          left: inset,
          top: inset,
          child: _GuideCorner(size: size, color: color),
        ),
        Positioned(
          right: inset,
          top: inset,
          child: RotatedBox(
            quarterTurns: 1,
            child: _GuideCorner(size: size, color: color),
          ),
        ),
        Positioned(
          right: inset,
          bottom: inset,
          child: RotatedBox(
            quarterTurns: 2,
            child: _GuideCorner(size: size, color: color),
          ),
        ),
        Positioned(
          left: inset,
          bottom: inset,
          child: RotatedBox(
            quarterTurns: 3,
            child: _GuideCorner(size: size, color: color),
          ),
        ),
      ],
    );
  }
}

class _GuideCorner extends StatelessWidget {
  const _GuideCorner({required this.size, required this.color});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: DecoratedBox(
        decoration: BoxDecoration(
          border: Border(
            left: BorderSide(color: color, width: 5),
            top: BorderSide(color: color, width: 5),
          ),
        ),
      ),
    );
  }
}

class _CaptureStatusPill extends StatelessWidget {
  const _CaptureStatusPill({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          Icon(icon, color: Colors.white, size: 20),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              label,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 15,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LocalCaptureQualityPanel extends StatelessWidget {
  const _LocalCaptureQualityPanel({required this.report});

  final _LocalCaptureQualityReport report;

  @override
  Widget build(BuildContext context) {
    final bool needsReview = report.requiresReview;
    final Color backgroundColor = needsReview
        ? const Color(0xFF2C2412)
        : const Color(0xFF14261D);
    final Color borderColor = needsReview
        ? const Color(0xFFFFC400)
        : const Color(0xFF4DD07A);
    final List<_LocalCaptureQualityIssue> issues = report.issues
        .take(3)
        .toList(growable: false);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: borderColor.withValues(alpha: 0.62)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Icon(
                  needsReview
                      ? Icons.warning_amber_rounded
                      : Icons.check_circle_outline_rounded,
                  color: borderColor,
                  size: 18,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    needsReview ? '촬영 품질을 확인해주세요' : '촬영 품질 확인됨',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
            if (issues.isNotEmpty) ...<Widget>[
              const SizedBox(height: 8),
              for (final _LocalCaptureQualityIssue issue in issues)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(
                    '${_captureQualityIssueLabel(issue.reasonCode)}: '
                    '${_captureQualityGuidance(issue.reasonCode) ?? '이미지를 다시 확인해주세요.'}',
                    style: const TextStyle(
                      color: Color(0xFFEDEDED),
                      fontSize: 13,
                      height: 1.28,
                    ),
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class _CaptureControls extends StatelessWidget {
  const _CaptureControls({
    required this.busy,
    required this.onCamera,
    required this.onGallery,
  });

  final bool busy;
  final VoidCallback onCamera;
  final VoidCallback onGallery;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Row(
        children: <Widget>[
          _SquareCaptureButton(
            icon: Icons.photo_library_outlined,
            onPressed: busy ? null : onGallery,
          ),
          const Spacer(),
          _ShutterButton(onPressed: busy ? null : onCamera),
          const Spacer(),
          const SizedBox(width: 64, height: 64),
        ],
      ),
    );
  }
}

class _PreviewControls extends StatelessWidget {
  const _PreviewControls({
    required this.busy,
    required this.source,
    required this.recoveredFromLostData,
    required this.onRetake,
    required this.onAnalyze,
  });

  final bool busy;
  final String source;
  final bool recoveredFromLostData;
  final VoidCallback onRetake;
  final VoidCallback onAnalyze;

  @override
  Widget build(BuildContext context) {
    final String sourceLabel = recoveredFromLostData
        ? '복구된 사진'
        : source == 'camera'
        ? '카메라 사진'
        : '갤러리 사진';
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        children: <Widget>[
          Text(
            '$sourceLabel 선택됨',
            style: const TextStyle(color: Color(0xFFC8C8C8), fontSize: 13),
          ),
          const SizedBox(height: 12),
          Row(
            children: <Widget>[
              Expanded(
                child: _DarkActionButton(
                  icon: Icons.refresh_rounded,
                  label: '다시 선택',
                  onPressed: busy ? null : onRetake,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: _YellowActionButton(
                  label: '분석하기',
                  onPressed: busy ? null : onAnalyze,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SquareCaptureButton extends StatelessWidget {
  const _SquareCaptureButton({required this.icon, required this.onPressed});

  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 64,
      height: 64,
      child: IconButton(
        tooltip: '갤러리',
        onPressed: onPressed,
        style: IconButton.styleFrom(
          backgroundColor: const Color(0xFF1B1B1B),
          foregroundColor: Colors.white,
          disabledBackgroundColor: const Color(0xFF141414),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
            side: BorderSide(color: Colors.white.withValues(alpha: 0.10)),
          ),
        ),
        icon: Icon(icon, size: 30),
      ),
    );
  }
}

class _ShutterButton extends StatelessWidget {
  const _ShutterButton({required this.onPressed});

  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 92,
      height: 92,
      child: IconButton(
        tooltip: '촬영',
        onPressed: onPressed,
        style: IconButton.styleFrom(
          backgroundColor: const Color(0xFFFFC400),
          foregroundColor: Colors.black,
          disabledBackgroundColor: const Color(0xFF725E08),
          shape: const CircleBorder(
            side: BorderSide(color: Color(0xFF8E8A76), width: 6),
          ),
        ),
        icon: const Icon(Icons.camera_alt_rounded, size: 32),
      ),
    );
  }
}

class _DarkActionButton extends StatelessWidget {
  const _DarkActionButton({
    required this.icon,
    required this.label,
    required this.onPressed,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return FilledButton.icon(
      onPressed: onPressed,
      style: FilledButton.styleFrom(
        backgroundColor: const Color(0xFF1B1B1B),
        foregroundColor: Colors.white,
        disabledBackgroundColor: const Color(0xFF141414),
        padding: const EdgeInsets.symmetric(vertical: 18),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      ),
      icon: Icon(icon),
      label: Text(label),
    );
  }
}

class _YellowActionButton extends StatelessWidget {
  const _YellowActionButton({required this.label, required this.onPressed});

  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: onPressed,
      style: FilledButton.styleFrom(
        backgroundColor: const Color(0xFFFFC400),
        foregroundColor: Colors.black,
        disabledBackgroundColor: const Color(0xFF725E08),
        padding: const EdgeInsets.symmetric(vertical: 20),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      ),
      child: Text(
        label,
        style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
      ),
    );
  }
}

class _ReviewTopBar extends StatelessWidget {
  const _ReviewTopBar({required this.onClose});

  final VoidCallback? onClose;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        IconButton(
          tooltip: '닫기',
          onPressed: onClose,
          icon: const Icon(Icons.close_rounded),
        ),
        const Expanded(
          child: Text(
            '영양제 분석',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
          ),
        ),
        const SizedBox(width: 48, height: 48),
      ],
    );
  }
}

class _ProcessingTimeline extends StatelessWidget {
  const _ProcessingTimeline({
    required this.stage,
    required this.preview,
    required this.busy,
  });

  final _SupplementFlowStage stage;
  final SupplementAnalysisPreview? preview;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final List<_TimelineStep> steps = <_TimelineStep>[
      _TimelineStep('Upload', _SupplementFlowStage.uploading),
      _TimelineStep('OCR', _SupplementFlowStage.ocrProcessing),
      _TimelineStep('Section', _SupplementFlowStage.sectionClassifying),
      _TimelineStep('Structure', _SupplementFlowStage.structuring),
      _TimelineStep('Confirm', _SupplementFlowStage.confirmationRequired),
    ];
    final int activeIndex = _stageIndex(stage);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Analysis progress',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                for (int index = 0; index < steps.length; index += 1)
                  _TimelineChip(
                    label: steps[index].label,
                    completed:
                        index < activeIndex ||
                        stage == _SupplementFlowStage.impactReady,
                    active: index == activeIndex && busy,
                    reviewNeeded: _stepNeedsReview(steps[index].stage),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  int _stageIndex(_SupplementFlowStage value) {
    return switch (value) {
      _SupplementFlowStage.idle => -1,
      _SupplementFlowStage.imageSelected => -1,
      _SupplementFlowStage.uploading => 0,
      _SupplementFlowStage.ocrProcessing => 1,
      _SupplementFlowStage.sectionClassifying => 2,
      _SupplementFlowStage.structuring => 3,
      _SupplementFlowStage.confirmationRequired => 4,
      _SupplementFlowStage.registering => 4,
      _SupplementFlowStage.registered => 4,
      _SupplementFlowStage.impactReady => 4,
    };
  }

  bool _stepNeedsReview(_SupplementFlowStage step) {
    final SupplementAnalysisPreview? currentPreview = preview;
    if (currentPreview == null) {
      return false;
    }
    if (step == _SupplementFlowStage.sectionClassifying) {
      return !currentPreview.layoutAvailable ||
          currentPreview.labelSections.any(
            (SupplementPreviewLabelSection section) => section.requiresReview,
          );
    }
    if (step == _SupplementFlowStage.structuring) {
      return currentPreview.lowConfidenceFields.isNotEmpty;
    }
    return false;
  }
}

class _TimelineStep {
  const _TimelineStep(this.label, this.stage);

  final String label;
  final _SupplementFlowStage stage;
}

class _TimelineChip extends StatelessWidget {
  const _TimelineChip({
    required this.label,
    required this.completed,
    required this.active,
    required this.reviewNeeded,
  });

  final String label;
  final bool completed;
  final bool active;
  final bool reviewNeeded;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;
    final Color color = reviewNeeded
        ? colors.errorContainer
        : completed
        ? colors.primaryContainer
        : colors.surfaceContainerHighest;
    return Chip(
      avatar: active
          ? const SizedBox.square(
              dimension: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : Icon(
              reviewNeeded
                  ? Icons.report_problem_outlined
                  : completed
                  ? Icons.check_circle_outline
                  : Icons.radio_button_unchecked,
              size: 18,
            ),
      backgroundColor: color,
      label: Text(reviewNeeded ? '$label: review' : label),
    );
  }
}

class _PreviewCard extends StatelessWidget {
  const _PreviewCard({required this.preview});

  final SupplementAnalysisPreview preview;

  @override
  Widget build(BuildContext context) {
    final String? ocrNotice = _ocrNoticeText(preview);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text('Preview', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text('Status: ${preview.status}'),
            Text('Ingredients: ${preview.ingredientCandidates.length}'),
            Text('Sections: ${preview.labelSections.length}'),
            if (ocrNotice != null) ...<Widget>[
              const SizedBox(height: 8),
              _LocalOcrNotice(message: ocrNotice),
            ],
            if (!preview.layoutAvailable)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: _ReviewBadge(
                  icon: Icons.view_agenda_outlined,
                  label: 'Section layout needs review',
                ),
              ),
            if (preview.requiresImageAction) ...<Widget>[
              const SizedBox(height: 8),
              _ImageRiskActionPanel(preview: preview),
            ],
            Text('Expires: ${preview.expiresAt.toLocal()}'),
            if (preview.warnings.isNotEmpty) ...<Widget>[
              const SizedBox(height: 8),
              for (final String warning in preview.warnings)
                Text('Warning: $warning'),
            ],
          ],
        ),
      ),
    );
  }
}

String? _ocrNoticeText(SupplementAnalysisPreview preview) {
  if (preview.ingredientCandidates.isNotEmpty) {
    return null;
  }
  final String warningText = preview.warnings.join(' ').toLowerCase();
  if (warningText.contains('automatic text extraction') ||
      warningText.contains('paddleocr') ||
      warningText.contains('ocr provider') ||
      warningText.contains('readable text')) {
    return '사진은 업로드됐지만 로컬 OCR이 라벨 성분을 읽지 못했어요. PaddleOCR 설정과 이미지 해상도/언어를 확인해주세요.';
  }
  return '사진은 업로드됐지만 성분 후보가 비어 있어요. 더 선명한 라벨 사진을 선택하거나 성분을 직접 입력해주세요.';
}

class _LocalOcrNotice extends StatelessWidget {
  const _LocalOcrNotice({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: colors.errorContainer.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: colors.error.withValues(alpha: 0.35)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(Icons.error_outline, color: colors.error, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                color: colors.onErrorContainer,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ImageRiskActionPanel extends StatelessWidget {
  const _ImageRiskActionPanel({required this.preview});

  final SupplementAnalysisPreview preview;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;
    final bool blocksRegistration = preview.blocksRegistrationForImageRisk;
    final Color backgroundColor = blocksRegistration
        ? colors.errorContainer
        : colors.tertiaryContainer;
    final Color foregroundColor = blocksRegistration
        ? colors.onErrorContainer
        : colors.onTertiaryContainer;
    final List<String> reasons =
        preview.imageQualityReport?.issues
            .map((SupplementImageQualityIssue issue) => issue.reasonCode)
            .take(3)
            .toList(growable: false) ??
        const <String>[];
    final List<String> guidance =
        preview.imageQualityReport?.issues
            .map(_imageQualityGuidance)
            .whereType<String>()
            .take(3)
            .toList(growable: false) ??
        const <String>[];
    return DecoratedBox(
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: DefaultTextStyle.merge(
          style: TextStyle(color: foregroundColor),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Icon(
                    blocksRegistration
                        ? Icons.block_outlined
                        : Icons.camera_alt_outlined,
                    color: foregroundColor,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      preview.imageActionLabel,
                      style: Theme.of(
                        context,
                      ).textTheme.labelLarge?.copyWith(color: foregroundColor),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text('Scope: ${preview.analysisScope}'),
              Text('Image role: ${preview.imageRole}'),
              if (preview.missingRequiredSections.isNotEmpty)
                Text('Missing: ${preview.missingRequiredSections.join(', ')}'),
              if (preview.detectedProductRegions.isNotEmpty)
                Text('Regions: ${preview.detectedProductRegions.length}'),
              if (reasons.isNotEmpty) Text('Reasons: ${reasons.join(', ')}'),
              for (final String item in guidance) Text(item),
              if (preview.identityConflict != null)
                Text(preview.identityConflict!.message),
            ],
          ),
        ),
      ),
    );
  }
}

String? _imageQualityGuidance(SupplementImageQualityIssue issue) {
  return _captureQualityGuidance(issue.reasonCode);
}

String _captureQualityIssueLabel(String reasonCode) {
  return switch (reasonCode) {
    'blurred_text' => '초점 흐림',
    'glare_or_reflection' => '반사광',
    'skewed_label' => '기울기',
    'cropped_label' => '잘림 가능성',
    'low_resolution' || 'too_small_text' => '해상도 낮음',
    'low_light' => '조도 낮음',
    'low_contrast' => '대비 낮음',
    _ => '품질 확인',
  };
}

String? _captureQualityGuidance(String reasonCode) {
  return switch (reasonCode) {
    'blurred_text' => '초점을 맞추고 흔들림 없이 다시 촬영해주세요.',
    'glare_or_reflection' => '반사광이 없도록 조명을 옆으로 두고 촬영해주세요.',
    'skewed_label' => '라벨을 정면에 맞추고 기울기를 줄여주세요.',
    'cropped_label' => '성분표 네 모서리가 모두 보이게 다시 촬영해주세요.',
    'low_resolution' || 'too_small_text' => '라벨 글자가 크게 보이도록 가까이 촬영해주세요.',
    'low_light' => '더 밝은 곳에서 촬영해주세요.',
    'low_contrast' => '그림자나 어두운 배경을 피해서 촬영해주세요.',
    _ => null,
  };
}

class _OcrTextCard extends StatelessWidget {
  const _OcrTextCard({
    required this.controller,
    required this.busy,
    required this.onSubmit,
  });

  final TextEditingController controller;
  final bool busy;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(
              'OCR text review',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            TextField(
              controller: controller,
              minLines: 4,
              maxLines: 8,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'Paste or edit OCR text from the supplement label.',
              ),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: busy ? null : onSubmit,
              icon: const Icon(Icons.text_fields),
              label: const Text('Parse OCR text'),
            ),
          ],
        ),
      ),
    );
  }
}

class _RegistrationCard extends StatelessWidget {
  const _RegistrationCard({
    required this.displayNameController,
    required this.manufacturerController,
    required this.servingAmountController,
    required this.servingUnitController,
    required this.dailyServingsController,
    required this.frequencyController,
    required this.timeOfDayController,
    required this.ingredientDrafts,
    required this.preview,
    required this.evidenceSpans,
    required this.busy,
    required this.onIngredientSelectionChanged,
    required this.onAddIngredient,
    required this.onRemoveIngredient,
    required this.onRegister,
  });

  final TextEditingController displayNameController;
  final TextEditingController manufacturerController;
  final TextEditingController servingAmountController;
  final TextEditingController servingUnitController;
  final TextEditingController dailyServingsController;
  final TextEditingController frequencyController;
  final TextEditingController timeOfDayController;
  final List<_IngredientDraft> ingredientDrafts;
  final SupplementAnalysisPreview preview;
  final List<SupplementPreviewEvidenceSpan> evidenceSpans;
  final bool busy;
  final void Function(_IngredientDraft draft, bool selected)
  onIngredientSelectionChanged;
  final VoidCallback onAddIngredient;
  final void Function(_IngredientDraft draft) onRemoveIngredient;
  final VoidCallback onRegister;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(
              'Confirm supplement',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: displayNameController,
              decoration: const InputDecoration(
                labelText: 'Display name',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: manufacturerController,
              decoration: const InputDecoration(
                labelText: 'Manufacturer',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            Text('Ingredients', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 8),
            for (final _IngredientDraft draft in ingredientDrafts)
              _IngredientDraftTile(
                draft: draft,
                evidenceSpans: evidenceSpans,
                onSelectionChanged: (bool selected) =>
                    onIngredientSelectionChanged(draft, selected),
                onRemove: ingredientDrafts.length == 1
                    ? null
                    : () => onRemoveIngredient(draft),
              ),
            OutlinedButton.icon(
              onPressed: onAddIngredient,
              icon: const Icon(Icons.add),
              label: const Text('Add ingredient'),
            ),
            const SizedBox(height: 16),
            Text('Serving', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 8),
            Row(
              children: <Widget>[
                Expanded(
                  child: TextField(
                    controller: servingAmountController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Amount',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: servingUnitController,
                    decoration: const InputDecoration(
                      labelText: 'Unit',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            TextField(
              controller: dailyServingsController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Daily servings',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: frequencyController,
              decoration: const InputDecoration(
                labelText: 'Frequency',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: timeOfDayController,
              decoration: const InputDecoration(
                labelText: 'Time of day, comma-separated',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            _SectionReview(preview: preview, evidenceSpans: evidenceSpans),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: busy ? null : onRegister,
              icon: const Icon(Icons.save_outlined),
              label: const Text('Register confirmed supplement'),
            ),
          ],
        ),
      ),
    );
  }
}

class _IngredientDraftTile extends StatelessWidget {
  const _IngredientDraftTile({
    required this.draft,
    required this.evidenceSpans,
    required this.onSelectionChanged,
    required this.onRemove,
  });

  final _IngredientDraft draft;
  final List<SupplementPreviewEvidenceSpan> evidenceSpans;
  final ValueChanged<bool> onSelectionChanged;
  final VoidCallback? onRemove;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: DecoratedBox(
        decoration: BoxDecoration(
          border: Border.all(color: Theme.of(context).colorScheme.outline),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: draft.selected,
                onChanged: (bool? value) => onSelectionChanged(value ?? false),
                title: Text(
                  draft.requiresReview
                      ? 'Ingredient candidate - review needed'
                      : 'Ingredient candidate',
                ),
                subtitle: Text(
                  'Confidence: ${_formatConfidence(draft.confidence)}',
                ),
                controlAffinity: ListTileControlAffinity.leading,
              ),
              if (draft.requiresReview)
                const Padding(
                  padding: EdgeInsets.only(bottom: 8),
                  child: _ReviewBadge(
                    icon: Icons.report_problem_outlined,
                    label: '확인 필요',
                  ),
                ),
              TextField(
                controller: draft.displayNameController,
                decoration: InputDecoration(
                  labelText: 'Ingredient',
                  border: const OutlineInputBorder(),
                  suffixIcon: onRemove == null
                      ? null
                      : IconButton(
                          tooltip: 'Remove ingredient',
                          onPressed: onRemove,
                          icon: const Icon(Icons.delete_outline),
                        ),
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: <Widget>[
                  Expanded(
                    child: TextField(
                      controller: draft.amountController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Amount',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: draft.unitController,
                      decoration: const InputDecoration(
                        labelText: 'Unit',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              TextField(
                controller: draft.nutrientCodeController,
                decoration: const InputDecoration(
                  labelText: 'Nutrient code',
                  border: OutlineInputBorder(),
                ),
              ),
              if (draft.evidenceRefs.isNotEmpty) ...<Widget>[
                const SizedBox(height: 8),
                TextButton.icon(
                  onPressed: () => _showEvidenceDialog(
                    context,
                    evidenceSpans,
                    draft.evidenceRefs,
                  ),
                  icon: const Icon(Icons.article_outlined),
                  label: const Text('Evidence'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionReview extends StatelessWidget {
  const _SectionReview({required this.preview, required this.evidenceSpans});

  final SupplementAnalysisPreview preview;
  final List<SupplementPreviewEvidenceSpan> evidenceSpans;

  @override
  Widget build(BuildContext context) {
    return ExpansionPanelList.radio(
      children: <ExpansionPanelRadio>[
        ExpansionPanelRadio(
          value: 'sections',
          headerBuilder: (BuildContext context, bool isExpanded) {
            return const ListTile(title: Text('Label sections'));
          },
          body: _LabelSectionList(
            sections: preview.labelSections,
            evidenceSpans: evidenceSpans,
          ),
        ),
        ExpansionPanelRadio(
          value: 'intake',
          headerBuilder: (BuildContext context, bool isExpanded) {
            return const ListTile(title: Text('Intake method'));
          },
          body: _IntakeMethodPanel(
            intakeMethod: preview.intakeMethod,
            evidenceSpans: evidenceSpans,
          ),
        ),
        ExpansionPanelRadio(
          value: 'precautions',
          headerBuilder: (BuildContext context, bool isExpanded) {
            return const ListTile(title: Text('Precautions'));
          },
          body: _ReadOnlyRowsPanel(
            emptyText: 'No label precautions found.',
            rows: <_ReviewRow>[
              for (final SupplementPreviewPrecaution item
                  in preview.precautions)
                _ReviewRow(
                  title: item.category,
                  body: item.text,
                  requiresReview: item.requiresReview,
                  evidenceRefs: item.evidenceRefs,
                ),
            ],
            evidenceSpans: evidenceSpans,
          ),
        ),
        ExpansionPanelRadio(
          value: 'claims',
          headerBuilder: (BuildContext context, bool isExpanded) {
            return const ListTile(title: Text('Functional claims'));
          },
          body: _ReadOnlyRowsPanel(
            emptyText: 'No label functional claims found.',
            rows: <_ReviewRow>[
              for (final SupplementPreviewFunctionalClaim item
                  in preview.functionalClaims)
                _ReviewRow(
                  title: item.claimType,
                  body: item.text,
                  requiresReview: item.requiresReview,
                  evidenceRefs: item.evidenceRefs,
                ),
            ],
            evidenceSpans: evidenceSpans,
          ),
        ),
      ],
    );
  }
}

class _LabelSectionList extends StatelessWidget {
  const _LabelSectionList({
    required this.sections,
    required this.evidenceSpans,
  });

  final List<SupplementPreviewLabelSection> sections;
  final List<SupplementPreviewEvidenceSpan> evidenceSpans;

  @override
  Widget build(BuildContext context) {
    if (sections.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Text('No structured sections found. Review fields manually.'),
      );
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          for (final SupplementPreviewLabelSection section in sections)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: <Widget>[
                      Text(
                        section.headingText ?? section.sectionType,
                        style: Theme.of(context).textTheme.labelLarge,
                      ),
                      if (section.requiresReview)
                        const _ReviewBadge(
                          icon: Icons.report_problem_outlined,
                          label: '확인 필요',
                        ),
                    ],
                  ),
                  if (section.textBundle != null) ...<Widget>[
                    const SizedBox(height: 4),
                    Text(section.textBundle!),
                  ],
                  if (section.evidenceRefs.isNotEmpty)
                    TextButton.icon(
                      onPressed: () => _showEvidenceDialog(
                        context,
                        evidenceSpans,
                        section.evidenceRefs,
                      ),
                      icon: const Icon(Icons.article_outlined),
                      label: const Text('Evidence'),
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _IntakeMethodPanel extends StatelessWidget {
  const _IntakeMethodPanel({
    required this.intakeMethod,
    required this.evidenceSpans,
  });

  final SupplementPreviewIntakeMethod intakeMethod;
  final List<SupplementPreviewEvidenceSpan> evidenceSpans;

  @override
  Widget build(BuildContext context) {
    final SupplementPreviewStructuredIntakeMethod structured =
        intakeMethod.structured;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (intakeMethod.requiresReview)
            const Padding(
              padding: EdgeInsets.only(bottom: 8),
              child: _ReviewBadge(
                icon: Icons.report_problem_outlined,
                label: '확인 필요',
              ),
            ),
          Text(intakeMethod.text ?? 'No intake method text found.'),
          const SizedBox(height: 8),
          Text('Frequency: ${structured.frequency}'),
          Text('Times per day: ${structured.timesPerDay ?? '-'}'),
          Text(
            'Amount per time: ${structured.amountPerTime ?? '-'} ${structured.amountUnit ?? ''}',
          ),
          if (intakeMethod.evidenceRefs.isNotEmpty)
            TextButton.icon(
              onPressed: () => _showEvidenceDialog(
                context,
                evidenceSpans,
                intakeMethod.evidenceRefs,
              ),
              icon: const Icon(Icons.article_outlined),
              label: const Text('Evidence'),
            ),
        ],
      ),
    );
  }
}

class _ReadOnlyRowsPanel extends StatelessWidget {
  const _ReadOnlyRowsPanel({
    required this.emptyText,
    required this.rows,
    required this.evidenceSpans,
  });

  final String emptyText;
  final List<_ReviewRow> rows;
  final List<SupplementPreviewEvidenceSpan> evidenceSpans;

  @override
  Widget build(BuildContext context) {
    if (rows.isEmpty) {
      return Padding(padding: const EdgeInsets.all(16), child: Text(emptyText));
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      child: Column(
        children: <Widget>[
          for (final _ReviewRow row in rows)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(row.title),
              subtitle: Text(row.body),
              trailing: row.requiresReview
                  ? const Icon(Icons.report_problem_outlined)
                  : null,
              onTap: row.evidenceRefs.isEmpty
                  ? null
                  : () => _showEvidenceDialog(
                      context,
                      evidenceSpans,
                      row.evidenceRefs,
                    ),
            ),
        ],
      ),
    );
  }
}

class _ReviewRow {
  const _ReviewRow({
    required this.title,
    required this.body,
    required this.requiresReview,
    required this.evidenceRefs,
  });

  final String title;
  final String body;
  final bool requiresReview;
  final List<String> evidenceRefs;
}

class _RegisteredCard extends StatelessWidget {
  const _RegisteredCard({required this.response});

  final UserSupplementResponse response;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: const Icon(Icons.check_circle_outline),
        title: Text(response.displayName),
        subtitle: Text('Registered supplement ID: ${response.id}'),
      ),
    );
  }
}

class _SupplementImpactCard extends StatelessWidget {
  const _SupplementImpactCard({
    required this.preview,
    required this.explanation,
    required this.busy,
    required this.onRefresh,
    required this.onExplain,
  });

  final SupplementImpactPreviewResponse preview;
  final SupplementRecommendationExplainResponse? explanation;
  final bool busy;
  final VoidCallback onRefresh;
  final VoidCallback onExplain;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(
              '현재 섭취 정보 기반 점검 결과',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(preview.safeUserMessage),
            const SizedBox(height: 8),
            Text('Status: ${preview.dataStatus}'),
            const SizedBox(height: 12),
            _ImpactBucket(
              title: 'Current supplement contributions',
              emptyText: 'No calculated supplement contributions.',
              children: <Widget>[
                for (final SupplementContributionAggregate item
                    in preview.currentSupplementContributions)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(item.nutrientName ?? item.nutrientCode),
                    subtitle: Text(
                      '${item.totalDailyAmount ?? '-'} ${item.referenceUnit ?? ''} · ${item.contributionCount} item(s)',
                    ),
                  ),
              ],
            ),
            _ImpactBucket(
              title: 'Deficiency overlap candidates',
              emptyText: 'No deficiency overlap candidates.',
              children: <Widget>[
                for (final SupplementNutritionInsight insight
                    in preview.deficiencySupportCandidates)
                  _InsightTile(insight: insight),
              ],
            ),
            _ImpactBucket(
              title: 'Duplicate or excess review',
              emptyText: 'No duplicate or upper-limit review items.',
              children: <Widget>[
                for (final SupplementNutritionInsight insight
                    in preview.excessOrDuplicateRisks)
                  _InsightTile(insight: insight),
              ],
            ),
            if (preview.missingProfileFields.isNotEmpty) ...<Widget>[
              const SizedBox(height: 8),
              Text(
                'Missing profile fields: ${preview.missingProfileFields.join(', ')}',
              ),
            ],
            if (preview.warnings.isNotEmpty) ...<Widget>[
              const SizedBox(height: 8),
              for (final String warning in preview.warnings)
                Text('Warning: $warning'),
            ],
            const SizedBox(height: 12),
            Text(
              preview.clinicalDisclaimer,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            if (explanation != null) ...<Widget>[
              const Divider(height: 24),
              Text(explanation!.safeUserMessage),
              for (final String bullet in explanation!.explanationBullets)
                Text('• $bullet'),
            ],
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                OutlinedButton.icon(
                  onPressed: busy ? null : onRefresh,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Refresh check'),
                ),
                OutlinedButton.icon(
                  onPressed: busy ? null : onExplain,
                  icon: const Icon(Icons.notes_outlined),
                  label: const Text('Explain'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ImpactBucket extends StatelessWidget {
  const _ImpactBucket({
    required this.title,
    required this.emptyText,
    required this.children,
  });

  final String title;
  final String emptyText;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.labelLarge),
          if (children.isEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(emptyText),
            )
          else
            ...children,
        ],
      ),
    );
  }
}

class _InsightTile extends StatelessWidget {
  const _InsightTile({required this.insight});

  final SupplementNutritionInsight insight;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: Icon(
        insight.actionLabel == 'avoid_duplicate'
            ? Icons.content_copy_outlined
            : Icons.info_outline,
      ),
      title: Text(insight.nutrientName ?? insight.nutrientCode),
      subtitle: Text(insight.userMessage),
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
    required this.evidenceRefs,
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
      evidenceRefs: const <String>[],
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
      evidenceRefs: const <String>[],
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
  final List<String> evidenceRefs;

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

class _LocalCaptureQualityReport {
  const _LocalCaptureQualityReport({
    required this.status,
    required this.issues,
    required this.metrics,
  });

  static const int _minTotalPixels = 1000000;
  static const int _minShortEdgePx = 900;
  static const double _minEdgeVariance = 24;
  static const double _minContrastStddev = 18;
  static const double _glareBrightRatio = 0.72;
  static const double _maxBorderInkRatio = 0.18;
  static const double _skewedAspectRatio = 2.8;
  static const int _analysisMaxEdgePx = 512;

  final String status;
  final List<_LocalCaptureQualityIssue> issues;
  final Map<String, num> metrics;

  bool get requiresReview => issues.isNotEmpty;

  static Future<_LocalCaptureQualityReport> analyzeFile(
    String imagePath,
  ) async {
    try {
      final Uint8List bytes = File(imagePath).readAsBytesSync();
      final _ImageDimensions? headerDimensions =
          _decodeImageDimensionsFromHeaders(bytes);
      if (headerDimensions != null &&
          _dimensionIssues(headerDimensions).isNotEmpty) {
        return _fromDimensionsOnly(headerDimensions);
      }
      final _ImageDimensions dimensions =
          headerDimensions ?? await _decodeImageDimensions(bytes);
      final int maxEdge = math.max(dimensions.width, dimensions.height);
      final double scale = maxEdge > _analysisMaxEdgePx
          ? _analysisMaxEdgePx / maxEdge
          : 1;
      final int analysisWidth = math.max(1, (dimensions.width * scale).round());
      final int analysisHeight = math.max(
        1,
        (dimensions.height * scale).round(),
      );
      final ui.Codec codec = await ui.instantiateImageCodec(
        bytes,
        targetWidth: analysisWidth,
        targetHeight: analysisHeight,
      );
      final ui.FrameInfo frame = await codec.getNextFrame();
      final ui.Image image = frame.image;
      try {
        final ByteData? byteData = await image.toByteData(
          format: ui.ImageByteFormat.rawRgba,
        );
        if (byteData == null) {
          return _LocalCaptureQualityReport(
            status: 'needs_review',
            issues: const <_LocalCaptureQualityIssue>[
              _LocalCaptureQualityIssue(
                reasonCode: 'quality_check_unavailable',
                severity: 'review',
              ),
            ],
            metrics: <String, num>{
              'image_width': dimensions.width,
              'image_height': dimensions.height,
            },
          );
        }
        return _LocalCaptureQualityReport._fromPixels(
          pixels: byteData.buffer.asUint8List(),
          analysisWidth: image.width,
          analysisHeight: image.height,
          originalWidth: dimensions.width,
          originalHeight: dimensions.height,
        );
      } finally {
        image.dispose();
        codec.dispose();
      }
    } catch (_) {
      return const _LocalCaptureQualityReport(
        status: 'needs_review',
        issues: <_LocalCaptureQualityIssue>[
          _LocalCaptureQualityIssue(
            reasonCode: 'quality_check_unavailable',
            severity: 'review',
          ),
        ],
        metrics: <String, num>{},
      );
    }
  }

  static Future<_ImageDimensions> _decodeImageDimensions(
    Uint8List bytes,
  ) async {
    final ui.Codec codec = await ui.instantiateImageCodec(bytes);
    final ui.FrameInfo frame = await codec.getNextFrame();
    final ui.Image image = frame.image;
    try {
      return _ImageDimensions(width: image.width, height: image.height);
    } finally {
      image.dispose();
      codec.dispose();
    }
  }

  static _ImageDimensions? _decodeImageDimensionsFromHeaders(Uint8List bytes) {
    if (_isPng(bytes)) {
      return _ImageDimensions(
        width: _readUint32(bytes, 16),
        height: _readUint32(bytes, 20),
      );
    }
    if (_isJpeg(bytes)) {
      return _decodeJpegDimensions(bytes);
    }
    return null;
  }

  static bool _isPng(Uint8List bytes) {
    return bytes.length >= 24 &&
        bytes[0] == 0x89 &&
        bytes[1] == 0x50 &&
        bytes[2] == 0x4E &&
        bytes[3] == 0x47 &&
        bytes[4] == 0x0D &&
        bytes[5] == 0x0A &&
        bytes[6] == 0x1A &&
        bytes[7] == 0x0A;
  }

  static bool _isJpeg(Uint8List bytes) {
    return bytes.length >= 4 && bytes[0] == 0xFF && bytes[1] == 0xD8;
  }

  static _ImageDimensions? _decodeJpegDimensions(Uint8List bytes) {
    int offset = 2;
    while (offset + 9 < bytes.length) {
      if (bytes[offset] != 0xFF) {
        offset += 1;
        continue;
      }
      while (offset < bytes.length && bytes[offset] == 0xFF) {
        offset += 1;
      }
      if (offset >= bytes.length) {
        return null;
      }
      final int marker = bytes[offset];
      offset += 1;
      if (marker == 0xD9 || marker == 0xDA) {
        return null;
      }
      if (offset + 1 >= bytes.length) {
        return null;
      }
      final int segmentLength = _readUint16(bytes, offset);
      if (segmentLength < 2 || offset + segmentLength > bytes.length) {
        return null;
      }
      if (_isJpegStartOfFrame(marker) && segmentLength >= 7) {
        return _ImageDimensions(
          height: _readUint16(bytes, offset + 3),
          width: _readUint16(bytes, offset + 5),
        );
      }
      offset += segmentLength;
    }
    return null;
  }

  static bool _isJpegStartOfFrame(int marker) {
    return (marker >= 0xC0 && marker <= 0xC3) ||
        (marker >= 0xC5 && marker <= 0xC7) ||
        (marker >= 0xC9 && marker <= 0xCB) ||
        (marker >= 0xCD && marker <= 0xCF);
  }

  static int _readUint16(Uint8List bytes, int offset) {
    return (bytes[offset] << 8) | bytes[offset + 1];
  }

  static int _readUint32(Uint8List bytes, int offset) {
    return (bytes[offset] << 24) |
        (bytes[offset + 1] << 16) |
        (bytes[offset + 2] << 8) |
        bytes[offset + 3];
  }

  static List<_LocalCaptureQualityIssue> _dimensionIssues(
    _ImageDimensions dimensions,
  ) {
    final int shortEdge = math.min(dimensions.width, dimensions.height);
    final int totalPixels = dimensions.width * dimensions.height;
    final double aspectRatio = math.max(
      dimensions.width / dimensions.height,
      dimensions.height / dimensions.width,
    );
    final List<_LocalCaptureQualityIssue> issues =
        <_LocalCaptureQualityIssue>[];
    if (totalPixels < _minTotalPixels || shortEdge < _minShortEdgePx) {
      issues.add(
        const _LocalCaptureQualityIssue(
          reasonCode: 'low_resolution',
          severity: 'retake',
        ),
      );
    }
    if (aspectRatio >= _skewedAspectRatio) {
      issues.add(
        const _LocalCaptureQualityIssue(
          reasonCode: 'skewed_label',
          severity: 'review',
        ),
      );
    }
    return issues;
  }

  static _LocalCaptureQualityReport _fromDimensionsOnly(
    _ImageDimensions dimensions,
  ) {
    final int shortEdge = math.min(dimensions.width, dimensions.height);
    final int totalPixels = dimensions.width * dimensions.height;
    final double aspectRatio = math.max(
      dimensions.width / dimensions.height,
      dimensions.height / dimensions.width,
    );
    return _LocalCaptureQualityReport(
      status: 'needs_review',
      issues: List<_LocalCaptureQualityIssue>.unmodifiable(
        _dimensionIssues(dimensions),
      ),
      metrics: <String, num>{
        'image_width': dimensions.width,
        'image_height': dimensions.height,
        'total_pixels': totalPixels,
        'short_edge_px': shortEdge,
        'aspect_ratio': _roundQualityMetric(aspectRatio),
      },
    );
  }

  factory _LocalCaptureQualityReport._fromPixels({
    required Uint8List pixels,
    required int analysisWidth,
    required int analysisHeight,
    required int originalWidth,
    required int originalHeight,
  }) {
    final List<double> luminance = _luminanceValues(pixels);
    final double contrastStddev = _standardDeviation(luminance);
    final double brightRatio = _brightPixelRatio(luminance);
    final double borderInkRatio = _borderInkRatio(
      luminance: luminance,
      width: analysisWidth,
      height: analysisHeight,
    );
    final double edgeVariance = _edgeVariance(
      luminance: luminance,
      width: analysisWidth,
      height: analysisHeight,
    );
    final int shortEdge = math.min(originalWidth, originalHeight);
    final int totalPixels = originalWidth * originalHeight;
    final double aspectRatio = math.max(
      originalWidth / originalHeight,
      originalHeight / originalWidth,
    );
    final List<_LocalCaptureQualityIssue> issues =
        <_LocalCaptureQualityIssue>[];
    if (totalPixels < _minTotalPixels || shortEdge < _minShortEdgePx) {
      issues.add(
        const _LocalCaptureQualityIssue(
          reasonCode: 'low_resolution',
          severity: 'retake',
        ),
      );
    }
    if (edgeVariance < _minEdgeVariance) {
      issues.add(
        const _LocalCaptureQualityIssue(
          reasonCode: 'blurred_text',
          severity: 'retake',
        ),
      );
    }
    if (contrastStddev < _minContrastStddev) {
      issues.add(
        const _LocalCaptureQualityIssue(
          reasonCode: 'low_contrast',
          severity: 'retake',
        ),
      );
    }
    if (brightRatio >= _glareBrightRatio &&
        contrastStddev < _minContrastStddev * 1.5) {
      issues.add(
        const _LocalCaptureQualityIssue(
          reasonCode: 'glare_or_reflection',
          severity: 'review',
        ),
      );
    }
    if (borderInkRatio >= _maxBorderInkRatio) {
      issues.add(
        const _LocalCaptureQualityIssue(
          reasonCode: 'cropped_label',
          severity: 'retake',
        ),
      );
    }
    if (aspectRatio >= _skewedAspectRatio) {
      issues.add(
        const _LocalCaptureQualityIssue(
          reasonCode: 'skewed_label',
          severity: 'review',
        ),
      );
    }
    return _LocalCaptureQualityReport(
      status: issues.isEmpty ? 'acceptable' : 'needs_review',
      issues: List<_LocalCaptureQualityIssue>.unmodifiable(issues),
      metrics: <String, num>{
        'image_width': originalWidth,
        'image_height': originalHeight,
        'total_pixels': totalPixels,
        'short_edge_px': shortEdge,
        'edge_variance': _roundQualityMetric(edgeVariance),
        'contrast_stddev': _roundQualityMetric(contrastStddev),
        'bright_pixel_ratio': _roundQualityMetric(brightRatio),
        'border_ink_ratio': _roundQualityMetric(borderInkRatio),
        'aspect_ratio': _roundQualityMetric(aspectRatio),
      },
    );
  }

  static List<double> _luminanceValues(Uint8List pixels) {
    final List<double> values = <double>[];
    for (int index = 0; index + 2 < pixels.length; index += 4) {
      final int red = pixels[index];
      final int green = pixels[index + 1];
      final int blue = pixels[index + 2];
      values.add((red * 0.299) + (green * 0.587) + (blue * 0.114));
    }
    return values;
  }

  static double _brightPixelRatio(List<double> luminance) {
    if (luminance.isEmpty) {
      return 0;
    }
    final int brightPixels = luminance
        .where((double value) => value >= 245)
        .length;
    return brightPixels / luminance.length;
  }

  static double _borderInkRatio({
    required List<double> luminance,
    required int width,
    required int height,
  }) {
    if (width <= 0 || height <= 0 || luminance.isEmpty) {
      return 0;
    }
    final int border = math.max(1, math.min(width, height) ~/ 20);
    int darkPixels = 0;
    int borderPixels = 0;
    for (int y = 0; y < height; y += 1) {
      for (int x = 0; x < width; x += 1) {
        if (x >= border &&
            x < width - border &&
            y >= border &&
            y < height - border) {
          continue;
        }
        final double value = luminance[(y * width) + x];
        if (value < 85) {
          darkPixels += 1;
        }
        borderPixels += 1;
      }
    }
    return borderPixels == 0 ? 0 : darkPixels / borderPixels;
  }

  static double _edgeVariance({
    required List<double> luminance,
    required int width,
    required int height,
  }) {
    if (width < 3 || height < 3 || luminance.isEmpty) {
      return 0;
    }
    final List<double> responses = <double>[];
    for (int y = 1; y < height - 1; y += 2) {
      for (int x = 1; x < width - 1; x += 2) {
        final int index = (y * width) + x;
        final double center = luminance[index] * 4;
        final double neighbors =
            luminance[index - 1] +
            luminance[index + 1] +
            luminance[index - width] +
            luminance[index + width];
        responses.add((center - neighbors).abs());
      }
    }
    return _variance(responses);
  }

  static double _standardDeviation(List<double> values) {
    return math.sqrt(_variance(values));
  }

  static double _variance(List<double> values) {
    if (values.isEmpty) {
      return 0;
    }
    final double mean =
        values.reduce((double left, double right) => left + right) /
        values.length;
    final double sumOfSquares = values.fold<double>(
      0,
      (double total, double value) =>
          total + math.pow(value - mean, 2).toDouble(),
    );
    return sumOfSquares / values.length;
  }
}

class _LocalCaptureQualityIssue {
  const _LocalCaptureQualityIssue({
    required this.reasonCode,
    required this.severity,
  });

  final String reasonCode;
  final String severity;
}

class _ImageDimensions {
  const _ImageDimensions({required this.width, required this.height});

  final int width;
  final int height;
}

num _roundQualityMetric(double value) {
  return double.parse(value.toStringAsFixed(4));
}

class _SelectedLabelImage {
  const _SelectedLabelImage({
    required this.path,
    required this.source,
    required this.recoveredFromLostData,
    this.captureQualityReport,
  });

  final String path;
  final String source;
  final bool recoveredFromLostData;
  final _LocalCaptureQualityReport? captureQualityReport;

  _SelectedLabelImage copyWith({
    _LocalCaptureQualityReport? captureQualityReport,
  }) {
    return _SelectedLabelImage(
      path: path,
      source: source,
      recoveredFromLostData: recoveredFromLostData,
      captureQualityReport: captureQualityReport ?? this.captureQualityReport,
    );
  }
}

enum _SupplementFlowStage {
  idle,
  imageSelected,
  uploading,
  ocrProcessing,
  sectionClassifying,
  structuring,
  confirmationRequired,
  registering,
  registered,
  impactReady,
}

class _ReviewBadge extends StatelessWidget {
  const _ReviewBadge({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: colors.errorContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(icon, size: 16),
            const SizedBox(width: 4),
            Text(label),
          ],
        ),
      ),
    );
  }
}

String _formatConfidence(double? value) {
  if (value == null) {
    return 'unknown';
  }
  return '${(value * 100).round()}%';
}

void _showEvidenceDialog(
  BuildContext context,
  List<SupplementPreviewEvidenceSpan> spans,
  List<String> refs,
) {
  final List<SupplementPreviewEvidenceSpan> matched = spans
      .where((SupplementPreviewEvidenceSpan span) => refs.contains(span.spanId))
      .toList(growable: false);
  showDialog<void>(
    context: context,
    builder: (BuildContext context) {
      return AlertDialog(
        title: const Text('Evidence'),
        content: matched.isEmpty
            ? const Text('No bounded evidence excerpt is available.')
            : Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  for (final SupplementPreviewEvidenceSpan span in matched)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(span.textExcerpt),
                    ),
                ],
              ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      );
    },
  );
}
