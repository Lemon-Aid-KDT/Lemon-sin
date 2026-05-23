# 2026-05-23 Mobile Camera Permission Gate Export Result

## Scope

`PR 4 - Mobile Release Security`에서 제외했던 native camera permission bridge를
별도 stacked branch로 분리했다. 이 branch는 `feat/mobile-native-security-gate`
위에 stack되며, OCR camera capture 전에 platform camera permission을 먼저
확인할 수 있는 MethodChannel gate를 추가한다.

## Official References

- Android `Manifest.permission.CAMERA`: <https://developer.android.com/reference/android/Manifest.permission.html>
- Android runtime permission `Activity.requestPermissions`:
  <https://developer.android.com/reference/android/app/Activity.html>
- Android `<uses-feature>` camera filtering:
  <https://developer.android.com/guide/topics/manifest/uses-feature-element>
- Apple `AVCaptureDevice.authorizationStatus(for:)`:
  <https://developer.apple.com/documentation/avfoundation/avcapturedevice/1624613-authorizationstatus>
- Flutter `MethodChannel`: <https://api.flutter.dev/flutter/services/MethodChannel-class.html>

## Branches

- Base branch: `feat/mobile-native-security-gate`
- Export branch: `feat/mobile-camera-permission-gate`
- Preserved remote: `origin/feat/mobile-camera-permission-gate`
- Base commit: `ca860026 feat(mobile): native 보안 gate를 추가`
- Patch commit: `cb3b1c76 feat(mobile): camera 권한 gate를 추가`

## Changed Files

- `mobile/android/app/src/main/AndroidManifest.xml`
- `mobile/android/app/src/main/kotlin/com/lemonaid/mobile/MainActivity.kt`
- `mobile/ios/Runner/AppDelegate.swift`
- `mobile/test/unit/release_security_config_test.dart`

Change size:

```text
4 files changed, 148 insertions(+)
```

## Behavior Covered

- Android manifest declares `android.hardware.camera` with
  `android:required="false"` so camera-capable behavior does not unnecessarily
  filter non-camera devices.
- Android native channel `com.lemonaid.mobile/camera_permission` checks and
  requests `Manifest.permission.CAMERA`, returning bounded permission states.
- Android rejects concurrent permission requests with a bounded
  `permission_request_in_progress` error.
- iOS native channel uses `AVCaptureDevice.authorizationStatus(for: .video)` and
  `requestAccess(for: .video)` to return `granted`, `denied`, or `restricted`.
- Static release tests keep broad gallery permissions out of the manifest.

## Validation

```text
flutter test release_security_config/app_config/api_client_certificate_pin: 21 passed
flutter analyze changed Dart files: No issues found
dart format --output=none --set-exit-if-changed changed Dart files: passed
flutter build apk --debug --flavor dev: passed
flutter build ios --simulator --debug: passed
detect-secrets-hook changed files: passed
git diff --cached --check: passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
```

## Security / Leakage Review

- No generated OCR artifacts, raw OCR text, provider payloads, request headers,
  image bytes, `.env`, or secret values were added.
- Build outputs under `mobile/build`, `.dart_tool`, iOS Pods/symlinks/ephemeral
  paths are ignored and not staged.
- Permission channel returns only bounded states/errors and does not expose image
  paths, camera frames, OCR text, or user identifiers.
- Broad gallery permissions (`READ_EXTERNAL_STORAGE`, `READ_MEDIA_IMAGES`) remain
  absent from the manifest.

## Remaining Mobile Work

The Flutter OCR preview UI and camera/gallery quality-warning flow are still
separate. This branch only installs the platform permission gate that the UI can
call before opening the camera picker.
