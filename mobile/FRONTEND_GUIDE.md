# Lemon Aid Mobile Frontend Guide

This guide documents the backend-connected mobile app on
`feat/db-internal-learning-pipeline` after selectively importing UIUX assets
from `origin/feat/mobile-dashboard-redesign`.

## Runtime Contract

- Package name: `lemon_aid_mobile`
- State model: `ChangeNotifier` through `AppController`
- API base config: `LEMON_API_BASE_URL`, which must end with `/api/v1`
- Optional local token config: `LEMON_API_TOKEN`; never embed it in release builds
- Release pin config: `LEMON_CERTIFICATE_PINS`

For Android emulator testing against a local backend, use:

```bash
flutter run --dart-define=LEMON_API_BASE_URL=http://10.0.2.2:8000/api/v1
```

For a physical device, use an HTTPS gateway or tunnel that points to the same
backend `/api/v1` routes.

## Imported UIUX Assets

The app imports reusable assets only:

- `assets/animations/`
- `assets/app_icon/`
- `assets/design_system/`
- `assets/fonts/`
- `assets/icons/`
- `assets/illustrations/`
- `assets/mascot/`

The source branch router, auth services, Riverpod providers, and replacement
Android/iOS project files were not imported.

## OCR Test Flow

The supplement flow uses the existing backend path:

- `POST /api/v1/supplements/analyze`
- multipart field: `image`
- form fields: `client_request_id`, `ocr_provider`

Debug builds expose these OCR provider selectors:

- `configured`
- `paddleocr`
- `google_vision`
- `clova`

YOLO ROI detection and Ollama vision assist remain backend runtime settings.
The Flutter app does not invent separate YOLO or Ollama endpoints.
