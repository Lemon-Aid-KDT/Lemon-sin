# 2026-05-22 P1 기능 품질 개선 상세 구현 플랜

## 1. 목표

P1의 목적은 OCR 모델을 바로 교체하기 전에 입력 품질, provider routing, layout regression, release safety를 먼저 안정화하는 것이다. real OCR 실패는 OCR 엔진 자체, 입력 이미지 품질, provider routing, layout parser, 모바일 release 설정이 함께 얽히므로 네 축을 작은 PR로 분리한다.

## 2. 공식 문서 근거

| 영역 | 공식 문서 | 적용 판단 |
|---|---|---|
| Flutter image picker | https://pub.dev/packages/image_picker | `pickImage`, `retrieveLostData`, Android Photo Picker/iOS PHPicker 동작을 기준으로 카메라/갤러리 플로우를 검증한다. |
| Flutter image decode | https://api.flutter.dev/flutter/dart-ui/instantiateImageCodec.html, https://api.flutter.dev/flutter/dart-ui/Image/toByteData.html, https://api.flutter.dev/flutter/dart-ui/ImageByteFormat.html | 모바일 선택 직후 local preflight는 파일 header와 축소 decode된 `rawRgba` luminance proxy만 사용하고 raw image를 저장하지 않는다. |
| Android Photo Picker | https://developer.android.com/training/data-storage/shared/photo-picker | Android 13 이상 갤러리 선택은 플랫폼 Photo Picker 흐름을 고려한다. |
| Android camera permission/feature | https://developer.android.com/reference/android/Manifest.permission, https://developer.android.com/guide/topics/manifest/uses-feature-element | `CAMERA` 권한과 camera feature filtering을 release checklist에 포함한다. |
| Android runtime permissions | https://developer.android.com/guide/topics/permissions/requesting | Android 6+ dangerous permission은 런타임 요청과 denied 처리 경로가 필요하므로 camera picker 호출 전에 앱에서 먼저 요청한다. |
| Flutter platform channels | https://docs.flutter.dev/platform-integration/platform-channels | Android/iOS native runtime permission 결과를 Flutter UI에 전달하기 위해 `MethodChannel`을 사용한다. |
| Apple camera/photo permission | https://developer.apple.com/documentation/bundleresources/information-property-list/nscamerausagedescription, https://developer.apple.com/documentation/BundleResources/Information-Property-List/NSPhotoLibraryUsageDescription | iOS `Info.plist` purpose string이 없으면 camera/photo 접근이 불가하므로 release gate로 검사한다. |
| Apple AVFoundation authorization | https://developer.apple.com/documentation/avfoundation/capture_setup/requesting_authorization_to_capture_and_save_media, https://developer.apple.com/documentation/avfoundation/avcapturedevice/1624613-authorizationstatus | iOS camera 사용 전 `AVCaptureDevice.authorizationStatus(for: .video)`를 확인하고 `.notDetermined`일 때 `requestAccess(for:)`로 prompt를 띄운다. |
| Dart TLS/certificate context | https://api.dart.dev/dart-io/HttpClient/HttpClient.html | release client hardening은 `SecurityContext`/`HttpClient` 계층 또는 플랫폼 network security config와 연결한다. |
| Dart bad certificate callback | https://api.dart.dev/dart-io/HttpClient/badCertificateCallback.html | `badCertificateCallback`은 인증 실패 certificate에서 호출되는 API라, 정상 chain에 대한 SPKI pin enforcement 대체재로 과대해석하지 않는다. |
| Android network security config | https://developer.android.com/training/articles/security-config | Android pin-set과 debug override를 release safety 검증 항목으로 둔다. |
| PaddleOCR 3.x | https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html | local PaddleOCR 기본값과 `use_textline_orientation`/model/device 옵션을 provider routing 비교 기준으로 사용한다. |
| Google Cloud Vision OCR | https://cloud.google.com/vision/docs/ocr | 외부 OCR은 `DOCUMENT_TEXT_DETECTION` 계열이며, 이미지 전송 opt-in과 credential gate가 필요하다. |
| NAVER CLOVA OCR | https://api.ncloud-docs.com/docs/en/ai-application-service-ocr, https://api.ncloud-docs.com/docs/en/ai-application-service-ocr-ocr | CLOVA는 API Gateway invoke URL과 `X-OCR-SECRET` 기반이므로 `ALLOW_EXTERNAL_OCR`와 credential gate 뒤에 둔다. |
| OpenCV Laplacian/thresholding | https://docs.opencv.org/4.x/d5/db5/tutorial_laplace_operator.html, https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html | blur/glare/contrast는 Laplacian/thresholding 계열의 deterministic proxy로 시작하되, 성능 claim은 repo fixture 평가 전 금지한다. |

