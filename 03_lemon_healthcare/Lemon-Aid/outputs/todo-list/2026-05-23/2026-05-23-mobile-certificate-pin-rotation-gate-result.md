# 2026-05-23 Mobile Certificate Pin Rotation Gate Result

## Scope

P1 품질 개선 플랜의 mobile release safety 항목 중 certificate pin 운영 리스크를
한 단계 더 닫았다. 기존 구현은 request 전 native TLS handshake와 pin mismatch
fail-closed는 수행했지만, release config가 단일 pin도 허용해 backup/rotation
pin 없이 배포될 수 있었다.

## Official References

- Dart `String.fromEnvironment`:
  <https://api.dart.dev/dart-core/String/String.fromEnvironment.html>
- Flutter build modes:
  <https://docs.flutter.dev/testing/build-modes>
- Flutter `kReleaseMode`:
  <https://api.flutter.dev/flutter/foundation/kReleaseMode-constant.html>

## Changed Files

- `mobile/lib/core/config/app_config.dart`
- `mobile/test/unit/app_config_test.dart`
- `outputs/todo-list/2026-05-22/2026-05-22-p1-quality-implementation-plan.md`
- `outputs/todo-list/2026-05-22/2026-05-22-ocr-quality-gates-implementation-progress.md`
- `outputs/todo-list/2026-05-23/2026-05-23-mobile-certificate-pin-rotation-gate-result.md`

## Result

- Release `AppConfig` now requires at least two unique
  `LEMON_CERTIFICATE_PINS` values.
- A single valid pin fails release config validation.
- Duplicate valid pins fail release config validation.
- The existing `sha256/<base64>` format validation still runs before the unique
  count gate.
- Local/debug mode remains unchanged.

## Validation

```text
dart format --output=none --set-exit-if-changed changed Dart files: passed
flutter test app_config/api_client_certificate_pin/release_security_config: 23 passed
```

```text
flutter analyze changed Dart files: No issues found
markdownlint changed docs: passed
detect-secrets changed docs/code: passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
git diff --check: passed
```

## Security Review

- This reduces the chance of shipping a release artifact that cannot survive
  certificate renewal or emergency pin rotation.
- No real pin value, certificate material, request header, OCR raw text,
  provider payload, image bytes, `.env`, or secret value was added.
- Test pins remain deterministic placeholders and are not production
  credentials.
- Native verifier still hashes certificate DER bytes. SPKI pinning remains an
  explicit hardening follow-up because platform-specific public-key DER
  canonicalization needs separate verification.
