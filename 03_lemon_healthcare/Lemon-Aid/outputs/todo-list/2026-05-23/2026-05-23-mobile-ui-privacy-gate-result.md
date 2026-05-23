# 2026-05-23 Mobile UI Privacy Gate Result

## Summary

- Base branch: `origin/feat/mobile-preview-metadata-summary`
- Export branch: `origin/test/mobile-ui-privacy-gate`
- Commit: `73e1e112 test(mobile): OCR UI privacy gate를 추가`
- Scope: mobile runtime source static privacy gate only

This branch adds a bounded static scanner for mobile OCR UI code. It blocks
high-risk raw OCR/provider markers in `mobile/lib/**/*.dart`, including
`raw_ocr_text`, `provider_payload`, `raw_provider_payload`, `request_headers`,
`image_bytes`, and OCR/provider secret-style keys.

The scanner intentionally allows the safe boolean flags
`raw_ocr_text_stored` and `raw_provider_payload_stored`, because the backend
returns these as redacted storage-status metadata. It also does not block the
normal API `Authorization` header, which belongs to general API auth rather than
OCR UI payload exposure.

## Files

- `backend/scripts/check_mobile_ocr_ui_privacy.py`
- `backend/Nutrition-backend/tests/unit/scripts/test_check_mobile_ocr_ui_privacy.py`

## Official References

- Python `argparse`: <https://docs.python.org/3/library/argparse.html>
- Python `pathlib`: <https://docs.python.org/3/library/pathlib.html>
- Python `re`: <https://docs.python.org/3/library/re.html>

## Validation

```text
pytest test_check_mobile_ocr_ui_privacy.py: 7 passed
check_mobile_ocr_ui_privacy.py --project-root /private/tmp/lemon-mobile-ui-privacy-gate:
  mobile_ocr_ui_privacy_ok files=18
black --check changed files: passed
ruff check changed files: passed
detect-secrets-hook changed files: passed
check_ocr_artifact_privacy --check-tracked-generated:
  ocr_artifact_privacy_ok files=0
git diff --check: passed
```

## Security Review

- No generated OCR artifacts were committed.
- No raw OCR text, provider payload, request headers, image bytes, `.env`, or
  secret values were printed or stored.
- CLI findings are bounded to path, line, code, and a fixed detail string; the
  scanner does not echo matched source content.
- The existing artifact privacy gate still reports no tracked generated OCR
  evaluation artifact.

## Limitations

- This is a static source gate, not a runtime proof. It catches high-risk raw
  OCR/provider key literals and identifiers before review.
- It scans mobile runtime source under `mobile/lib` by default. Tests and docs
  may contain forbidden strings as negative assertions, so they remain outside
  the default runtime scan.
- It does not forbid the existing transient `ocr_text` request field, because
  the current manual parse request uses that client-to-backend key. Backend API
  response leakage remains covered by the product API smoke helper and artifact
  privacy gates.
