// screens/camera_screen.dart — D1 셸
//
// 참조: PROJECT_GUIDE.md §3.7 영양제 분석 흐름 / §8.5 OCR 파이프라인

import 'package:flutter/material.dart';

import '../utils/tokens.dart';

class CameraScreen extends StatelessWidget {
  const CameraScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('촬영하기')),
      body: Center(
            child: Padding(
              padding: const EdgeInsets.all(LemonSpace.lg),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.photo_camera, size: 80, color: LemonColors.brand),
                  const SizedBox(height: LemonSpace.lg),
                  const Text('영양제 라벨 또는 음식을 촬영', style: LemonText.heading),
                  const SizedBox(height: LemonSpace.xl),
                  ElevatedButton.icon(
                    onPressed: () {
                      // TODO(A): image_picker로 카메라 호출
                    },
                    icon: const Icon(Icons.photo_camera),
                    label: const Text('카메라로 촬영'),
                  ),
                  const SizedBox(height: LemonSpace.md),
                  OutlinedButton.icon(
                    onPressed: () {
                      // TODO(A): image_picker로 갤러리 선택
                    },
                    icon: const Icon(Icons.photo_library),
                    label: const Text('갤러리에서 선택'),
                  ),
                ],
              ),
            ),
          ),
    );
  }

}
