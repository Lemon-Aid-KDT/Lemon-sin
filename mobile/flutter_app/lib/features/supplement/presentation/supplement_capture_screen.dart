import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../../shared/state/confirmed_entry_store.dart';
import '../../../shared/theme/lemon_theme.dart';
import '../../../shared/widgets/capture_frame_card.dart';
import '../../../shared/widgets/medical_disclaimer.dart';
import '../data/supplement_capture_repository.dart';
import '../domain/supplement_analysis_preview.dart';

class SupplementCaptureScreen extends StatefulWidget {
  const SupplementCaptureScreen({super.key});

  @override
  State<SupplementCaptureScreen> createState() =>
      _SupplementCaptureScreenState();
}

class _SupplementCaptureScreenState extends State<SupplementCaptureScreen> {
  final ImagePicker _picker = ImagePicker();
  final SupplementCaptureRepository _repository = SupplementCaptureRepository();
  final TextEditingController _productNameController = TextEditingController();
  final TextEditingController _manufacturerController = TextEditingController();
  final TextEditingController _ingredientNameController =
      TextEditingController();
  final TextEditingController _ingredientAmountController =
      TextEditingController();
  final TextEditingController _ingredientUnitController =
      TextEditingController();
  final TextEditingController _servingAmountController =
      TextEditingController();
  final TextEditingController _servingUnitController = TextEditingController();
  final TextEditingController _dailyServingsController =
      TextEditingController(text: '1');
  final TextEditingController _frequencyController =
      TextEditingController(text: 'daily');

  String? _selectedImageName;
  String? _statusMessage;
  SupplementAnalysisPreview? _preview;
  bool _isSelecting = false;
  bool _isSaving = false;
  bool _userConfirmed = false;

  @override
  void dispose() {
    _productNameController.dispose();
    _manufacturerController.dispose();
    _ingredientNameController.dispose();
    _ingredientAmountController.dispose();
    _ingredientUnitController.dispose();
    _servingAmountController.dispose();
    _servingUnitController.dispose();
    _dailyServingsController.dispose();
    _frequencyController.dispose();
    super.dispose();
  }

