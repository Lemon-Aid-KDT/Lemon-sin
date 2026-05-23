# 2026-05-23 Mobile Provider Observations Export Result

## Scope

Flutter OCR preview UI를 바로 옮기면 화면 파일만 700줄 이상이라 PR 크기
위험이 크다. 따라서 먼저 backend가 내려주는 sanitized
`provider_observations`를 모바일 모델이 읽을 수 있게 하는 작은 stacked
branch를 만들었다.

이 branch는 raw OCR text나 provider payload를 들고 오지 않는다. UI는 이후
branch에서 이 bounded metadata만 사용해 OCR provider 상태와 품질 경고를
표시할 수 있다.

## Official References

- Dart named parameters:
  <https://dart.dev/language/functions#named-parameters>
- Dart collections:
  <https://dart.dev/language/collections>
- Flutter testing overview:
  <https://docs.flutter.dev/testing/overview>

## Branches

- Base branch: `fix/mobile-certificate-pin-wiring`
- Export branch: `feat/mobile-provider-observations`
- Preserved remote: `origin/feat/mobile-provider-observations`
- Base commit: `420da8ed fix(mobile): 인증서 pin 설정을 연결`
- Patch commit: `9966ec7c feat(mobile): OCR 관측 모델을 추가`

## Changed Files

- `mobile/lib/features/supplements/supplement_models.dart`
- `mobile/test/unit/supplement_models_test.dart`

Change size:

```text
2 files changed, 93 insertions(+)
```

## Behavior Covered

- `SupplementAnalysisPreview` now parses optional `provider_observations`.
- `SupplementOcrProviderObservation` stores only bounded fields:
  provider, stage, status, latency, boolean parse/text flags, warning codes,
  error code, and raw-storage booleans.
- Unit test verifies `raw_ocr_text_stored=false` and
  `raw_provider_payload_stored=false` are preserved.
- No UI screen changes are included in this branch.

## Validation

```text
flutter test test/unit/supplement_models_test.dart: 2 passed
flutter analyze changed Dart files: No issues found
dart format --output=none --set-exit-if-changed changed Dart files: passed
detect-secrets-hook changed files: passed
git diff --cached --check: passed
check_ocr_artifact_privacy --check-tracked-generated: ocr_artifact_privacy_ok files=0
```

## Security / Leakage Review

- No generated OCR artifacts, raw OCR text, provider raw payloads, request
  headers, image bytes, `.env`, or secret values were added.
- The model accepts only sanitized observation fields and does not include OCR
  content, image paths, provider request/response bodies, or headers.
- `flutter test` resolved packages in the temporary worktree, but no generated
  dependency/build files were staged.

## Remaining Mobile Work

The next mobile slice can add OCR preview UI and image quality warnings on top
of this branch. Keep that UI branch separate because `supplement_flow_screen.dart`
is substantially larger than this model-only branch.
