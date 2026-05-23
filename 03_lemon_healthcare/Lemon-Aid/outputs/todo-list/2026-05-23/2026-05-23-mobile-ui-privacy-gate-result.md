# 2026-05-23 Mobile UI Privacy Gate Result

## Summary

- Current integration branch: `feat/ocr-quality-gates`
- Previous export branch: `origin/test/mobile-ui-privacy-gate`
- Previous static-gate-only commit: `73e1e112 test(mobile): OCR UI privacy gate를 추가`
- Scope: remove public raw OCR text UI and add a static regression gate

This update removes the public Flutter UI path that let a user paste or edit raw
OCR text for an existing supplement preview. The manual parse method, repository
endpoint wiring, and mobile request model were removed together so the product
UI stays on the image-upload, sanitized-preview, user-confirmed-registration
flow.

The static scanner remains as a bounded regression gate for mobile OCR UI code.
It blocks high-risk raw OCR/provider markers in `mobile/lib/**/*.dart`,
including `raw_ocr_text`, `ocr_text`, `provider_payload`,
`raw_provider_payload`, `request_headers`, `image_bytes`, manual parse
identifiers, and OCR/provider secret-style keys.

The scanner intentionally allows the safe boolean flags
`raw_ocr_text_stored` and `raw_provider_payload_stored`, because the backend
returns these as redacted storage-status metadata. It also does not block the
normal API `Authorization` header or API error redaction marker list, which
belong to auth and sanitizer plumbing rather than OCR UI payload exposure.

## Files

- `mobile/lib/app_controller.dart`
- `mobile/lib/features/supplements/supplement_flow_screen.dart`
- `mobile/lib/features/supplements/supplement_models.dart`
- `mobile/lib/features/supplements/supplement_repository.dart`
- `mobile/test/widget_test.dart`
- `mobile/test/supplement_flow_image_picker_test.dart`
- `mobile/test/unit/app_controller_error_privacy_test.dart`
- `backend/scripts/check_mobile_ocr_ui_privacy.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_mobile_ocr_ui_privacy.py`

## Official References

- Flutter `TextField`: <https://api.flutter.dev/flutter/material/TextField-class.html>
- Flutter `FilledButton`: <https://api.flutter.dev/flutter/material/FilledButton-class.html>
- Python `argparse`: <https://docs.python.org/3/library/argparse.html>
- Python `pathlib`: <https://docs.python.org/3/library/pathlib.html>
- Python `re`: <https://docs.python.org/3/library/re.html>

## Validation

```text
pytest test_check_mobile_ocr_ui_privacy.py: 8 passed
check_mobile_ocr_ui_privacy.py --project-root .:
  mobile_ocr_ui_privacy_ok files=18
```

## Security Review

- No generated OCR artifacts were committed.
- No raw OCR text, provider payload, request headers, image bytes, `.env`, or
  secret values were printed or stored.
- CLI findings are bounded to path, line, code, and a fixed detail string; the
  scanner does not echo matched source content.
- The public supplement screen no longer contains the raw OCR text review card,
  text controller, manual parse button, or client-to-backend `/ocr-text` wiring.
- The existing artifact privacy gate still reports no tracked generated OCR
  evaluation artifact.

## Limitations

- This is a static source gate, not a runtime proof. It catches high-risk raw
  OCR/provider key literals and identifiers before review.
- It scans mobile runtime source under `mobile/lib` by default. Tests and docs
  may contain forbidden strings as negative assertions, so they remain outside
  the default runtime scan.
- Backend API response leakage remains covered by the product API smoke helper,
  mobile API error privacy gate, and artifact privacy gates.