  Future<void> _selectImage(ImageSource source) async {
    setState(() {
      _isSelecting = true;
      _statusMessage = null;
      _userConfirmed = false;
    });

    try {
      if (source == ImageSource.camera) {
        final PermissionStatus status = await Permission.camera.request();
        if (!status.isGranted) {
          if (!mounted) {
            return;
          }
          setState(() {
            _statusMessage = '카메라 권한이 필요합니다.';
          });
          return;
        }
      }

      final XFile? image = await _picker.pickImage(
        source: source,
        imageQuality: 92,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _selectedImageName = image?.name;
        _statusMessage = image == null ? '선택된 이미지가 없습니다.' : '이미지를 선택했습니다.';
      });
      if (image != null) {
        await _analyzeImage(image);
      }
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _statusMessage = '이미지를 불러오지 못했습니다.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSelecting = false;
        });
      }
    }
  }

  Future<void> _analyzeImage(XFile image) async {
    setState(() {
      _statusMessage = '영양제 preview를 요청하는 중입니다.';
    });
    try {
      await _repository.grantOcrImageProcessingConsent();
      final SupplementAnalysisPreview preview =
          await _repository.analyzeLabelImage(image);
      if (!mounted) {
        return;
      }
      _fillPreviewFields(preview);
      setState(() {
        _preview = preview;
        _statusMessage = '저장 전에 preview를 확인하고 수정해 주세요.';
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _statusMessage = 'Preview 요청을 완료하지 못했습니다.';
      });
    }
  }

  void _fillPreviewFields(SupplementAnalysisPreview preview) {
    final SupplementIngredientCandidate? firstIngredient =
        preview.ingredientCandidates.isEmpty
            ? null
            : preview.ingredientCandidates.first;
    _productNameController.text = preview.parsedProduct.productName;
    _manufacturerController.text = preview.parsedProduct.manufacturer;
    _ingredientNameController.text = firstIngredient?.displayName ?? '';
    _ingredientAmountController.text = _formatNumber(firstIngredient?.amount);
    _ingredientUnitController.text = firstIngredient?.unit ?? '';
    _dailyServingsController.text =
        _formatNumber(preview.parsedProduct.dailyServings) == ''
            ? '1'
            : _formatNumber(preview.parsedProduct.dailyServings);
  }

  Future<void> _saveConfirmedPreview() async {
    final SupplementConfirmedInput? input = _confirmedForSave();
    if (input == null) {
      setState(() {
        _statusMessage = '필수 값을 채우고 preview 확인 체크를 해 주세요.';
      });
      return;
    }

    setState(() {
      _isSaving = true;
      _statusMessage = '확정 영양제를 저장하는 중입니다.';
    });

    try {
      await _repository.saveConfirmedSupplement(input);
      if (!mounted) {
        return;
      }
      setState(() {
        ConfirmedEntryStore.instance.addSupplement(input);
        _statusMessage = '확정 영양제를 저장했습니다.';
      });
      context.go(
        '/entry-result'
        '?type=supplement'
        '&title=${Uri.encodeComponent(input.displayName)}'
        '&subtitle=${Uri.encodeComponent('영양제 기록이 저장되고 코칭 근거로 준비되었습니다.')}'
        '&detail1=${Uri.encodeComponent(input.manufacturer == null || input.manufacturer!.isEmpty ? '제조사: 미입력' : '제조사: ${input.manufacturer}')}'
        '&detail2=${Uri.encodeComponent('성분: ${input.ingredients.first.displayName}')}'
        '&detail3=${Uri.encodeComponent('하루 섭취 횟수: ${input.serving.dailyServings}')}',
      );
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _statusMessage = '확정 영양제를 저장하지 못했습니다.';
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  SupplementConfirmedInput? _confirmedForSave() {
    final SupplementAnalysisPreview? preview = _preview;
    final String productName = _productNameController.text.trim();
    final String ingredientName = _ingredientNameController.text.trim();
    final double dailyServings =
        double.tryParse(_dailyServingsController.text.trim()) ?? 0;

    if (!_userConfirmed ||
        preview == null ||
        productName.isEmpty ||
        ingredientName.isEmpty) {
      return null;
    }
    if (dailyServings <= 0 || dailyServings > 20) {
      return null;
    }

    return SupplementConfirmedInput(
      analysisId: preview.analysisId,
      displayName: productName,
      manufacturer: _manufacturerController.text.trim(),
      ingredients: <SupplementConfirmedIngredientInput>[
        SupplementConfirmedIngredientInput(
          displayName: ingredientName,
          nutrientCode: null,
          amount: double.tryParse(_ingredientAmountController.text.trim()),
          unit: _ingredientUnitController.text.trim(),
        ),
      ],
      serving: SupplementServingInput(
        amount: double.tryParse(_servingAmountController.text.trim()),
        unit: _servingUnitController.text.trim(),
        dailyServings: dailyServings,
      ),
      intakeSchedule: SupplementIntakeScheduleInput(
        frequency: _frequencyController.text.trim().isEmpty
            ? 'daily'
            : _frequencyController.text.trim(),
        timeOfDay: <String>[],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 28),
          children: <Widget>[
            Row(
              children: <Widget>[
                IconButton(
                  onPressed: () => context.go('/'),
                  icon: const Icon(Icons.arrow_back_rounded),
                ),
                Expanded(
                  child: Text(
                    '영양제 기록',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            LemonCard(
              color: LemonColors.lemonSoft,
              child: Row(
                children: <Widget>[
                  const Icon(
                    Icons.medication_liquid_rounded,
                    color: LemonColors.warning,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      '분석 preview를 확인하고 수정한 뒤에만 확정 저장합니다.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            CaptureFrameCard(
              title: '영양제 라벨',
              subtitle: '제품명과 성분표가 잘 보이도록 프레임 안에 맞춰 주세요.',
              icon: Icons.medication_liquid_rounded,
              accentColor: LemonColors.warning,
              selectedImageName: _selectedImageName,
              isSelecting: _isSelecting,
              onPick: _selectImage,
            ),
            if (_selectedImageName != null ||
                _statusMessage != null) ...<Widget>[
              const SizedBox(height: 12),
              LemonCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    if (_selectedImageName != null)
                      LemonPill(
                        label: _selectedImageName!,
                        color: LemonColors.sky,
                        backgroundColor: LemonColors.skySoft,
                      ),
                    if (_statusMessage != null) ...<Widget>[
                      const SizedBox(height: 8),
                      Text(_statusMessage!),
                    ],
                  ],
                ),
              ),
            ],
            if (_preview != null)
              _SupplementPreviewForm(
                preview: _preview!,
                productNameController: _productNameController,
                manufacturerController: _manufacturerController,
                ingredientNameController: _ingredientNameController,
                ingredientAmountController: _ingredientAmountController,
                ingredientUnitController: _ingredientUnitController,
                servingAmountController: _servingAmountController,
                servingUnitController: _servingUnitController,
                dailyServingsController: _dailyServingsController,
                frequencyController: _frequencyController,
                userConfirmed: _userConfirmed,
                isSaving: _isSaving,
                onConfirmedChanged: (bool? value) {
                  setState(() {
                    _userConfirmed = value ?? false;
                  });
                },
                onSave: _saveConfirmedPreview,
              ),
            const SizedBox(height: 24),
            const MedicalDisclaimer(),
          ],
        ),
      ),
    );
  }
}

class _SupplementPreviewForm extends StatelessWidget {
  const _SupplementPreviewForm({
    required this.preview,
    required this.productNameController,
    required this.manufacturerController,
    required this.ingredientNameController,
    required this.ingredientAmountController,
    required this.ingredientUnitController,
    required this.servingAmountController,
    required this.servingUnitController,
    required this.dailyServingsController,
    required this.frequencyController,
    required this.userConfirmed,
    required this.isSaving,
    required this.onConfirmedChanged,
    required this.onSave,
  });

  final SupplementAnalysisPreview preview;
  final TextEditingController productNameController;
  final TextEditingController manufacturerController;
  final TextEditingController ingredientNameController;
  final TextEditingController ingredientAmountController;
  final TextEditingController ingredientUnitController;
  final TextEditingController servingAmountController;
  final TextEditingController servingUnitController;
  final TextEditingController dailyServingsController;
  final TextEditingController frequencyController;
  final bool userConfirmed;
  final bool isSaving;
  final ValueChanged<bool?> onConfirmedChanged;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: LemonCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                LemonPill(
                  label: preview.status,
                  color: LemonColors.leaf,
                  backgroundColor: LemonColors.leafSoft,
                ),
                const SizedBox(width: 8),
                LemonPill(
                  label: preview.ocrProvider,
                  color: LemonColors.sky,
                  backgroundColor: LemonColors.skySoft,
                ),
              ],
            ),
            if (preview.warnings.isNotEmpty) ...<Widget>[
              const SizedBox(height: 10),
              Text('주의: ${preview.warnings.first}'),
            ],
            const SizedBox(height: 12),
            TextField(
              controller: productNameController,
              decoration: const InputDecoration(labelText: '제품명'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: manufacturerController,
              decoration: const InputDecoration(labelText: '제조사'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: ingredientNameController,
              decoration: const InputDecoration(labelText: '성분명'),
            ),
            const SizedBox(height: 10),
            Row(
              children: <Widget>[
                Expanded(
                  child: TextField(
                    controller: ingredientAmountController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: '성분 함량'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: ingredientUnitController,
                    decoration: const InputDecoration(labelText: '단위'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: <Widget>[
                Expanded(
                  child: TextField(
                    controller: servingAmountController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: '1회 섭취량'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: servingUnitController,
                    decoration: const InputDecoration(labelText: '섭취 단위'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            TextField(
              controller: dailyServingsController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: '하루 섭취 횟수'),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: frequencyController,
              decoration: const InputDecoration(labelText: '섭취 주기'),
            ),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              value: userConfirmed,
              onChanged: onConfirmedChanged,
              title: const Text('preview 값을 확인하고 수정했습니다.'),
            ),
            FilledButton.icon(
              onPressed: isSaving ? null : onSave,
              icon: const Icon(Icons.check_circle_outline),
              label: const Text('확정 영양제 저장'),
            ),
          ],
        ),
      ),
    );
  }
}

String _formatNumber(double? value) {
  if (value == null) {
    return '';
  }
  if (value == value.roundToDouble()) {
    return value.toInt().toString();
  }
  return value.toString();
}
