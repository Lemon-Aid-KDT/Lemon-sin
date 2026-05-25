# Android OCR + YOLO + Ollama Smoke Plan

This plan keeps the backend-connected Flutter app as the source of truth and
uses the teammate UIUX branch only for visual assets and camera interaction
patterns.

## Implementation Boundary

- Keep `LEMON_API_BASE_URL`, `LEMON_API_TOKEN`, `LEMON_DEV_GATEWAY_TOKEN`, and
  `LEMON_CERTIFICATE_PINS`.
- Keep `BackendLemonAidRepository.analyzeSupplementImage()`.
- Keep `POST /api/v1/supplements/analyze` with multipart field `image` and
  form fields `client_request_id` and `ocr_provider`.
- Keep supplement review, confirmation, registration, and local LLM explanation
  flow.
- Do not import source-branch mock analysis screens or source auth services.

## Android Studio Run

1. Start the local backend on the host Mac at `127.0.0.1:8000`.
2. Open the Android Studio AVD Manager and boot the target emulator.
3. From `mobile/`, run the dev flavor against the Android emulator host alias:

```bash
flutter run -d emulator-5554 --flavor dev \
  --dart-define=LEMON_API_BASE_URL=http://10.0.2.2:8000/api/v1
```

`10.0.2.2` is the Android Emulator alias for the host loopback interface.
The current app has Android product flavors, so `--flavor dev` is required for
debug smoke runs.

## Provider Scenarios

- `configured`: validates the backend-selected OCR provider.
- `paddleocr`: validates local PaddleOCR routing.
- `google_vision`: validates Google Vision routing; credential failures should
  be treated separately from mobile endpoint failures.
- `clova`: validates CLOVA OCR routing.

YOLO ROI and Ollama vision/parser behavior remain backend runtime settings.
The mobile app only reports the pipeline metadata returned by the backend and
does not create separate YOLO or Ollama endpoints.

## Expected Evidence

- The app reaches the 5-tab shell.
- The camera tab can use gallery fallback or direct AVD camera capture.
- Tapping `분석하기` calls the current repository flow, not a mock result route.
- Preview metadata shows actual OCR provider, YOLO ROI state, parser state, and
  clean retention state.
- Registration remains blocked until user review confirms usable ingredients.

## References

- Flutter CLI: https://docs.flutter.dev/reference/flutter-cli
- Android Emulator networking: https://developer.android.com/studio/run/emulator-networking-address
- Flutter camera plugin: https://pub.dev/packages/camera
