# 2026-05-23 Mobile Native Security Gate Export Result

## Scope

`PR 4 - Mobile Release Security`의 두 번째 slice로 Android/iOS native
certificate verifier와 release artifact scanner를 분리했다. 이 branch는
`feat/mobile-release-security-core` 위에 stack되어 Dart `MethodChannel`
gate가 실제 native verifier와 연결된다.

## Official References

- Android `HttpsURLConnection` hostname verifier and TLS APIs:
  <https://developer.android.com/reference/javax/net/ssl/HttpsURLConnection>
- Android network security config and cleartext opt-out:
  <https://developer.android.com/training/articles/security-config>
- Apple `SecPolicyCreateSSL` hostname policy:
  <https://developer.apple.com/documentation/security/secpolicycreatessl%28_%3A_%3A%29>
- Apple `SecTrustEvaluateWithError` trust evaluation:
  <https://developer.apple.com/documentation/security/sectrustevaluatewitherror%28_%3A_%3A%29>
- Flutter `MethodChannel` platform bridge:
  <https://api.flutter.dev/flutter/services/MethodChannel-class.html>

## Branches

- Base branch: `feat/mobile-release-security-core`
- Export branch: `feat/mobile-native-security-gate`
- Preserved remote: `origin/feat/mobile-native-security-gate`
- Base commit: `a71b464c feat(mobile): 인증서 pin gate를 추가`
- Patch commit: `ca860026 feat(mobile): native 보안 gate를 추가`

## Changed Files

- `mobile/android/app/src/main/AndroidManifest.xml`
- `mobile/android/app/src/main/kotlin/com/example/lemon_aid_mobile/MainActivity.kt`
- `mobile/android/app/src/main/kotlin/com/lemonaid/mobile/MainActivity.kt`
- `mobile/ios/Runner/AppDelegate.swift`
- `mobile/scripts/verify_release_artifact.py`
- `mobile/test/unit/release_security_config_test.dart`

Change size:

```text
6 files changed, 453 insertions(+), 7 deletions(-)
```

## Behavior Covered

- Moves Android release activity out of the default `com.example` package.
- Android native verifier opens an SSL socket, runs hostname verification through
  `HttpsURLConnection.getDefaultHostnameVerifier()`, hashes peer certificates,
  and returns bounded MethodChannel error codes.
- iOS native verifier creates an SSL hostname policy, sets it on `SecTrust`, runs
  trust evaluation, hashes server certificates, and returns bounded
  `FlutterError` codes.
- Existing Android network security config keeps cleartext disabled.
- Existing iOS ATS keeps arbitrary loads disabled.
- Adds a release artifact scanner that blocks dev endpoints such as localhost,
  emulator loopback, and ngrok strings in built artifacts.

## Validation

```text
flutter test release_security_config/app_config/api_client_certificate_pin: 17 passed
flutter analyze changed Dart files: No issues found
dart format --output=none --set-exit-if-changed changed Dart files: passed
python3 mobile/scripts/verify_release_artifact.py mobile/pubspec.yaml: passed
python3 mobile/scripts/verify_release_artifact.py debug APK: failed as expected on local dev URLs
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
- Error outputs are bounded codes/messages and do not include certificate bytes,
  request headers, pins, or secrets.
- The debug APK verifier failure is expected because debug builds still contain
  local development URLs; this confirms the scanner catches those strings before
  a release artifact can be accepted.

## Remaining Mobile Work

The camera permission / OCR preview UI changes from the original large mobile
commit remain intentionally separate. They should not be mixed into the release
security gate PR unless the team explicitly decides to broaden the mobile PR.
