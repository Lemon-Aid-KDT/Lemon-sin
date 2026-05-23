# 2026-05-23 Mobile API Error Privacy Gate Result

## Scope

P1 품질 개선 플랜의 raw OCR/provider payload 비노출 원칙을 mobile error path까지
확장했다. 기존 mobile client는 backend error `detail` 문자열이나 raw response
body, unexpected exception `toString()`을 그대로 `ErrorPanel` message에 보존할
수 있었다.

## Official References

- Dart JSON decoding tutorial:
  <https://dart.dev/learn/tutorial/data-and-json>
- Flutter error handling:
  <https://docs.flutter.dev/testing/errors>
- Dart `Object.toString`:
  <https://api.flutter.dev/flutter/dart-core/Object/toString.html>

## Changed Files

- `mobile/lib/core/api/api_error.dart`
- `mobile/lib/app_controller.dart`
- `mobile/test/unit/api_error_test.dart`
- `mobile/test/unit/app_controller_error_privacy_test.dart`
- `outputs/todo-list/2026-05-22/2026-05-22-p1-quality-implementation-plan.md`
- `outputs/todo-list/2026-05-22/2026-05-22-ocr-quality-gates-implementation-progress.md`
- `outputs/todo-list/2026-05-23/2026-05-23-mobile-api-error-privacy-gate-result.md`

## Result

- `ApiError.fromBody()` no longer uses the raw HTTP response body as a
  user-facing message.
- Backend `detail.message` and string `detail` are displayed only when short and
  free of sensitive markers.
- Sensitive markers such as raw OCR keys, provider payload keys, request header
  keys, bearer/authorization text, secrets/API keys, and local absolute path
  markers are replaced with `Request failed.`
- Unsafe backend `detail.code` values are dropped.
- `AppController` no longer stores arbitrary `error.toString()` or
  `FormatException.message` in UI state.

## Validation

```text
dart format --output=none --set-exit-if-changed changed Dart files: passed
flutter test api_error/app_controller_error_privacy/widget: 9 passed
flutter analyze changed Dart files: No issues found
```

```text
markdownlint changed docs: passed
detect-secrets changed docs/code: passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
git diff --check: passed
```

## Security Review

- This closes a UI leakage path where backend/proxy error bodies could echo raw
  OCR text, provider payload snippets, request headers, local file paths, or
  secret-looking values.
- Consent-required errors still preserve stable code, safe message, and required
  consent names.
- Raw OCR text, provider payload, request headers, image bytes, `.env`, secret
  values, and real credentials were not added.
