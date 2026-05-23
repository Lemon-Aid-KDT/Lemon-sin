# 2026-05-23 Mobile Preview Metadata Summary Result

## Scope

Confirmation 화면에서 backend가 내려주는 sanitized `image_quality_report`와
`provider_observations`를 compact하게 보여주는 UI slice를 추가했다. 이
branch는 OCR 원문이나 provider payload를 보여주지 않고, 사용자가 확인해야 할
품질/처리 상태만 표시한다.

## Official References

- Flutter widget testing:
  <https://docs.flutter.dev/cookbook/testing/widget/introduction>
- Flutter `Card`:
  <https://api.flutter.dev/flutter/material/Card-class.html>
- Flutter `Text`:
  <https://api.flutter.dev/flutter/widgets/Text-class.html>

## Branches

- Base branch: `feat/mobile-capture-quality-metrics`
- Export branch: `feat/mobile-preview-metadata-summary`
- Preserved remote: `origin/feat/mobile-preview-metadata-summary`
- Base commit: `b44a6a3c feat(mobile): 촬영 품질 metric을 확장`
- Patch commit: `77f9c279 feat(mobile): OCR 품질 요약을 표시`

## Changed Files

- `mobile/lib/features/supplements/supplement_flow_screen.dart`
- `mobile/test/supplement_flow_preview_metadata_test.dart`

Change size:

```text
2 files changed, 370 insertions(+)
```

## Behavior Covered

- Preview card now shows `OCR 품질 요약` when image-quality or provider
  observation metadata exists.
- Image quality summary displays only bounded fields:
  status, image size, ROI count, and mapped issue labels.
- Provider observation summary displays only bounded fields:
  provider, stage, status, latency, text/parser booleans, warning code summary,
  and raw-storage boolean status.
- UI text explicitly indicates `원문 저장 없음` when both raw-storage flags are
  false.
- Widget test verifies the summary appears and raw-key strings such as
  `raw_ocr_text`, `provider_payload`, and `authorization` do not appear.

## Validation

```text
flutter test test/supplement_flow_preview_metadata_test.dart: 1 passed
flutter test preview metadata + image picker permission + capture quality + supplement models: 10 passed
flutter analyze changed Dart files: No issues found
dart format --output=none --set-exit-if-changed changed Dart files: passed
detect-secrets-hook changed files: passed
git diff --cached --check: passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
```

## Security / Leakage Review

- No generated OCR artifacts, raw OCR text, provider payloads, request headers,
  image bytes, `.env`, or secret values were added.
- The UI consumes only already-sanitized model fields and does not read files,
  images, provider responses, headers, or environment variables.
- The widget test uses synthetic in-memory JSON and no image fixtures.
- The screen intentionally avoids rendering raw keys or raw provider payload
  fields even when provider observation metadata exists.

## Remaining Mobile Work

The mobile confirmation path now has provider observation parsing, permission
feedback, local capture quality warnings, and sanitized metadata summary UI. A
future slice can improve copy/visual density after product review, but the raw
OCR/provider-payload privacy boundary is now represented in the UI test.