## 3. PR 분할

| 순서 | 추천 branch | 범위 | 이유 |
|---:|---|---|---|
| 1 | `feat/ocr-quality-gates` | capture quality report 연결, 모바일 안내 문구, normalized layout DTO 회귀 복구, P1 계획 문서 | PR #3과 충돌이 적고 즉시 UX 개선이 가능하다. |
| 2 | `refactor/ocr-provider-routing` | PaddleOCR 기본 유지, Google/CLOVA external gate, provider metrics schema | PR #3의 CLOVA primary 변경이 base에 들어온 뒤 진행해야 충돌이 작다. |
| 3 | `test/ocr-layout-regression` | normalized DTO fixture 기반 `OCRResult -> LabelLayout` 회귀 확대 | PR #3의 `OCRResult.pages` DTO가 선행되어야 한다. |
| 4 | `test/mobile-release-safety` | HTTPS, certificate pin, release token, iOS/Android permission flow 검증 | 모바일 build/device gate가 필요해 별도 PR로 분리한다. |

## 4. Capture Quality Gate 상세 플랜

### 4.1 구현 내용

- backend가 OCR provider 호출 전에 redacted `ImageQualityReport`를 생성한다.
- report는 raw image, OCR text, provider payload를 저장하지 않는다.
- reason code는 다음 입력 품질 문제를 안정적으로 표현한다.
  - `blurred_text`
  - `glare_or_reflection`
  - `skewed_label`
  - `cropped_label`
  - `low_resolution`
  - 기존 `low_light`, `low_contrast`, `too_small_text`, `partial_table`와 호환 유지
- preview 응답은 기존 모바일 계약을 재사용한다.
  - `image_quality_report`
  - `analysis_scope`
  - `action_required`
  - `missing_required_sections`
  - `image_role`
  - `source_type`
- 모바일은 기존 `_ImageRiskActionPanel`에서 reason code를 사람이 바로 행동할 수 있는 안내 문구로 바꿔 보여준다.

### 4.2 현재 적용한 1차 변경

- `src/services/supplement_image_quality.py` 추가
  - 해상도, edge variance, luminance contrast, bright pixel ratio, border ink ratio, aspect ratio를 계산한다.
  - 수치 metric만 저장한다.
- `analyze_supplement_image()`에서 OCR 전에 image quality report를 만들고 preview snapshot에 저장한다.
- `supplement_analysis_run_to_preview()`가 snapshot의 image quality contract를 response로 복원한다.
- parser가 OCR parse 이후에도 image quality contract를 보존한다.
- Flutter preview panel이 reason code별 한국어 촬영 안내를 표시한다.

### 4.3 검증 기준

- 단위 테스트:
  - 낮은 해상도/흐림/반사/낮은 대비 fixture
  - 고해상도 sharp label-like fixture
  - border crop/aspect skew fixture
- API preview:
  - `image_quality_report.status`
  - `action_required`
  - `missing_required_sections`
  - raw OCR text 미포함
- 모바일:
  - warning panel이 reason code와 촬영 안내를 표시
  - 기존 selected image preview가 깨지지 않음

## 5. OCR Provider Routing 상세 플랜

### 5.1 정책

- 기본 provider는 local PaddleOCR이다.
- Google Vision과 CLOVA는 둘 다 외부 이미지 전송이므로 다음 조건을 모두 만족할 때만 활성화한다.
  - `ALLOW_EXTERNAL_OCR=true`
  - provider-specific credential 존재
  - production validation 통과
- request selector가 `paddleocr`이면 외부 provider fallback을 타지 않는다.
- request selector가 `configured`이면 settings-driven chain만 사용한다.

