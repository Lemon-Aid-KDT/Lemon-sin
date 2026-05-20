import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../../shared/widgets/medical_disclaimer.dart';
import '../data/supplement_capture_repository.dart';
import '../domain/supplement_analysis_preview.dart';

class SupplementCaptureScreen extends StatefulWidget {
  const SupplementCaptureScreen({super.key});

  @override
  State<SupplementCaptureScreen> createState() => _SupplementCaptureScreenState();
}

class _SupplementCaptureScreenState extends State<SupplementCaptureScreen> {
  final ImagePicker _picker = ImagePicker();
  final SupplementCaptureRepository _repository = SupplementCaptureRepository();
  String? _selectedImageName;
  String? _statusMessage;
  SupplementAnalysisPreview? _preview;
  bool _isSelecting = false;

  Future<void> _selectImage(ImageSource source) async {
    setState(() {
      _isSelecting = true;
      _statusMessage = null;
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
        _statusMessage = '이미지를 가져오지 못했습니다.';
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
      _statusMessage = '분석 요청 중입니다.';
    });
    try {
      await _repository.grantOcrImageProcessingConsent();
      final SupplementAnalysisPreview preview = await _repository.analyzeLabelImage(image);
      if (!mounted) {
        return;
      }
      setState(() {
        _preview = preview;
        _statusMessage = '분석 미리보기를 받았습니다.';
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _statusMessage = '분석 요청을 완료하지 못했습니다.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('영양제 촬영')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: <Widget>[
          const Text('영양제 제품명, 성분표, 섭취 방법이 보이도록 촬영해 주세요.'),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _isSelecting ? null : () => _selectImage(ImageSource.camera),
            icon: const Icon(Icons.photo_camera_outlined),
            label: const Text('카메라 열기'),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _isSelecting ? null : () => _selectImage(ImageSource.gallery),
            icon: const Icon(Icons.photo_library_outlined),
            label: const Text('갤러리에서 선택'),
          ),
          const SizedBox(height: 16),
          if (_selectedImageName != null) Text('선택 파일: $_selectedImageName'),
          if (_statusMessage != null) Text(_statusMessage!),
          if (_preview != null) _SupplementPreviewPanel(preview: _preview!),
          const SizedBox(height: 24),
          const MedicalDisclaimer(),
        ],
      ),
    );
  }
}

class _SupplementPreviewPanel extends StatelessWidget {
  const _SupplementPreviewPanel({required this.preview});

  final SupplementAnalysisPreview preview;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: DecoratedBox(
        decoration: BoxDecoration(
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('분석 상태: ${preview.status}'),
              Text('OCR provider: ${preview.ocrProvider}'),
              if (preview.warnings.isNotEmpty) Text('주의: ${preview.warnings.first}'),
            ],
          ),
        ),
      ),
    );
  }
}
