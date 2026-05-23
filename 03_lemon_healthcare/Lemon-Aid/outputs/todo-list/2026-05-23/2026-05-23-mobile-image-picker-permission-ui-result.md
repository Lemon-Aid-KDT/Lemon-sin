# 2026-05-23 Mobile Image Picker Permission UI Result

## Scope

Mobile OCR preview UI의 큰 `supplement_flow_screen.dart` 변경을 한 번에
export하지 않고, 먼저 image picker permission/error feedback만 작은 stacked
branch로 분리했다. 이 branch는 camera/gallery 선택 실패 시 bounded user
message를 보여주며, 로컬 촬영 품질 분석 패널은 포함하지 않는다.

## Official References

- `image_picker` package:
  <https://pub.dev/packages/image_picker>
- Flutter `MethodChannel`:
  <https://api.flutter.dev/flutter/services/MethodChannel-class.html>
- Flutter `PlatformException`:
  <https://api.flutter.dev/flutter/services/PlatformException-class.html>

## Branches

- Base branch: `feat/mobile-provider-observations`
- Export branch: `feat/mobile-image-picker-permission-ui`
- Preserved remote: `origin/feat/mobile-image-picker-permission-ui`
- Base commit: `9966ec7c feat(mobile): OCR 관측 모델을 추가`
- Patch commit: `8913bcd1 feat(mobile): 이미지 선택 권한 안내를 추가`

## Changed Files

- `mobile/lib/features/supplements/supplement_flow_screen.dart`
- `mobile/test/supplement_flow_image_picker_permission_test.dart`

Change size:

```text
2 files changed, 260 insertions(+), 6 deletions(-)
```

## Behavior Covered

- Camera flow checks the existing native
  `com.lemonaid.mobile/camera_permission` channel before `pickImage` on
  Android/iOS.
- `MissingPluginException` stays non-blocking for widget tests and unsupported
  local plugin environments.
- `PlatformException` codes from image picker are converted into bounded Korean
  retry guidance for camera and gallery permission failures.
- Widget tests cover camera permission denial and gallery permission denial.

## Validation

```text
flutter test test/supplement_flow_image_picker_permission_test.dart: 2 passed
flutter analyze changed Dart files: No issues found
dart format --output=none --set-exit-if-changed changed Dart files: passed
detect-secrets-hook changed files: passed
git diff --cached --check: passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
```

## Security / Leakage Review

- No generated OCR artifacts, raw OCR text, provider payloads, request headers,
  image bytes, `.env`, or secret values were added.
- Permission handling returns and displays bounded state/error messages only.
- Test image picker throws synthetic `PlatformException` values and does not
  read camera frames, gallery files, OCR text, provider payloads, local image
  paths, request headers, or environment variables.
- This branch adds no external OCR/LLM calls.

## Remaining Mobile Work

The next mobile slice can add local capture quality analysis and warning UI on
top of this branch. Keep that separate because it adds image decoding and
quality metrics logic that needs its own security review.