### 5.2 metrics schema

provider별 observation은 같은 field를 사용한다.

| 필드 | 의미 |
|---|---|
| `provider` | `paddleocr_local`, `google_vision_document`, `clova_ocr` |
| `stage` | `primary`, `multimodal_fallback`, `secondary_fallback`, `verification` |
| `status` | `completed`, `error`, `skipped` |
| `latency_ms` | provider call wall-clock |
| `text_non_empty` | OCR text가 비어 있지 않은지 |
| `parser_success` | structured parser 성공 여부 |
| `error_code` | bounded provider or parser error |
| `warning_codes` | empty text, low confidence, external disabled 등 |
| `raw_ocr_text_stored` | 항상 false |
| `raw_provider_payload_stored` | 항상 false |

### 5.3 현재 적용한 1차 변경

- runtime preview schema에 `provider_observations`를 추가했다.
- `analyze_supplement_image()`의 OCR provider 호출 지점에서 `latency_ms`, `status`, `text_non_empty`, `error_code`, `warning_codes`, `parser_success`를 수집한다.
- primary OCR, multimodal fallback, secondary fallback 호출은 같은 observation schema를 사용한다.
- observation은 raw OCR text, provider raw payload, image bytes를 저장하지 않고 bounded metadata만 snapshot/response에 남긴다.
- parser가 snapshot을 갱신해도 `provider_observations`가 보존된다.
- Flutter model도 `provider_observations`를 파싱하되, UI에는 원문/secret을 표시하지 않는다.

### 5.4 PR #3 이후 작업

- `SupplementOCRProviderSelector`에 CLOVA selector가 들어간 base에서 작업한다.
- CLOVA primary selector와 `OCR_PRIMARY_PROVIDER=clova` production validation을 base에 병합한 뒤 runtime routing과 충돌 없이 맞춘다.
- fallback 중복 호출 방지 테스트를 CLOVA primary path까지 확장한다.
- external provider가 gate 없이 호출되지 않는 것을 production validation과 unit test로 계속 증명한다.

## 6. Layout Parser Regression 상세 플랜

### 6.1 정책

- fixture는 provider raw JSON이 아니라 normalized DTO를 사용한다.
- 목적은 OCR vendor별 payload 변화가 아니라 `OCRResult -> LabelLayout` 계약을 고정하는 것이다.

### 6.2 테스트 케이스

| 케이스 | 기대 |
|---|---|
| bounding box 누락 | `ocr_words_missing_bounding_box`, layout degradation |
| 좌표 scale mismatch | `ocr_word_coordinate_scale_mismatch` |
| 빈 pages/words | `layout_unavailable` 또는 `layout_words_unavailable` |
| 한글 anchor variation | `영양 기능정보`, `영양·기능정보`, `섭취 시 주의사항` 모두 section anchor |
| table row x-gap | ingredient/dosage cell 분리 |
| row y-band noise | 같은 행의 작은 y 오차를 한 row로 그룹화 |

### 6.3 현재 적용한 1차 변경

- 기본 checkout에서 이미 `layout_parser.py`가 참조하던 `OCRResult.pages`, `OCRWord`, `OCRPage`, `OCRBoundingPoly` DTO가 실제 `src/ocr/base.py`에 없어 unit 수집이 깨졌다.
- `src/models/schemas/label_layout.py`와 `src/models/schemas/supplement_layout_context.py`를 추가해 `LabelLayout`, `LabelSection`, `LabelCell`, `LabelBox`, `SupplementLayoutContextV1` 계약을 복구했다.
- `tests/unit/parsing/test_layout_parser.py`를 추가해 빈 pages, missing bbox, coordinate scale mismatch, 한글 anchor variation을 normalized DTO 기준으로 검증한다.
- `tests/fixtures/supplement_labels/manifest.json`과 synthetic `ko_dense_table_001.snapshot_v2.json` fixture를 추가해 snapshot schema test의 누락 fixture를 복구했다. 이 fixture는 raw OCR 원문이 아니라 bounded schema 계약 검증용 synthetic 데이터다.

## 7. Mobile Release Safety 상세 플랜

