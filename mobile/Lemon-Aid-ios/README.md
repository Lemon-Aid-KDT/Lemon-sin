# Lemon Aid Native iOS

이 폴더는 Xcode에서 직접 실행하는 Lemon Aid SwiftUI native smoke 앱이다.
Flutter 앱을 대체하지 않고, OCR/YOLO/Ollama backend endpoint 연결을 iOS
native shell에서 빠르게 검증하기 위한 작업 공간이다.

## Xcode 실행 기준

Xcode에서 다음 프로젝트를 연다.

```text
mobile/Lemon-Aid-ios/Lemon-Aid.xcodeproj
```

- Scheme: `Lemon-Aid`
- Bundle ID: `yeongs.Lemon-Aid`
- 기본 local API base: `http://127.0.0.1:8000/api/v1`

Xcode Scheme Environment Variables에는 필요한 값만 로컬로 주입한다.

```text
LEMON_API_BASE_URL=http://127.0.0.1:8000/api/v1
LEMON_API_TOKEN=<optional local jwt>
LEMON_DEV_GATEWAY_TOKEN=<optional local gateway token>
```

`.env`, ngrok token, gateway token, provider credential, raw OCR text,
provider raw payload, image bytes, object URI는 앱 bundle이나 문서에 넣지
않는다.

## Endpoint 계약

Swift 앱은 Flutter 앱과 같은 단일 이미지 분석 endpoint를 호출한다.

- Method: `POST`
- Path: `/api/v1/supplements/analyze`
- Multipart file field: `image`
- Form fields:
  - `client_request_id`
  - `ocr_provider`
- Debug provider values:
  - `configured`
  - `paddleocr`
  - `google_vision`
  - `clova`

YOLO ROI와 Ollama parser/vision assist는 모바일 앱이 fake endpoint를
만들지 않고 backend runtime 설정을 따른다.

## 검증 명령

```bash
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
xcodebuild \
  -project mobile/Lemon-Aid-ios/Lemon-Aid.xcodeproj \
  -scheme Lemon-Aid \
  -configuration Debug \
  -sdk iphonesimulator \
  -destination 'platform=iOS Simulator,id=7B2E1A72-B3C9-4102-8E3C-0009CCBFB4FB' \
  -derivedDataPath /private/tmp/lemon-aid-ios-xcode-derived \
  CODE_SIGNING_ALLOWED=NO \
  build
```

## 공식 참고

- SwiftUI app structure: <https://developer.apple.com/documentation/swiftui>
- Xcode command-line tools: <https://developer.apple.com/documentation/xcode/xcode-command-line-tool-reference>
- PhotosPicker: <https://developer.apple.com/documentation/photokit/photospicker>
- URLRequest: <https://developer.apple.com/documentation/foundation/urlrequest>
- NSCameraUsageDescription: <https://developer.apple.com/documentation/bundleresources/information-property-list/nscamerausagedescription>
- NSAllowsLocalNetworking: <https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity/nsallowslocalnetworking>
