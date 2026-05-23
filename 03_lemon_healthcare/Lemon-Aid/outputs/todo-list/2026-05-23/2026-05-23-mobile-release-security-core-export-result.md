# 2026-05-23 Mobile Release Security Core Export Result

## Scope

`PR 4 - Mobile Release Security` 중 Dart/API core certificate pin gate를
clean code-bearing base 위의 독립 branch로 먼저 분리했다. 이 slice는 release
API 요청이 backend로 나가기 전에 configured certificate pins를 검증하도록
만드는 fail-closed client-side gate다.

## Branches

- Base branch: `chore/ocr-clean-export-base`
- Export branch: `feat/mobile-release-security-core`
- Preserved remote: `origin/feat/mobile-release-security-core`
- Base commit: `67b9bc46 chore(ocr): export base artifact 추적을 제거`
- Patch commit: `a71b464c feat(mobile): 인증서 pin gate를 추가`

## Changed Files

- `mobile/lib/core/api/api_client.dart`
- `mobile/lib/core/api/certificate_pin_verifier.dart`
- `mobile/lib/core/config/app_config.dart`
- `mobile/test/unit/api_client_certificate_pin_test.dart`
- `mobile/test/unit/app_config_test.dart`

Change size:

```text
5 files changed, 285 insertions(+), 10 deletions(-)
```

## Behavior Covered

- `ApiClient` verifies configured certificate pins before GET, JSON POST, and
  multipart upload requests.
- Certificate pin verification requires HTTPS when pins are configured.
- Missing native verifier plugin or pin mismatch fails before network request
  dispatch.
- Release `AppConfig` rejects missing or malformed `sha256/<base64>` pins.
- Development remains compatible with local HTTP and optional test tokens.

## Validation

```text
flutter test test/unit/app_config_test.dart test/unit/api_client_certificate_pin_test.dart: 11 passed
flutter analyze changed Dart files: No issues found
dart format --output=none --set-exit-if-changed changed Dart files: passed
detect-secrets-hook changed files: passed
git diff --cached --check: passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
```

## Security / Leakage Review

- No generated OCR artifacts, raw OCR text, provider payloads, request headers,
  image bytes, `.env`, or secret values were added.
- Test certificate pins are deterministic placeholder strings, not real pins.
- This slice is intentionally fail-closed until the Android/iOS native
  certificate verifier branch lands.

## Remaining Mobile Security Slice

The native/platform half of `PR 4` remains separate because the original mobile
commit also includes camera permission and Flutter UI work. The next branch
should cover Android/iOS native certificate pin verification, cleartext/ATS
guards, and release artifact verification without mixing supplement flow UI
changes.