### 7.1 검사 항목

| 항목 | 기준 |
|---|---|
| `LEMON_API_BASE_URL` | release에서 HTTPS 필수, `/api/v1` suffix 필수 |
| release token | `LEMON_API_TOKEN` embedding 금지 |
| certificate pin | release에서 `LEMON_CERTIFICATE_PINS` 필수 |
| Android camera | `CAMERA` permission과 camera feature filtering 확인 |
| Android gallery | Photo Picker 동작 확인, broad media permission 최소화 |
| iOS camera/photo | `NSCameraUsageDescription`, `NSPhotoLibraryUsageDescription` 확인 |
| dev URL leakage | release artifact에 localhost/ngrok/dev URL이 없는지 검색 |

### 7.2 현 상태

- `AppConfig`는 release HTTPS, token 금지, certificate pin 필수 테스트를 이미 갖고 있다.
- 현재 branch의 certificate pin 검증은 release config와 artifact 확인에 더해, API request 직전 Flutter `MethodChannel`로 Android/iOS native TLS handshake를 수행해 server certificate chain 중 하나가 설정 pin과 일치하는지 확인한다.
- pin 값은 `sha256/<base64>` 형식의 certificate DER SHA-256 fingerprint로 검증한다. SPKI pinning은 아직 구현하지 않았으므로, production 적용 전 실제 인증서 fingerprint와 rotation/backup pin 운영 절차를 별도로 확정해야 한다.
- 실제 `flutter build apk --release --flavor prod`를 호출했을 때 `LEMON_ANDROID_APPLICATION_ID`가 production reverse-domain 값으로 설정되지 않으면 Gradle이 fail-closed로 막는 것을 확인했다.
- Android `MainActivity`를 `com.example` 패키지 밖인 `com.lemonaid.mobile.MainActivity`로 이동했고, release APK의 package/activity가 AAPT에서 `com.lemonaid.mobile`로 확인된다.
- Android manifest 정적 테스트를 추가해 `CAMERA` 권한은 선언하되 `android.hardware.camera`는 `required=false`로 둔다. broad gallery 권한(`READ_EXTERNAL_STORAGE`, `READ_MEDIA_IMAGES`)은 선언하지 않음을 검증한다.
- iOS `Info.plist` 정적 테스트를 추가해 `NSCameraUsageDescription`, `NSPhotoLibraryUsageDescription`, ATS arbitrary loads false를 검증한다.
- `mobile/scripts/verify_release_artifact.py`를 추가해 built APK/AAB에서 expected HTTPS base URL/certificate pin 문자열 존재와 local/dev URL/token sentinel 부재를 post-build로 검증한다.
- `image_picker`의 `PlatformException.code`를 기준으로 camera/photo 권한 거부와 제한 상태를 구분해, 사용자가 설정 허용 또는 갤러리 재시도 경로를 바로 알 수 있게 했다.
- Android는 `MainActivity`의 `MethodChannel("com.lemonaid.mobile/camera_permission")`로 `Manifest.permission.CAMERA`를 먼저 요청하고, denied이면 `image_picker` camera intent를 열지 않고 앱 내부 SnackBar를 표시한다.
- iOS는 `AppDelegate`의 동일 `MethodChannel`에서 `AVCaptureDevice.authorizationStatus(for: .video)`와 `requestAccess(for: .video)`를 처리해, denied/restricted 상태를 Flutter UX 메시지로 일관되게 연결한다.

## 8. 즉시 다음 작업

1. 이번 branch의 capture quality gate slice를 검증한다.
2. PR #3 merge/base 조정이 끝나면 provider routing과 layout regression을 별도 branch로 진행한다.
3. mobile release safety는 실제 emulator/device 또는 release build 가능한 환경에서 별도 테스트 PR로 진행한다.

## 9. 완료 기준

