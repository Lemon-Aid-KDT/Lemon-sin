import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../../shared/widgets/medical_disclaimer.dart';

class SupplementCaptureScreen extends StatefulWidget {
  const SupplementCaptureScreen({super.key});

  @override
  State<SupplementCaptureScreen> createState() => _SupplementCaptureScreenState();
}

class _SupplementCaptureScreenState extends State<SupplementCaptureScreen> {
  final ImagePicker _picker = ImagePicker();
  String? _selectedImageName;
  String? _statusMessage;
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
          const SizedBox(height: 24),
          const MedicalDisclaimer(),
        ],
      ),
    );
  }
}
