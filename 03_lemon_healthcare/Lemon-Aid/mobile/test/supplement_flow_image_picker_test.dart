import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';
import 'package:lemon_aid_mobile/app_controller.dart';
import 'package:lemon_aid_mobile/features/consent/consent_models.dart';
import 'package:lemon_aid_mobile/features/dashboard/dashboard_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_flow_screen.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_models.dart';
import 'package:lemon_aid_mobile/features/supplements/supplement_repository.dart';

void main() {
  testWidgets('camera permission denial tells user how to retry', (
    WidgetTester tester,
  ) async {
    await _pumpSupplementFlow(
      tester,
      _ThrowingImagePicker(PlatformException(code: 'camera_access_denied')),
    );

    await tester.tap(find.byTooltip('촬영'));
    await tester.pump();

    expect(
      find.text('카메라 권한이 거부됐어요. 설정에서 카메라 접근을 허용하거나 갤러리 사진으로 다시 시도해주세요.'),
      findsOneWidget,
    );
  });

  testWidgets('gallery permission denial keeps the retry path visible', (
    WidgetTester tester,
  ) async {
    await _pumpSupplementFlow(
      tester,
      _ThrowingImagePicker(PlatformException(code: 'photo_access_denied')),
    );

    await tester.tap(find.byTooltip('갤러리'));
    await tester.pump();

    expect(
      find.text('사진 접근 권한이 거부됐어요. 선택 가능한 사진을 허용하거나 다시 선택해주세요.'),
      findsOneWidget,
    );
  });

  testWidgets('selected low resolution image warns before OCR analysis', (
    WidgetTester tester,
  ) async {
    final File image = _writeTinyPng();
    addTearDown(() {
      final Directory parent = image.parent;
      if (parent.existsSync()) {
        parent.deleteSync(recursive: true);
      }
    });
    final _ConsentReadyRepository repository = _ConsentReadyRepository();
    await _pumpSupplementFlow(
      tester,
      _ReturningImagePicker(XFile(image.path)),
      repository: repository,
    );

    await tester.tap(find.byTooltip('갤러리'));
    await tester.runAsync(() async {
      await Future<void>.delayed(const Duration(milliseconds: 200));
    });
    await tester.pump();
    await tester.pumpAndSettle();
    expect(find.text('촬영 품질을 확인해주세요'), findsOneWidget);
    expect(find.textContaining('해상도 낮음'), findsOneWidget);
    expect(repository.analyzeCallCount, 0);

    await tester.tap(find.text('분석하기'));
    await tester.pumpAndSettle();

    expect(find.text('촬영 품질 확인'), findsOneWidget);
    expect(repository.analyzeCallCount, 0);
  });

  testWidgets('captured low resolution image warns before OCR analysis', (
    WidgetTester tester,
  ) async {
    final File image = _writeTinyPng();
    addTearDown(() => _deleteGeneratedImage(image));
    final _ConsentReadyRepository repository = _ConsentReadyRepository();
    await _pumpSupplementFlow(
      tester,
      _ReturningImagePicker(XFile(image.path)),
      repository: repository,
    );

    await tester.tap(find.byTooltip('촬영'));
    await tester.runAsync(() async {
      await Future<void>.delayed(const Duration(milliseconds: 200));
    });
    await tester.pump();
    await tester.pumpAndSettle();

    expect(find.text('촬영 품질을 확인해주세요'), findsOneWidget);
    expect(find.textContaining('해상도 낮음'), findsOneWidget);
    expect(repository.analyzeCallCount, 0);
  });

  testWidgets('selected blurred image warns before OCR analysis', (
    WidgetTester tester,
  ) async {
    final File image = await _writeSolidPng(
      width: 1200,
      height: 900,
      color: const _Rgb(0x88, 0x88, 0x88),
    );
    addTearDown(() => _deleteGeneratedImage(image));
    final _ConsentReadyRepository repository = _ConsentReadyRepository();
    await _pumpSupplementFlow(
      tester,
      _ReturningImagePicker(XFile(image.path)),
      repository: repository,
    );

    await _selectGalleryImage(tester);

    expect(find.text('촬영 품질을 확인해주세요'), findsOneWidget);
    expect(find.textContaining('초점 흐림'), findsOneWidget);
    expect(repository.analyzeCallCount, 0);
  });

  testWidgets('selected glare image warns before OCR analysis', (
    WidgetTester tester,
  ) async {
    final File image = await _writeSolidPng(
      width: 1200,
      height: 900,
      color: const _Rgb(0xFF, 0xFF, 0xFF),
    );
    addTearDown(() => _deleteGeneratedImage(image));
    final _ConsentReadyRepository repository = _ConsentReadyRepository();
    await _pumpSupplementFlow(
      tester,
      _ReturningImagePicker(XFile(image.path)),
      repository: repository,
    );

    await _selectGalleryImage(tester);

    expect(find.text('촬영 품질을 확인해주세요'), findsOneWidget);
    expect(find.textContaining('반사광'), findsOneWidget);
    expect(repository.analyzeCallCount, 0);
  });

  testWidgets('selected cropped label image warns before OCR analysis', (
    WidgetTester tester,
  ) async {
    final File image = await _writeBorderPng(width: 1200, height: 900);
    addTearDown(() => _deleteGeneratedImage(image));
    final _ConsentReadyRepository repository = _ConsentReadyRepository();
    await _pumpSupplementFlow(
      tester,
      _ReturningImagePicker(XFile(image.path)),
      repository: repository,
    );

    await _selectGalleryImage(tester);

    expect(find.text('촬영 품질을 확인해주세요'), findsOneWidget);
    expect(find.textContaining('잘림 가능성'), findsOneWidget);
    expect(repository.analyzeCallCount, 0);
  });

  testWidgets('selected skewed label image warns before OCR analysis', (
    WidgetTester tester,
  ) async {
    final File image = await _writeSolidPng(
      width: 3000,
      height: 900,
      color: const _Rgb(0x88, 0x88, 0x88),
    );
    addTearDown(() => _deleteGeneratedImage(image));
    final _ConsentReadyRepository repository = _ConsentReadyRepository();
    await _pumpSupplementFlow(
      tester,
      _ReturningImagePicker(XFile(image.path)),
      repository: repository,
    );

    await _selectGalleryImage(tester);

    expect(find.text('촬영 품질을 확인해주세요'), findsOneWidget);
    expect(find.textContaining('기울기'), findsOneWidget);
    expect(repository.analyzeCallCount, 0);
  });
}

