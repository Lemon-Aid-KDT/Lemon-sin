# 2026-05-23 Mobile Capture Quality Warning Result

## Scope

Mobile OCR preview UI에서 가장 먼저 필요한 local capture quality gate를
작게 분리했다. 이 branch는 저해상도 라벨 이미지를 OCR 분석 전에 감지해
사용자에게 재촬영/재선택 확인을 요구한다.

Blur, glare, crop, skew heuristic은 포함하지 않았다. 해당 metric은 별도
branch에서 추가해 PR 크기와 검증 범위를 분리한다.

## Official References

- Flutter `instantiateImageCodec`:
  <https://api.flutter.dev/flutter/dart-ui/instantiateImageCodec.html>
- Dart `File.readAsBytesSync`:
  <https://api.dart.dev/dart-io/File/readAsBytesSync.html>
- Flutter widget testing:
  <https://docs.flutter.dev/testing/overview>

## Branches

- Base branch: `feat/mobile-image-picker-permission-ui`
- Export branch: `feat/mobile-capture-quality-warning`
- Preserved remote: `origin/feat/mobile-capture-quality-warning`
- Base commit: `8913bcd1 feat(mobile): 이미지 선택 권한 안내를 추가`
- Patch commit: `198aaa68 feat(mobile): 촬영 품질 경고를 추가`

## Changed Files

- `mobile/lib/features/supplements/supplement_flow_screen.dart`
- `mobile/test/supplement_flow_capture_quality_test.dart`

Change size:

```text
2 files changed, 510 insertions(+)
```

This is slightly above the 500-line recommendation because the widget test
contains a self-contained repository stub and generated temporary PNG fixture.
No binary fixture file is committed.

## Behavior Covered

- Selected or recovered images receive a local capture quality report.
- PNG header dimensions are read without storing image bytes in app state.
- Images below the minimum total-pixel or short-edge threshold get a
  `low_resolution` issue.
- Preview UI shows a bounded Korean warning before OCR upload.
- Pressing `분석하기` on a low-resolution image opens a confirmation dialog and
  does not call backend analysis unless the user explicitly proceeds.

## Validation

```text
flutter test test/supplement_flow_capture_quality_test.dart: 1 passed
flutter test image picker permission + capture quality tests: 3 passed
flutter analyze changed Dart files: No issues found
dart format --output=none --set-exit-if-changed changed Dart files: passed
detect-secrets-hook changed files: passed
git diff --cached --check: passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
```

## Security / Leakage Review

- No generated OCR artifacts, raw OCR text, provider payloads, request headers,
  image bytes, `.env`, or secret values were added.
- The test creates a temporary 1x1 PNG at runtime and deletes the temp
  directory after the test.
- The app state keeps only bounded metrics such as width, height, total pixels,
  short-edge pixels, status, and reason code.
- The quality gate runs before OCR upload and does not call external OCR/LLM.

## Remaining Mobile Work

The next capture-quality branch can add blur, glare, crop, and skew metrics.
Keep those as another slice because they require pixel-level analysis and more
image fixture coverage.
