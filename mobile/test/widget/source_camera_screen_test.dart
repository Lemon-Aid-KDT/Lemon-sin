import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:lemon_aid_mobile/screens/camera_screen.dart';

void main() {
  testWidgets('gallery pick opens the OCR preview with safer picker options', (
    WidgetTester tester,
  ) async {
    await _usePhoneSurface(tester);
    final File source = _writeTinyPng();
    final _FakeImagePicker picker = _FakeImagePicker(source.path);

    await tester.pumpWidget(
      MaterialApp(
        home: CameraScreen(
          imagePicker: picker,
          onAnalyzeSupplementImage:
              (String imagePath, {required String ocrProvider}) async {},
        ),
      ),
    );
    await tester.pump(const Duration(seconds: 1));

    await tester.tap(find.byIcon(Icons.photo_library_rounded));
    await tester.pump();
    await tester.runAsync(() async {
      await Future<void>.delayed(const Duration(seconds: 1));
    });
    await tester.pump(const Duration(milliseconds: 600));

    expect(picker.lastMaxWidth, 2400);
    expect(picker.lastImageQuality, 95);
    expect(picker.lastRequestFullMetadata, isFalse);
    expect(find.text('갤러리 이미지를 불러오지 못했어요. 다른 사진을 선택해주세요.'), findsNothing);
    expect(find.text('미리보기'), findsOneWidget);
    expect(find.text('분석하기'), findsOneWidget);
  });

  testWidgets('emulator camera fallback opens picker camera source', (
    WidgetTester tester,
  ) async {
    await _usePhoneSurface(tester);
    final File source = _writeTinyPng();
    final _FakeImagePicker picker = _FakeImagePicker(source.path);

    await tester.pumpWidget(
      MaterialApp(
        home: CameraScreen(
          imagePicker: picker,
          useCameraPickerFallback: true,
          onAnalyzeSupplementImage:
              (String imagePath, {required String ocrProvider}) async {},
        ),
      ),
    );
    await tester.pump(const Duration(seconds: 1));

    await tester.tap(find.bySemanticsLabel('사진 촬영'));
    await tester.pump();
    await tester.runAsync(() async {
      await Future<void>.delayed(const Duration(seconds: 1));
    });
    await tester.pump(const Duration(milliseconds: 600));

    expect(picker.lastSource, ImageSource.camera);
    expect(picker.lastMaxWidth, 2400);
    expect(picker.lastImageQuality, 95);
    expect(picker.lastRequestFullMetadata, isFalse);
    expect(find.text('미리보기'), findsOneWidget);
    expect(find.text('분석하기'), findsOneWidget);
  });
}

Future<void> _usePhoneSurface(WidgetTester tester) async {
  await tester.binding.setSurfaceSize(const Size(390, 844));
  addTearDown(() => tester.binding.setSurfaceSize(null));
}

File _writeTinyPng() {
  final File file = File(
    '${Directory.systemTemp.path}/lemon_camera_test_${DateTime.now().microsecondsSinceEpoch}.png',
  );
  const String base64Png =
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=';
  file.writeAsBytesSync(base64Decode(base64Png));
  return file;
}

class _FakeImagePicker extends ImagePicker {
  _FakeImagePicker(this.path);

  final String path;
  ImageSource? lastSource;
  double? lastMaxWidth;
  int? lastImageQuality;
  bool? lastRequestFullMetadata;

  @override
  Future<XFile?> pickImage({
    required ImageSource source,
    double? maxWidth,
    double? maxHeight,
    int? imageQuality,
    CameraDevice preferredCameraDevice = CameraDevice.rear,
    bool requestFullMetadata = true,
  }) {
    lastSource = source;
    lastMaxWidth = maxWidth;
    lastImageQuality = imageQuality;
    lastRequestFullMetadata = requestFullMetadata;
    return Future<XFile?>.value(_xfileFromPath(path));
  }

  @override
  Future<LostDataResponse> retrieveLostData() {
    return Future<LostDataResponse>.value(LostDataResponse.empty());
  }

  XFile _xfileFromPath(String imagePath) {
    return XFile(imagePath, name: 'source.png', mimeType: 'image/png');
  }
}