Future<void> _pumpSupplementFlow(
  WidgetTester tester,
  ImagePicker imagePicker, {
  _ConsentReadyRepository? repository,
}) async {
  final AppController controller = AppController(
    repository: repository ?? _ConsentReadyRepository(),
  );
  await controller.bootstrap();
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: SupplementFlowScreen(
          controller: controller,
          imagePicker: imagePicker,
        ),
      ),
    ),
  );
  await tester.pump();
}

class _ThrowingImagePicker extends ImagePicker {
  _ThrowingImagePicker(this.error);

  final PlatformException error;

  @override
  Future<XFile?> pickImage({
    required ImageSource source,
    double? maxWidth,
    double? maxHeight,
    int? imageQuality,
    CameraDevice preferredCameraDevice = CameraDevice.rear,
    bool requestFullMetadata = true,
  }) async {
    throw error;
  }

  @override
  Future<LostDataResponse> retrieveLostData() async {
    return LostDataResponse.empty();
  }
}

class _ReturningImagePicker extends ImagePicker {
  _ReturningImagePicker(this.image);

  final XFile image;

  @override
  Future<XFile?> pickImage({
    required ImageSource source,
    double? maxWidth,
    double? maxHeight,
    int? imageQuality,
    CameraDevice preferredCameraDevice = CameraDevice.rear,
    bool requestFullMetadata = true,
  }) async {
    return image;
  }

  @override
  Future<LostDataResponse> retrieveLostData() async {
    return LostDataResponse.empty();
  }
}

class _ConsentReadyRepository implements LemonAidRepository {
  int analyzeCallCount = 0;

  @override
  Future<SupplementAnalysisPreview> analyzeSupplementImage(String imagePath) {
    analyzeCallCount += 1;
    throw UnimplementedError();
  }

  @override
  void close() {}

  @override
  Future<ConsentState> fetchConsents() async {
    return ConsentState(
      consents: <ConsentStatus>[
        _consent(AppController.ocrConsent),
        _consent(AppController.healthConsent),
      ],
    );
  }

  @override
  Future<DashboardSummary> fetchDashboardSummary({int days = 30}) async {
    return DashboardSummary(
      asOf: DateTime.utc(2026, 5, 22),
      nutrition: const DashboardNutritionSummary(
        dataStatus: 'ready',
        lowCount: 0,
        highCount: 0,
        datasetVersion: 'test',
      ),
      activity: const DashboardActivitySummary(
        dataStatus: 'not_ready',
        latestSteps: null,
        latestActivityScore: null,
      ),
      weight: const DashboardWeightSummary(
        dataStatus: 'not_ready',
        latestWeightKg: null,
        predictedWeightKg: null,
      ),
      supplements: const DashboardSupplementSummary(
        registeredCount: 0,
        requiresReviewCount: 0,
      ),
      disclaimers: const <String>[],
      algorithmVersion: 'test',
    );
  }

  @override
  Future<ConsentAction> grantConsent(String consentType) async {
    return ConsentAction(
      consentType: consentType,
      policyVersion: 'test',
      granted: true,
      occurredAt: DateTime.utc(2026, 5, 22),
    );
  }