- backend preview가 OCR 이전 image quality report를 항상 생성한다.
- 모바일이 이미지 선택 직후 local preflight로 resolution/angle 계열 경고를 즉시 표시하고, backend preview의 blur, angle, crop, glare, resolution 경고도 같은 안내 문구로 보여준다.
- local preflight에서 문제가 감지되면 `분석하기` 전에 확인 dialog를 띄워 OCR provider 호출 전 UX gate를 강제한다.
- provider routing은 외부 OCR gate 없이 이미지를 전송하지 않는다.
- production은 process-local upload limiter만으로 부팅하지 않고 `RATE_LIMIT_EXTERNAL_ENFORCEMENT=true`를 요구한다.
- layout parser는 provider raw payload가 아니라 normalized DTO fixture로 회귀를 잡는다.
- release build에서 HTTPS, certificate pin, no embedded token, camera/gallery permission이 검증된다.
- certificate pin은 request-path native TLS handshake로 fail-closed 검증한다. 다만 현재 구현은 certificate DER fingerprint 방식이며, SPKI pinning과 production pin rotation 검증은 별도 hardening 항목으로 남긴다.

## 10. 2026-05-22 검증 결과

```bash
PYTHONPATH=backend/Nutrition-backend:backend \
OCR_PRIMARY_PROVIDER=paddleocr ENABLE_LOCAL_OCR=true \
ENABLE_CLOVA_OCR=false ALLOW_EXTERNAL_OCR=false \
/private/tmp/lemon-p1-quality-venv/bin/python -m pytest \
  backend/Nutrition-backend/tests/unit -q --no-cov
# 582 passed

/private/tmp/lemon-p1-quality-venv/bin/python -m black --check <changed-python-files>
# pass

/private/tmp/lemon-p1-quality-venv/bin/python -m ruff check --ignore RUF001 <changed-python-files>
# pass

git diff --check
# pass

flutter analyze
# No issues found

flutter test
# 35 passed

flutter build apk --release --flavor prod \
  --dart-define=LEMON_API_BASE_URL=https://api.example.com/api/v1 \
  --dart-define=LEMON_CERTIFICATE_PINS=sha256/<primary-pin>,sha256/<backup-pin>
# expected fail-closed: Set -PLEMON_ANDROID_APPLICATION_ID ...

flutter build apk --release --flavor prod \
  -PLEMON_ANDROID_APPLICATION_ID=com.lemonaid.mobile \
  --dart-define=LEMON_API_BASE_URL=https://api.example.com/api/v1 \
  --dart-define=LEMON_CERTIFICATE_PINS=sha256/<primary-pin>,sha256/<backup-pin>
# Built build/app/outputs/flutter-apk/app-prod-release.apk (50.5MB)
# 2026-05-22 13:09 KST 재검증: ignored 임시 key.properties + /private/tmp test keystore로 build 통과 후 둘 다 삭제

python3 mobile/scripts/verify_release_artifact.py \
  mobile/build/app/outputs/flutter-apk/app-prod-release.apk \
  --expect https://api.example.com/api/v1 \
  --expect sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
  --expect sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB= \
  --forbid must-not-ship \
  --forbid local-token \
  --forbid dev-token \
  --forbid test-token \
  --forbid changeit
# release_artifact_ok=.../app-prod-release.apk

/opt/homebrew/share/android-commandlinetools/build-tools/36.0.0/aapt \
  dump badging mobile/build/app/outputs/flutter-apk/app-prod-release.apk
# package: name='com.lemonaid.mobile'
# launchable-activity: name='com.lemonaid.mobile.MainActivity'
# uses-feature-not-required: name='android.hardware.camera'

/opt/homebrew/share/android-commandlinetools/build-tools/36.0.0/aapt \
  dump permissions mobile/build/app/outputs/flutter-apk/app-prod-release.apk
# CAMERA, INTERNET, dynamic receiver permission only; no broad gallery read permission

flutter build ios --simulator --debug --no-codesign
# Built build/ios/iphonesimulator/Runner.app

flutter test integration_test/supplement_ios_camera_permission_test.dart \
  -d 71FB0384-0C75-4CC4-925A-2A6598CAE89A
# All tests passed with a mocked camera permission channel denial

flutter test integration_test/certificate_pin_live_test.dart \
  -d 71FB0384-0C75-4CC4-925A-2A6598CAE89A \
  --dart-define=RUN_CERTIFICATE_PIN_LIVE_TEST=true \
  --dart-define=CERTIFICATE_PIN_TEST_HOST=example.com \
  --dart-define=CERTIFICATE_PIN_TEST_VALID_PIN=sha256/GvYnxsKsmS48kQJDj0Z8TCONMRIyWsfPkAPXf3Xv/7o=
# iOS simulator: success pin matched, mismatch pin rejected

flutter test integration_test/certificate_pin_live_test.dart \
  -d emulator-5554 \
  --flavor dev \
  --dart-define=RUN_CERTIFICATE_PIN_LIVE_TEST=true \
  --dart-define=CERTIFICATE_PIN_TEST_HOST=example.com \
  --dart-define=CERTIFICATE_PIN_TEST_VALID_PIN=sha256/GvYnxsKsmS48kQJDj0Z8TCONMRIyWsfPkAPXf3Xv/7o=
# Android emulator: success pin matched, mismatch pin rejected

/Applications/Xcode.app/Contents/Developer/usr/bin/simctl install booted \
  build/ios/iphonesimulator/Runner.app

/Applications/Xcode.app/Contents/Developer/usr/bin/simctl launch booted \
  com.example.lemonAidMobile
# com.example.lemonAidMobile: <pid>

flutter build apk --debug --flavor dev \
  --dart-define=LEMON_API_BASE_URL=http://10.0.2.2:8001/api/v1
# Built build/app/outputs/flutter-apk/app-dev-debug.apk
```

