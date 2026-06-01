# Lemon Aid Mobile

Minimal Flutter client for the Nutrition backend demo flow.

## Scope

- Grant required consent buckets through `/api/v1/me/privacy/consents`.
- Load `/api/v1/dashboard/summary`.
- Upload supplement label images to `/api/v1/supplements/analyze`.
- Submit reviewed OCR text to `/api/v1/supplements/analyses/{analysis_id}/ocr-text`.
- Register only user-confirmed supplement data through `/api/v1/supplements`.

OCR output is shown as review-required candidate data. The client does not intentionally persist raw images or raw OCR text.

## Run

```sh
flutter pub get
flutter run --dart-define=LEMON_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

For Android emulator, use:

```sh
flutter run --dart-define=LEMON_API_BASE_URL=http://10.0.2.2:8000/api/v1
```

If the backend runs with JWT auth enabled, also pass:

```sh
--dart-define=LEMON_API_TOKEN=<dev-token>
```

Local backend development can run without `LEMON_API_TOKEN` when `AUTH_MODE=disabled`.

## Xcode With The Same Flutter UIUX

The Android Studio app UIUX is implemented in Flutter under `mobile/lib`.
To see the same UIUX in Xcode, open and run the Flutter iOS workspace:

```text
mobile/ios/Runner.xcworkspace
```

The old native SwiftUI smoke shell under `mobile/Lemon-Aid-ios` has been
removed because it rendered a different app and confused Xcode simulator
testing. The only supported iOS target for UIUX parity is the Flutter Runner
workspace above.

Before opening Xcode, prepare the ignored Flutter iOS build settings:

```sh
LEMON_API_BASE_URL=http://127.0.0.1:8000/api/v1 \
  ./scripts/prepare-ios-flutter-uiux-xcode.sh
```

Then open `ios/Runner.xcworkspace` in Xcode and run the `Runner` scheme on an
`iPhone 17 Pro` iOS 26.5 simulator. `LEMON_API_BASE_URL`, `LEMON_API_TOKEN`,
`LEMON_DEV_GATEWAY_TOKEN`, and `LEMON_CERTIFICATE_PINS` are compile-time
Flutter values, so pass them through `flutter build`/`flutter run`
`--dart-define` values or the helper script. Xcode scheme runtime environment
variables alone do not update `String.fromEnvironment` values in Dart.

Flutter screens are Dart-rendered, so Xcode's SwiftUI Canvas Preview is not the
authoritative preview surface for this app. Use Xcode `Product > Run` or
`flutter run` with the `Runner` scheme and verify the UI in Simulator.

If Xcode shows a scheme other than `Runner`, close that window and open
`mobile/ios/Runner.xcworkspace`.

### iOS Simulator With Mac Camera

The iOS Simulator does not behave like a physical iPhone camera device. Apple
documents that Simulator is not a replacement for every hardware feature, and
camera-specific verification should still be confirmed on real hardware before
release. For local OCR smoke, this project provides a debug-only localhost
bridge that lets the Flutter iOS Simulator shutter button capture one JPEG from
the host Mac camera. The bridge also streams debug preview frames so the
simulator camera screen can show the label alignment before capture.

List the Mac camera devices:

```sh
./scripts/dev_mac_camera_bridge.py --list-devices
```

Start the bridge with the MacBook camera, usually device `0`:

```sh
./scripts/dev_mac_camera_bridge.py \
  --listen-host 127.0.0.1 \
  --listen-port 8755 \
  --device 0
```

Then build or run the Flutter Runner with the bridge URL:

```sh
LEMON_API_BASE_URL=http://127.0.0.1:8000/api/v1 \
LEMON_MAC_CAMERA_BRIDGE_URL=http://127.0.0.1:8755 \
  ./scripts/prepare-ios-flutter-uiux-xcode.sh
```

With that dart define present, the iOS Simulator camera screen polls
`/frame.jpg` from the localhost bridge and renders the latest Mac camera frame
behind the existing guide overlay. Pressing the shutter stores the visible frame
or falls back to `/capture`, then continues into the same preview and OCR
analysis flow as a normal captured image. The bridge is disabled in release
builds and must not be used as a substitute for final physical iPhone camera
testing.

Official references:

- Flutter iOS setup: <https://docs.flutter.dev/platform-integration/ios/setup>
- Flutter iOS build and release: <https://docs.flutter.dev/deployment/ios>
- Flutter camera plugin: <https://pub.dev/packages/camera>
- Apple simulator run workflow: <https://developer.apple.com/documentation/xcode/running-your-app-in-simulator-or-on-a-device>
- Apple Simulator versus hardware: <https://developer.apple.com/documentation/xcode/testing-in-simulator-versus-testing-on-hardware-devices>

## Device Smoke

The local device smoke completed on 2026-05-16 with Flutter `3.41.9`.

### iOS Simulator

Use `DEVELOPER_DIR` on this machine because global `xcode-select` still points
to CommandLineTools.

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  flutter build ios --simulator --debug \
  --dart-define=LEMON_API_BASE_URL=http://127.0.0.1:8000/api/v1

DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  flutter run -d C98610F7-7B4C-4202-A18C-498F43A20AA0 \
  --dart-define=LEMON_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

### Android Emulator

The configured local AVD is `lemon_pixel_8_api_36`. In this Codex environment,
launching through `flutter emulators --launch` did not leave a running emulator
process, so use the emulator binary directly.

```sh
/opt/homebrew/share/android-commandlinetools/emulator/emulator \
  -avd lemon_pixel_8_api_36 -no-window -no-audio -no-snapshot -no-metrics

flutter build apk --debug \
  --dart-define=LEMON_API_BASE_URL=http://10.0.2.2:8000/api/v1

flutter run -d emulator-5554 \
  --dart-define=LEMON_API_BASE_URL=http://10.0.2.2:8000/api/v1
```

Android emulator backend calls need both:

- `LEMON_API_BASE_URL=http://10.0.2.2:8000/api/v1`
- backend `ALLOWED_HOSTS` including `10.0.2.2`

`android/app/src/debug/AndroidManifest.xml` allows cleartext traffic for local
debug smoke only. Do not copy that allowance into release configuration.

### Backend Smoke

For local backend-connected smoke, run the Nutrition backend on host port
`8000` with `AUTH_MODE=disabled` and the Android emulator host allowed:

```sh
ALLOWED_HOSTS='["localhost","127.0.0.1","testserver","10.0.2.2"]' \
  ../.venv/bin/python -m uvicorn src.main:app \
  --app-dir Nutrition-backend \
  --host 127.0.0.1 \
  --port 8000
```

The completed smoke covered:

- consent state read and consent grant
- dashboard summary
- image intake through `/api/v1/supplements/analyze`
- manual OCR text parse
- user-confirmed supplement registration
- dashboard refresh with `registered_count=1`

If using the stock `postgres:16` Docker image, apply migrations through
`0004_create_p1_supplement_health` for this mobile flow. Full Alembic `head`
currently requires a pgvector-enabled PostgreSQL image.

## Verify

```sh
dart format --output=none --set-exit-if-changed .
flutter analyze
flutter test
```
