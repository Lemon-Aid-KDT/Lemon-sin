# Lemon Aid Mobile Frontend Guide

This guide documents the backend-connected mobile app on
`feat/db-internal-learning-pipeline` after selectively importing UIUX assets
from `origin/feat/mobile-dashboard-redesign`.

## Runtime Contract

- Package name: `lemon_aid_mobile`
- State model: `ChangeNotifier` through `AppController`
- API base config: `LEMON_API_BASE_URL`, which must end with `/api/v1`
- Optional local token config: `LEMON_API_TOKEN`; never embed it in release builds
- Optional local gateway config: `LEMON_DEV_GATEWAY_TOKEN`; never embed it in release builds
- Release pin config: `LEMON_CERTIFICATE_PINS`

For Android emulator testing against a local backend, use:

```bash
flutter run --flavor dev \
  --dart-define=LEMON_API_BASE_URL=http://10.0.2.2:8000/api/v1
```

For a physical device, use an HTTPS gateway or tunnel that points to the same
backend `/api/v1` routes. Do not put ngrok basic-auth credentials or API tokens
in `--dart-define` values that might be reused for release builds.

## Device Camera and ngrok Smoke

The supplement capture screen now uses the Flutter `camera` plugin for direct
device preview and capture. The gallery path still uses `image_picker`, so iOS
simulator testing can use gallery images when a hardware camera is unavailable.

Use this local-only flow when a physical phone needs to call a backend running on
the developer machine:

1. Start the backend on `127.0.0.1:8000`.
2. Start the local Host-rewriting gateway:

```bash
export LEMON_DEV_GATEWAY_TOKEN=<random-local-smoke-token>
python backend/scripts/dev_mobile_ngrok_backend_gateway.py \
  --listen-port 8010 \
  --backend-url http://127.0.0.1:8000 \
  --require-token
```

3. Start a fresh public tunnel to the gateway:

```bash
ngrok http 8010 --web-addr 127.0.0.1:4041
```

4. Run Flutter against the HTTPS tunnel:

```bash
flutter run -d <ios-device-id> \
  --dart-define=LEMON_API_BASE_URL=https://<ngrok-host>/api/v1 \
  --dart-define=LEMON_DEV_GATEWAY_TOKEN=${LEMON_DEV_GATEWAY_TOKEN}
```

For Android physical devices, add the dev flavor:

```bash
flutter run -d <android-device-id> --flavor dev \
  --dart-define=LEMON_API_BASE_URL=https://<ngrok-host>/api/v1 \
  --dart-define=LEMON_DEV_GATEWAY_TOKEN=${LEMON_DEV_GATEWAY_TOKEN}
```

The gateway rewrites the public ngrok `Host` header to the local backend host so
the backend `ALLOWED_HOSTS` policy does not need to allow arbitrary ngrok hosts.
It must only be used for local development smoke tests. The gateway token is
checked at the gateway and is not forwarded to the backend.

iOS Simulator can validate the app build and gallery-based OCR flow, but direct
camera capture requires a physical iPhone with Developer Mode enabled. Android
emulator local backend smoke should keep using `10.0.2.2`.

Before a physical-device smoke run, use the repo preflight from the project
root:

```bash
python backend/scripts/check_mobile_ngrok_camera_readiness.py \
  --require-gateway \
  --require-ngrok \
  --require-physical-device
```

This check fails closed when the backend, token-gated gateway, matching ngrok
tunnel, or physical device is missing. It prints only sanitized counts and
status flags.

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