주의: 기본 로컬 `.env`에는 CLOVA Phase 0용 값이 남아 있어, 현재 checkout에서 전체 unit을 재현할 때는 위처럼 `ENABLE_CLOVA_OCR=false`와 `ALLOW_EXTERNAL_OCR=false`를 명시해야 한다. 이 branch의 구현은 raw OCR text, provider raw payload, image bytes를 새 snapshot/report에 저장하지 않는다.

현재 연결된 Flutter 대상:

```bash
flutter devices
# iPhone 17 Pro simulator, macOS, Chrome

flutter emulators
# apple_ios_simulator, lemon_pixel_8_api_36, plusultra_pixel_8_api_36
```

실기기/에뮬레이터 권한 플로우는 2026-05-22 기준으로 다음 범위까지 확인했다.

iOS simulator:

- `Info.plist`에 `NSCameraUsageDescription`, `NSPhotoLibraryUsageDescription`가 존재한다.
- `AppDelegate`가 `MethodChannel("com.lemonaid.mobile/camera_permission")`로 `AVCaptureDevice.authorizationStatus(for: .video)`와 `requestAccess(for: .video)`를 호출하도록 보강했다.
- `flutter build ios --simulator --debug --no-codesign`로 Swift compile과 simulator app build가 통과했다.
- Supplement tab 진입 후 camera action에서 `NSCameraUsageDescription` 문구가 들어간 camera permission dialog가 뜨는 것을 확인했다.
- permission 허용 후 Simulator camera unavailable fallback과 gallery CTA가 표시되는 것을 확인했다.
- gallery CTA를 통해 picker 선택 후 preview 화면과 `분석하기` CTA까지 도달했다.
- 이 Xcode 26.3 `simctl privacy` 명령은 `camera` service를 지원하지 않는다. 실제 iOS 물리 기기는 연결되지 않았으므로 OS-level denied/retry는 아직 물리 기기에서 확인해야 한다.
- `flutter test integration_test/supplement_ios_camera_permission_test.dart -d 71FB0384-0C75-4CC4-925A-2A6598CAE89A`는 mocked `MethodChannel` denied 응답으로 통과해, Flutter UX가 denied status를 retry guidance SnackBar로 연결함을 확인했다.
- evidence screenshots:
  - `/private/tmp/lemon-aid-ios-camera-permission.png`
  - `/private/tmp/lemon-aid-ios-camera-fallback.png`
  - `/private/tmp/lemon-aid-ios-gallery-preview.png`
  - `/private/tmp/lemon-aid-ios-native-bridge-dashboard.png`

Android emulator:

- `lemon_pixel_8_api_36` emulator가 `emulator-5554`로 부팅 완료됨을 확인했다.
- 기존 설치본은 backend host mismatch로 consent gate가 막혀, 권한 플로우만 분리 검증하기 위해 로컬 stub API를 `http://10.0.2.2:8001/api/v1`로 사용했다. stub은 consent/dashboard JSON만 반환하고 OCR 원문, 이미지, provider payload를 저장하지 않는다.
- `flutter build apk --debug --dart-define=LEMON_API_BASE_URL=http://10.0.2.2:8001/api/v1` 실행 후 multi-flavor 프로젝트 특성상 Flutter CLI는 output discovery 실패를 반환했지만, `build/app/outputs/flutter-apk/app-dev-debug.apk`가 생성되어 `adb install -r`로 설치했다.
- dev 앱에서 consent gate 통과, camera unavailable fallback, Android Photo Picker, gallery 선택 후 preview 화면과 `분석하기` CTA까지 도달했다.
- Android Photo Picker 화면은 "This app can only access the photos you select" 문구가 표시되어 broad gallery permission 없이 선택형 접근을 사용하는 것을 확인했다.
- Android runtime camera permission prompt와 denied retry UX를 `app-dev-debug.apk` 실제 설치본에서 확인했다.
  - `flutter build apk --debug --flavor dev --dart-define=LEMON_API_BASE_URL=http://10.0.2.2:8001/api/v1`
  - `adb install -r build/app/outputs/flutter-apk/app-dev-debug.apk`
  - `adb shell pm revoke com.example.lemon_aid_mobile.dev android.permission.CAMERA`
  - `adb shell pm set-permission-flags com.example.lemon_aid_mobile.dev android.permission.CAMERA user-set user-fixed`
  - denied 재시도 시 camera intent가 열리지 않고 앱 내부 SnackBar가 표시됨을 확인했다.
- evidence screenshots:
  - `/private/tmp/lemon-aid-android-dev-dashboard.png`
  - `/private/tmp/lemon-aid-android-camera-permission-or-sheet.png`
  - `/private/tmp/lemon-aid-android-gallery-picker.png`
  - `/private/tmp/lemon-aid-android-gallery-preview.png`
  - `/private/tmp/lemon-aid-android-methodchannel-permission-prompt.png`
  - `/private/tmp/lemon-aid-android-user-fixed-after-restart.png`

권한 예외 UX 단위 검증:

```bash
flutter test test/supplement_flow_image_picker_test.dart
# 8 passed

flutter analyze
# No issues found

flutter test
# 35 passed
```

- `camera_access_denied`는 "설정에서 카메라 접근 허용" 또는 "갤러리 사진으로 재시도" 안내를 표시한다.
- `photo_access_denied`는 선택 가능한 사진 허용 또는 재선택 안내를 표시한다.
- 촬영 직후 low-resolution 이미지와 선택 직후 low-resolution, blur, glare, cropped label, skewed label 이미지는 OCR 분석 전에 촬영 품질 경고를 표시한다.
- `ApiClient`는 certificate pin이 설정된 경우 GET, POST, multipart upload 모두 HTTP request 전 native verifier를 먼저 호출한다.
- Android/iOS native camera permission bridge는 정적 release safety test로 고정한다.
- iOS native bridge는 simulator build와 mocked denial integration test로 검증했다.
- Android/iOS native certificate pin bridge는 `example.com` live TLS endpoint로 success pin과 mismatch pin 경로를 모두 검증했다.

후속 hardening:

- production에서 `RATE_LIMIT_EXTERNAL_ENFORCEMENT=true`를 설정하기 전에 실제 ingress/API gateway/Redis rate-limit rule과 운영 증거를 남긴다. 현재 runtime guard는 외부 계층 종류(`RATE_LIMIT_EXTERNAL_PROVIDER`)와 non-secret 증거 참조(`RATE_LIMIT_EXTERNAL_POLICY_REF`)를 함께 요구한다.
- 실제 Android 물리 기기에서 OS camera permission allow/deny/retry 흐름을 한 번 더 확인한다.
- 실제 iOS 물리 기기에서 OS camera permission allow/deny/retry 흐름을 한 번 더 확인한다.
- production/staging API 인증서 pin과 rotation/backup pin 운영 절차를 확정한 뒤 같은 live test를 내부 endpoint로 재실행한다.
