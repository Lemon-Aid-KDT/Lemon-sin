# 09. Mobile UIUX Selective Import and Simulator Diagnostics

- Date: 2026-05-25
- Branch: `feat/db-internal-learning-pipeline`
- Source UIUX branch:
  `origin/feat/mobile-dashboard-redesign@e170a187d784d65accfe2c392eaa2e65dffe6540`
- Scope: iOS Simulator app mismatch diagnosis, selective UIUX import boundary,
  and OCR/YOLO/Ollama mobile live-test plan

## 0. Official References Checked

| Area | Source | Use in this plan |
| --- | --- | --- |
| Flutter CLI | https://docs.flutter.dev/reference/flutter-cli | `flutter devices` and `flutter run` are the supported command-line entry points for local device/simulator runs. |
| Flutter camera plugin | https://pub.dev/packages/camera | Current direct-camera flow should stay on the `camera` plugin rather than a fake mobile endpoint. |
| Android emulator loopback | https://developer.android.com/studio/run/emulator-networking-address | Android emulator local backend smoke uses `10.0.2.2`. |

## 1. Current Finding

The iPhone 17 Pro Simulator and iPhone 17 Simulator showed different Lemon-Aid
apps because they had different bundle IDs installed.

| Device | Installed app observed | Bundle ID | Meaning |
| --- | --- | --- | --- |
| iPhone 17 Pro Simulator | UIUX branch-style camera/review app | `com.lemonaid.lemonAid` | A stale or source-branch app was still installed. |
| iPhone 17 Simulator | Current backend-connected app | `com.example.lemonAidMobile` | Current branch app was installed. |
| iPhone 17 Pro Simulator after `flutter run` from this branch | Current dashboard/capture flow | `com.example.lemonAidMobile` | The UI difference disappeared after installing the current branch app. |

This was not a runtime rendering difference inside one app. It was an app
identity/install-state mismatch across simulators.

Use these checks before comparing screens:

```bash
flutter devices --machine
xcrun simctl get_app_container <simulator-udid> com.example.lemonAidMobile app
xcrun simctl listapps <simulator-udid> | rg "com.example.lemonAidMobile|com.lemonaid.lemonAid|CFBundle"
```

To install the current branch app on a specific simulator:

```bash
cd mobile
flutter run -d <simulator-udid> --no-resident \
  --dart-define=LEMON_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Only if the stale source-branch simulator app should be removed, uninstall that
separate bundle from the simulator:

```bash
xcrun simctl uninstall <simulator-udid> com.lemonaid.lemonAid
```

This deletes simulator-local app data for that bundle, so run it only when the
old app state is no longer needed.

## 2. Team Collaboration Constraints Applied

The archived team documents under
`/Users/yeong/99_me/00_github/03_lemon_healthcare/_archive/yeong-Lemon-Aid/docs/team-collaboration`
were rechecked before this plan.

Rules that matter for this work:

- Keep work on `feat/db-internal-learning-pipeline` and push the same branch.
- Use Conventional Commits with a useful `Why` body.
- Do not use `git commit --no-verify`.
- Do not use force push without lease.
- Do not commit `.env`, secrets, raw OCR/provider payloads, image bytes, object
  URIs, or transient ngrok URLs.
- Keep feature-to-`develop` integration as Squash and `develop`-to-`main` as a
  merge commit.
- Keep PRs small enough to review; split asset import, UI flow, and backend
  contract changes if the diff grows.

## 3. Why Whole-Branch Import Is Unsafe

`origin/feat/mobile-dashboard-redesign` is a useful UIUX reference, but its
`mobile/` tree is not a safe merge target for this branch.

| Source branch area | Risk if imported as-is | Current branch decision |
| --- | --- | --- |
| `mobile/lib/services/api_client.dart` | Replaces current `LEMON_API_BASE_URL` and backend route contract. | Do not import. Keep `mobile/lib/core/api`. |
| `mobile/lib/utils/router.dart` and `main_shell.dart` | Moves app to `go_router` shell architecture. | Do not import. Keep `MaterialApp` + `ChangeNotifier`. |
| `mobile/lib/screens/auth/*` and OAuth services | Adds auth assumptions that are not aligned with current backend smoke flow. | Do not import as-is. |
| `mobile/pubspec.yaml` | Adds `.env` as a Flutter asset and many unused deps. | Keep current dependency set; never list `.env` as an asset. |
| Android package move to `com.lemonaid.lemon_aid` | Changes release guardrails and explains the simulator mismatch. | Keep current package until a coordinated app-ID migration is planned. |
| iOS project replacement/deletions | Deletes current iOS project files and can break simulator/device builds. | Do not import. |
| Test deletions | Removes current backend-connected mobile tests. | Do not import. |
| Asset directories | Reusable and already compatible with current UI. | Safe to keep selectively. |
| Camera/dashboard visual language | Useful design reference but tied to source architecture. | Adapt small pieces into current screens only. |

## 4. Selective Import Boundary

Already accepted reusable UIUX assets:

- `mobile/assets/animations/`
- `mobile/assets/app_icon/`
- `mobile/assets/design_system/`
- `mobile/assets/fonts/`
- `mobile/assets/icons/`
- `mobile/assets/illustrations/`
- `mobile/assets/mascot/`

Preserved current backend-connected architecture:

- `mobile/lib/core/api`
- `mobile/lib/core/config`
- `mobile/lib/app.dart`
- `mobile/lib/app_controller.dart`
- `mobile/lib/features/consent`
- `mobile/lib/features/dashboard`
- `mobile/lib/features/supplements`
- `mobile/test/unit`
- `mobile/test/widget`
- current Android signing scaffold, including `android/key.properties.example`
- current iOS project files

The current supplement flow already contains the important endpoint alignment:

- `BackendLemonAidRepository.analyzeSupplementImage`
- `POST /api/v1/supplements/analyze`
- multipart field `image`
- form fields `client_request_id` and `ocr_provider`
- debug-only provider choices:
  `configured`, `paddleocr`, `google_vision`, `clova`

YOLO ROI and Ollama vision assist stay backend runtime settings:

- `ENABLE_VISION_CLASSIFIER`
- `ENABLE_MULTIMODAL_LLM`
- `/supplements/recommendations/explain` for local LLM explanation support

The mobile app should not invent separate YOLO or Ollama endpoints.

## 5. Safe UIUX Adaptation Plan

### 5.1 Short Term

1. Keep the current branch bundle/package identity for this PR.
2. Use the simulator bundle identity checks above before screenshot comparison.
3. Keep the source branch installed app separate unless a simulator reset is
   explicitly needed.
4. Continue using the current full-screen black capture flow because it is
   already wired to `AppController.analyzeImage(image.path, ocrProvider: ...)`.
5. Use the source branch camera screen only as a visual reference for future
   polish: guide frame density, captured preview controls, and central shutter
   layout.

### 5.2 Next Code Change Candidates

These are safe candidates because they preserve the backend contract:

- tighten the current capture preview spacing to match the source branch visual
  rhythm;
- reuse source-style action labels only where the current flow already has the
  same action: retake, gallery, analyze;
- add widget tests around the debug OCR provider selector and analysis call;
- add a lightweight dashboard visual pass that still renders live
  `DashboardSummary`;
- add screenshots to the runbook after physical-device smoke succeeds.

Avoid these changes in this branch unless a separate architecture PR is planned:

- replacing the app with `go_router`;
- adopting Riverpod/Dio auth services;
- adding `.env` asset loading;
- renaming bundle IDs or Android package IDs;
- replacing iOS or Android project trees;
- deleting existing unit/widget tests.

## 6. Live Test Plan

### 6.1 iOS Simulator

Purpose: verify install identity, dashboard contract, gallery OCR flow, and
review/registration UI. Direct camera is not available in iOS Simulator.

```bash
cd mobile
flutter run -d <ios-simulator-udid> --no-resident \
  --dart-define=LEMON_API_BASE_URL=http://127.0.0.1:8010/api/v1 \
  --dart-define=LEMON_DEV_GATEWAY_TOKEN=<local-smoke-token>
```

Expected checks:

- current app bundle is `com.example.lemonAidMobile`;
- dashboard loads through `/api/v1/me/privacy/consents`;
- supplement capture opens;
- gallery image can be selected;
- debug OCR provider selector forwards the selected provider;
- analysis enters the existing review/registration steps.

### 6.2 Android Emulator

Purpose: verify host loopback and backend contract without a public tunnel.

```bash
cd mobile
flutter run -d emulator-5554 --flavor dev \
  --dart-define=LEMON_API_BASE_URL=http://10.0.2.2:8000/api/v1
```

Expected checks:

- dashboard launch contract succeeds;
- supplement gallery flow can call `POST /api/v1/supplements/analyze`;
- no release token is embedded.

### 6.3 Physical iPhone

Purpose: verify real camera capture and full OCR/YOLO/Ollama backend behavior.

Preflight:

```bash
python backend/scripts/check_mobile_ngrok_camera_readiness.py \
  --require-gateway \
  --require-ngrok \
  --require-physical-device
```

Run:

```bash
cd mobile
flutter run -d <ios-device-id> \
  --dart-define=LEMON_API_BASE_URL=https://<ngrok-host>/api/v1 \
  --dart-define=LEMON_DEV_GATEWAY_TOKEN=<local-smoke-token>
```

Manual path:

1. Open supplement capture.
2. Select OCR provider.
3. Capture the full supplement label.
4. Analyze.
5. Review OCR-derived fields before registration.
6. Register the supplement.
7. Request the local LLM explanation through the existing explanation route
   when the backend has local LLM enabled.

Do not commit the public tunnel URL, gateway token, raw OCR text, provider raw
payload, image bytes, or object storage URI.

## 7. Verification Gates

For docs-only updates:

```bash
git diff --check
detect-secrets scan
```

For mobile code updates:

```bash
cd mobile
flutter pub get
dart format --output=none --set-exit-if-changed lib test
flutter analyze
flutter test
```

For backend endpoint or provider-selector changes:

```bash
PYTHONPATH=Nutrition-backend:.. /private/tmp/lemon-p1-quality-venv/bin/python \
  -m pytest Nutrition-backend/tests/unit -q --no-cov
```

Run the narrower supplement API tests first if only the analyze contract is
touched.

## 8. Open Follow-Ups

- Decide whether the product app ID should eventually become the source branch
  ID. That must be a coordinated release task, not a selective UI import.
- After the pasted ngrok credential is rotated, repeat the physical-device smoke
  with a fresh local gateway token and no credential values in logs.
- If a source-style dashboard pass is needed, implement it against live
  `DashboardSummary` data first and only then add static polish.