  @override
  Future<SupplementRecommendationExplainResponse>
  explainSupplementRecommendation(
    SupplementImpactPreviewResponse preview, {
    bool useLocalLlm = false,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<SupplementImpactPreviewResponse>
  fetchLatestSupplementRecommendation() {
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
  Future<SupplementImpactPreviewResponse> previewSupplementImpact(
    SupplementImpactPreviewRequest request,
  ) {
    throw UnimplementedError();
  }

  @override
  Future<UserSupplementResponse> registerSupplement(
    UserSupplementCreate request,
  ) {
    throw UnimplementedError();
  }

  ConsentStatus _consent(String consentType) {
    return ConsentStatus(
      consentType: consentType,
      policyVersion: 'test',
      title: consentType,
      required: true,
      granted: true,
      occurredAt: DateTime.utc(2026, 5, 22),
      revokedAt: null,
    );
  }
}

File _writeTinyPng() {
  final Directory directory = Directory.systemTemp.createTempSync(
    'lemon-aid-capture-quality-test-',
  );
  final File file = File('${directory.path}/label.png');
  file.writeAsBytesSync(
    base64Decode(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=',
    ),
  );
  return file;
}

Future<void> _selectGalleryImage(WidgetTester tester) async {
  await tester.tap(find.byTooltip('갤러리'));
  await tester.runAsync(() async {
    await Future<void>.delayed(const Duration(milliseconds: 300));
  });
  await tester.pump();
  await tester.pumpAndSettle();
}

Future<File> _writeSolidPng({
  required int width,
  required int height,
  required _Rgb color,
}) async {
  return _writeGeneratedPng(
    width: width,
    height: height,
    pixel: (_, _) => color,
  );
}

Future<File> _writeBorderPng({required int width, required int height}) async {
  const int border = 80;
  return _writeGeneratedPng(
    width: width,
    height: height,
    pixel: (int x, int y) {
      final bool inBorder =
          x < border ||
          x >= width - border ||
          y < border ||
          y >= height - border;
      return inBorder
          ? const _Rgb(0x00, 0x00, 0x00)
          : const _Rgb(0xFF, 0xFF, 0xFF);
    },
  );
}

Future<File> _writeGeneratedPng({
  required int width,
  required int height,
  required _Rgb Function(int x, int y) pixel,
}) async {
  final BytesBuilder raw = BytesBuilder(copy: false);
  for (int y = 0; y < height; y += 1) {
    raw.addByte(0);
    for (int x = 0; x < width; x += 1) {
      final _Rgb color = pixel(x, y);
      raw.addByte(color.red);
      raw.addByte(color.green);
      raw.addByte(color.blue);
    }
  }
  final List<int> compressed = ZLibEncoder().convert(raw.takeBytes());
  final BytesBuilder png = BytesBuilder(copy: false)
    ..add(const <int>[0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
    ..add(
      _pngChunk('IHDR', <int>[
        ..._uint32Bytes(width),
        ..._uint32Bytes(height),
        8,
        2,
        0,
        0,
        0,
      ]),
    )
    ..add(_pngChunk('IDAT', compressed))
    ..add(_pngChunk('IEND', const <int>[]));

  final Directory directory = Directory.systemTemp.createTempSync(
    'lemon-aid-capture-quality-test-',
  );
  final File file = File('${directory.path}/label.png');
  file.writeAsBytesSync(png.takeBytes());
  return file;
}

void _deleteGeneratedImage(File image) {
  final Directory parent = image.parent;
  if (parent.existsSync()) {
    parent.deleteSync(recursive: true);
  }
}

List<int> _pngChunk(String type, List<int> data) {
  final List<int> typeBytes = ascii.encode(type);
  final List<int> checksumInput = <int>[...typeBytes, ...data];
  return <int>[
    ..._uint32Bytes(data.length),
    ...typeBytes,
    ...data,
    ..._uint32Bytes(_crc32(checksumInput)),
  ];
}

List<int> _uint32Bytes(int value) {
  return <int>[
    (value >> 24) & 0xFF,
    (value >> 16) & 0xFF,
    (value >> 8) & 0xFF,
    value & 0xFF,
  ];
}

int _crc32(List<int> bytes) {
  int crc = 0xFFFFFFFF;
  for (final int byte in bytes) {
    crc ^= byte;
    for (int bit = 0; bit < 8; bit += 1) {
      final int mask = -(crc & 1);
      crc = (crc >> 1) ^ (0xEDB88320 & mask);
    }
  }
  return (crc ^ 0xFFFFFFFF) & 0xFFFFFFFF;
}

class _Rgb {
  const _Rgb(this.red, this.green, this.blue);

  final int red;
  final int green;
  final int blue;
}
