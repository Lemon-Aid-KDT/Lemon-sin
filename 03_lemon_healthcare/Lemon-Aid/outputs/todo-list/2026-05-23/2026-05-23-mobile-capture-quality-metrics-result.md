# 2026-05-23 Mobile Capture Quality Metrics Result

## Scope

`feat/mobile-capture-quality-warning`의 low-resolution gate 위에 blur, glare,
crop, skew local metric을 추가했다. OCR upload 전에 명확히 품질이 나쁜 라벨
이미지를 사용자에게 경고해, 원격/백엔드 분석으로 보내기 전에 재촬영 기회를
준다.

이 branch는 성능 claim이 아니라 deterministic preflight warning이다. 실제
OCR 정확도 개선 여부는 fixture benchmark로 별도 검증해야 한다.

## Official References

- Flutter `instantiateImageCodec`:
  <https://api.flutter.dev/flutter/dart-ui/instantiateImageCodec.html>
- Dart `File.readAsBytesSync`:
  <https://api.dart.dev/dart-io/File/readAsBytesSync.html>
- Flutter widget testing:
  <https://docs.flutter.dev/cookbook/testing/widget/introduction>
- OpenCV Laplacian image filtering reference:
  <https://docs.opencv.org/3.4/d4/d86/group__imgproc__filter.html>

## Branches

- Base branch: `feat/mobile-capture-quality-warning`
- Export branch: `feat/mobile-capture-quality-metrics`
- Preserved remote: `origin/feat/mobile-capture-quality-metrics`
- Base commit: `198aaa68 feat(mobile): 촬영 품질 경고를 추가`
- Patch commit: `b44a6a3c feat(mobile): 촬영 품질 metric을 확장`

## Changed Files

- `mobile/lib/features/supplements/supplement_flow_screen.dart`
- `mobile/test/supplement_flow_capture_quality_test.dart`

Change size:

```text
2 files changed, 514 insertions(+), 23 deletions(-)
```

This is slightly above the 500-line recommendation because the branch keeps the
metric implementation and runtime-generated PNG fixture coverage together. No
binary image fixture is committed.

## Behavior Covered

- Decodes selected images to a bounded max edge before pixel-level analysis.
- Stores only bounded metrics: dimensions, total pixels, short edge,
  edge variance, contrast standard deviation, bright pixel ratio, border ink
  ratio, and aspect ratio.
- Adds local warning reason codes:
  `blurred_text`, `glare_or_reflection`, `cropped_label`, `skewed_label`,
  `low_contrast`, and existing `low_resolution`.
- Uses a Laplacian-style local edge variance proxy for blur risk. This is a
  deterministic warning heuristic, not an OCR accuracy metric.
- Widget tests cover low resolution, blur, glare, crop, and skew warnings with
  temporary PNG files generated at runtime.

## Validation

```text
flutter test test/supplement_flow_capture_quality_test.dart: 5 passed
flutter test image picker permission + capture quality tests: 7 passed
flutter analyze changed Dart files: No issues found
dart format --output=none --set-exit-if-changed changed Dart files: passed
detect-secrets-hook changed files: passed
git diff --cached --check: passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
```

## Security / Leakage Review

- No generated OCR artifacts, raw OCR text, provider payloads, request headers,
  committed image bytes, `.env`, or secret values were added.
- Runtime image bytes are read only to compute local preflight metrics and are
  not stored in model state, output files, logs, or repo artifacts.
- Tests generate temporary PNG files and delete their temp directories.
- The branch does not add external OCR/LLM calls.
- The app state keeps only bounded numeric metrics and warning reason codes.

## Remaining Mobile Work

The mobile OCR preview path now has provider observation parsing, permission
feedback, and local capture quality warnings. The remaining UI work is to decide
whether to expose backend `image_quality_report`/provider observations in the
confirmation screen with compact copy, without surfacing raw OCR text or provider
payloads.
