# 2026-05-23 Mobile Certificate Pin Wiring Result

## Scope

`PR 4 - Mobile Release Security` stacked branches에서 발견한 corrective
security gap을 별도 branch로 분리했다. 기존 Dart `ApiClient`와 native
certificate verifier는 준비되어 있었지만, 실제 app entrypoint
`mobile/lib/main.dart`가 `config.certificatePins`를 `ApiClient`에 넘기지 않아
release certificate pin gate가 runtime path에서 비활성화될 수 있었다.

이번 branch는 기존 release/camera permission stack 위에서 실제 wiring만
수정하고, 같은 회귀가 다시 생기지 않도록 static unit test를 추가한다.

## Official References

- Dart named parameters:
  <https://dart.dev/language/functions#named-parameters>
- Flutter testing overview:
  <https://docs.flutter.dev/testing/overview>

## Branches

- Base branch: `feat/mobile-camera-permission-gate`
- Export branch: `fix/mobile-certificate-pin-wiring`
- Preserved remote: `origin/fix/mobile-certificate-pin-wiring`
- Base commit: `cb3b1c76 feat(mobile): camera 권한 gate를 추가`
- Patch commit: `420da8ed fix(mobile): 인증서 pin 설정을 연결`

## Changed Files

- `mobile/lib/main.dart`
- `mobile/test/unit/release_security_config_test.dart`

Change size:

```text
2 files changed, 7 insertions(+)
```

## Behavior Covered

- App entrypoint now passes `certificatePins: config.certificatePins` into
  `ApiClient`.
- Static release security test asserts the wiring remains present in
  `mobile/lib/main.dart`.
- The fix does not change certificate values, platform verifier logic, OCR
  upload behavior, provider routing, or generated artifact handling.

## Validation

```text
flutter test release_security_config/app_config/api_client_certificate_pin: 22 passed
flutter analyze changed Dart files: No issues found
dart format --output=none --set-exit-if-changed changed Dart files: passed
detect-secrets-hook changed files: passed
git diff --cached --check: passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
```

## Security / Leakage Review

- The previous gap was security-relevant: certificate pin validation was
  implemented but not connected to the production app entrypoint.
- No generated OCR artifacts, raw OCR text, provider payloads, request headers,
  image bytes, `.env`, or secret values were added.
- The static test reads source text only and does not read environment files,
  built artifacts, images, OCR outputs, provider payloads, request headers, or
  local private paths.
- This branch adds no external network calls and performs no OCR provider
  transmission.

## Remaining Mobile Work

The Flutter OCR preview UI and quality-warning flow are still separate. Start
that slice only after this wiring fix is preserved, because the UI slice should
build on the security stack with the certificate pin path actually active.
